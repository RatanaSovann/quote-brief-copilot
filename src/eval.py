"""Stage 4: run every labelled enquiry through the pipeline and score it against SPEC.md's pass bars.

Run:  python src/eval.py            (all of E1-E10, writes web/eval.json)
      python src/eval.py E4 E6      (just these; quicker and cheaper while fixing one failure)

Costs real money: about 10 x (1 Haiku + 2 Sonnet calls). The total is printed at the end.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import llm
import pipeline
import scoring

ROOT = Path(__file__).resolve().parent.parent


def print_one(s):
    stated_ok = sum(ok for _, ok in s["stated"])
    line = f"{s['id']:<4}route {'ok ' if s['route_ok'] else 'BAD'} {s['route']:<16}"
    if s["stated"]:
        line += f"stated {stated_ok}/{len(s['stated'])}  "
    if s["words"] is not None:
        line += f"{s['words']} words"
    print(line)
    for name, ok in s["stated"]:
        if not ok:
            print(f"      wrong:     {name}")
    for name in s["invented"]:
        print(f"      INVENTED:  {name} (label says missing)")
    for name, want, got in s["flags"]:
        print(f"      flag:      {name} label={want} model={got}{'' if want == got else '  <- differs'}")
    for name in s["missed_asks"]:
        print(f"      NOT ASKED: {name}")
    for name in s["extra_asks"]:
        print(f"      extra ask: {name}")
    if s["scope_ok"] is False:
        print("      SCOPE:     in / out of scope call disagrees with the label")
    for hit in s["guardrail_hits"]:
        print(f"      GUARDRAIL: {hit['rule']} -> \"{hit['text']}\"")
    if s["unlabelled"]:
        print(f"      review:    stated but not labelled: {', '.join(s['unlabelled'])}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*", help="enquiry ids; default is all")
    args = parser.parse_args()

    label_files = sorted((ROOT / "data" / "labels").glob("*.json"), key=lambda p: int(p.stem[1:]))
    if args.ids:
        label_files = [f for f in label_files if f.stem in args.ids]

    scores, records, total = [], [], 0.0
    for lf in label_files:
        label = json.loads(lf.read_text(encoding="utf-8"))
        text = (ROOT / "data" / "enquiries" / f"{lf.stem}.txt").read_text(encoding="utf-8")
        profile = json.loads((ROOT / "profiles" / f"{label['profile']}.json").read_text(encoding="utf-8"))
        result = pipeline.run(lf.stem, text, profile)
        s = scoring.score(result, label)
        print_one(s)
        cost = sum(c.cost_aud for c in result["calls"])
        total += cost
        scores.append(s)
        card = result.get("card")  # absent when the enquiry was routed away from drafting
        # Save what the model actually said, so a failed field can be diagnosed without a paid rerun.
        records.append({**s, "cost_aud": round(cost, 5),
                        "card": card.model_dump() if card else None,
                        "evidence_changes": result.get("evidence_changes", []),
                        "reply": result.get("reply", {}).get("text")})
    llm.flush()

    print(f"\n{'Check':<32}{'Measured':<22}{'Bar':<10}Result")
    bars = scoring.summarise(scores)
    for check, measured, bar, passed in bars:
        print(f"{check:<32}{measured:<22}{bar:<10}{'PASS' if passed else 'FAIL'}")
    print(f"\nCost of this eval: {total * 100:.2f} AU cents for {len(scores)} enquiries")

    if not args.ids:
        # Only a full run is the record of truth for the demo page (Tab 3).
        out = {"run_at": datetime.now().isoformat(timespec="seconds"),
               "bars": [dict(zip(["check", "measured", "bar", "passed"], b)) for b in bars],
               "enquiries": records, "cost_aud": round(total, 5)}
        (ROOT / "web" / "eval.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("Saved: web/eval.json")


if __name__ == "__main__":
    main()
