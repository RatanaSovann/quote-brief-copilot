"""Step 2: enquiry text -> job card, using Sonnet 5.5."""
from pathlib import Path

import config
import llm
from schema import JobCard

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "extract.txt"

# Medium effort: extraction needs some care (conflicts, hedged wording) but
# not deep reasoning. Raise it only if accuracy in Stage 4 says so.
EFFORT = "medium"


def extract(enquiry_text, profile):
    """Returns (JobCard, CallRecord). The card is unchecked; run evidence.enforce next."""
    system = PROMPT.read_text(encoding="utf-8").format(
        business_name=profile["business_name"],
        product_types=", ".join(profile["product_types"]),
    )
    user = f"<enquiry>\n{enquiry_text}\n</enquiry>"
    return llm.call_structured("extract", config.EXTRACT_MODEL, system, user, JobCard, EFFORT)
