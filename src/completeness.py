"""Step 4: what's missing? Decided by the profile checklist, not by the model.

The model fills in the card; this file decides whether the card is complete.
"""


def match_product(card, profile):
    """The profile's product name for this card, or None if it isn't one we sell."""
    value = card.product_type.value
    if card.product_type.status == "missing" or not isinstance(value, str):
        return None
    wanted = value.strip().lower()
    for product in profile["product_types"]:
        if product.lower() == wanted:
            return product
    return None


def check(card, profile):
    """Returns {product, out_of_scope, required, missing, conflicts}.

    Inferred fields count as present: the reply doesn't ask about them,
    but the quote brief flags them for the estimator.
    """
    product = match_product(card, profile)
    # Out of scope = they named something we don't sell (say "carport"). Nothing to ask:
    # the reply declines instead. Different from not saying a product at all,
    # which is just a missing field to ask about.
    out_of_scope = product is None and card.product_type.status != "missing"
    if out_of_scope:
        return {"product": None, "out_of_scope": True, "required": [], "missing": [], "conflicts": []}
    required = list(profile["always_required"])
    if product:
        required += profile["required_by_product"][product]

    missing = [n for n in required if getattr(card, n).status == "missing"]
    conflicts = [n for n in required if getattr(card, n).status == "conflict"]
    return {"product": product, "out_of_scope": False, "required": required, "missing": missing, "conflicts": conflicts}
