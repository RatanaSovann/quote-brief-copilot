"""Step 1: label the message with Haiku 4.5 before anything else runs.

Cheap model first, so complaints and non-enquiries never pay for Sonnet.
"""
from pathlib import Path

import config
import llm
from schema import Classification

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "classify.txt"


def classify(message_text, profile):
    """Returns (Classification, CallRecord)."""
    # No product list: whether we sell it is checked later in code (completeness), not guessed here.
    system = PROMPT.read_text(encoding="utf-8").format(business_name=profile["business_name"])
    user = f"<message>\n{message_text}\n</message>"
    # A label and one sentence: 1024 tokens is plenty, and caps the cost of a runaway answer.
    return llm.call_structured("classify", config.CLASSIFY_MODEL, system, user, Classification, max_tokens=1024)
