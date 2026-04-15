import sys
import uuid
from pathlib import Path
import unittest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.alerts import ingest_alert
from app.db.session import Base, SessionLocal, engine
from app.models.action import Action
from app.models.alert import Alert
from app.models.case import Case
from app.schemas.alert_schema import AlertInput
from app.store.memory_store import action_store


class IngestDetectionRiskEnrichmentFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def test_ingest_to_detection_risk_enrichment_flow(self):
        alert_id = f"e2e-{uuid.uuid4()}"
        db = SessionLocal()

        try:
            payload = AlertInput(
                alert_id=alert_id,
                source="wazuh",
                ip="10.10.10.9",
                process="powershell.exe",
                command="powershell.exe -enc SQBlAHgA IEX",
                timestamp="2026-04-04T10:30:00Z",
            )

            response = ingest_alert(payload, db)

            self.assertEqual(response["status"], "success")
            pipeline_result = response["pipeline_result"]

            self.assertIn("detection", pipeline_result)
            self.assertIn("risk", pipeline_result)
            self.assertIn("enrichment", pipeline_result)

            self.assertIn("false_positive_risk", pipeline_result["detection"])
            self.assertIn("risk_score", pipeline_result["risk"])
            self.assertIn("risk_label", pipeline_result["risk"])
            self.assertIn("description", pipeline_result["risk"])
            self.assertIn("decision", pipeline_result)

            self.assertEqual(
                pipeline_result["intel"]["risk_score"],
                pipeline_result["risk"]["risk_score"],
            )

            enrichment = pipeline_result["enrichment"]
            self.assertIn("asset_context", enrichment)
            self.assertIn("threat_context", enrichment)
            self.assertIn("detection_context", enrichment)
            self.assertIn("hunt_context", enrichment)

            self.assertEqual(
                enrichment["threat_context"]["risk_score"],
                pipeline_result["risk"]["risk_score"],
            )
            self.assertEqual(
                enrichment["threat_context"]["risk_label"],
                pipeline_result["risk"]["risk_label"],
            )

            summary_technical = pipeline_result["summary"]["technical_summary"]
            self.assertEqual(
                summary_technical["risk_score"], pipeline_result["risk"]["risk_score"]
            )
            self.assertTrue(pipeline_result["risk"]["description"])
            self.assertEqual(enrichment["asset_context"]["ip"], "10.10.10.9")
            self.assertGreaterEqual(pipeline_result["risk"]["risk_score"], 0.0)

            risk_label = pipeline_result["risk"]["risk_label"]
            severity = pipeline_result["decision"]["severity"]
            label_to_expected_severity = {
                "low": "low",
                "medium": "medium",
                "high": "high",
                "critical": "critical",
            }
            self.assertEqual(severity, label_to_expected_severity[risk_label])

            for playbook_result in pipeline_result["decision"]["playbook_results"]:
                self.assertEqual(
                    playbook_result["risk_score"], pipeline_result["risk"]["risk_score"]
                )

        finally:
            db.query(Action).filter(Action.alert_id == alert_id).delete(
                synchronize_session=False
            )
            db.query(Case).filter(Case.alert_id == alert_id).delete(
                synchronize_session=False
            )
            db.query(Alert).filter(Alert.alert_id == alert_id).delete(
                synchronize_session=False
            )
            db.commit()
            db.close()

            for action_id in list(action_store.keys()):
                action = action_store.get(action_id) or {}
                if action.get("alert_id") == alert_id:
                    action_store.pop(action_id, None)


if __name__ == "__main__":
    unittest.main()
