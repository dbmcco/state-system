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

    def test_thoughtforge_uses_meeting_idea_without_losing_provenance(self):
        index = ExampleIndex.load(ROOT / "examples")

        source = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "source-thoughtforge-meeting-idea-004.json"
        )
        package = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "thoughtforge-author-context-package-004.json"
        )
        output = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "thoughtforge-meeting-idea-model-proposal-output-004.json"
        )
        commit = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "thoughtforge-meeting-idea-commit-result-004.json"
        )
        interview_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "thoughtforge-interview-prompt-candidate-004.json"
        )
        longform_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "thoughtforge-longform-candidate-004.json"
        )
        conformance = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "conformance-no-hardcoded-author-source-free-publication-004.json"
        )

        self.assertEqual("thoughtforge", source["source_system"])
        self.assertEqual("thoughtforge_author_package", package["package_type"])
        self.assertIn(source["source_refs"][0], package["evidence_context"]["evidence_refs"])
        self.assertEqual("needs_approval", output["decision"])
        self.assertEqual("pending_approval", commit["status"])
        self.assertEqual(
            {interview_artifact["id"], longform_artifact["id"]},
            set(commit["review_signal"]["follow_up_refs"]),
        )
        self.assertEqual(
            "thoughtforge_interview_prompt_candidate",
            interview_artifact["artifact_type"],
        )
        self.assertEqual("thoughtforge_longform_candidate", longform_artifact["artifact_type"])
        self.assertEqual("pending_approval", longform_artifact["approval_status"])
        self.assertIn(
            "gdrive:doc:meeting-streamlinear-strategy-003",
            longform_artifact["payload"]["source_refs"],
        )
        self.assertNotIn("author_score", longform_artifact["payload"])
        self.assertEqual("no_hardcoded_author_source_free_publication", conformance["check_type"])
        self.assertEqual([], conformance["deterministic_judgment_rules"])
        self.assertEqual([], [
            ref
            for artifact in [interview_artifact, longform_artifact]
            for ref in artifact["evidence_refs"]
            if ref not in index.by_id
        ])

    def test_visual_forge_preserves_qualitative_creative_feedback(self):
        index = ExampleIndex.load(ROOT / "examples")

        source = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "source-visual-forge-creative-review-005.json"
        )
        package = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "visual-forge-workspace-context-package-005.json"
        )
        output = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "visual-forge-creative-review-model-proposal-output-005.json"
        )
        commit = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "visual-forge-creative-review-commit-result-005.json"
        )
        revision_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "visual-forge-revision-candidate-005.json"
        )
        memory_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "visual-forge-corpus-memory-candidate-005.json"
        )
        conformance = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "conformance-no-style-score-hidden-prompt-rewrite-005.json"
        )

        self.assertEqual("visual_forge", source["source_system"])
        self.assertEqual("visual_forge_workspace_package", package["package_type"])
        self.assertIn(source["source_refs"][0], package["evidence_context"]["evidence_refs"])
        self.assertEqual("needs_approval", output["decision"])
        self.assertEqual("pending_approval", commit["status"])
        self.assertEqual(
            {revision_artifact["id"], memory_artifact["id"]},
            set(commit["review_signal"]["follow_up_refs"]),
        )
        self.assertEqual("visual_forge_revision_candidate", revision_artifact["artifact_type"])
        self.assertEqual("visual_forge_corpus_memory_candidate", memory_artifact["artifact_type"])
        self.assertEqual("pending_approval", memory_artifact["approval_status"])
        self.assertIn("keep texture from version two", revision_artifact["payload"]["human_feedback"])
        self.assertNotIn("style_score", revision_artifact["payload"])
        self.assertNotIn("rewritten_prompt", revision_artifact["payload"])
        self.assertEqual("no_style_score_hidden_prompt_rewrite", conformance["check_type"])
        self.assertEqual([], conformance["deterministic_judgment_rules"])
        self.assertEqual([], [
            ref
            for artifact in [revision_artifact, memory_artifact]
            for ref in artifact["evidence_refs"]
            if ref not in index.by_id
        ])

    def test_crm_outcome_feeds_prospect_and_outreach_doctrine(self):
        index = ExampleIndex.load(ROOT / "examples")

        source = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "source-crm-relationship-outcome-006.json"
        )
        package = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "crm-outcome-learning-context-package-006.json"
        )
        output = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "crm-outcome-learning-model-proposal-output-006.json"
        )
        commit = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "crm-outcome-learning-commit-result-006.json"
        )
        prospect_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "prospect-referral-doctrine-candidate-006.json"
        )
        outreach_artifact = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "outreach-referral-doctrine-candidate-006.json"
        )
        conformance = load_json(
            ROOT
            / "examples"
            / "app-integrations"
            / "conformance-no-sales-score-app-local-doctrine-006.json"
        )

        self.assertEqual("lfw_ai_graph_crm", source["source_system"])
        self.assertEqual("crm_outcome_learning_package", package["package_type"])
        self.assertIn(source["source_refs"][0], package["evidence_context"]["evidence_refs"])
        self.assertEqual("needs_approval", output["decision"])
        self.assertEqual("pending_approval", commit["status"])
        self.assertEqual(
            {prospect_artifact["id"], outreach_artifact["id"]},
            set(commit["review_signal"]["follow_up_refs"]),
        )
        self.assertEqual(
            "prospect_referral_doctrine_candidate",
            prospect_artifact["artifact_type"],
        )
        self.assertEqual(
            "outreach_referral_doctrine_candidate",
            outreach_artifact["artifact_type"],
        )
        self.assertEqual("pending_approval", prospect_artifact["approval_status"])
        self.assertEqual("pending_approval", outreach_artifact["approval_status"])
        self.assertIn("relationship evidence", prospect_artifact["payload"]["learning"])
        self.assertNotIn("sales_score", prospect_artifact["payload"])
        self.assertNotIn("referral_weight", prospect_artifact["payload"])
        self.assertNotIn("tone_rule", outreach_artifact["payload"])
        self.assertEqual("no_sales_score_app_local_doctrine", conformance["check_type"])
        self.assertEqual([], conformance["deterministic_judgment_rules"])
        self.assertEqual([], [
            ref
            for artifact in [prospect_artifact, outreach_artifact]
            for ref in artifact["evidence_refs"]
            if ref not in index.by_id
        ])


if __name__ == "__main__":
    unittest.main()
