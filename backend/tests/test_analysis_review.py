from app.services.analysis_review import apply_analysis_review, get_review_targets


def test_review_targets_include_dimensions_fits_and_form_features():
    analysis = {
        "manufacturing_operations": {
            "turning": [{"feature": "diameter", "dimensions": [{"callout": "Ø10", "value": 10.0}]}],
            "milling": [],
        },
        "precision_fits": [{"fit": "H7", "callout": "Ø10 H7"}],
        "geometric_tolerances": [{"feature": "position", "callout": "⌖ 0.1 A"}],
        "form_features": [{"feature": "chamfer", "callout": "0.5 x 45°"}],
    }

    targets = get_review_targets(analysis)

    assert set(targets) == {
        "manufacturing_operations.turning.0.dimensions.0",
        "precision_fits.0",
        "geometric_tolerances.0",
        "form_features.0",
    }


def test_apply_review_preserves_source_and_applies_corrections_and_rejections():
    analysis = {
        "manufacturing_operations": {
            "turning": [
                {"feature": "diameter", "dimensions": [
                    {"callout": "Ø10", "value": 10.0, "units": "mm"},
                    {"callout": "Ø99", "value": 99.0, "units": "mm"},
                ]},
            ],
            "milling": [],
        },
        "precision_fits": [{"fit": "H7", "callout": "Ø10 H7"}],
        "geometric_tolerances": [
            {"feature": "position", "callout": "⌖ 0.1 A"},
            {"feature": "flatness", "callout": "▱ 0.2"},
        ],
        "form_features": [],
    }

    reviewed = apply_analysis_review(analysis, [
        {
            "target_id": "manufacturing_operations.turning.0.dimensions.0",
            "decision": "corrected",
            "corrected_value": 10.5,
            "corrected_callout": "Ø10.5",
        },
        {
            "target_id": "manufacturing_operations.turning.0.dimensions.1",
            "decision": "rejected",
        },
        {
            "target_id": "geometric_tolerances.0",
            "decision": "corrected",
            "corrected_feature": "true position",
        },
        {
            "target_id": "geometric_tolerances.1",
            "decision": "rejected",
        },
    ])

    assert analysis["manufacturing_operations"]["turning"][0]["dimensions"][0]["value"] == 10.0
    assert reviewed["manufacturing_operations"]["turning"][0]["dimensions"] == [
        {"callout": "Ø10.5", "value": 10.5, "units": "mm"}
    ]
    assert analysis["geometric_tolerances"][0]["feature"] == "position"
    assert reviewed["geometric_tolerances"] == [
        {"feature": "true position", "callout": "⌖ 0.1 A"}
    ]
