"""Step 8: the estimator's one-screen view, plus CSV/JSON export. Plain code.

The brief never contains a price; it's what an estimator needs to set one.
"""
import csv
import json


def build(enquiry_id, profile, card, gaps):
    fields = [
        {"field": name, "value": f.value, "status": f.status, "evidence": f.evidence,
         "required": name in gaps["required"]}
        for name, f in card
    ]
    flags = [f"{r['field']}: {r['status']}" for r in fields if r["status"] in ("inferred", "conflict")]
    if card.other_products.status != "missing":
        flags.append(f"also asked about: {card.other_products.value}")
    if gaps["out_of_scope"]:
        flags.append(f"out of scope: '{card.product_type.value}' is not one of this business's products")
    return {
        "enquiry_id": enquiry_id,
        "business": profile["business_name"],
        "product": gaps["product"],
        "missing": gaps["missing"],
        "flags": flags,
        "fields": fields,
    }


def to_json(brief, path):
    path.write_text(json.dumps(brief, indent=2), encoding="utf-8")


def to_csv(brief, path):
    # One row per field: opens straight into Excel for an estimator.
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["field", "value", "status", "evidence", "required"])
        writer.writeheader()
        writer.writerows(brief["fields"])


def as_text(brief):
    lines = [f"QUOTE BRIEF  {brief['enquiry_id']}  |  {brief['business']}  |  product: {brief['product'] or '?'}"]
    for r in brief["fields"]:
        if r["status"] == "missing" and not r["required"]:
            continue  # optional and absent: noise for the estimator
        mark = {"stated": " ", "inferred": "?", "conflict": "!", "missing": "x"}[r["status"]]
        value = "" if r["value"] is None else str(r["value"])
        lines.append(f"  {mark} {r['field']:<24}{value}")
    lines.append(f"  Missing: {', '.join(brief['missing']) or 'none'}")
    lines.append(f"  Flags:   {'; '.join(brief['flags']) or 'none'}")
    lines.append("  Key: ? inferred   ! conflict   x missing")
    return "\n".join(lines)
