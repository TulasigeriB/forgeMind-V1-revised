from pathlib import Path

from app.services.feature_normalizer import FeatureNormalizer


def test_feature_normalizer_handles_raw_extraction_payload():
    sample_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "services" / "Untitled-1.json"
    result = FeatureNormalizer.normalize(sample_path)

    structured = result["structured"]
    summary = result["summary"]

    assert structured["part_identifier"] == "AS-WER-12"
    assert structured["material_specification"] in {None, "AL-6061", "SS-304"}
    assert structured["turning_features"]
    assert isinstance(summary, dict)
    assert summary["part_identifier"] == "AS-WER-12"
    assert summary["review_status"] in {"in_review", "approved"}
    assert any(feature["feature"] == "outer diameter / shoulder length" for feature in structured["turning_features"])


def test_feature_normalizer_normalizes_fit_callout_and_material_family():
    raw = {
        "part_identifier": "PT-100",
        "metadata_and_notes": [{"material": "AL-6061"}],
        "manufacturing_operations": {
            "turning": [{
                "feature": "diameter",
                "dimensions": [{
                    "callout": "Ø32.000 n6 +0.033 +0.017",
                    "value": 32.0,
                    "type": "diameter",
                    "symbol": "Ø",
                    "confidence": 0.83,
                    "needs_engineer_confirmation": False,
                }],
            }],
        },
    }

    result = FeatureNormalizer.normalize(raw)
    flow = result["structured"]
    assert flow["material_family"] == "aluminum"
    assert flow["turning_features"][0]["dimensions"][0]["normalized_callout"].startswith("Ø")
