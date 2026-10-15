"""Regression checks for the fictional assignment fixture, NOT agent heuristics."""
import argparse
import json
from pathlib import Path
import re
from agent import SECTIONS, save_json


def evaluate(folder):
    result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    documents = json.loads((folder / "documents.json").read_text(encoding="utf-8"))["documents"]
    by_file = {d["file"]: d["id"] for d in documents}
    decisions = {d["source_id"]: d["disposition"] for d in result["source_decisions"]}
    all_claims = [c for s in SECTIONS for c in result[s]]
    text = " ".join(c["text"] for c in all_claims)
    snapshot = " ".join(c["text"] for c in result["snapshot"])
    bears = " ".join(c["text"] for c in result["bear_case"])
    questions = " ".join(c["text"] for c in result["open_questions"])
    get = lambda prefix: next(sid for name, sid in by_file.items() if name.startswith(prefix))
    def has_citation(section, sid):
        return any(e["source_id"] == sid for c in result[section] for e in c["evidence"])
    tests = {
        "business_and_latest_results": bool(re.search(r"manufactur|power cables", snapshot, re.I)) and "1,248" in snapshot and "82" in snapshot,
        "revenue_conflict_explained_and_both_sources_cited": "1,428" in questions and "1,248" in questions and has_citation("open_questions", get("businessdaily")) and has_citation("open_questions", get("ir_press")),
        "current_pledge_and_denominator": "4.1%" in text and "promoter holding" in text.lower(),
        "latest_gst_risk_in_bear_case": "46.3" in bears and has_citation("bear_case", get("nse_announcement")),
        "working_capital_risk": "96" in bears and "78" in bears,
        "wrong_entity_excluded": decisions.get(get("nagpur")) == "exclude" and not any(e["source_id"] == get("nagpur") for c in all_claims for e in c["evidence"]),
        "promotional_injection_excluded": decisions.get(get("multibagger")) == "exclude" and not re.search(r"strong buy|consensus is positive|60% upside", text, re.I),
        "all_claims_have_evidence": all(c["evidence"] for c in all_claims),
    }
    return {"passed": sum(tests.values()), "total": len(tests), "checks": tests,
            "note": "Fixture-specific presence/structure checks; semantic support also needs review."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", nargs="+")
    args = parser.parse_args()
    for name in args.folders:
        folder = Path(name)
        report = evaluate(folder)
        save_json(folder / "evaluation.json", report)
        print(f"{name}: {report['passed']}/{report['total']}")
        for check, passed in report["checks"].items():
            print(f"  {'PASS' if passed else 'FAIL'} {check}")
