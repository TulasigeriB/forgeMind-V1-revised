from sqlalchemy.orm import Session
from app.models.feature import ManufacturingFeature, CostTemplate
from app.models.operation import ManufacturingOperation
from uuid import UUID
from typing import Any, List
import re

class ProcessPlanner:
    """
    The reasoning layer translates extracted features into a manufacturing sequence.
    """

    _socket_head_screw_costs = {
        "raw_material": 0.18,
        "cold_heading": 0.10,
        "turning": 0.12,
        "knurling": 0.06,
        "thread_rolling": 0.08,
        "passivation": 0.07,
        "quality_control": 0.05,
    }

    @staticmethod
    def plan_operations(
        db: Session,
        project_id: UUID,
        analysis: dict[str, Any] | None = None,
    ) -> list[ManufacturingOperation]:
        fastener_operations = ProcessPlanner._plan_socket_head_screw(project_id, analysis)
        if fastener_operations is not None:
            return fastener_operations

        features = db.query(ManufacturingFeature).filter(ManufacturingFeature.project_id == project_id).all()
        templates = db.query(CostTemplate).all()
        template_map = {t.feature_type: t for t in templates}

        operations = []
        current_sequence = 10

        # 1. Group features by process type (Turning vs Milling)
        # In a real system, this is derived from the geometric analysis
        turning_features = [f for f in features if f.feature_type in ["Bore", "Diameter", "Thread"]]
        milling_features = [f for f in features if f.feature_type in ["Slot", "Chamfer", "Socket"]]

        # 2. Plan Turning Operations (Roughing -> Finishing)
        if turning_features:
            for feat in turning_features:
                template = template_map.get(feat.feature_type)
                if template is None:
                    raise ValueError(
                        f"No cost template is configured for feature type {feat.feature_type}"
                    )
                precision_multiplier = (
                    template.precision_multiplier
                    if feat.tolerance and feat.tolerance.lower() != "standard"
                    else 1.0
                )
                cost = template.base_cost_per_unit * feat.quantity * precision_multiplier

                operations.append(ManufacturingOperation(
                    project_id=project_id,
                    operation_name=f"Turn {feat.feature_type} ({feat.dimension})",
                    sequence_order=current_sequence,
                    estimated_time_minutes=template.time_per_unit_minutes * feat.quantity,
                    estimated_cost=cost,
                    machine_type="CNC Lathe"
                ))
                current_sequence += 10

        # 3. Plan Milling Operations
        if milling_features:
            for feat in milling_features:
                template = template_map.get(feat.feature_type)
                if template is None:
                    raise ValueError(
                        f"No cost template is configured for feature type {feat.feature_type}"
                    )
                cost = template.base_cost_per_unit * feat.quantity

                operations.append(ManufacturingOperation(
                    project_id=project_id,
                    operation_name=f"Mill {feat.feature_type} ({feat.dimension})",
                    sequence_order=current_sequence,
                    estimated_time_minutes=template.time_per_unit_minutes * feat.quantity,
                    estimated_cost=cost,
                    machine_type="CNC Mill"
                ))
                current_sequence += 10

        return operations

    @classmethod
    def _plan_socket_head_screw(
        cls,
        project_id: UUID,
        analysis: dict[str, Any] | None,
    ) -> list[ManufacturingOperation] | None:
        if analysis is None:
            return None
        metadata = next(iter(analysis.get("metadata_and_notes", [])), {})
        material = str(metadata.get("material") or "")
        description = str(metadata.get("drawing_description") or "")
        is_socket_head_screw = (
            metadata.get("component_type") == "socket_head_screw"
            or bool(re.search(r"\bsocket[\s-]+head\s+(?:cap\s+)?screw\b", description, re.IGNORECASE))
        )
        if not is_socket_head_screw or not re.search(
            r"\b18-8\b.*\bstainless\b|\bstainless\b.*\b18-8\b",
            material,
            re.IGNORECASE,
        ):
            return None

        dimensions = [
            dimension
            for features in analysis.get("manufacturing_operations", {}).values()
            for feature in features
            for dimension in feature.get("dimensions", [])
        ]
        has_thread = any(dimension.get("type") == "thread" for dimension in dimensions)
        has_knurl = any(
            "knurl" in str(feature.get("feature", "")).lower()
            for feature in analysis.get("form_features", [])
        )

        steps = [
            ("raw_material", "Raw Material (18-8 Stainless Steel Wire)", "Wire preparation"),
            ("cold_heading", "Cold Heading & Socket Punching", "Cold header"),
            ("turning", "Turning, Facing & Head Profiling", "CNC lathe"),
        ]
        if has_knurl:
            steps.append(("knurling", "Perimeter Knurling", "Knurling station"))
        if has_thread:
            steps.append(("thread_rolling", "Thread Rolling", "Thread roller"))
        steps.extend([
            ("passivation", "Chemical Passivation & Cleaning", "Passivation line"),
            ("quality_control", "Quality Control & Packaging", "Inspection / packaging"),
        ])

        return [
            ManufacturingOperation(
                project_id=project_id,
                operation_name=name,
                sequence_order=sequence * 10,
                estimated_time_minutes=0.0,
                estimated_cost=cls._socket_head_screw_costs[cost_key],
                machine_type=machine,
            )
            for sequence, (cost_key, name, machine) in enumerate(steps, start=1)
        ]
