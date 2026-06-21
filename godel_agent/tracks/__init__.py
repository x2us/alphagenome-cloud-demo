"""The three competition tracks (赛道).

Track 1: MGSM   — multilingual grade-school math (answer = integer)
Track 2: GPQA   — graduate science multiple choice (answer = letter A-D)
Track 3: Game24 — Game of 24 search (answer = expression == 24)

Each track exposes:
    NAME        : str
    EXTRACTOR   : key into godel_agent.extract.EXTRACTORS used by default
    load()      -> list[dict]  items with 'question' and 'gold'
    score(pred, gold) -> bool
    build_prompt(item) -> str
"""

from . import mgsm, gpqa, game24

TRACKS = {
    "track1_mgsm": mgsm,
    "track2_gpqa": gpqa,
    "track3_game24": game24,
}
