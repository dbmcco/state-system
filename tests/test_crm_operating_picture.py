from pathlib import Path
import unittest

from state_system.contracts import ExampleIndex, load_json
from state_system.crm_operating_picture import build_crm_operating_picture_summary


ROOT = Path(__file__).resolve().parents[1]
CRM_FIXTURE = ROOT / "examples" / "company-memory" / "acme-crm-operating-picture.json"


class CrmOperatingPictureTests(unittest.TestCase):
    def test_crm_operating_picture_keeps_interpretation_separate_from_crm_record(self):
        picture = load_json(CRM_FIXTURE)
        summary = build_crm_operating_picture_summary(picture)

        self.assertEqual("acme_crm", summary["system_of_record_ref"])
        self.assertEqual("state_system_interpretation", summary["state_system_role"])
        self.assertEqual(1, summary["active_opportunity_count"])
        self.assertEqual(2, summary["open_loop_count"])
        self.assertEqual([], summary["hidden_sales_scores"])

    def test_crm_evidence_refs_resolve_to_fixture_records(self):
        index = ExampleIndex.load(ROOT / "examples")
        picture = load_json(CRM_FIXTURE)
        refs = set(picture["evidence_refs"])

        for relationship in picture["relationships"]:
            refs.update(relationship["evidence_refs"])
        for opportunity in picture["opportunities"]:
            refs.update(opportunity["evidence_refs"])
        for loop in picture["open_loops"]:
            refs.update(loop["evidence_refs"])

        missing = sorted(ref for ref in refs if ref not in index.by_id)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
