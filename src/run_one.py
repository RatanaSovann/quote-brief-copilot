"""Run the full pipeline on one enquiry and print what a person would review.

Run:  python src/run_one.py E1
      python src/run_one.py E1 --profile windows_doors   (try another profile)
      python src/run_one.py --file my_test.txt --profile outdoor_structures
      python src/run_one.py E1 --export   (also save the brief to out/<id>_brief.json and .csv)
"""
import argparse
import json
from pathlib import Path

import brief
import llm
import pipeline

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def load(args):
    if args.file:
        if not args.profile:
            raise SystemExit("--file needs --profile (there's no label to read it from)")
        return Path(args.file).stem, Path(args.file).read_text(encoding="utf-8"), args.profile
    text = (ROOT / "data" / "enquiries" / f"{args.enquiry_id}.txt").read_text(encoding="utf-8")
    # The label only tells us which business the enquiry was sent to; nothing else is read from it.
    label = json.loads((ROOT / "data" / "labels" / f"{args.enquiry_id}.json").read_text(encoding="utf-8"))
    return args.enquiry_id, text, args.profile or label["profile"]


def print_card(card):
    print(f"{'field':<24}{'status':<10}{'value':<40}evidence")
    for name, f in card:
        value = "" if f.value is None else str(f.value)
        print(f"{name:<24}{f.status:<10}{value[:38]:<40}{f.evidence or ''}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("enquiry_id", nargs="?", help="e.g. E1")
    parser.add_argument("--profile", help="profile id; defaults to the one in the enquiry's label")
    parser.add_argument("--file", help="run your own enquiry text file instead of E1-E8")
    parser.add_argument("--export", action="store_true", help="save the brief as JSON and CSV in out/")
    args = parser.parse_args()
    if not (args.enquiry_id or args.file):
        parser.error("give an enquiry id (E1) or --file")

    enquiry_id, text, profile_id = load(args)
    profile = json.loads((ROOT / "profiles" / f"{profile_id}.json").read_text(encoding="utf-8"))
    result = pipeline.run(enquiry_id, text, profile)
    llm.flush()

    c = result["classification"]
    print(f"{enquiry_id}  profile: {profile_id}")
    print(f"Classified: {c['label']}  ({c['reason']})")
    print(f"Route: {result['route']}")

    if result["route"] == "draft_reply":
        print()
        print_card(result["card"])
        changes = result["evidence_changes"]
        print("\nEvidence check:", "no changes" if not changes else "")
        for line in changes:
            print(f"  - {line}")

        r = result["reply"]
        status = "BLOCKED - do not send, edit first" if r["blocked"] else "passed screen, awaiting approval"
        print(f"\n--- DRAFT REPLY ({status}) ---\n{r['text']}\n---")
        for w in r["warnings"]:
            print(f"  CHECK: {w}")
        for hit in r["hits"]:
            print(f"  guardrail: {hit['rule']} -> \"{hit['text']}\"")

        print("\n" + brief.as_text(result["brief"]))
        if args.export:
            OUT.mkdir(exist_ok=True)
            brief.to_json(result["brief"], OUT / f"{enquiry_id}_brief.json")
            brief.to_csv(result["brief"], OUT / f"{enquiry_id}_brief.csv")
            print(f"  Saved: out/{enquiry_id}_brief.json, .csv")
    else:
        print("No extraction, no draft. " + ("A person should handle this." if result["route"] == "route_to_person" else "Ignored."))

    print("\nCost:")
    total = 0
    for call in result["calls"]:
        total += call.cost_aud
        print(f"  {call.step:<9}{call.model:<20}{call.input_tokens:>6} in /{call.output_tokens:>6} out  "
              f"{call.seconds:>5}s  {call.cost_aud * 100:.2f} AU cents")
    print(f"  total{'':<24}{total * 100:.2f} AU cents")


if __name__ == "__main__":
    main()
