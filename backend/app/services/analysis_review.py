from copy import deepcopy
from typing import Any


def get_review_targets(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}
    operations = analysis.get("manufacturing_operations", {})
    if isinstance(operations, dict):
        for process_name, features in operations.items():
            if not isinstance(features, list):
                continue
            for feature_index, feature in enumerate(features):
                if not isinstance(feature, dict):
                    continue
                dimensions = feature.get("dimensions", [])
                if not isinstance(dimensions, list):
                    continue
                for dimension_index, dimension in enumerate(dimensions):
                    if isinstance(dimension, dict):
                        target_id = (
                            f"manufacturing_operations.{process_name}."
                            f"{feature_index}.dimensions.{dimension_index}"
                        )
                        targets[target_id] = dimension

    for collection_name in ("precision_fits", "form_features", "geometric_tolerances"):
        collection = analysis.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for index, entity in enumerate(collection):
            if isinstance(entity, dict):
                targets[f"{collection_name}.{index}"] = entity
    return targets


def apply_analysis_review(
    analysis: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    reviewed = deepcopy(analysis)
    decisions_by_target = {decision["target_id"]: decision for decision in decisions}
    targets = get_review_targets(reviewed)
    rejected_targets: list[str] = []

    for target_id, decision in decisions_by_target.items():
        target = targets.get(target_id)
        if target is None:
            raise ValueError(f"Review target no longer exists: {target_id}")

        if decision["decision"] == "rejected":
            rejected_targets.append(target_id)
            continue

        if decision["decision"] != "corrected":
            continue
        for field in ("corrected_callout", "corrected_value", "corrected_feature", "corrected_units"):
            value = decision.get(field)
            if value is None:
                continue
            target_field = {
                "corrected_callout": "callout",
                "corrected_value": "value",
                "corrected_feature": "fit" if target_id.startswith("precision_fits.") else "feature",
                "corrected_units": "units",
            }[field]
            target[target_field] = value

    rejected_dimensions: dict[tuple[str, int], set[int]] = {}
    rejected_features: dict[str, set[int]] = {}
    rejected_collections: dict[str, set[int]] = {}
    for target_id in rejected_targets:
        parts = target_id.split(".")
        if parts[0] == "manufacturing_operations":
            rejected_dimensions.setdefault((parts[1], int(parts[2])), set()).add(int(parts[4]))
        else:
            rejected_collections.setdefault(parts[0], set()).add(int(parts[1]))

    for process_name, feature_index in sorted(rejected_dimensions, reverse=True):
        feature = reviewed["manufacturing_operations"][process_name][feature_index]
        feature["dimensions"] = [
            dimension for index, dimension in enumerate(feature.get("dimensions", []))
            if index not in rejected_dimensions[(process_name, feature_index)]
        ]
        if not feature["dimensions"]:
            rejected_features.setdefault(process_name, set()).add(feature_index)

    for process_name, indices in rejected_features.items():
        reviewed["manufacturing_operations"][process_name] = [
            feature for index, feature in enumerate(reviewed["manufacturing_operations"][process_name])
            if index not in indices
        ]
    for collection_name, rejected_indices in rejected_collections.items():
        reviewed[collection_name] = [
            feature for index, feature in enumerate(reviewed.get(collection_name, []))
            if index not in rejected_indices
        ]
    return reviewed
