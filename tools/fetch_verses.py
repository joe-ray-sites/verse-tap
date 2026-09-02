#!/usr/bin/env python3
"""Fetch the curated VerseTap verse pool (NIV) from bolls.life and emit verses.js.

Pool layout mirrors the Verse Drop / Tap-In tier structure: 5 tiers x 24 refs,
one tier per round, ordered easy -> hard. Unlike Verse Drop, every tier draws
from the whole Bible - the round's difficulty comes from how well-known the
verse is (and, in game.js, from how many books are on the strip).

  Tier 0: Well-Worn Verses   (round 1, 10-book strip)
  Tier 1: Familiar Ground    (round 2, 10-book strip)
  Tier 2: Deeper Cuts        (round 3, 14-book strip)
  Tier 3: Off the Path       (round 4, 16-book strip)
  Tier 4: Deep Wells         (round 5, 20-book strip)

Each emitted entry: {book, ref, context, text}. `book` is the 1-based position
in the 66-book Protestant canon (Genesis=1 ... Revelation=66); the strip is
built from BIBLE_BOOKS by that index. The verse TEXT must never name its book.
"""
import json, re, time, urllib.request, html, os

API = "https://bolls.life/get-paralel-verses/"

# 66 books, NIV naming, canonical order. Index 0 = Genesis = book 1.
BOOKS = [
  "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
  "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra",
  "Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Songs",
  "Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos",
  "Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah",
  "Malachi",
  "Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians",
  "Galatians","Ephesians","Philippians","Colossians","1 Thessalonians",
  "2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James",
  "1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation",
]
IDX = {name: i + 1 for i, name in enumerate(BOOKS)}
SINGLE_CHAPTER = {"Obadiah", "Philemon", "2 John", "3 John", "Jude"}

