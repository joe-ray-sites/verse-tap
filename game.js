// VerseTap — a daily "which book is this verse from?" game.
// Built on the Verse Drop / Tap-In USA framework: static site, no build step,
// no backend, localStorage persistence, date-seeded daily content, GitHub Pages.
(() => {
  // ───────────────────────── Config ─────────────────────────
  const ROUNDS = 5;
  const STRIP = [10, 10, 14, 16, 20];       // consecutive books on the strip, per round
  const PTS_HIT = 950;                      // bullseye
  const PTS_SPEED_MAX = 50;                 // full at <=12s, fades to 0 at 60s (bullseyes only)
  const PTS_FLOOR = 100;                    // the farthest possible miss still scores this much
  const MAX_OFF = 19;                       // farthest possible miss (20-book strip)
  const LOG_DROP = (PTS_HIT - PTS_FLOOR) / Math.log(1 + MAX_OFF);   // ≈284 per ln(1+d)
  const MAX_ROUND = PTS_HIT + PTS_SPEED_MAX;   // 1000
  const MAX_GAME = MAX_ROUND * ROUNDS;         // 5000
  const EPOCH = [2026, 8, 1];               // Sep 1 2026 = VerseTap No. 1
  const SHARE_URL = 'joe-ray-sites.github.io/verse-tap';
  const NT_START = 40;                      // Matthew's 1-based canon position

  const LOADING_PUNS = [
    'Shuffling the scrolls…',
    'Numbering the books…',
    'Dusting off Habakkuk…',
    'Finding Obadiah again…',
    'Sorting the Minor Prophets…',
  ];

  // Result-sheet subtitles: church-sign and youth-group humor, circa 1980-2010.
  // The tone gets less gentle the farther the tap lands from the answer.
  const ROUND_TERMS = {
    fast: { t: '🎯⚡ LIGHTNING TAP', subs: [
      'Jesus took the wheel. You just held on.',
      'Exposure to the Son prevents burning. You’re glowing.',
      'God answers knee-mails. That one was already read.',
      'Walking on water would have been slower.',
      'Youth-pastor speed. Somebody grab the acoustic guitar.',
      'That was so quick the ushers missed it.',
      'Honk if you love Jesus. You didn’t even need to.',
    ] },
    hit: { t: '🎯 BULLSEYE', subs: [
      'CH_ _ CH: what’s missing? Not you. Dead center.',
      'WWJD? Exactly what you just did.',
      'Somebody’s Bible isn’t dusty.',
      'Don’t wait for six strong men to take you to church. You walked right in.',
      'God works in mysterious ways. This wasn’t one of them.',
      'True love waits. You didn’t have to.',
      'Right book, first tap. No altar call needed.',
    ] },
    one: { t: '🔥 ONE BOOK OFF', subs: [
      'Side hug. Close, but the youth pastor saw daylight.',
      'Next-door neighbors. Borrow a cup of sugar and a table of contents.',
      'One pew over. Scoot down, there’s room.',
      'Love the tapper, hate the tap. One page away.',
      'Forbidden fruit creates many jams. This was a light spread.',
      'So close the choir almost stood up.',
      'Right shelf, wrong spine. God still loves you.',
    ] },
    warm: { t: '♨️ WARM', subs: [
      'God won’t give you more than you can handle. Apparently that’s about three books.',
      'Things happen on God’s time. Your tap happened a few books early.',
      'God wants you to grow through what you go through. Grow through this.',
      'You wandered off in the concordance. Follow the ushers back.',
      'Right neighborhood, wrong house. Try the fellowship hall.',
      'Close enough to hear the organ, not the sermon.',
      'Moses was a basket case too, and look how that turned out.',
    ] },
    cool: { t: '🌬️ COOL', subs: [
      'If God is your co-pilot, switch seats. He knows where this verse is.',
      'Dusty Bibles lead to dirty lives, and to taps like that.',
      'Satan called. He wants his tap back.',
      'Looking for a lifeguard? You weren’t even near the pool.',
      'That’s not a mysterious way. That’s just the wrong way.',
      'Six strong men could not have carried you closer.',
      'Somewhere a Sunday school teacher just sighed.',
    ] },
    cold: { t: '🧊 ICE COLD', subs: [
      'In case of rapture, this tap will be unmanned. It already was.',
      'Honk if you love Jesus. Text if you need a map.',
      'That wasn’t a wrong turn. That was a different zip code.',
      'CH_ _ CH: what’s missing? Any idea where you are.',
      'Jesus, take the wheel. And the phone.',
      'Don’t give up. Jonah got there eventually, by fish.',
      'God works in mysterious ways. So did that tap.',
      'Dusty Bible alert. The ushers are on their way.',
    ] },
  };

  const RATINGS = [
    { min: 5000, title: 'PERFECT CANON', quip: 'All 5,000. Five bullseyes, all at speed. Selah.' },
    { min: 4500, title: 'SCRIBE OF THE SCROLLS', quip: 'You could shelve a Bible blindfolded.' },
    { min: 4000, title: 'CANON KEEPER', quip: 'Book after book, right where it belongs.' },
    { min: 3250, title: 'STEADY NAVIGATOR', quip: 'Solid work — a couple of taps drifted down the shelf.' },
    { min: 2500, title: 'HALFWAY HOME', quip: 'Half the canon is in your pocket. Go get the rest.' },
    { min: 1500, title: 'STILL FLIPPING PAGES', quip: 'The table of contents is your friend.' },
    { min: 0,    title: 'LOST IN LEVITICUS', quip: 'It happens to everyone. Come back tomorrow.' },
  ];

  // ───────────────────────── Utilities ─────────────────────────
  const $ = (id) => document.getElementById(id);

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hashStr(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function todayKey() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  // Pure function of the local calendar date (no DST/timezone-offset drift), so
  // every player sees the identical verses on a given date.
  function puzzleNumber() {
    const d = new Date();
    const days = (Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - Date.UTC(...EPOCH)) / 86400000;
    return Math.max(1, days + 1);
  }
  function fmtPts(n) { return n.toLocaleString('en-US'); }
  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function toast(msg) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._h);
    toast._h = setTimeout(() => t.classList.remove('show'), 2200);
  }
  const bookName = (i) => BIBLE_BOOKS[i - 1];   // 1-based canon position → NIV name

  // ───────────────────────── Daily content scheduler ─────────────────────────
  // Deterministic from the date alone — same rotation design as Tap-In / Verse
  // Drop. Each tier's verses are dealt through seeded shuffle-cycles: every
  // verse appears exactly ONCE per 24-day cycle, each cycle reshuffles, and the
  // block windows guarantee a repeat gap of 19+ days even across cycle seams.
  function seededOrder(n, seedStr) {
    const idx = Array.from({ length: n }, (_, i) => i);
    const rand = mulberry32(hashStr(seedStr));
    for (let i = n - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    return idx;
  }
  function frontVerseIndex(tier, dayNum) {
    const len = VERSE_TIERS[tier].verses.length;
    const b = len % 6 === 0 ? 6 : (len % 2 === 0 ? len >> 1 : len);   // block size
    const base = seededOrder(len, `rot-${tier}-base`);
    const cycle = Math.floor(dayNum / len), pos = dayNum % len;
    const block = Math.floor(pos / b);
    return base[block * b + seededOrder(b, `rot-${tier}-${cycle}-${block}`)[pos % b]];
  }
  function buildDaily(dayNum) {
    return VERSE_TIERS.map((tier, t) => tier.verses[frontVerseIndex(t, dayNum)]);
  }
  // Practice: a spare verse per tier, reshuffled daily, never today's real verse.
  function buildPractice(dayNum) {
    return VERSE_TIERS.map((tier, t) => {
      const today = frontVerseIndex(t, dayNum);
      const ord = seededOrder(tier.verses.length, `practice-${t}-${dayNum}`);
      return tier.verses[ord.find(i => i !== today)];
    });
  }

  // ───────────────────────── Strip engine ─────────────────────────
  // A strip is N consecutive books (canon order) that contains the answer. The
  // answer's position inside the strip is seeded-random, clamped so the strip
  // never runs off either end of the canon.
  function buildRound(verse, r, seedTag) {
    const n = STRIP[r];
    const rng = mulberry32(hashStr(`${seedTag}-r${r}`));
    const loMin = Math.max(1, verse.book - n + 1);
    const loMax = Math.min(verse.book, BIBLE_BOOKS.length - n + 1);
    const lo = loMin + Math.floor(rng() * (loMax - loMin + 1));
    const books = Array.from({ length: n }, (_, i) => lo + i);
    return { verse, books, n, answerPos: verse.book - lo };
  }

  // Points for a tap `d` books from the answer: full at d=0, then a logarithmic
  // falloff per book (steep for the first few, flattening after), floored so no
  // book on any strip is ever worth zero. Independent of strip size.
  function tapPoints(d) {
    if (d === 0) return PTS_HIT;
    return Math.max(PTS_FLOOR, Math.round(PTS_HIT - LOG_DROP * Math.log(1 + d)));
  }
  function speedBonus(secs) {
    return Math.round(PTS_SPEED_MAX * Math.min(1, Math.max(0, (60 - secs) / 48)));
  }
  function squareFor(d) {
    return d === 0 ? '🎯' : d === 1 ? '🟩' : d <= 3 ? '🟨' : d <= 6 ? '🟧' : '🟥';
  }
  // Heat color for the reveal: t = 0 (the answer) → 1 (far end of the strip).
  function heatColor(t) {
    const hot = [46, 139, 87], warm = [217, 170, 60], cold = [58, 74, 99];
    const mix = (a, b, k) => a.map((v, i) => Math.round(v + (b[i] - v) * k));
    const c = t < 0.35 ? mix(hot, warm, t / 0.35) : mix(warm, cold, (t - 0.35) / 0.65);
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  }

  // ───────────────────────── Game state ─────────────────────────
  const state = {
    phase: 'loading',        // play | reveal | done
    round: 0,
    total: 0,
    results: [],             // {ref, d, pts, sq, fast}
    course: [],              // today's 5 verse entries
    practice: false,
    cur: null,               // active buildRound() output
    sel: null,               // selected canon position (1-based)
    startAt: 0,
    rng: null,               // flavor-text rng
  };
  const seedTag = () => (state.practice ? 'p' : 'd') + puzzleNumber();

  // ───────────────────────── Board rendering ─────────────────────────
  function renderRound() {
    const { verse, books, n } = state.cur;
    const card = $('verse-card');
    card.classList.remove('revealed');
    $('card-tag').textContent = '📖 THE VERSE';
    $('verse-text').textContent = verse.text;
    $('verse-ref').textContent = '';

    const strip = $('strip');
    strip.classList.remove('revealed');
    strip.innerHTML = books.map(b =>
      (b === NT_START && books[0] < NT_START ? `<div class="strip-div">✝ NEW TESTAMENT</div>` : '') +
      `<button class="bk" data-b="${b}">${esc(bookName(b))}</button>`).join('');
    $('strip-label').textContent = 'TAP THE BOOK';
    $('strip-count').textContent = `${n} BOOKS`;
    state.sel = null;
    updateConfirm();

    const roundNo = state.round + 1;
    $('round-label').textContent = state.practice ? `PRACTICE · ${roundNo}/${ROUNDS}` : `ROUND ${roundNo} OF ${ROUNDS}`;
    $('round-tier').textContent = VERSE_TIERS[state.round].label.toUpperCase();
    $('round-prompt').innerHTML = '';
    gsap.fromTo('#round-banner', { y: -16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4, ease: 'power2.out' });
    gsap.fromTo('#verse-card', { y: 14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4, ease: 'power2.out' });
    // clearProps: GSAP's inline styles would otherwise fight the .sel / reveal classes
    gsap.fromTo('#strip .bk', { y: 10, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, stagger: 0.03, ease: 'power2.out', clearProps: 'opacity,transform' });
    $('board').scrollTop = 0;
  }

  function updateConfirm() {
    $('btn-confirm').disabled = state.sel === null;
    $('btn-confirm').textContent = state.sel === null ? '🎯 Tap In' : `🎯 Tap In · ${bookName(state.sel)}`;
    $('confirm-bar').classList.toggle('show', state.phase === 'play');
  }

  $('strip').addEventListener('click', (e) => {
    const cell = e.target.closest('.bk');
    if (!cell || state.phase !== 'play') return;
    const b = +cell.dataset.b;
    $('strip').querySelectorAll('.bk.sel').forEach(el => el.classList.remove('sel'));
    if (state.sel === b) { state.sel = null; updateConfirm(); return; }   // tap again to clear
    state.sel = b;
    cell.classList.add('sel');
    gsap.fromTo(cell, { scale: 0.92 }, { scale: 1, duration: 0.25, ease: 'back.out(2.5)', clearProps: 'transform' });
    updateConfirm();
  });

  // ───────────────────────── Round flow ─────────────────────────
  function startRound() {
    state.phase = 'play';
    hidePeeks();
    state.cur = buildRound(state.course[state.round], state.round, seedTag());
    renderRound();
    state.startAt = Date.now();
  }

  function tapIn() {
    if (state.phase !== 'play' || state.sel === null) return;
    state.phase = 'reveal';
    $('confirm-bar').classList.remove('show');
    const secs = (Date.now() - state.startAt) / 1000;
    const { verse, books, n } = state.cur;
    const d = Math.abs(state.sel - verse.book);
    const hit = d === 0;
    const bonus = hit ? speedBonus(secs) : 0;
    const pts = tapPoints(d) + bonus;
    const fast = hit && bonus >= PTS_SPEED_MAX * 2 / 3;
    const sq = squareFor(d);

    // Heat-map reveal: ripple outward from the answer.
    const strip = $('strip');
    strip.classList.add('revealed');
    strip.querySelectorAll('.bk.sel').forEach(el => el.classList.remove('sel'));
    strip.querySelectorAll('.bk').forEach(el => {
      const b = +el.dataset.b, dist = Math.abs(b - verse.book);
      const you = b === state.sel, isHit = b === verse.book;
      gsap.to(el, {
        backgroundColor: heatColor(dist / (n - 1)), duration: 0.35, delay: 0.12 + dist * 0.05, ease: 'power1.out',
        onStart: () => {
          el.classList.add('heat');
          if (isHit) { el.classList.add('hit'); el.insertAdjacentHTML('beforeend', '<span class="badge">🎯 HERE</span>'); }
          else if (you) { el.classList.add('you'); el.insertAdjacentHTML('beforeend', '<span class="badge">YOU</span>'); }
        },
      });
      if (isHit) gsap.fromTo(el, { scale: 0.9 }, { scale: 1, duration: 0.45, delay: 0.15, ease: 'back.out(3)', clearProps: 'transform' });
    });
    $('verse-card').classList.add('revealed');
    $('verse-ref').textContent = `— ${verse.ref} (NIV)`;

    const prevTotal = state.total;
    state.total += pts;
    state.results.push({ ref: verse.ref, d, pts, sq, fast });

    const term = fast ? ROUND_TERMS.fast
      : hit ? ROUND_TERMS.hit
      : d === 1 ? ROUND_TERMS.one
      : d <= 3 ? ROUND_TERMS.warm
      : d <= 6 ? ROUND_TERMS.cool
      : ROUND_TERMS.cold;
    let sub = term.subs[Math.floor(state.rng() * term.subs.length)];
    const run = bullseyeRun();
    if (hit && run >= 2) sub += ` That’s ${run} in a row.`;
    $('res-term').textContent = term.t;
    $('res-term').classList.toggle('bad', d >= 4);
    $('res-sub').textContent = sub;
    $('res-dist').textContent = hit ? '0' : String(d);
    $('res-bonus').textContent = bonus ? `+${bonus}` : (hit ? '+0' : '—');
    $('res-pts').textContent = fmtPts(pts);
    $('res-ref').textContent = `📍 ${verse.ref} (NIV)`;
    $('res-context').textContent = `💡 ${verse.context}`;
    const nextLabel = state.round === ROUNDS - 1 ? 'See the Scorecard 🏆' : 'Next Verse →';
    $('btn-next').textContent = nextLabel;
    $('btn-next-mini').textContent = nextLabel;
    $('result-peek-info').textContent = `${sq}${fast ? '⚡' : ''} · ${fmtPts(pts)}${hit ? '' : ` · ${d} off`}`;
    resultMin = false;
    gsap.set('#result-peek', { y: '110%' });
    gsap.to('#result-sheet', { y: '0%', duration: 0.55, delay: 1.2, ease: 'power3.out' });
    animateScore(prevTotal, state.total);
  }

  function bullseyeRun() {
    let k = 0;
    for (let i = state.results.length - 1; i >= 0 && state.results[i].d === 0; i--) k++;
    return k;
  }

  function animateScore(from, to) {
    const obj = { v: from };
    gsap.to(obj, {
      v: to, duration: 0.8, delay: 1.2, ease: 'power1.out',
      onUpdate: () => { $('total-score').textContent = fmtPts(Math.round(obj.v)); },
    });
  }

  function nextRound() {
    gsap.to('#result-sheet', { y: '110%', duration: 0.4, ease: 'power2.in' });
    gsap.to('#result-peek', { y: '110%', duration: 0.25, ease: 'power2.in' });
    resultMin = false;
    state.round++;
    if (state.round >= ROUNDS) { finishGame(); return; }
    setTimeout(startRound, 350);
  }

  function finishGame() {
    state.phase = 'done';
    if (!state.practice) saveDailyResult();
    renderFinal();
    $('round-label').textContent = state.practice ? 'PRACTICE COMPLETE' : 'GAME COMPLETE';
    $('round-tier').textContent = '🎯 WELL DONE';
    $('round-prompt').innerHTML = state.practice
      ? 'Practice is free — the daily game is the one that counts.'
      : 'Today’s verses are tapped. New set at <b>midnight</b> — practice (☰) is always open.';
    finalMin = false;
    gsap.set('#final-peek', { y: '110%' });
    gsap.to('#final-sheet', { y: '0%', duration: 0.6, delay: 0.5, ease: 'power3.out' });
  }

  function renderFinal() {
    const rating = RATINGS.find(r => state.total >= r.min);
    const bulls = state.results.filter(r => r.d === 0).length;
    $('final-title').textContent = `${rating.title} — ${fmtPts(state.total)}`;
    $('final-quip').textContent = rating.quip;
    $('final-peek-info').textContent = `🎯 ${rating.title} · ${fmtPts(state.total)}`;

    let rows = `<tr><th>RD</th><th>VERSE</th><th>TAP</th><th style="text-align:right">PTS</th></tr>`;
    state.results.forEach((r, i) => {
      rows += `<tr><td>${i + 1}</td><td>${esc(r.ref)}</td><td class="sq">${r.sq}${r.fast ? '⚡' : ''} ${r.d === 0 ? 'bullseye' : `${r.d} off`}</td><td class="pts">${fmtPts(r.pts)}</td></tr>`;
    });
    rows += `<tr class="total"><td colspan="3">TOTAL${state.practice ? ' (practice)' : ''} · ${bulls} bullseye${bulls === 1 ? '' : 's'}</td><td class="pts">${fmtPts(state.total)} / ${fmtPts(MAX_GAME)}</td></tr>`;
    $('final-table').innerHTML = rows;

    if (state.practice) {
      $('streak-line').textContent = 'Practice games don’t count. But the verses still do.';
    } else {
      const stats = loadStats();
      $('streak-line').innerHTML =
        `🔥 Streak: ${stats.streak || 1} day${(stats.streak || 1) === 1 ? '' : 's'} · 🏆 Best: ${fmtPts(stats.best || state.total)}` +
        `<br><span id="countdown"></span>`;
      tickCountdown();
    }
  }

  function tickCountdown() {
    const el = $('countdown');
    if (!el) return;
    const now = new Date();
    const mid = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const mins = Math.max(0, Math.round((mid - now) / 60000));
    el.textContent = `⏳ VerseTap No. ${puzzleNumber() + 1} in ${Math.floor(mins / 60)}h ${mins % 60}m`;
    clearTimeout(tickCountdown._h);
    tickCountdown._h = setTimeout(tickCountdown, 30000);
  }

  // ───────────────────────── Storage ─────────────────────────
  const KEY_STATS = 'versetap-stats-v1';
  const KEY_TODAY = 'versetap-today-v1';
  const KEY_HELP = 'versetap-seen-help';
  function loadStats() {
    try { return JSON.parse(localStorage.getItem(KEY_STATS)) || {}; } catch { return {}; }
  }
  function saveDailyResult() {
    const stats = loadStats();
    const today = todayKey();
    if (stats.lastDate !== today) {
      const yest = new Date(); yest.setDate(yest.getDate() - 1);
      const yKey = `${yest.getFullYear()}-${String(yest.getMonth() + 1).padStart(2, '0')}-${String(yest.getDate()).padStart(2, '0')}`;
      stats.streak = (stats.lastDate === yKey) ? (stats.streak || 0) + 1 : 1;
      stats.maxStreak = Math.max(stats.maxStreak || 0, stats.streak);
      stats.lastDate = today;
      stats.played = (stats.played || 0) + 1;
      stats.sum = (stats.sum || 0) + state.total;
      stats.bull = (stats.bull || 0) + state.results.filter(r => r.d === 0).length;
      stats.best = Math.max(stats.best || 0, state.total);
    }
    localStorage.setItem(KEY_STATS, JSON.stringify(stats));
    localStorage.setItem(KEY_TODAY, JSON.stringify({ date: today, results: state.results, total: state.total }));
  }

  // ───────────────────────── Share ─────────────────────────
  function shareCard() {
    // scheme-less on purpose: messaging apps keep it inline-clickable text
    // instead of expanding it into a rich link-preview card
    const bulls = state.results.filter(r => r.d === 0).length;
    const lines = [
      `🎯 VerseTap No. ${puzzleNumber()}${state.practice ? ' (practice)' : ''} · NIV`,
      ...state.results.map(r => `${r.sq}${r.fast ? '⚡' : ''} ${fmtPts(r.pts)}${r.d ? ` · ${r.d} off` : ''}`),
      `TOTAL ${fmtPts(state.total)} / ${fmtPts(MAX_GAME)} · ${bulls} bullseye${bulls === 1 ? '' : 's'}`,
      SHARE_URL,
    ];
    const text = lines.join('\n');
    if (navigator.share) {
      navigator.share({ text }).catch(() => {});
    } else {
      navigator.clipboard?.writeText(text).then(
        () => toast('Score copied — go challenge the group chat 🎯'),
        () => toast('Could not copy — screenshot it like it’s 2009')
      );
    }
  }

  // ───────────────────────── Bottom sheets (Tap-In kit) ─────────────────────────
  let resultMin = false, finalMin = false;
  function minimizeResult() {
    if (state.phase !== 'reveal' || resultMin) return;
    resultMin = true;
    gsap.killTweensOf('#result-sheet');
    gsap.to('#result-sheet', { y: '110%', duration: 0.35, ease: 'power2.in' });
    gsap.fromTo('#result-peek', { y: '110%' }, { y: '0%', duration: 0.3, delay: 0.15, ease: 'power2.out' });
  }
  function restoreResult() {
    if (!resultMin) return;
    resultMin = false;
    gsap.to('#result-peek', { y: '110%', duration: 0.25, ease: 'power2.in' });
    gsap.to('#result-sheet', { y: '0%', duration: 0.4, ease: 'power3.out' });
  }
  function minimizeFinal() {
    if (state.phase !== 'done' || finalMin) return;
    finalMin = true;
    gsap.killTweensOf('#final-sheet');
    gsap.to('#final-sheet', { y: '110%', duration: 0.35, ease: 'power2.in' });
    gsap.fromTo('#final-peek', { y: '110%' }, { y: '0%', duration: 0.3, delay: 0.15, ease: 'power2.out' });
  }
  function restoreFinal() {
    if (!finalMin) return;
    finalMin = false;
    gsap.to('#final-peek', { y: '110%', duration: 0.25, ease: 'power2.in' });
    gsap.to('#final-sheet', { y: '0%', duration: 0.4, ease: 'power3.out' });
  }
  function hidePeeks() {
    resultMin = false; finalMin = false;
    gsap.set('#result-peek', { y: '110%' });
    gsap.set('#final-peek', { y: '110%' });
  }
  function enableSheetDrag(sheetId, onDismiss) {
    const sheet = $(sheetId);
    const zone = sheet.querySelector('.grip-zone');
    let startY = null, dy = 0, dragging = false;
    zone.addEventListener('pointerdown', (e) => {
      dragging = true; startY = e.clientY; dy = 0;
      try { zone.setPointerCapture(e.pointerId); } catch {}
    });
    zone.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      dy = Math.max(0, e.clientY - startY);
      gsap.set(sheet, { y: dy });
    });
    const end = () => {
      if (!dragging) return;
      dragging = false;
      if (dy > 60) onDismiss();
      else gsap.to(sheet, { y: 0, duration: 0.25, ease: 'power2.out' });
      dy = 0;
    };
    zone.addEventListener('pointerup', end);
    zone.addEventListener('pointercancel', end);
  }

  // ───────────────────────── Stats UI ─────────────────────────
  function openStats() {
    const s = loadStats();
    $('st-played').textContent = s.played || 0;
    $('st-streak').textContent = s.streak || 0;
    $('st-max').textContent = s.maxStreak || 0;
    $('st-best').textContent = s.best ? fmtPts(s.best) : '—';
    $('st-avg').textContent = s.played ? fmtPts(Math.round(s.sum / s.played)) : '—';
    $('st-bull').textContent = s.bull || 0;
    $('stats-overlay').classList.add('show');
  }

  // ───────────────────────── Practice ─────────────────────────
  function startPractice() {
    gsap.to('#final-sheet', { y: '110%', duration: 0.4, ease: 'power2.in' });
    hidePeeks();
    state.practice = true;
    state.course = buildPractice(puzzleNumber());
    state.round = 0; state.total = 0; state.results = [];
    $('total-score').textContent = '0';
    setTimeout(startRound, 400);
  }

  // ───────────────────────── Boot ─────────────────────────
  function startGame() {
    $('loading').style.display = 'none';
    clearInterval(startGame._punTimer);

    const today = todayKey();
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(KEY_TODAY)); } catch {}

    state.course = buildDaily(puzzleNumber());
    state.rng = mulberry32(hashStr('flavor-' + today));

    if (saved && saved.date === today) {
      // already played today — show the scorecard
      state.results = saved.results; state.total = saved.total; state.phase = 'done';
      $('total-score').textContent = fmtPts(state.total);
      finishGameFromSave();
      return;
    }

    if (!localStorage.getItem(KEY_HELP)) {
      $('help-overlay').classList.add('show');
      localStorage.setItem(KEY_HELP, '1');
    }
    startRound();
  }
  function finishGameFromSave() {
    renderFinal();
    $('round-label').textContent = 'GAME COMPLETE';
    $('round-tier').textContent = '🎯 SEE YOU TOMORROW';
    $('round-prompt').innerHTML =
      'Today’s verses are tapped. New set at <b>midnight</b> — practice (☰) is always open.';
    $('verse-card').classList.remove('revealed');
    $('card-tag').textContent = '🎯 TODAY’S TAPS';
    $('verse-text').innerHTML = state.results.map(r =>
      `<div style="font-size:15px;line-height:1.8;font-family:-apple-system,sans-serif">${r.sq}${r.fast ? '⚡' : ''} <b>${esc(r.ref)}</b> — ${fmtPts(r.pts)}</div>`).join('');
    $('strip-label').textContent = '';
    $('strip-count').textContent = '';
    $('strip').innerHTML = '';
    gsap.to('#final-sheet', { y: '0%', duration: 0.6, delay: 0.4, ease: 'power3.out' });
  }

  // header date + puzzle number
  $('hdr-date').textContent =
    `No. ${puzzleNumber()} · ` +
    new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  // loading puns
  (function cyclePuns() {
    let i = 0;
    startGame._punTimer = setInterval(() => {
      i = (i + 1) % LOADING_PUNS.length;
      $('loading-pun').textContent = LOADING_PUNS[i];
    }, 1400);
  })();

  // buttons
  $('btn-confirm').addEventListener('click', tapIn);
  $('btn-next').addEventListener('click', nextRound);
  $('btn-share').addEventListener('click', shareCard);
  $('btn-practice').addEventListener('click', startPractice);
  $('btn-help').addEventListener('click', () => $('help-overlay').classList.add('show'));
  $('btn-help-close').addEventListener('click', () => $('help-overlay').classList.remove('show'));

  // sheet minimize / restore wiring
  enableSheetDrag('result-sheet', minimizeResult);
  enableSheetDrag('final-sheet', minimizeFinal);
  $('btn-next-mini').addEventListener('click', (e) => { e.stopPropagation(); nextRound(); });
  $('result-peek').addEventListener('click', restoreResult);
  $('final-peek').addEventListener('click', restoreFinal);

  // ☰ menu
  const closeMenu = () => $('menu-overlay').classList.remove('show');
  $('btn-menu').addEventListener('click', () => $('menu-overlay').classList.add('show'));
  $('btn-menu-close').addEventListener('click', closeMenu);
  $('mi-stats').addEventListener('click', () => { closeMenu(); openStats(); });
  $('stats-close').addEventListener('click', () => $('stats-overlay').classList.remove('show'));
  $('mi-practice').addEventListener('click', () => {
    if (state.phase === 'done') { closeMenu(); startPractice(); }
    else toast('Finish today’s game first');
  });
  $('mi-help').addEventListener('click', () => { closeMenu(); $('help-overlay').classList.add('show'); });

  // debug hooks: preview the content calendar / strip builder in the console
  window.__tapSchedule = (days = 30) =>
    Array.from({ length: days }, (_, i) => {
      const dn = puzzleNumber() + i;
      return { day: dn, verses: buildDaily(dn).map(v => v.ref) };
    });
  window.__tapDebug = { buildRound, buildDaily, buildPractice, tapPoints, speedBonus, startRound, state };

  // brief branded pause, then deal today's verses
  setTimeout(startGame, 900);
})();
