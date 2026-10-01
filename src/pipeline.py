"""The whole pipeline for one enquiry, steps 1-8. Step 9 (approve) is always a person.

Kept separate from run_one.py so run_all.py (Stage 5) runs exactly the same steps.
"""
import brief
import completeness
import evidence
import guardrails
import reply
import router
from classify import classify
from extract import extract


def run(enquiry_id, enquiry_text, profile):
    """Returns a dict with everything a person (or the eval) needs to see."""
    result = {"enquiry_id": enquiry_id, "profile": profile["profile_id"], "calls": []}

    label, call = classify(enquiry_text, profile)
    result["calls"].append(call)
    result["classification"] = label.model_dump()
    result["route"] = router.route(label.label)
    if result["route"] != "draft_reply":
        # Stop here: complaints and non-enquiries never reach Sonnet.
        return result

    raw_card, call = extract(enquiry_text, profile)
    result["calls"].append(call)
    card, result["evidence_changes"] = evidence.enforce(raw_card, enquiry_text)
    gaps = completeness.check(card, profile)

    body, call = reply.draft(enquiry_text, card, gaps, profile)
    result["calls"].append(call)
    text = reply.sign(body, profile)
    hits = guardrails.screen(text)

    result["card"] = card
    result["gaps"] = gaps
    # Not a block: declining politely is still a reply worth sending, but a person checks it first.
    warnings = []
    if gaps["out_of_scope"]:
        warnings.append(f"Out of scope: '{card.product_type.value}' isn't one of this business's products. "
                        "The draft declines; check that's right before sending.")
    if card.other_products.status != "missing":
        warnings.append(f"They also asked about {card.other_products.value}. "
                        "The draft only covers one product; answer the rest yourself.")
    result["reply"] = {"body": body, "text": text, "blocked": bool(hits), "hits": hits, "warnings": warnings}
    result["brief"] = brief.build(enquiry_id, profile, card, gaps)
    return result
