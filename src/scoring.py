"""Stage 4: score one pipeline result against its hand label. Pure code, no API calls.

Kept apart from eval.py so the scoring rules can be read (and tested) on their own.
"""
import re

# Free-text catch-all: its wording has no single right answer, so it isn't scored.
# It still goes through the evidence check and into the brief.
UNSCORED = {"notes"}


def norm(value):
    """Lower-case, punctuation out, single spaces: "Install please" == "install please"."""
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(value).lower()).split())


def field_correct(want, got):
    """A labelled 'stated' field is correct if the model also says 'stated' and either
    the values agree or both point at the same words in the enquiry.

    Exact string equality would be unfair: "approx 1500 x 1200 each" and
    "about 1500 x 1200 each" are the same fact. Evidence overlap is safe here
    because evidence.py already proved every quote is verbatim.
    """
    if got.status != "stated":
        return False
    a, b = norm(want["value"]), norm(got.value)
    if a == b or (a and a in b) or (b and b in a):
        return True
    ev_a, ev_b = want["evidence"] or "", got.evidence or ""
    return bool(ev_a and ev_b) and (ev_a in ev_b or ev_b in ev_a)


def score(result, label):
    s = {
        "id": label["id"],
        "route_ok": result["route"] == label["route"],
        "route": result["route"],
        "stated": [],          # (field, correct?) for every labelled stated field
        "invented": [],        # labelled missing, but the model filled it
        "flags": [],           # (field, wanted status, got status) for inferred/conflict labels
        "expected_asks": 0,    # how many fields the label says need asking about
        "missed_asks": [],     # should have been asked about, wasn't
        "extra_asks": [],      # asked about, but the label says it was given
        "unlabelled": [],      # model says 'stated' on a field the label doesn't cover: review by eye
        "guardrail_hits": [],
        "words": None,
        "scope_ok": None,      # draft_reply labels only: did code agree it's in / out of scope?
    }
    if label["route"] != "draft_reply":
        return s

    expected_asks = set(label["expected_missing"]) | set(label["expected_conflicts"])
    s["expected_asks"] = len(expected_asks)
    want_out = label.get("in_scope") is False
    if result["route"] != "draft_reply":
        s["scope_ok"] = False
        # Wrongly routed: nothing was extracted, so every labelled fact counts as lost.
        s["stated"] = [(n, False) for n, f in label["fields"].items()
                       if f["status"] == "stated" and n not in UNSCORED]
        s["missed_asks"] = sorted(expected_asks)
        return s

    card = result["card"]
    s["scope_ok"] = result["gaps"]["out_of_scope"] == want_out
    for name, want in label["fields"].items():
        if name in UNSCORED:
            continue
        got = getattr(card, name)
        if want["status"] == "stated":
            s["stated"].append((name, field_correct(want, got)))
        elif want["status"] == "missing" and got.status != "missing":
            s["invented"].append(name)
        elif want["status"] in ("inferred", "conflict"):
            s["flags"].append((name, want["status"], got.status))
    s["unlabelled"] = [n for n, f in card
                       if n not in label["fields"] and n not in UNSCORED and f.status == "stated"]

    asked = set(result["gaps"]["missing"]) | set(result["gaps"]["conflicts"])
    s["missed_asks"] = sorted(expected_asks - asked)
    s["extra_asks"] = sorted(asked - expected_asks)
    s["guardrail_hits"] = result["reply"]["hits"]
    s["words"] = len(result["reply"]["body"].split())
    return s


def summarise(scores):
    """The SPEC.md pass bars, computed over every scored enquiry."""
    stated = [ok for s in scores for _, ok in s["stated"]]
    expected = sum(s["expected_asks"] for s in scores)
    missed = sum(len(s["missed_asks"]) for s in scores)
    recall = (expected - missed) / expected if expected else 1.0
    words = [s["words"] for s in scores if s["words"] is not None]
    scope = [s["scope_ok"] for s in scores if s["scope_ok"] is not None]
    accuracy = sum(stated) / len(stated) if stated else 0.0
    return [
        # (check, measured, bar, passed)
        ("Field accuracy (stated fields)", f"{accuracy:.0%} ({sum(stated)}/{len(stated)})", ">= 90%", accuracy >= 0.9),
        ("Invented facts", str(sum(len(s["invented"]) for s in scores)), "0",
         all(not s["invented"] for s in scores)),
        ("Missing-info recall", f"{recall:.0%} ({expected - missed}/{expected})", "100%", missed == 0),
        ("Price guardrail breaches", str(sum(bool(s["guardrail_hits"]) for s in scores)), "0",
         all(not s["guardrail_hits"] for s in scores)),
        ("Routing", f"{sum(s['route_ok'] for s in scores)}/{len(scores)} correct", "all", all(s["route_ok"] for s in scores)),
        ("In / out of scope", f"{sum(scope)}/{len(scope)} correct", "all", all(scope)),
        ("Reply length", f"max {max(words)} words" if words else "no drafts", "< 120", all(w < 120 for w in words)),
    ]
