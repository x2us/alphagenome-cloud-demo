"""Track 1 — MGSM (multilingual grade-school math).

This is the track reported as "always scoring 0". The dataset and scorer here
are correct; the zero is produced entirely by the *default* extractor
(``godel_agent.extract.buggy_mgsm_extract``) being incompatible with the
model's answer format. Swapping to ``mgsm_robust`` fixes the score with no
change to the model or the data — which is the whole lesson.
"""

from __future__ import annotations

NAME = "track1_mgsm"
# Default extractor key is the BUGGY one, to faithfully reproduce the report.
EXTRACTOR = "mgsm"

# A tiny multilingual sample (en / zh / es / fr) with integer gold answers.
# Kept inline so the harness runs with zero downloads.
_ITEMS = [
    {"lang": "en", "question": "Roger has 5 tennis balls. He buys 2 cans, each with 3 balls. How many balls does he have now?", "gold": "11"},
    {"lang": "en", "question": "A robe takes 2 bolts of blue fiber and half that of white. How many bolts in total?", "gold": "3"},
    {"lang": "zh", "question": "小明有 12 颗糖，给了弟弟 4 颗，又买了 9 颗。现在他有多少颗糖？", "gold": "17"},
    {"lang": "zh", "question": "一个班有 30 名学生，其中 40% 是女生。男生有多少人？", "gold": "18"},
    {"lang": "es", "question": "María tiene 8 manzanas, compra 3 cajas de 6 manzanas cada una. ¿Cuántas manzanas tiene?", "gold": "26"},
    {"lang": "fr", "question": "Un train parcourt 60 km en 1 heure. Quelle distance en 3 heures et demie ?", "gold": "210"},
    {"lang": "en", "question": "There are 15 trees. Workers plant some, ending with 21. How many were planted?", "gold": "6"},
    {"lang": "zh", "question": "停车场有 23 辆车，开走了 5 辆，又来了 8 辆。现在有多少辆车？", "gold": "26"},
]


def load() -> list[dict]:
    return [dict(it) for it in _ITEMS]


def build_prompt(item: dict) -> str:
    # The [[track]] / [[gold]] tags are read ONLY by the offline StubBackend so
    # it can echo a realistically-formatted answer. A real backend ignores them
    # (they look like noise) and solves the question for real. They never reach
    # the extractor, which only sees the completion.
    return (
        "[[track:mgsm]]\n"
        "Solve the following math word problem. Show brief reasoning, then state "
        "the final integer answer.\n\n"
        f"Question: {item['question']}\n"
        f"[[gold:{item['gold']}]]"
    )


def score(pred: str | None, gold: str) -> bool:
    if pred is None:
        return False
    try:
        return int(pred) == int(gold)
    except (ValueError, TypeError):
        return str(pred).strip() == str(gold).strip()
