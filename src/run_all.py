"""Stage 5: run every enquiry through the pipeline and save it all to web/runs.json.

Run:  python src/run_all.py

The hosted demo page is static and can't call the API, so it shows these saved runs.
Each enquiry runs against the business it was sent to (its label's profile).
Costs real money: 10 runs, about 15 AU cents.
"""
import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import config
import llm
import pipeline

ROOT = Path(__file__).resolve().parent.parent
ENQUIRIES_PER_MONTH = 100 * 52 / 12  # 100 a week


def to_record(result, seconds):
    """Everything the demo page shows for one run, as plain JSON. serve.py uses it too."""
    card = result.get("card")
    return {
        "enquiry_id": result["enquiry_id"],
        "profile": result["profile"],
        "classification": result["classification"],
        "route": result["route"],
        "card": card.model_dump() if card else None,
        "evidence_changes": result.get("evidence_changes", []),
        "gaps": result.get("gaps"),
        "reply": result.get("reply"),
        "brief": result.get("brief"),
        "seconds": round(seconds, 2),
        "calls": [{**asdict(c), "cost_aud": c.cost_aud} for c in result["calls"]],
        "cost_aud": sum(c.cost_aud for c in result["calls"]),
    }


def cost_report(runs):
    by_model = {}
    for call in (c for r in runs for c in r["calls"]):
        m = by_model.setdefault(call["model"], {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                                                "cost_usd": 0.0, "cost_aud": 0.0})
        m["calls"] += 1
        for key in ("input_tokens", "output_tokens", "cost_usd", "cost_aud"):
            m[key] += call[key]

    drafted = [r["cost_aud"] for r in runs if r["route"] == "draft_reply"]
    avg_drafted = sum(drafted) / len(drafted)
    return {
        "per_enquiry": [{"enquiry_id": r["enquiry_id"], "route": r["route"], "seconds": r["seconds"],
                         "cost_usd": r["cost_aud"] / config.AUD_PER_USD, "cost_aud": r["cost_aud"]}
                        for r in runs],
        "by_model": by_model,
        "total_aud": sum(r["cost_aud"] for r in runs),
        "avg_aud_all": sum(r["cost_aud"] for r in runs) / len(runs),
        "avg_aud_drafted": avg_drafted,
        # Upper bound: prices every message as a full enquiry, though complaints and spam cost far less.
        "monthly_aud_100_per_week": avg_drafted * ENQUIRIES_PER_MONTH,
    }


def print_report(report):
    print(f"\n{'Enquiry':<9}{'Route':<17}{'Seconds':>8}{'US cents':>10}{'AU cents':>10}")
    for e in report["per_enquiry"]:
        print(f"{e['enquiry_id']:<9}{e['route']:<17}{e['seconds']:>8.1f}"
              f"{e['cost_usd'] * 100:>10.2f}{e['cost_aud'] * 100:>10.2f}")
    print(f"\n{'Model':<20}{'Calls':>6}{'In tokens':>11}{'Out tokens':>12}{'AU cents':>10}")
    for model, m in report["by_model"].items():
        print(f"{model:<20}{m['calls']:>6}{m['input_tokens']:>11}{m['output_tokens']:>12}{m['cost_aud'] * 100:>10.2f}")
    print(f"\nTotal:                         {report['total_aud'] * 100:.2f} AU cents")
    print(f"Average per message (all):     {report['avg_aud_all'] * 100:.2f} AU cents")
    print(f"Average per drafted enquiry:   {report['avg_aud_drafted'] * 100:.2f} AU cents  (target 2-5)")
    print(f"Monthly at 100 a week:         A${report['monthly_aud_100_per_week']:.2f}  (upper bound, every message drafted)")


def main():
    profiles = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "profiles").glob("*.json")}
    paths = sorted((ROOT / "data" / "enquiries").glob("*.txt"), key=lambda p: int(p.stem[1:]))
    enquiries, runs = {}, []
    for path in paths:
        eid = path.stem
        # Only the business it went to and a display title are read from the label; no answers.
        label = json.loads((ROOT / "data" / "labels" / f"{eid}.json").read_text(encoding="utf-8"))
        pid = label["profile"]
        enquiries[eid] = {"text": path.read_text(encoding="utf-8"), "profile": pid,
                          "title": label["title"], "channel": label["channel"]}
        start = time.perf_counter()
        result = pipeline.run(eid, enquiries[eid]["text"], profiles[pid])
        runs.append(to_record(result, time.perf_counter() - start))
        print(f"{eid:<4}{pid:<20}{runs[-1]['route']:<17}{runs[-1]['cost_aud'] * 100:.2f} AU cents")
    llm.flush()

    report = cost_report(runs)
    print_report(report)

    # Written only after every run succeeded: the demo must never show a partial batch.
    out = {"run_at": datetime.now().isoformat(timespec="seconds"),
           "models": {"extract_and_reply": config.EXTRACT_MODEL, "classify": config.CLASSIFY_MODEL},
           "prices_usd_per_mtok": config.PRICES_USD_PER_MTOK, "aud_per_usd": config.AUD_PER_USD,
           # The checklist is shown on Tab 3 as "who defines complete".
           "profiles": {pid: {k: p[k] for k in ("business_name", "product_types", "always_required", "required_by_product")}
                        for pid, p in profiles.items()},
           "enquiries": enquiries, "runs": runs, "cost": report}
    (ROOT / "web" / "runs.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Saved: web/runs.json")


if __name__ == "__main__":
    main()
