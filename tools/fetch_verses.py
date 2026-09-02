#!/usr/bin/env python3
"""Fetch the curated VerseTap verse pool (NIV) from bolls.life and emit verses.js.

Pool layout mirrors the Verse Drop / Tap-In tier structure: 5 tiers x 90 refs
(489 verses, under Biblica's 500-verse no-permission-needed ceiling),
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
  ("Psalms",23,[4],"The valley of the shadow, from the shepherd psalm."),
  ("Psalms",46,[10],"Be still: near the end of the psalm behind A Mighty Fortress."),
  ("Psalms",118,[24],"The morning verse for the day the Lord has made."),
  ('Psalms',51,[10],"David's plea for a clean heart after Nathan confronted him."),
  ("Psalms",34,[8],"Taste and see, from a psalm David wrote after feigning madness."),
  ("Psalms",91,[1],"The shelter of the Most High, opening line."),
  ("Psalms",56,[3],"David, seized by the Philistines in Gath, decides where to put his fear."),
  ("Psalms",103,[12],"How far God removes our sins, measured in compass points."),
  ("Psalms",150,[6],"The last line of the whole Psalter."),
  ('Proverbs',4,[23],"Guard your heart: a father's advice on where life flows from."),
  ("Proverbs",16,[3],"Commit your plans, and watch what happens to them."),
  ("Proverbs",17,[17],"The proverb on friendship and hard times."),
  ("Proverbs",15,[1],"The gentle answer, and what it does to anger."),
  ("Proverbs",1,[7],"The thesis statement of the whole book of wisdom."),
  ("Isaiah",9,[6],"The Christmas prophecy: a child, a son, four names."),
  ("Isaiah",40,[8],"Grass withers, flowers fall, one thing stands."),
  ('Isaiah',6,[8],"The prophet's response to a vision of the throne room."),
  ('Jeremiah',1,[5],"God's first words to a young prophet from Anathoth."),
  ("Matthew",5,[9],"One of the Beatitudes, on peacemakers."),
  ('Matthew',6,[9],"The opening of the Lord's Prayer."),
  ("Matthew",19,[26],"Jesus, after the rich young ruler walked away."),
  ("Matthew",22,[39],"The second greatest commandment, per Jesus."),
  ("Matthew",18,[20],"Where two or three gather."),
  ("Matthew",4,[4],"Jesus answers the tempter in the wilderness with Deuteronomy."),
  ("Matthew",7,[7],"Jesus on prayer: three verbs, three promises."),
  ("Matthew",28,[20],"The last verse of the first gospel."),
  ("Mark",16,[15],"Go into all the world, from the closing commission."),
  ('Luke',2,[11],"The angel's announcement to the shepherds."),
  ('Luke',23,[34],"The first of Jesus' words from the cross."),
  ("John",1,[14],"The Word became flesh."),
  ("John",3,[17],"The verse right after the most famous one in the Bible."),
  ("John",8,[32],"Truth and freedom, spoken to believers in the temple courts."),
  ('John',10,[10],"The Good Shepherd contrasts his mission with the thief's."),
  ("John",11,[25],"Said to Martha moments before Lazarus walked out of the tomb."),
  ("John",15,[13],"Greater love, from the upper room discourse."),
  ('John',16,[33],"Jesus' last words of comfort before his arrest."),
  ("John",14,[27],"A parting gift no army or economy can issue."),
  ("John",15,[5],"From the upper room: the vine, the branches, and abiding."),
  ("John",8,[12],"Spoken in the temple courts during the Feast of Tabernacles."),
  ('Acts',2,[38],"Peter's answer when the Pentecost crowd asked what to do."),
  ("Acts",4,[12],"Peter before the Sanhedrin, unable to stay quiet."),
  ('Acts',16,[31],"The answer to the Philippian jailer's midnight question."),
  ('Romans',5,[8],"God's love proved by its timing, not our merit."),
  ('Romans',8,[38, 39],"Paul's list of everything that cannot separate us from God's love."),
  ("Romans",8,[1],"The verdict for everyone who is in Christ Jesus."),
  ('Romans',15,[13],"Paul's benediction of hope, joy and peace."),
  ("1 Corinthians",10,[31],"Eating, drinking, and everything else, aimed at one purpose."),
  ('1 Corinthians',13,[13],"The last word of the Bible's great chapter on love."),
  ('2 Corinthians',5,[7],"Six words that define the Christian's operating system."),
  ("2 Corinthians",9,[7],"The cheerful giver."),
  ("Galatians",6,[9],"Encouragement for anyone tired of doing the right thing."),
  ("Ephesians",4,[32],"Forgiveness with a reason attached: you were forgiven first."),
  ('Philippians',1,[6],"Paul's confidence about the work God started in his readers."),
  ('Philippians',4,[8],"Paul's list of what to think about."),
  ("Colossians",3,[17],"Whatever you do, in word or deed."),
  ("2 Timothy",1,[7],"Paul reminds Timothy what kind of spirit he was given."),
  ('2 Timothy',4,[7],"Paul's epitaph, written from his last imprisonment."),
  ("Hebrews",13,[5],"Contentment, and a promise never to be left."),
  ("James",4,[7],"Submit, resist, and watch the devil flee."),
  ("James",1,[17],"Every good and perfect gift, and where it comes from."),
  ("1 Peter",2,[9],"A chosen people, a royal priesthood."),
  ("1 John",4,[8],"God is love, in three words."),
  ("1 John",4,[19],"Why we love at all."),
  ("Revelation",21,[4],"No more tears, from the vision of the new Jerusalem."),
  ('Genesis',1,[27],"Humanity made in God's image, on day six."),
  ("Exodus",20,[3],"The first commandment, from Mount Sinai."),
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
  ('Psalms',19,[14],"David's closing prayer in a psalm about skies and Scripture."),
  ("Proverbs",31,[30],"From the closing poem on a wife of noble character."),
  ('Matthew',5,[44],"Love your enemies: the Sermon on the Mount's hardest line."),
  ("Mark",9,[23],"Jesus to a desperate father: everything is possible for one who believes."),
  ('Romans',12,[21],"The last verse of Paul's chapter on living sacrifices."),
  ('1 Corinthians',16,[14],"Paul's five-word sign-off instruction to Corinth."),
  ('Ephesians',3,[20],"Immeasurably more: Paul's doxology before the practical chapters."),
  ("Philippians",4,[19],"A promise about needs, from a thank-you note for a gift."),
  ("Hebrews",4,[16],"The invitation to approach the throne of grace."),
  ("James",5,[16],"The prayer of a righteous person."),
  ("1 John",4,[4],"Greater is the one who is in you."),
  ('Revelation',22,[13],"Alpha and Omega, from the Bible's final chapter."),
  ('Deuteronomy',31,[8],"Moses' charge to Joshua in front of all Israel."),
  ("Matthew",6,[21],"Where your treasure is, from the Sermon on the Mount."),
  ('Psalms',16,[11],"David on the path of life and the joy of God's presence."),
  ("Psalms",30,[5],"Weeping for a night, joy in the morning."),
  ("Psalms",34,[18],"Close to the brokenhearted."),
  ("Psalms",42,[1],"The deer panting for streams of water."),
  ('Psalms',55,[22],"Cast your cares, from a psalm David wrote after a friend's betrayal."),
  ('Psalms',73,[26],"My flesh and my heart may fail, from Asaph's psalm of doubt."),
  ("Psalms",119,[11],"Word hidden in the heart, from the longest chapter in the Bible."),
  ("Psalms",127,[1],"Unless the Lord builds the house, from a psalm of Solomon."),
  ("Psalms",139,[23, 24],"Search me, God: the closing prayer of a psalm about being known."),
  ("Psalms",147,[3],"He heals the brokenhearted."),
  ('Psalms',24,[1],"The earth is the Lord's, and everything in it."),
  ("Proverbs",14,[12],"The way that appears right."),
  ("Proverbs",16,[18],"Pride, and what it goes before."),
  ("Isaiah",1,[18],"Sins like scarlet, white as snow."),
  ("Isaiah",43,[19],"See, I am doing a new thing."),
  ("Isaiah",54,[17],"No weapon forged against you."),
  ('Matthew',6,[14],"Forgive others, right after the Lord's Prayer."),
  ("Matthew",6,[26],"Look at the birds of the air."),
  ("Matthew",14,[27],"Take courage! Spoken while walking on the water."),
  ("Matthew",17,[20],"Faith as small as a mustard seed."),
  ("Matthew",25,[21],"Well done, good and faithful servant."),
  ("Mark",8,[36],"What good is it to gain the whole world?"),
  ("Luke",6,[38],"Give, and it will be given to you."),
  ('Luke',19,[10],"Jesus explains why he invited himself to Zacchaeus' house."),
  ("John",6,[35],"I am the bread of life."),
  ("John",10,[11],"I am the good shepherd."),
  ("John",14,[1],"Do not let your hearts be troubled."),
  ("John",1,[12],"The right to become children of God."),
  ("John",20,[29],"Spoken to Thomas one week after the resurrection."),
  ("Romans",1,[16],"Paul is not ashamed of the gospel."),
  ("Romans",5,[1],"Peace with God through faith."),
  ("Romans",8,[18],"Present sufferings versus coming glory."),
  ("Romans",8,[31],"If God is for us."),
  ("Romans",8,[37],"More than conquerors."),
  ("Romans",12,[1],"Living sacrifices."),
  ("1 Corinthians",6,[19, 20],"Your body is a temple; you were bought at a price."),
  ("1 Corinthians",15,[55],"Where, O death, is your sting?"),
  ("2 Corinthians",5,[21],"The great exchange: he became sin so we might become righteousness."),
  ("Galatians",3,[28],"Neither Jew nor Gentile, slave nor free."),
  ('Ephesians',2,[10],"God's handiwork, created for good works."),
  ("Philippians",4,[4],"Rejoice in the Lord always. Again."),
  ('Philippians',1,[21],"Paul's ledger: both columns come out ahead."),
  ("Philippians",3,[13, 14],"Forgetting what is behind, pressing on."),
  ('1 Timothy',4,[12],"Don't let anyone look down on you because you are young."),
  ('Hebrews',10,[24, 25],"Spur one another on; don't give up meeting together."),
  ("Hebrews",12,[1, 2],"Throw off everything that hinders, fix your eyes on Jesus."),
  ("James",1,[22],"Do not merely listen to the word."),
  ("James",2,[17],"Faith without deeds is dead."),
  ("1 Peter",4,[8],"Love covers over a multitude of sins."),
  ("1 John",3,[1],"See what great love the Father has lavished on us."),
  ("1 John",4,[18],"Perfect love drives out fear."),
  ("Revelation",21,[5],"I am making everything new."),
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
  ('Psalms',32,[8],"God's promise to instruct and counsel, in a psalm of confession."),
  ('Psalms',133,[1],"How good it is when God's people live together in unity."),
  ("Proverbs",11,[25],"The generous person and the one who refreshes others."),
  ("Proverbs",13,[20],"Walk with the wise."),
  ("Proverbs",19,[21],"Many plans, one purpose."),
  ("Proverbs",22,[1],"A good name versus great riches."),
  ("Isaiah",30,[21],"A voice behind you saying, this is the way."),
  ("Isaiah",64,[8],"We are the clay, you are the potter."),
  ("Jeremiah",32,[27],"Is anything too hard for me? Asked while Babylon besieged Jerusalem."),
  ("Malachi",3,[6],"I the Lord do not change."),
  ("Matthew",9,[37],"The harvest is plentiful, the workers few."),
  ("Matthew",24,[35],"Heaven and earth will pass away."),
  ("Matthew",26,[41],"The spirit is willing, from Gethsemane."),
  ("Mark",11,[24],"Whatever you ask for in prayer."),
  ("John",4,[24],"God is spirit, said to a Samaritan woman at a well."),
  ("Romans",10,[17],"Faith comes from hearing."),
  ("1 Corinthians",2,[9],"What no eye has seen."),
  ("2 Corinthians",3,[17],"Where the Spirit of the Lord is, there is freedom."),
  ("Galatians",5,[1],"It is for freedom that Christ has set us free."),
  ("Ephesians",6,[12],"Our struggle is not against flesh and blood."),
  ("Colossians",3,[12, 13],"Clothe yourselves with compassion."),
  ("1 Timothy",6,[10],"The love of money."),
  ("Hebrews",11,[6],"Without faith it is impossible to please God."),
  ("James",1,[19],"Quick to listen, slow to speak."),
  ("1 Peter",2,[24],"By his wounds you have been healed."),
  ('Genesis',8,[22],"God's promise after the flood: seasons will not cease."),
  ('Genesis',18,[14],"Asked at Abraham's tent when Sarah laughed."),
  ("Exodus",3,[14],"God gives Moses his name at the burning bush."),
  ("Exodus",34,[6],"God describes himself to Moses on Sinai, the second time up."),
  ("Deuteronomy",7,[9],"The faithful God who keeps covenant to a thousand generations."),
  ('Deuteronomy',33,[27],"Everlasting arms, from Moses' final blessing."),
  ("Joshua",1,[8],"Meditate on it day and night: instructions to a new commander."),
  ('1 Samuel',12,[24],"An old judge's farewell charge to Israel."),
  ("1 Kings",19,[12],"Not in the wind, earthquake or fire: a gentle whisper on Horeb."),
  ('1 Chronicles',29,[11],"David's prayer at the offering for the temple."),
  ("2 Chronicles",20,[15],"Jahaziel to King Jehoshaphat: the battle is not yours."),
  ("Esther",4,[16],"If I perish, I perish."),
  ('Job',1,[21],"Job's response to losing everything in one day."),
  ('Job',38,[4],"God's first question from the storm."),
  ('Psalms',18,[2],"Rock, fortress, deliverer: David's song after escaping Saul."),
  ("Psalms",84,[10],"Better is one day in your courts."),
  ("Psalms",86,[11],"Give me an undivided heart."),
  ("Psalms",145,[18],"The Lord is near to all who call on him."),
  ("Proverbs",17,[22],"A cheerful heart is good medicine."),
  ("Proverbs",18,[21],"The tongue has the power of life and death."),
  ("Proverbs",29,[25],"Fear of man is a snare."),
  ("Ecclesiastes",3,[11],"Eternity set in the human heart."),
  ("Ecclesiastes",9,[10],"Whatever your hand finds to do."),
  ("Isaiah",40,[29],"Strength to the weary."),
  ("Isaiah",41,[13],"I will hold your right hand."),
  ("Isaiah",55,[6],"Seek the Lord while he may be found."),
  ('Isaiah',55,[11],"God's word will not return empty."),
  ("Isaiah",61,[1],"The passage Jesus read aloud in the Nazareth synagogue."),
  ("Jeremiah",6,[16],"Ask for the ancient paths."),
  ("Jeremiah",17,[9],"The heart is deceitful above all things."),
  ("Jeremiah",29,[12, 13],"Two verses after the famous one: seek me with all your heart."),
  ("Ezekiel",22,[30],"Looking for someone to stand in the gap."),
  ("Joel",2,[25],"The years the locusts have eaten."),
  ("Micah",7,[7],"But as for me, I watch in hope."),
  ("Habakkuk",2,[3],"Though it linger, wait for it."),
  ("Zechariah",4,[10],"Who dares despise the day of small things?"),
  ("Matthew",7,[13, 14],"The narrow gate."),
  ("Matthew",10,[16],"Sheep among wolves, shrewd as snakes."),
  ("Matthew",25,[40],"Whatever you did for the least of these."),
  ("Luke",12,[32],"Do not be afraid, little flock."),
  ("Luke",23,[43],"Today you will be with me in paradise."),
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
  ("Genesis",15,[6],"Abram believed, and it was credited to him as righteousness."),
  ('Deuteronomy',10,[12],"What does the Lord ask of you? Moses' summary."),
  ("Joshua",1,[5],"As I was with Moses, so I will be with you."),
  ('1 Samuel',2,[2],"From Hannah's prayer after Samuel's birth."),
  ('1 Kings',3,[9],"Solomon's request at Gibeon."),
  ("1 Chronicles",4,[10],"The prayer of Jabez."),
  ("Nehemiah",6,[3],"The wall-builder refuses to come down for a meeting."),
  ('Job',28,[28],"Where wisdom is found, from Job's poem on mining."),
  ("Psalms",1,[3],"The tree planted by streams of water."),
  ("Psalms",25,[4, 5],"Show me your ways, teach me your paths."),
  ("Psalms",28,[7],"My heart leaps for joy."),
  ("Psalms",31,[24],"Be strong and take heart, all you who hope."),
  ("Psalms",138,[8],"The Lord will vindicate me."),
  ("Proverbs",2,[6],"The Lord gives wisdom."),
  ("Proverbs",11,[2],"With humility comes wisdom."),
  ("Proverbs",13,[12],"Hope deferred makes the heart sick."),
  ("Proverbs",15,[22],"Plans fail for lack of counsel."),
  ("Proverbs",16,[24],"Gracious words are a honeycomb."),
  ("Proverbs",31,[25],"Clothed with strength and dignity."),
  ("Ecclesiastes",1,[9],"Nothing new under the sun."),
  ('Song of Songs',6,[3],"I am my beloved's and my beloved is mine."),
  ("Isaiah",12,[2],"Surely God is my salvation, from a short song of praise."),
  ("Isaiah",30,[15],"In repentance and rest is your salvation."),
  ("Isaiah",52,[7],"How beautiful on the mountains are the feet."),
  ("Isaiah",54,[10],"Though the mountains be shaken."),
  ("Isaiah",60,[1],"Arise, shine, for your light has come."),
  ("Jeremiah",9,[23, 24],"Let not the wise boast of their wisdom."),
  ("Jeremiah",31,[25],"I will refresh the weary."),
  ("Lamentations",3,[31, 32],"No one is cast off by the Lord forever."),
  ("Ezekiel",34,[16],"The shepherd who searches for the lost sheep."),
  ('Daniel',6,[22],"A report from the lions' den, the morning after."),
  ("Hosea",10,[12],"Break up your unplowed ground."),
  ("Joel",2,[12, 13],"Rend your heart and not your garments."),
  ("Amos",3,[7],"The Lord does nothing without revealing his plan to the prophets."),
  ("Amos",4,[12],"Prepare to meet your God."),
  ('Obadiah',1,[15],"The day of the Lord is near, from the Old Testament's shortest book."),
  ("Jonah",2,[9],"The end of the prayer from inside the fish."),
  ("Micah",5,[2],"Bethlehem Ephrathah, small among the clans of Judah."),
  ("Micah",7,[8],"Though I sit in darkness, the Lord will be my light."),
  ("Nahum",1,[3],"Slow to anger but great in power."),
  ("Habakkuk",3,[19],"Feet like the feet of a deer: the last verse of the book."),
  ("Zephaniah",2,[3],"Seek the Lord, all you humble of the land."),
  ("Haggai",2,[9],"The glory of this present house will be greater."),
  ("Zechariah",1,[3],"Return to me, and I will return to you."),
  ("Zechariah",2,[8],"The apple of his eye."),
  ("Malachi",4,[2],"The sun of righteousness with healing in its rays."),
  ("John",1,[5],"The light shines in the darkness."),
  ('John',17,[3],"Now this is eternal life, from Jesus' high-priestly prayer."),
  ("John",8,[36],"If the Son sets you free."),
  ('Acts',2,[42],"The first church's four devotions."),
  ("Acts",4,[13],"Unschooled, ordinary men who had been with Jesus."),
  ("Romans",8,[26],"The Spirit intercedes with wordless groans."),
  ("Romans",11,[33],"Oh, the depth of the riches of the wisdom and knowledge of God!"),
  ("1 Corinthians",1,[27],"God chose the foolish things of the world."),
  ('1 Corinthians',3,[16],"Don't you know that you yourselves are God's temple?"),
  ("1 Corinthians",12,[27],"You are the body of Christ."),
  ("2 Corinthians",1,[3, 4],"The God of all comfort."),
  ("Galatians",5,[16],"Walk by the Spirit."),
  ("Galatians",6,[10],"Do good to all people, especially the family of believers."),
  ("Philippians",2,[3, 4],"Value others above yourselves."),
  ("Colossians",1,[16, 17],"In him all things hold together."),
  ("1 Timothy",2,[5],"One mediator between God and mankind."),
  ("Hebrews",7,[25],"He always lives to intercede for them."),
  ("James",1,[12],"Blessed is the one who perseveres under trial."),
  ("1 Peter",5,[8, 9],"Your enemy the devil prowls around like a roaring lion."),
  ("Revelation",2,[10],"Be faithful, even to the point of death: the letter to Smyrna."),
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
  ("Genesis",2,[18],"Not good for the man to be alone."),
  ("Exodus",15,[2],"The Song of Moses on the far bank of the Red Sea."),
  ("Leviticus",20,[26],"Be holy, because I am holy: set apart from the nations."),
  ('Numbers',14,[18],"Moses quotes God's own self-description back to him at Kadesh."),
  ('Deuteronomy',32,[4],"He is the Rock: the opening of Moses' song."),
  ("Judges",6,[12],"The angel greets Gideon, hiding in a winepress."),
  ('2 Samuel',7,[22],"David's prayer after the covenant promise through Nathan."),
  ('2 Kings',20,[5],"God's reply to Hezekiah's tears, via Isaiah."),
  ('1 Chronicles',28,[9],"David's charge to Solomon about the temple and the heart."),
  ("2 Chronicles",15,[7],"Azariah the prophet to King Asa: your work will be rewarded."),
  ("2 John",1,[6],"This is love: that we walk in obedience, from a one-chapter letter."),
  ("Psalms",111,[10],"The fear of the Lord, from an acrostic psalm."),
  ("Proverbs",24,[16],"The righteous fall seven times and rise again."),
  ("Proverbs",27,[1],"Do not boast about tomorrow."),
  ("Song of Songs",2,[4],"His banner over me is love."),
  ("Isaiah",46,[4],"Even to your old age and gray hairs."),
  ("Isaiah",59,[1],"The arm of the Lord is not too short to save."),
  ("Jeremiah",15,[16],"When your words came, I ate them."),
  ("Ezekiel",36,[27],"The verse after the heart transplant: a new Spirit."),
  ("Hosea",14,[9],"The last verse of Hosea."),
  ("Genesis",32,[26],"Jacob wrestling until daybreak: I will not let you go."),
  ('Exodus',14,[13],"Stand firm: Moses to a terrified Israel at the sea's edge."),
  ("Deuteronomy",4,[29],"You will find him if you seek him with all your heart."),
  ("Deuteronomy",29,[29],"The secret things belong to the Lord."),
  ('Joshua',23,[14],"Joshua's farewell: not one promise has failed."),
  ('Judges',7,[2],"God trims Gideon's army so Israel can't boast."),
  ('1 Samuel',17,[45],"David's speech to Goliath, before the sling."),
  ("2 Samuel",24,[24],"David refuses to offer what costs him nothing."),
  ("1 Kings",8,[56],"Solomon at the temple dedication: not one word has failed."),
  ('2 Kings',6,[17],"Elisha prays for his servant's eyes: hills full of chariots of fire."),
  ("2 Chronicles",32,[8],"Hezekiah rallies Jerusalem against Sennacherib."),
  ("Nehemiah",4,[14],"The governor rallies the wall-builders: remember the Lord."),
  ("Job",13,[15],"Though he slay me, yet will I hope in him."),
  ("Psalms",63,[3],"Your love is better than life, from a psalm written in the desert."),
  ("Psalms",130,[5],"I wait for the Lord, from the depths."),
  ("Psalms",143,[8],"Let the morning bring me word of your unfailing love."),
  ("Proverbs",25,[11],"Apples of gold in settings of silver."),
  ("Ecclesiastes",7,[8],"The end of a matter is better than its beginning."),
  ("Isaiah",49,[16],"Engraved on the palms of my hands."),
  ("Isaiah",65,[24],"Before they call I will answer."),
  ("Jeremiah",20,[9],"His word is like a fire shut up in my bones."),
  ("Daniel",2,[21],"He changes times and seasons; he deposes kings."),
  ("Hosea",6,[3],"Let us press on to acknowledge the Lord."),
  ("Jonah",4,[2],"The prophet sulks about Nineveh being spared."),
  ("Habakkuk",2,[20],"The Lord is in his holy temple; let all the earth be silent."),
  ("Zechariah",13,[9],"I will refine them like silver."),
  ("Matthew",13,[44],"The kingdom of heaven is like treasure hidden in a field."),
  ("Matthew",22,[14],"Many are invited, but few are chosen."),
  ("Mark",9,[24],"I do believe; help me overcome my unbelief!"),
  ("Mark",2,[17],"It is not the healthy who need a doctor."),
  ("Luke",16,[10],"Whoever can be trusted with very little."),
  ("Luke",9,[62],"No one who puts a hand to the plow and looks back."),
  ('Acts',10,[34, 35],"Peter at Cornelius' house: God does not show favoritism."),
  ("Romans",12,[11],"Never be lacking in zeal."),
  ("1 Corinthians",16,[13],"Be on your guard; stand firm; be courageous; be strong."),
  ("2 Corinthians",3,[18],"Transformed into his image with ever-increasing glory."),
  ("Galatians",1,[10],"Am I now trying to win the approval of human beings, or of God?"),
  ("Colossians",4,[2],"Devote yourselves to prayer."),
  ("2 Thessalonians",3,[16],"The Lord of peace himself give you peace at all times."),
  ("2 Timothy",4,[2],"Preach the word; be prepared in season and out."),
  ("Hebrews",13,[2],"Some people have shown hospitality to angels without knowing it."),
  ("James",4,[6],"God opposes the proud but shows favor to the humble."),
  ("2 Peter",3,[8],"With the Lord a day is like a thousand years."),
  ("1 John",4,[1],"Test the spirits."),
  ("3 John",1,[11],"Do not imitate what is evil but what is good."),
  ("Revelation",22,[20],"The second-to-last verse of the Bible."),
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
    # Book-division headings ("BOOK II", "Psalms 42–72") precede the psalm number
    # at the start of each of the Psalter's five books.
    while segs and re.match(r"^\s*(BOOK [IVX]+|Psalms \d+[\u2013-]\d+)\s*$", segs[0]):
        segs = segs[1:]
    if segs and re.match(r"^\s*Psalm \d+\s*$", segs[0]):
        segs = segs[1:]
        while segs and len(segs[0]) < 120 and segs[0].strip().endswith(".") and SUPERSCRIPT.search(segs[0]):
            segs = segs[1:]
    t = " ".join(segs)
    t = re.sub(r"<[^>]+>", "", t)          # footnote / markup tags
    t = t.replace("“", "").replace("”", "").replace('"', "")
    t = re.sub(r"\s+", " ", t).strip()
    return t

# Resume cache: bolls.life rate-limits bursts (HTTP 429), so every fetched
# passage is cached on disk and a re-run only asks for what it doesn't have.
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fetch-cache.json")
try:
    CACHE = json.load(open(CACHE_PATH))
except Exception:
    CACHE = {}

def fetch(book, chapter, verses):
    key = f"{book}:{chapter}:{','.join(map(str, verses))}"
    if key in CACHE:
        return CACHE[key]
    body = json.dumps({"translations": ["NIV"], "book": book,
                       "chapter": chapter, "verses": verses}).encode()
    req = urllib.request.Request(API, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "versetap-builder"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            CACHE[key] = data
            json.dump(CACHE, open(CACHE_PATH, "w"))
            return data
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            wait = 15 * (attempt + 1)
            print(f"  rate-limited, waiting {wait}s")
            time.sleep(wait)

def ref_of(book, ch, vv):
    vs = str(vv[0]) if len(vv) == 1 else f"{vv[0]}-{vv[-1]}"
    name = "Psalm" if book == "Psalms" else book
    return f"{name} {vs}" if book in SINGLE_CHAPTER else f"{name} {ch}:{vs}"

# Pre-flight: tier sizes, duplicate refs, and Biblica's 500-verse ceiling.
_seen = set(); _verses = 0
for _label, _refs in TIERS:
    assert len(_refs) % 6 == 0, f"{_label}: {len(_refs)} refs (keep tiers a multiple of 6 for the scheduler)"
    for _bk, _ch, _vv, _ctx in _refs:
        assert _bk in IDX, f"unknown book {_bk}"
        _r = ref_of(_bk, _ch, _vv)
        assert _r not in _seen, f"duplicate {_r}"
        _seen.add(_r); _verses += len(_vv)
assert _verses <= 500, f"{_verses} verses exceeds Biblica's 500-verse permission ceiling"
print(f"{len(_seen)} passages, {_verses} verses (ceiling 500), tiers: {[len(r) for _, r in TIERS]}")

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
        time.sleep(0.6)
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
