"""Step 7: screen every draft for prices, discounts and time promises. Plain regex.

The prompt already says "never", but a prompt is a request, not a guarantee.
This is the guarantee. It errs towards blocking: a false alarm costs a person
ten seconds of editing; a promised price or date can cost the business.
"""
import re

MONTHS = "January|February|March|April|June|July|August|September|October|November|December"
WEEKDAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
COUNT = r"(?:\d+|one|two|three|four|five|six|a few|a couple of)"

# (rule name, pattern, flags). Month and weekday names are case-sensitive
# so "march" (the verb) or "may" (as in "you may") don't trip them.
RULES = [
    ("price", r"\$|\bAUD\b|\bdollars?\b|\bbucks\b", re.I),
    ("price", r"\b\d+(?:\.\d+)?\s?k\b", 0),                     # "5k", "2.5 k"
    ("discount", r"\bdiscount|\d\s?%|\bper ?cent\b|\bspecial offer|\bpromo|\bon sale\b", re.I),
    ("date", rf"\b(?:{MONTHS})\b|\b(?:{WEEKDAYS})\b", 0),
    ("date", r"\b(?:in|by|before|until|early|mid|late|end of) May\b|\bMay \d", 0),
    ("date", r"\b(?:Christmas|Easter|New Year)\b", re.I),
    ("date", r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", 0),            # 29/9, 01/11/2026
    ("date", r"\b(?:today|tomorrow|tonight|fortnight)\b", re.I),
    ("lead_time", rf"\b{COUNT}\s*(?:-\s*\d+\s*)?(?:business |working )?(?:days?|weeks?|months?)\b", re.I),
    ("lead_time", r"\b(?:next|this|within a|in a) (?:week|month)\b", re.I),
]
_COMPILED = [(name, re.compile(pattern, flags)) for name, pattern, flags in RULES]


def screen(text):
    """Returns a list of {rule, text} hits. Empty list = the draft may go to a person."""
    hits = []
    for name, pattern in _COMPILED:
        for m in pattern.finditer(text):
            hits.append({"rule": name, "text": m.group(0)})
    return hits
