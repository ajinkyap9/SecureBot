import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api import detection as detection_api
from app.schemas.risk_schema import DetectionOutputInput, RiskAssessmentRequest
from app.services.explanation_service import ExplanationService
from app.services.risk_service import RiskScoringService


RISK_FEATURE_ORDER = [
    "ae_score",
    "if_score",
    "combined_detection_score",
    "rule_hit_count",
    "max_rule_severity",
    "asset_criticality",
    "public_facing_flag",
    "privileged_account_flag",
    "sensitive_data_flag",
    "crown_jewel_flag",
    "spread_count_hosts",
    "ueba_score",
    "lateral_movement_flag",
    "persistence_flag",
    "max_cvss_score",
    "user_risk_score",
]


class _FakeRiskModel:
    def predict_proba(self, model_input_df):
        _ = model_input_df
        return np.array([[0.1594, 0.8406]])


class _FakeExplainer:
    def shap_values(self, model_input_df):
        _ = model_input_df
        return np.array([[0.10, -0.80, 0.20, 0.60, -0.40]])


class RiskServiceTests(unittest.TestCase):
    def _make_service(self):
        with patch.object(RiskScoringService, "_load_artifacts", return_value=None):
            service = RiskScoringService()
        service.model = _FakeRiskModel()
        service.feature_columns = list(RISK_FEATURE_ORDER)
        return service

    def test_build_model_input_maps_and_orders_features(self):
        service = self._make_service()

        model_input = service.build_model_input(
            {
                "ae_score": 0.82,
                "if_score": 0.76,
                "asset_criticality": "critical",
                "max_cvss_score": 9.8,
            }
        )

        self.assertEqual(list(model_input.columns), RISK_FEATURE_ORDER)
        self.assertEqual(float(model_input.iloc[0]["asset_criticality"]), 4.0)
        self.assertEqual(float(model_input.iloc[0]["rule_hit_count"]), 0.0)

    def test_predict_risk_returns_score_and_label(self):
        service = self._make_service()

        result = service.predict_risk(
            {
                "ae_score": 0.82,
                "if_score": 0.76,
                "combined_detection_score": 0.79,
                "asset_criticality": "high",
            }
        )

        self.assertEqual(result["risk_score"], 84.06)
        self.assertEqual(result["risk_label"], "critical")


class ExplanationServiceTests(unittest.TestCase):
    def test_explain_returns_top_factors_and_description(self):
        service = ExplanationService()
        service.explainer = _FakeExplainer()

        model_input_df = pd.DataFrame(
            [
                {
                    "ae_score": 0.82,
                    "if_score": 0.76,
                    "combined_detection_score": 0.79,
                    "max_rule_severity": 9,
                    "max_cvss_score": 9.8,
                }
            ]
        )

        result = service.explain(model_input_df, "critical")

        self.assertEqual(len(result["top_risk_factors"]), 5)
        self.assertIn("This incident requires immediate investigation", result["description"])


class DetectionApiIntegrationTests(unittest.TestCase):
    def test_detect_with_risk_combines_detection_risk_and_explanation(self):
        payload = RiskAssessmentRequest(
            detection_output=DetectionOutputInput(
                ae_score=0.82,
                if_score=0.76,
                combined_detection_score=0.79,
                detection_label="high_anomaly",
            ),
            max_rule_severity=9,
            spread_count_hosts=4,
            max_cvss_score=9.8,
            privileged_account_flag=1,
        )

        with patch.object(detection_api, "initialize_risk_services", return_value=None), patch.object(
            detection_api.risk_scoring_service,
            "predict_risk",
            return_value={"risk_score": 84.06, "risk_label": "critical"},
        ), patch.object(
            detection_api.risk_scoring_service,
            "build_model_input",
            return_value=pd.DataFrame([{"ae_score": 0.82}]),
        ), patch.object(
            detection_api.explanation_service,
            "explain",
            return_value={
                "top_risk_factors": [
                    "max_rule_severity",
                    "spread_count_hosts",
                    "max_cvss_score",
                    "ae_score",
                    "privileged_account_flag",
                ],
                "description": "Detected high severity alerts. This incident requires immediate investigation and response.",
            },
        ):
            result = detection_api.detect_with_risk(payload)

        self.assertEqual(result["detection_label"], "high_anomaly")
        self.assertEqual(result["risk_label"], "critical")
        self.assertEqual(result["risk_score"], 84.06)
        self.assertEqual(len(result["top_risk_factors"]), 5)


if __name__ == "__main__":
    unittest.main()
