"""Step 3: code checks the model's evidence. The model's word is not enough.

Rule: a field can only be "stated" if its evidence appears verbatim in the
enquiry. Matching is exact (case, spacing, punctuation) on purpose: a loose
match would let a paraphrase pass as a quote.
"""


def enforce(card, enquiry_text):
    """Returns (checked copy of the card, list of human-readable changes)."""
    card = card.model_copy(deep=True)
    changes = []
    for name, field in card:
        if field.status == "missing":
            # Missing means nothing was found, so there can't be a value or a quote.
            if field.value is not None or field.evidence is not None:
                changes.append(f"{name}: missing field had a value/evidence, cleared")
            field.value, field.evidence = None, None
            continue

        if field.evidence and field.evidence in enquiry_text:
            continue

        if field.status == "stated":
            field.status = "inferred"
            changes.append(f"{name}: evidence not found verbatim, stated -> inferred")
        else:
            changes.append(f"{name}: evidence not found verbatim, quote removed")
        # Keep the value for a person to judge, but never show a fake quote.
        field.evidence = None
    return card, changes
