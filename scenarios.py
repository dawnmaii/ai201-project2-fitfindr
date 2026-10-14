"""
The runs your test needs. 
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Criterion 3: state consistency
        "name": "state consistency check",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4: fit card content/length
        "name": "fit card under five sentences",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Criterion 5: price ceiling respected
        "name": "item is under max price",
        "query": "graphic tee under $20",
        "wardrobe": "example",
        "criterion": 5,
    }
]

WARDROBES = ("example", "empty")

def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