# (book, chapter, [verses], reveal blurb)
TIERS = [
 ("Well-Worn Verses", [
  ("John",3,[16],          "The gospel in one sentence, spoken to Nicodemus at night."),
  ("Psalms",23,[1],        "David's shepherd psalm opens with the whole point."),
  ("Philippians",4,[13],   "Paul's secret of contentment, written from a Roman prison."),
  ("Romans",8,[28],        "A promise for those who love God, even in the mess."),
  ("Genesis",1,[1],        "The first words of the Bible."),
  ("Proverbs",3,[5,6],     "Solomon's most-quoted advice on decision-making."),
  ("Jeremiah",29,[11],     "Written to exiles in Babylon, with seventy years still to go."),
  ("Matthew",28,[19],      "The Great Commission, given on a mountain in Galilee."),
  ("Isaiah",40,[31],       "Comfort for a weary nation: eagles, running, walking."),
  ("Joshua",1,[9],         "God's charge to Joshua right after Moses died."),
  ("Romans",3,[23],        "Paul levels the field: every person, same diagnosis."),
  ("Ephesians",2,[8,9],    "Salvation's source, means, and the boast it rules out."),
  ("1 Corinthians",13,[4], "The love chapter, read at more weddings than any other text."),
  ("Galatians",5,[22,23],  "The fruit of the Spirit: nine traits, one harvest."),
  ("Psalms",119,[105],     "From the longest chapter in the Bible, an ode to God's word."),
  ("John",14,[6],          "Jesus' answer to Thomas the night before the cross."),
  ("Matthew",6,[33],       "From the Sermon on the Mount, on where worry should rank."),
  ("Hebrews",11,[1],       "The opening line of the Bible's hall of faith."),
  ("2 Timothy",3,[16],     "Paul's final letter, on where Scripture comes from."),
  ("1 John",1,[9],         "John's assurance for anyone who has blown it."),
  ("Revelation",3,[20],    "Jesus knocking, in the letter to lukewarm Laodicea."),
  ("Psalms",46,[1],        "The psalm behind Luther's hymn A Mighty Fortress."),
  ("Matthew",11,[28],      "An open invitation to everyone worn out by life and religion."),
  ("Romans",6,[23],        "Wages versus gift: Paul's starkest contrast."),
 ]),
 ("Familiar Ground", [
  ("Psalms",27,[1],        "David: light, salvation, stronghold. So why be afraid?"),
  ("Isaiah",41,[10],       "Do not fear, with four promises attached."),
  ("Romans",12,[2],        "The alternative to being squeezed into the world's mold."),
  ("2 Corinthians",5,[17], "What actually happens when someone comes to Christ."),
  ("Proverbs",22,[6],      "The classic proverb for parents."),
  ("Deuteronomy",6,[5],    "The Shema's command, which Jesus called the greatest."),
  ("1 Peter",5,[7],        "Peter's one-line cure for anxiety."),
  ("Hebrews",4,[12],       "Scripture described as a living, cutting blade."),
  ("Philippians",4,[6,7],  "Paul's prescription for anxiety, written from prison."),
  ("John",1,[1],           "John opens his gospel where Genesis opens the Bible."),
  ("Lamentations",3,[22,23],"Hope written in the rubble of Jerusalem."),
  ("Psalms",121,[1,2],     "A song for pilgrims climbing the road to Jerusalem."),
  ("Psalms",139,[14],      "David marvels at how he was made."),
  ("Isaiah",53,[5],        "The suffering servant, seven centuries before the cross."),
  ("Mark",10,[45],         "Jesus defines greatness by pointing at his own mission."),
  ("Luke",1,[37],          "Gabriel's word to Mary in Nazareth."),
  ("Acts",1,[8],           "The risen Jesus' final promise before ascending."),
  ("Colossians",3,[23],    "Work re-aimed: same tasks, different boss."),
  ("1 Thessalonians",5,[16,17,18], "Three habits Paul calls God's will for you."),
  ("Galatians",2,[20],     "Paul's own testimony in a single sentence."),
  ("Ephesians",6,[10,11],  "The opening bell of the armor-of-God passage."),
  ("Romans",10,[9],        "Paul spells out how anyone is saved."),
  ("Matthew",5,[16],       "Jesus tells his followers what their good works are for."),
  ("James",1,[5],          "James on where to get wisdom, and how generously it's given."),
 ]),
 ("Deeper Cuts", [
  ("Exodus",14,[14],       "Moses at the Red Sea, with Egypt's army closing in."),
  ("Numbers",6,[24,25,26], "The blessing Aaron and his sons were told to speak over Israel."),
  ("Deuteronomy",31,[6],   "Moses' farewell charge to Israel before the Jordan crossing."),
  ("1 Samuel",17,[47],     "A shepherd boy to a giant, moments before the sling."),
  ("2 Chronicles",7,[14],  "God's reply to Solomon the night after the temple was dedicated."),
  ("Job",19,[25],          "Job's defiant hope, spoken from the ash heap."),
  ("Psalms",37,[4],        "From David's psalm on not fretting over the wicked."),
  ("Proverbs",18,[10],     "A proverb that pictures God's name as a fortress."),
  ("Ecclesiastes",3,[1],   "The opening of the Teacher's famous poem on seasons."),
  ("Isaiah",26,[3],        "A song of praise from the prophet's vision of the last days."),
  ("Jeremiah",17,[7,8],    "The prophet's tree planted by the water."),
  ("Ezekiel",36,[26],      "A promise to exiles: a transplant of the heart."),
  ("Daniel",3,[17,18],     "Three friends answer the king in front of the furnace."),
  ("Hosea",6,[6],          "A verse Jesus quoted twice to the Pharisees."),
  ("Joel",2,[28],          "The prophecy Peter quoted at Pentecost."),
  ("Amos",5,[24],          "The shepherd-prophet's line made famous by Dr. King."),
  ("Jonah",2,[2],          "A prayer prayed from inside a fish."),
  ("Habakkuk",3,[17,18],   "The prophet's decision to rejoice with the barns empty."),
  ("Zephaniah",3,[17],     "God pictured as singing over his people."),
  ("Malachi",3,[10],       "The last book of the Old Testament, on tithes and floodgates."),
  ("Matthew",5,[14],       "From the Sermon on the Mount: a city on a hill."),
  ("Luke",6,[31],          "The Golden Rule, in Jesus' own words."),
  ("John",13,[34,35],      "A new command, given right after Jesus washed feet."),
  ("Titus",3,[5],          "Paul reminding a young pastor on Crete how salvation works."),
 ]),
 ("Off the Path", [
  ("Genesis",50,[20],      "Joseph to the brothers who sold him, decades later."),
  ("Leviticus",19,[18],    "The second-greatest commandment, tucked inside the holiness code."),
  ("Joshua",24,[15],       "Joshua's last speech to Israel at Shechem."),
  ("Ruth",2,[12],          "Boaz's blessing over a Moabite widow gleaning his field."),
  ("1 Kings",18,[21],      "Elijah's challenge to the crowd on Mount Carmel."),
  ("2 Kings",6,[16],       "Elisha calms his servant, surrounded by an army."),
  ("1 Chronicles",16,[11], "From David's song when the ark came to Jerusalem."),
  ("Ezra",3,[11],          "The second temple's foundation is laid, to shouts and weeping."),
  ("Esther",4,[14],        "Mordecai's message to a queen inside the palace."),
  ("Job",42,[2],           "Job's reply after God speaks from the storm."),
  ("Psalms",90,[12],       "From the only psalm attributed to Moses."),
  ("Proverbs",16,[9],      "Planning versus providence, in one line."),
  ("Ecclesiastes",12,[13], "The Teacher's final conclusion."),
  ("Song of Songs",8,[7],  "The Song's climactic word on love and floods."),
  ("Isaiah",55,[8,9],      "God on the gap between his thoughts and ours."),
  ("Jeremiah",31,[3],      "Everlasting love, promised to a nation headed for exile."),
  ("Ezekiel",37,[4,5],     "Prophesying to a valley of dry bones."),
  ("Nahum",1,[7],          "A tender line in a book that is mostly about Nineveh's doom."),
  ("Zechariah",4,[6],      "A word to Zerubbabel about rebuilding the temple."),
  ("Matthew",16,[24],      "Jesus, right after Peter's confession at Caesarea Philippi."),
  ("Acts",20,[35],         "A saying of Jesus preserved nowhere in the four Gospels."),
  ("1 Timothy",6,[6],      "Paul to Timothy on gain of a different kind."),
  ("1 Peter",3,[15],       "Peter's charge to be ready with an answer."),
  ("Jude",1,[24,25],       "The doxology that closes one of the Bible's shortest letters."),
 ]),
 ("Deep Wells", [
  ("Genesis",28,[15],      "God's promise to Jacob at Bethel, asleep on a stone."),
  ("Exodus",33,[14],       "God's reply when Moses refused to go on without him."),
  ("Numbers",23,[19],      "Balaam, hired to curse Israel, blesses them instead."),
  ("Deuteronomy",30,[19],  "Moses sets the choice before Israel on the plains of Moab."),
  ("Judges",21,[25],       "The last verse of Judges, and its whole diagnosis."),
  ("2 Samuel",22,[31],     "David's song of deliverance, near the end of his life."),
  ("2 Chronicles",16,[9],  "Hanani the seer rebukes King Asa."),
  ("Job",23,[10],          "Job, mid-argument, still trusting the outcome."),
  ("Psalms",62,[1,2],      "David: rest, rock, salvation, fortress."),
  ("Proverbs",27,[17],     "Iron sharpening iron."),
  ("Ecclesiastes",4,[9,10],"The Teacher on why two beat one."),
  ("Isaiah",43,[2],        "Promises for the waters and the fire."),
  ("Jeremiah",33,[3],      "Spoken to the prophet while he was confined in the courtyard of the guard."),
  ("Lamentations",3,[25,26],"Quiet waiting, from a book of tears."),
  ("Daniel",12,[3],        "Daniel's final chapter, on those who shine like stars."),
  ("Micah",6,[8],          "The prophet's summary of what God actually requires."),
  ("Habakkuk",2,[14],      "A promise tucked among five woes against Babylon."),
  ("Haggai",1,[5],         "The prophet's refrain to a people who had stopped building."),
  ("Zechariah",9,[9],      "The Palm Sunday prophecy, five centuries early."),
  ("1 Corinthians",10,[13],"Paul on temptation and the way out."),
  ("2 Corinthians",12,[9], "God's answer to Paul's thorn."),
  ("Philemon",1,[6],       "Paul's prayer for a slave owner in Colossae."),
  ("3 John",1,[4],         "The elder's greatest joy, in one of the Bible's shortest books."),
  ("Hebrews",13,[8],       "One line on the unchanging Christ, near the end of Hebrews."),
 ]),
]

