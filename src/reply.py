"""Step 6: draft a reply that asks only for what's missing or conflicting."""
from pathlib import Path

import config
import llm
from schema import ReplyDraft

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "reply.txt"

# Low effort: a short, rule-bound email doesn't need deep reasoning.
EFFORT = "low"


def _bullets(lines):
    return "\n".join(f"- {line}" for line in lines) or "- nothing"


def draft(enquiry_text, card, gaps, profile):
    """Returns (reply body, CallRecord). Use sign() to add the sign-off.

    The model only sees which fields to ask about; code chose them (completeness.check).
    """
    system = PROMPT.read_text(encoding="utf-8").format(
        business_name=profile["business_name"],
        reply_tone=profile["reply_tone"],
        product_types=", ".join(profile["product_types"]),
    )
    ask = [name.replace("_", " ") for name in gaps["missing"]]
    out_of_scope = f"yes, they asked for {card.product_type.value}" if gaps["out_of_scope"] else "no"
    clarify = [f"{name.replace('_', ' ')}: {getattr(card, name).value}" for name in gaps["conflicts"]]
    user = (
        f"<enquiry>\n{enquiry_text}\n</enquiry>\n\n"
        f"Customer name: {card.customer_name.value or 'unknown'}\n"
        f"Out of scope: {out_of_scope}\n\n"
        f"Ask for:\n{_bullets(ask)}\n\n"
        f"Clarify:\n{_bullets(clarify)}"
    )
    result, record = llm.call_structured("reply", config.EXTRACT_MODEL, system, user, ReplyDraft, EFFORT)
    return result.body.strip(), record


def sign(body, profile):
    # Sign-off comes from the profile, so changing it never needs a prompt change.
    return f"{body}\n\n{profile['sign_off']}"
