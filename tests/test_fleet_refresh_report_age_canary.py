from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from state_system.contracts import load_json, validate_schema
from state_system.fleet_refresh import (
    check_fleet_refresh_report_age,
    run_fleet_refresh,
)

ROOT = Path(__file__).resolve().parents[1]


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_report(path: Path, *, checked_at: str, stale_after: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "id": "fleet_refresh_report.test",
                "checked_at": checked_at,
                "stale_after": stale_after,
                "ok": True,
            }
        ),
        encoding="utf-8",
    )


class FleetRefreshReportAgeCanaryTests(unittest.TestCase):
    def test_canary_fails_for_a_missing_report(self) -> None:
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist" / "fleet-refresh-report.json"
            result = check_fleet_refresh_report_age(missing, as_of=_iso(datetime.now(timezone.utc)))
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["reason"], "missing")
        self.assertFalse(result["exists"])

    def test_canary_fails_for_an_over_age_report(self) -> None:
        now = datetime.now(timezone.utc)
        checked_at = now - timedelta(hours=3)
        # stale_after was declared as checked_at + 1h, so it is long past at `now`.
        stale_after = checked_at + timedelta(hours=1)
        with TemporaryDirectory() as tmp:
            report = Path(tmp) / "fleet-refresh-report.json"
            _write_report(report, checked_at=_iso(checked_at), stale_after=_iso(stale_after))
            result = check_fleet_refresh_report_age(report, as_of=_iso(now))
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["reason"], "over_age")
        self.assertTrue(result["exists"])
        # TTL is derived from the report's own stale_after window (1h = 3600s).
        self.assertEqual(result["ttl_seconds"], 3600)
        self.assertGreater(result["age_seconds"], 3600)

    def test_canary_passes_for_a_fresh_report(self) -> None:
        now = datetime.now(timezone.utc)
        checked_at = now - timedelta(minutes=5)
        stale_after = now + timedelta(hours=1)
        with TemporaryDirectory() as tmp:
            report = Path(tmp) / "fleet-refresh-report.json"
            _write_report(report, checked_at=_iso(checked_at), stale_after=_iso(stale_after))
            result = check_fleet_refresh_report_age(report, as_of=_iso(now))
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["reason"], "fresh")
        self.assertLess(result["age_seconds"], 3600)

    def test_canary_honors_an_explicit_ttl_override(self) -> None:
        now = datetime.now(timezone.utc)
        checked_at = now - timedelta(minutes=10)
        stale_after = checked_at + timedelta(hours=1)
        with TemporaryDirectory() as tmp:
            report = Path(tmp) / "fleet-refresh-report.json"
            _write_report(report, checked_at=_iso(checked_at), stale_after=_iso(stale_after))
            # Explicit 5-minute TTL: 10 minutes old is over-age.
            over = check_fleet_refresh_report_age(report, as_of=_iso(now), ttl_seconds=300)
            # Explicit 1-hour TTL: 10 minutes old is fresh.
            fresh = check_fleet_refresh_report_age(report, as_of=_iso(now), ttl_seconds=3600)
        self.assertEqual(over["status"], "fail")
        self.assertEqual(fresh["status"], "pass")

    def test_canary_fails_for_an_unreadable_report(self) -> None:
        now = datetime.now(timezone.utc)
        with TemporaryDirectory() as tmp:
            report = Path(tmp) / "fleet-refresh-report.json"
            report.write_text("{not valid json", encoding="utf-8")
            result = check_fleet_refresh_report_age(report, as_of=_iso(now))
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["reason"], "unreadable")
        self.assertTrue(result["exists"])

    def test_fleet_refresh_report_embeds_the_freshness_contract(self) -> None:
        # The generated report carries the freshness contract (ttl + report_ref)
        # so a consumer can re-evaluate it later with a real as_of. At generation
        # time (as_of == checked_at) it is fresh by construction.
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            state_root = project_root / "instance"
            (state_root / "instance-agent-package").mkdir(parents=True)
            manifest = load_json(
                ROOT / "examples" / "fleet-refresh-manifest.example.json"
            ) if (ROOT / "examples" / "fleet-refresh-manifest.example.json").exists() else {
                "id": "test-fleet",
                "default_ttl_seconds": 3600,
                "instances": [],
                "entity_current_state": None,
                "pressure": None,
            }
            manifest["instances"] = []
            output_dir = project_root / "fleet-refresh"
            report = run_fleet_refresh(
                manifest,
                project_root=project_root,
                checked_at="2026-07-29T20:00:00Z",
                stale_after="2026-07-29T21:00:00Z",
                output_dir=output_dir,
                dry_run=True,
            )
        canary = report["report_age_canary"]
        self.assertEqual(canary["status"], "pass")
        self.assertEqual(canary["reason"], "fresh")
        self.assertEqual(canary["ttl_seconds"], 3600)
        self.assertEqual(canary["report_checked_at"], "2026-07-29T20:00:00Z")
        # The on-disk artifact path is stamped once the report is written.
        self.assertTrue(str(canary["report_ref"]).endswith("fleet-refresh-report.json"))


class FleetRefreshManifestSchemaTests(unittest.TestCase):
    def test_manifest_schema_rejects_empty_instances(self) -> None:
        schema = load_json(ROOT / "schemas" / "fleet-refresh-manifest.schema.json")
        errors = validate_schema(
            {"id": "fleet_refresh_manifest.empty", "instances": []}, schema
        )
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