SUPERSCRIPT = re.compile(r"(psalm|director|song|of david|of asaph|of solomon|sons of korah|jeduthun|"
                         r"ascents|maskil|miktam|shiggaion|according to|of moses|prayer of|to the tune|"
                         r"of ethan|of heman|for the|when he|when the)", re.I)

def clean(t):
    t = html.unescape(t)
    # bolls prefixes verse 1 of each psalm with "Psalm N<br/>superscription.<br/>" -
    # drop the heading and any superscription lines (they name the book).
    segs = re.split(r"<br\s*/?>", t)
    if re.match(r"^\s*Psalm \d+\s*$", segs[0]):
        segs = segs[1:]
        while segs and len(segs[0]) < 120 and segs[0].strip().endswith(".") and SUPERSCRIPT.search(segs[0]):
            segs = segs[1:]
    t = " ".join(segs)
    t = re.sub(r"<[^>]+>", "", t)          # footnote / markup tags
    t = t.replace("“", "").replace("”", "").replace('"', "")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def fetch(book, chapter, verses):
    body = json.dumps({"translations": ["NIV"], "book": book,
                       "chapter": chapter, "verses": verses}).encode()
    req = urllib.request.Request(API, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "versetap-builder"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def ref_of(book, ch, vv):
    vs = str(vv[0]) if len(vv) == 1 else f"{vv[0]}-{vv[-1]}"
    name = "Psalm" if book == "Psalms" else book
    return f"{name} {vs}" if book in SINGLE_CHAPTER else f"{name} {ch}:{vs}"

out_tiers = []
total = sum(len(refs) for _, refs in TIERS)
done = 0
seen = set()
for label, refs in TIERS:
    entries = []
    for (bk, ch, vv, ctx) in refs:
        assert bk in IDX, f"unknown book {bk}"
        ref = ref_of(bk, ch, vv)
        assert ref not in seen, f"duplicate {ref}"
        seen.add(ref)
        rows = fetch(IDX[bk], ch, vv)[0]
        text = " ".join(clean(r["text"]) for r in sorted(rows, key=lambda r: r["verse"]))
        if not text or len(rows) != len(vv):
            raise SystemExit(f"MISSING text for {ref}")
        # A verse that names its own book would be a giveaway.
        if re.search(r"\b" + re.escape(bk.split()[-1]) + r"\b", text) and bk not in ("John", "Jude"):
            print(f"  ! {ref} mentions '{bk}' in its text - consider swapping it")
        entries.append({"book": IDX[bk], "ref": ref, "context": ctx, "text": text})
        done += 1
        print(f"[{done}/{total}] {ref}  ({len(text.split())} words)")
        time.sleep(0.3)
    out_tiers.append({"label": label, "verses": entries})

lines = [
  "// verses.js - VerseTap content pool (NIV). Generated by tools/fetch_verses.py.",
  "// BIBLE_BOOKS: the 66-book canon in order (index 0 = Genesis). VERSE_TIERS: 5 tiers",
  "// x 24 verses, one tier per round, easy -> hard. Entry: {book, ref, context, text}",
  "// where `book` is the 1-based canon position. See README for the NIV copyright notice.",
  "const BIBLE_BOOKS = " + json.dumps(BOOKS, ensure_ascii=False) + ";",
  "const VERSE_TIERS = " + json.dumps(out_tiers, indent=1, ensure_ascii=False) + ";",
]
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "..", "verses.js"), "w") as f:
    f.write("\n".join(lines) + "\n")
print("wrote verses.js")
