import copy
import json
from pathlib import Path
import tempfile
import unittest
from datetime import date
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import ROOT, load_documents, validate, render


class EvidenceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents, _ = load_documents(ROOT / "research_pack", date(2026, 9, 23))

    def candidate(self):
        # Use a recorded candidate as a realistic mutation target. No model call.
        return json.loads((ROOT / "runs/v3/result.json").read_text(encoding="utf-8"))

    def test_reference_packet(self):
        self.assertEqual(len(self.documents), 8)

    def test_future_source_is_removed(self):
        docs, skipped = load_documents(ROOT / "research_pack", date(2026, 8, 15))
        self.assertEqual(len(docs), 6)
        self.assertEqual(len(skipped), 2)
        self.assertTrue(all(d["published"] <= "2026-08-15" for d in docs))

    def test_invalid_packet_fails_actionably(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "bad.md").write_text("No front matter", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "front matter"):
                load_documents(Path(folder), date(2026, 9, 23))

    def test_final_candidate_is_mechanically_valid(self):
        self.assertEqual(validate(self.candidate(), self.documents, "SRVCABLE", "2026-09-23"), [])

    def test_fabricated_quote_is_rejected(self):
        result = self.candidate()
        result["snapshot"][0]["evidence"][0]["quote"] = "This claim does not exist in any source."
        self.assertTrue(any("not an exact passage" in s for s in validate(result, self.documents, "SRVCABLE", "2026-09-23")))

    def test_unknown_source_is_rejected(self):
        result = self.candidate()
        result["bear_case"][0]["evidence"][0]["source_id"] = "S999"
        self.assertTrue(any("unknown source" in s for s in validate(result, self.documents, "SRVCABLE", "2026-09-23")))

    def test_excluded_source_cannot_support_claim(self):
        result = self.candidate()
        sid = result["snapshot"][0]["evidence"][0]["source_id"]
        next(d for d in result["source_decisions"] if d["source_id"] == sid)["disposition"] = "exclude"
        self.assertTrue(any("excluded source" in s for s in validate(result, self.documents, "SRVCABLE", "2026-09-23")))

    def test_ticker_and_date_cannot_drift(self):
        result = self.candidate()
        result["as_of"] = "2026-10-15"
        self.assertTrue(any("as-of" in s for s in validate(result, self.documents, "SRVCABLE", "2026-09-23")))

    def test_missing_claim_evidence_is_rejected(self):
        result = self.candidate()
        result["bull_case"][0]["evidence"] = []
        self.assertTrue(any("missing supporting evidence" in s for s in validate(result, self.documents, "SRVCABLE", "2026-09-23")))

    def test_incomplete_triage_is_rejected(self):
        result = self.candidate()
        result["source_decisions"].pop()
        self.assertTrue(any("every supplied source" in s for s in validate(result, self.documents, "SRVCABLE", "2026-09-23")))

    def test_brief_is_exact_renderer_output(self):
        self.assertEqual(render(self.candidate(), self.documents), (ROOT / "runs/v3/brief.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
