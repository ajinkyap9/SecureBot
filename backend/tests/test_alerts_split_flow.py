import sys
import uuid
from pathlib import Path
import unittest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.alerts import ingest_alert_detection, ingest_alert_risk_description
from app.db.session import Base, SessionLocal, engine
from app.models.action import Action
from app.models.alert import Alert
from app.models.case import Case
from app.schemas.alert_schema import AlertInput
from app.store.memory_store import action_store


class AlertsSplitFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def test_detection_only_endpoint_returns_compact_routing_decision(self):
        alert_id = f"split-det-{uuid.uuid4()}"
        db = SessionLocal()

        try:
            payload = AlertInput(
                alert_id=alert_id,
                source="endpoint",
                ip="10.10.10.10",
                process="chrome.exe",
                command="chrome.exe --version",
                timestamp="2026-04-05T16:00:00Z",
                rule_hit_count=1,
                max_rule_severity=1,
                privileged_account_flag=0,
            )

            response = ingest_alert_detection(payload, db)

            self.assertEqual(response["status"], "success")
            self.assertEqual(response["mode"], "detection_only")
            self.assertIn("detection_section", response)
            detection_section = response["detection_section"]
            self.assertIn("detection_output", detection_section)
            self.assertIn("should_run_risk", detection_section)

        finally:
            _cleanup_alert_data(db, alert_id)

    def test_risk_description_endpoint_skips_non_potential_alert(self):
        alert_id = f"split-skip-{uuid.uuid4()}"
        db = SessionLocal()

        try:
            payload = AlertInput(
                alert_id=alert_id,
                source="endpoint",
                ip="10.10.10.11",
                process="notepad.exe",
                command="notepad.exe readme.txt",
                timestamp="2026-04-05T16:05:00Z",
                rule_hit_count=0,
                max_rule_severity=1,
                privileged_account_flag=0,
            )

            response = ingest_alert_risk_description(payload, db)

            self.assertEqual(response["status"], "success")
            self.assertEqual(response["mode"], "detection_only")
            self.assertIsNone(response["risk_section"])
            self.assertIsNone(response["description_section"])
            self.assertFalse(response["detection_section"]["should_run_risk"])

        finally:
            _cleanup_alert_data(db, alert_id)

    def test_risk_description_endpoint_runs_for_potential_alert(self):
        alert_id = f"split-risk-{uuid.uuid4()}"
        db = SessionLocal()

        try:
            payload = AlertInput(
                alert_id=alert_id,
                source="wazuh",
                ip="10.10.10.70",
                process="powershell.exe",
                command="powershell.exe -enc SQBlAHgA IEX",
                timestamp="2026-04-05T15:22:00Z",
                rule_hit_count=8,
                max_rule_severity=8,
                asset_criticality="high",
                public_facing_flag=1,
                privileged_account_flag=1,
                sensitive_data_flag=1,
                crown_jewel_flag=0,
                spread_count_hosts=2,
                lateral_movement_flag=1,
                persistence_flag=1,
                max_cvss_score=8.2,
                user_risk_score=0.73,
            )

            response = ingest_alert_risk_description(payload, db)

            self.assertEqual(response["status"], "success")
            self.assertEqual(response["mode"], "risk_and_description")
            self.assertTrue(response["detection_section"]["should_run_risk"])
            self.assertIsInstance(response["risk_section"], dict)
            self.assertIsInstance(response["description_section"], dict)

            detection_output = response["detection_section"]["detection_output"]
            self.assertIn("combined_detection_score", detection_output)
            self.assertNotEqual(
                response["detection_section"]["detection_source"],
                "derived",
            )

        finally:
            _cleanup_alert_data(db, alert_id)


def _cleanup_alert_data(db, alert_id: str) -> None:
    db.query(Action).filter(Action.alert_id == alert_id).delete(synchronize_session=False)
    db.query(Case).filter(Case.alert_id == alert_id).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.alert_id == alert_id).delete(synchronize_session=False)
    db.commit()

    for action_id in list(action_store.keys()):
        action = action_store.get(action_id) or {}
        if action.get("alert_id") == alert_id:
            action_store.pop(action_id, None)

    db.close()


if __name__ == "__main__":
    unittest.main()
