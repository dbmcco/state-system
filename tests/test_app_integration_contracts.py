from pathlib import Path
import unittest

from state_system.contracts import ExampleIndex, load_json, validate_all_examples


ROOT = Path(__file__).resolve().parents[1]


class AppIntegrationContractTests(unittest.TestCase):
    def test_app_integration_examples_validate(self):
        results = validate_all_examples(ROOT)
        app_results = [
            result
            for result in results
            if "app-integrations" in result.path.parts
            and result.path.suffix == ".json"
        ]

        self.assertGreater(len(app_results), 0)
        self.assertEqual([], [result for result in app_results if not result.ok])

    def test_prospect_opportunity_package_becomes_outreach_candidate(self):
        index = ExampleIndex.load(ROOT / "examples")

        source = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "source-prospect-campaign-research-001.json"
        )
        package = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "prospect-opportunity-context-package-001.json"
        )
        output = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "prospect-to-outreach-model-proposal-output-001.json"
        )
        commit = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "prospect-to-outreach-commit-result-001.json"
        )
        artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "outreach-candidate-package-001.json"
        )
        conformance = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "conformance-no-hidden-fit-scoring-001.json"
        )

        self.assertEqual("prospect_researcher", source["source_system"])
        self.assertEqual("prospect_opportunity_package", package["package_type"])
        self.assertIn(source["source_refs"][0], package["evidence_context"]["evidence_refs"])
        self.assertEqual("propose_updates", output["decision"])
        self.assertTrue(
            any(
                proposal["target"]["app_ref"] == "app.outreach-engine"
                for proposal in output["action_proposals"]
            )
        )
        self.assertEqual("pending_approval", commit["status"])
        self.assertIn(artifact["id"], commit["review_signal"]["follow_up_refs"])
        self.assertEqual(package["id"], artifact["source_package_ref"])
        self.assertEqual(commit["id"], artifact["commit_result_ref"])
        self.assertEqual("outreach_candidate_package", artifact["artifact_type"])
        self.assertEqual("model_interpretation", artifact["handoff_basis"])
        self.assertIn("crm:contact:aurora-mills:morgan-chen", artifact["contact_refs"])
        self.assertEqual("no_hidden_scoring", conformance["check_type"])
        self.assertEqual([], conformance["deterministic_judgment_rules"])
        self.assertEqual([], [
            ref for ref in artifact["evidence_refs"] if ref not in index.by_id
        ])

    def test_outreach_reply_creates_crm_handoff_and_secondary_contacts(self):
        index = ExampleIndex.load(ROOT / "examples")

        source = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "source-outreach-email-reply-002.json"
        )
        package = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "outreach-engagement-context-package-002.json"
        )
        output = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "outreach-reply-routing-model-proposal-output-002.json"
        )
        commit = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "outreach-reply-crm-secondary-contacts-commit-result-002.json"
        )
        crm_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "crm-relationship-update-002.json"
        )
        contacts_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "prospect-secondary-contact-candidates-002.json"
        )
        intelligence_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "outreach-engagement-intelligence-002.json"
        )
        conformance = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "conformance-no-regex-reply-routing-002.json"
        )

        self.assertEqual("outreach_engine", source["source_system"])
        self.assertEqual("outreach_engagement_package", package["package_type"])
        self.assertIn(source["source_refs"][0], package["evidence_context"]["evidence_refs"])
        self.assertEqual("needs_approval", output["decision"])
        self.assertGreaterEqual(len(output["action_proposals"]), 3)
        self.assertEqual("pending_approval", commit["status"])
        self.assertEqual(
            {
                crm_artifact["id"],
                contacts_artifact["id"],
                intelligence_artifact["id"],
            },
            set(commit["review_signal"]["follow_up_refs"]),
        )
        self.assertEqual("crm_relationship_update", crm_artifact["artifact_type"])
        self.assertEqual("prospect_secondary_contact_candidates", contacts_artifact["artifact_type"])
        self.assertEqual("outreach_engagement_intelligence", intelligence_artifact["artifact_type"])
        self.assertIn("crm:contact:aurora-mills:priya-shah", contacts_artifact["contact_refs"])
        self.assertIn("crm:contact:aurora-mills:eli-roberts", contacts_artifact["contact_refs"])
        self.assertEqual("no_regex_routing", conformance["check_type"])
        self.assertEqual([], conformance["deterministic_judgment_rules"])
        self.assertEqual([], [
            ref
            for artifact in [crm_artifact, contacts_artifact, intelligence_artifact]
            for ref in artifact["evidence_refs"]
            if ref not in index.by_id
        ])

    def test_meeting_creates_cross_app_coordination_updates(self):
        index = ExampleIndex.load(ROOT / "examples")

        source = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "source-meeting-coordination-003.json"
        )
        package = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "meeting-coordination-context-package-003.json"
        )
        output = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "meeting-coordination-model-proposal-output-003.json"
        )
        commit = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "meeting-coordination-commit-result-003.json"
        )
        task_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "work-follow-up-task-package-003.json"
        )
        crm_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "crm-referral-update-003.json"
        )
        prospect_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "prospect-referral-signal-003.json"
        )
        thoughtforge_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "thoughtforge-idea-candidate-003.json"
        )
        conformance = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "conformance-no-keyword-extraction-source-free-ideas-003.json"
        )

        self.assertEqual("meeting_manager", source["source_system"])
        self.assertEqual("meeting_coordination_package", package["package_type"])
        self.assertIn(source["source_refs"][0], package["evidence_context"]["evidence_refs"])
        self.assertEqual("needs_approval", output["decision"])
        self.assertGreaterEqual(len(output["action_proposals"]), 4)
        self.assertEqual("pending_approval", commit["status"])
        self.assertEqual(
            {
                task_artifact["id"],
                crm_artifact["id"],
                prospect_artifact["id"],
                thoughtforge_artifact["id"],
            },
            set(commit["review_signal"]["follow_up_refs"]),
        )
        self.assertEqual("work_follow_up_task_package", task_artifact["artifact_type"])
        self.assertEqual("crm_referral_update", crm_artifact["artifact_type"])
        self.assertEqual("prospect_referral_signal", prospect_artifact["artifact_type"])
        self.assertEqual("thoughtforge_idea_candidate", thoughtforge_artifact["artifact_type"])
        self.assertEqual("pending_approval", crm_artifact["approval_status"])
        self.assertEqual("pending_approval", thoughtforge_artifact["approval_status"])
        self.assertEqual("no_keyword_extraction_source_free_ideas", conformance["check_type"])
        self.assertEqual([], conformance["deterministic_judgment_rules"])
        self.assertEqual([], [
            ref
            for artifact in [
                task_artifact,
                crm_artifact,
                prospect_artifact,
                thoughtforge_artifact,
            ]
            for ref in artifact["evidence_refs"]
            if ref not in index.by_id
        ])


if __name__ == "__main__":
    unittest.main()
