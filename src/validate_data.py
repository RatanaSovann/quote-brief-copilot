"""Stage 1: check that profiles, enquiries and labels agree with each other.

Why this exists: the labels are our definition of "correct". If a label is
wrong, every later accuracy score is wrong too. So we test the test data first.

Run:  python src/validate_data.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
ENQUIRIES = ROOT / "data" / "enquiries"
LABELS = ROOT / "data" / "labels"

STATUSES = {"stated", "inferred", "missing", "conflict"}
ROUTES = {"draft_reply", "route_to_person", "skip"}
KNOWN_FIELDS = {
    "customer_name", "contact", "suburb", "product_type", "other_products", "timeframe",
    "dimensions", "material_or_finish", "colour", "quantity",
    "install_required", "site_access",
    "budget_mentioned", "attachments_referenced", "notes",
}


def enquiry_order(path):
    """E2 before E10: sort by the number, not the text."""
    return int(path.stem[1:])


def load_profiles():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in PROFILES.glob("*.json")}


def check_profile(pid, prof):
    errors = []
    for key in ["business_name", "product_types", "always_required", "required_by_product", "reply_tone", "sign_off"]:
        if key not in prof:
            errors.append(f"missing key '{key}'")
    for product in prof.get("product_types", []):
        if product not in prof.get("required_by_product", {}):
            errors.append(f"product '{product}' has no required-field list")
    all_fields = set(prof.get("always_required", []))
    for fields in prof.get("required_by_product", {}).values():
        all_fields |= set(fields)
    unknown = all_fields - KNOWN_FIELDS
    if unknown:
        errors.append(f"unknown fields {sorted(unknown)}")
    return errors


def required_fields(prof, product):
    return prof["always_required"] + prof["required_by_product"].get(product, [])


def check_label(label, enquiry_text, profiles):
    errors = []
    prof = profiles.get(label["profile"])
    if prof is None:
        return [f"profile '{label['profile']}' not found"]
    if label["route"] not in ROUTES:
        errors.append(f"route '{label['route']}' invalid")

    # Evidence rule: anything not 'missing' must quote the enquiry word for word.
    for name, field in label["fields"].items():
        if name not in KNOWN_FIELDS:
            errors.append(f"{name}: unknown field")
        status = field["status"]
        if status not in STATUSES:
            errors.append(f"{name}: bad status '{status}'")
        elif status == "missing":
            if field["value"] is not None or field["evidence"] is not None:
                errors.append(f"{name}: missing fields must have value and evidence = null")
        else:
            ev = field["evidence"]
            if not ev:
                errors.append(f"{name}: '{status}' field has no evidence")
            elif ev not in enquiry_text:
                errors.append(f"{name}: evidence not found in enquiry -> \"{ev}\"")

    # Out of scope: they asked for something we don't sell, so the reply asks for nothing.
    if label["route"] == "draft_reply" and label.get("in_scope") is False:
        if label["product_type"] in prof["product_types"]:
            errors.append(f"out-of-scope label names '{label['product_type']}', which the profile sells")
        if label["expected_missing"] or label["expected_conflicts"]:
            errors.append("out-of-scope enquiries expect nothing to be asked")
    # Only full, in-scope enquiries need a complete checklist.
    elif label["route"] == "draft_reply":
        product = label["product_type"]
        if product not in prof["product_types"]:
            errors.append(f"product '{product}' not in profile '{label['profile']}'")
        required = required_fields(prof, product)
        for name in required:
            if name not in label["fields"]:
                errors.append(f"{name}: required by profile but not labelled")
        missing = sorted(n for n in required if label["fields"].get(n, {}).get("status") == "missing")
        if missing != sorted(label["expected_missing"]):
            errors.append(f"expected_missing {sorted(label['expected_missing'])} != fields marked missing {missing}")

    conflicts = sorted(n for n, f in label["fields"].items() if f["status"] == "conflict")
    if conflicts != sorted(label.get("expected_conflicts", [])):
        errors.append(f"expected_conflicts {label.get('expected_conflicts')} != fields marked conflict {conflicts}")
    return errors


def main():
    failed = False
    profiles = load_profiles()
    print(f"Profiles ({len(profiles)})")
    for pid, prof in profiles.items():
        errs = check_profile(pid, prof)
        failed |= bool(errs)
        print(f"  {'PASS' if not errs else 'FAIL'}  {pid}")
        for e in errs:
            print(f"        - {e}")

    label_files = sorted(LABELS.glob("*.json"), key=enquiry_order)
    print(f"\nEnquiries + labels ({len(label_files)})")
    for lf in label_files:
        label = json.loads(lf.read_text(encoding="utf-8"))
        enquiry = ENQUIRIES / f"{lf.stem}.txt"
        if not enquiry.exists():
            errs = [f"no enquiry file {enquiry.name}"]
        else:
            errs = check_label(label, enquiry.read_text(encoding="utf-8"), profiles)
        failed |= bool(errs)
        print(f"  {'PASS' if not errs else 'FAIL'}  {lf.stem}  [{label['route']}]  {label['tests']}")
        for e in errs:
            print(f"        - {e}")

    print("\nAll checks passed." if not failed else "\nSome checks FAILED - fix the labels or profiles above.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
