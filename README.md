# VerseTap 🎯

A daily Bible game: five verses, no references. Read the verse, then tap the
book it comes from on a strip of consecutive books. The closer your tap, the
more you score. Built on the [Verse Drop framework](../Memory%20Verse%20Game/FRAMEWORK.md)
(itself lifted from Tap-In USA): static HTML/JS, no build step, no backend,
everything client-side, deployable straight to GitHub Pages.

## How a day plays

| Round | Tier | Books on the strip |
|---|---|---|
| 1 | Well-Worn Verses | 10 |
| 2 | Familiar Ground | 10 |
| 3 | Deeper Cuts | 14 |
| 4 | Off the Path | 16 |
| 5 | Deep Wells | 20 |

The strip is always consecutive books in canon order, and the answer sits at a
seeded-random position inside it (clamped so the strip never runs off Genesis
or Revelation). When the strip crosses Malachi → Matthew a "New Testament"
divider is shown.

Scoring is points-up (maptap.gg style): **950 for a bullseye**, plus a **speed
bonus up to +50** on bullseyes only (full at ≤12s, zero at 60s). A miss falls
off logarithmically per book, independent of strip size:
`max(100, 950 − 284 × ln(1 + d))` where `d` is books off — so 1 off ≈ 753,
2 off ≈ 638, 5 off ≈ 442, 10 off ≈ 270, and the floor of 100 means no book is
ever worth zero. Max 1,000 per round, **5,000 per day**.

After Tap In, the strip becomes a heat map (green at the answer fading to slate
at the far end), with the answer badged 🎯 HERE and your tap badged YOU.

Share text uses emoji squares per round: 🎯 bullseye, 🟩 1 off, 🟨 2–3, 🟧 4–6,
🟥 7+, with ⚡ on lightning bullseyes.

## File map

| File | What it is |
|---|---|
| `index.html` | All markup + CSS. Header, round banner, verse card + book strip, bottom sheets, modals, toast. |
| `game.js` | One IIFE: daily scheduler, strip engine + distance scoring, heat-map reveal, storage, share, sheet UI kit. Sections labeled with `── banner comments ──`. |
| `verses.js` | Content: `BIBLE_BOOKS` (66 NIV names in order) and `VERSE_TIERS`, 5 tiers × 24 entries of `{book, ref, context, text}`. |
| `tools/fetch_verses.py` | Regenerates `verses.js` from bolls.life (NIV). Edit its `TIERS` list to add/swap verses, then `python3 tools/fetch_verses.py`. It strips psalm superscriptions and warns if a verse's text names its own book. |
| `.claude/launch.json` | Dev server (`python3 -m http.server 8473`) for Claude's browser preview. |

## Framework conventions kept

- **No build step, no backend** — edit, push, done. localStorage only
  (`versetap-*-v1` keys; bump the suffix on schema changes).
- **Date-seeded daily content**: `puzzleNumber()` is a pure function of the
  local calendar date (DST-proof); `mulberry32` + `hashStr` + seeded
  Fisher-Yates deal the verses and the strip position. Each 24-verse tier deals
  every verse exactly once per 24-day cycle, repeat gap ≥ 19 days.
- **Versioned script tags** — `?v=YYYYMMDD` on `verses.js`/`game.js`; bump on
  every push or iOS serves stale JS (same-day pushes: append a letter).
- **Share text** uses a scheme-less URL so iMessage keeps it inline.
- Debug hooks in the console: `__tapSchedule(days)` previews the content
  calendar; `__tapDebug.buildRound(verse, round, seed)` builds any strip.

## Content notes

Text comes from **bolls.life** (free JSON, no key). Its NIV matches the
**1984 edition** in places (e.g. Psalm 23:1 "I shall not be in want" rather
than 2011's "I lack nothing"). Swap in the official NIV via
[API.Bible](https://scripture.api.bible/) if edition accuracy matters.

Content rules enforced by the fetch tool: the verse text must never name its
own book (so Ruth 1:16, 1 Samuel 16:7, Nehemiah 8:10 and Ezra 7:10 were
swapped out), and psalm headings/superscriptions are stripped.

### Copyright

> Scripture quotations taken from The Holy Bible, New International Version®
> NIV®. Copyright © 1973, 1978, 1984, 2011 by Biblica, Inc.™ Used by
> permission. All rights reserved worldwide.

Biblica permits quoting up to 500 verses without written permission provided
the notice appears; this app stores 120 passages.

## Deploy (GitHub Pages)

1. Create the repo (e.g. `joe-ray-sites/verse-tap`), push this folder to `main`.
2. Settings → Pages → deploy from `main`, root.
3. On every push: bump the `?v=` query on both script tags in `index.html`.
4. Check builds: `gh api repos/joe-ray-sites/verse-tap/pages/builds/latest --jq .status`
5. If the repo name differs, update `SHARE_URL` at the top of `game.js`.
