"""Curated question bank for deliberation experiments."""

QUESTION_BANK = [
    "Is it ethical to use AI in the judicial system?",
    "Should the federal minimum wage be raised to $20 per hour?",
    "Should the U.S. create a pathway to citizenship for all undocumented immigrants currently living in the country?",
]


def short_label(question: str, max_len: int = 40) -> str:
    """Return a short label for filenames and logging."""
    return question[:max_len].rstrip("? ").strip()
