from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NormalizedDimension(BaseModel):
    feature: str
    dimension_type: str = "linear"
    value: float | None = None
    units: str = "mm"
    symbol: str = "LINEAR"
    callout: str | None = None
    normalized_callout: str | None = None
    tolerance: str | None = None
    upper_deviation: str | None = None
    lower_deviation: str | None = None
    confidence: float = 0.0
    needs_engineer_confirmation: bool = False
    semantic_source: str = "normalized"
    classification: str = "turning"
    bounding_box: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class NormalizedFeature(BaseModel):
    feature: str
    feature_class: str
    dimensions: list[NormalizedDimension] = Field(default_factory=list)
    confidence: float = 0.0
    needs_engineer_confirmation: bool = False
    notes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class FeatureNormalizationResult(BaseModel):
    part_identifier: str | None = None
    drawing_number: str | None = None
    material_specification: str | None = None
    material_family: str | None = None
    turning_features: list[NormalizedFeature] = Field(default_factory=list)
    milling_features: list[NormalizedFeature] = Field(default_factory=list)
    form_features: list[NormalizedFeature] = Field(default_factory=list)
    inspection_requirements: list[str] = Field(default_factory=list)
    review_status: Literal["draft", "in_review", "approved"] = "draft"
    review_notes: list[str] = Field(default_factory=list)
    feature_classification: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class FeatureNormalizer:
    _diameter_symbol_re = re.compile(r"(?:Ø|PHI|\u03d5|⌀|∅|DIA|DIA\.)", re.IGNORECASE)
    _radius_symbol_re = re.compile(r"\bR\b|RADIUS", re.IGNORECASE)
    _angle_symbol_re = re.compile(r"(?:°|DEG|DEGREES)", re.IGNORECASE)
    _fit_re = re.compile(
        r"(?:(?:Ø|PHI|DIA|DIAMETER)[\s\-]*)?(\d+(?:[.,]\d+)?)\s*(?:[A-HJ-NP-Za-hj-np-z]\d)\b",
        re.IGNORECASE,
    )
    _material_family_map = {
        "al": "aluminum",
        "aluminum": "aluminum",
        "al-6061": "aluminum",
        "6061": "aluminum",
        "ss": "stainless steel",
        "stainless": "stainless steel",
        "304": "stainless steel",
        "316": "stainless steel",
        "steel": "steel",
        "ms": "steel",
        "brass": "brass",
        "copper": "copper",
        "titanium": "titanium",
    }

    @classmethod
    def normalize(cls, raw_data: Mapping[str, Any] | str | Path) -> dict[str, Any]:
        payload = cls._load_payload(raw_data)
        result = cls._normalize_payload(payload)
        return {
            "summary": result.summary,
            "structured": result.model_dump(mode="json"),
        }

    @classmethod
    def normalize_to_dict(cls, raw_data: Mapping[str, Any] | str | Path) -> dict[str, Any]:
        return cls.normalize(raw_data)["structured"]

    @classmethod
    def normalize_summary(cls, raw_data: Mapping[str, Any] | str | Path) -> dict[str, Any]:
        return cls.normalize(raw_data)["summary"]

    @staticmethod
    def _load_payload(raw_data: Mapping[str, Any] | str | Path) -> dict[str, Any]:
        if isinstance(raw_data, Path):
            with raw_data.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        if isinstance(raw_data, str):
            raw_path = Path(raw_data)
            if raw_path.exists():
                with raw_path.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            return json.loads(raw_data)
        if isinstance(raw_data, Mapping):
            return dict(raw_data)
        raise TypeError("raw_data must be a mapping, JSON string, or filesystem path")

    @classmethod
    def _normalize_payload(cls, payload: Mapping[str, Any]) -> FeatureNormalizationResult:
        operations = payload.get("manufacturing_operations", {})
        turning_raw = operations.get("turning", []) if isinstance(operations, Mapping) else []
        milling_raw = operations.get("milling", []) if isinstance(operations, Mapping) else []
        form_raw = payload.get("form_features", [])
        precision_fits = payload.get("precision_fits", [])
        metadata = payload.get("metadata_and_notes", [])
        review_flags = payload.get("review_flags", [])

        turning_features = [cls._normalize_feature_group(item, "turning") for item in turning_raw]
        milling_features = [cls._normalize_feature_group(item, "milling") for item in milling_raw]
        form_features = [cls._normalize_feature_group(item, "form") for item in form_raw]

        material_specification = cls._extract_material_specification(payload, metadata)
        material_family = cls._material_family(material_specification)
        review_notes = [str(flag.get("issue", "")) for flag in review_flags if isinstance(flag, Mapping) and flag.get("issue")]
        status = "in_review" if review_notes or any(item.needs_engineer_confirmation for group in turning_features + milling_features + form_features for item in group.dimensions) else "approved"

        feature_classification: list[str] = []
        for group in turning_features + milling_features + form_features:
            feature_classification.append(group.feature_class)
            for dim in group.dimensions:
                if dim.classification not in feature_classification:
                    feature_classification.append(dim.classification)

        inspection_requirements: list[str] = []
        for flag in review_flags:
            if isinstance(flag, Mapping):
                issue = str(flag.get("issue", "")).strip()
                if issue:
                    inspection_requirements.append(issue)
        for fit in precision_fits:
            if isinstance(fit, Mapping):
                if fit.get("fit"):
                    inspection_requirements.append(f"Fit class {fit['fit']} requires tolerance verification")

        summary = {
            "part_identifier": payload.get("part_identifier") or payload.get("drawing_number"),
            "drawing_number": payload.get("part_identifier") or payload.get("drawing_number"),
            "material_specification": material_specification,
            "material_family": material_family,
            "turning_features": [f.feature for f in turning_features],
            "milling_features": [f.feature for f in milling_features],
            "form_features": [f.feature for f in form_features],
            "review_status": status,
            "review_notes": review_notes,
            "feature_classification": sorted(set(feature_classification)),
        }

        result = FeatureNormalizationResult(
            part_identifier=summary["part_identifier"],
            drawing_number=summary["drawing_number"],
            material_specification=material_specification,
            material_family=material_family,
            turning_features=turning_features,
            milling_features=milling_features,
            form_features=form_features,
            inspection_requirements=inspection_requirements,
            review_status=status,
            review_notes=review_notes,
            feature_classification=sorted(set(feature_classification)),
            summary=summary,
        )
        return result

    @classmethod
    def _normalize_feature_group(cls, item: Mapping[str, Any], default_class: str) -> NormalizedFeature:
        feature_name = str(item.get("feature") or "general feature")
        normalized_name = cls._normalize_feature_name(feature_name)
        dims: list[NormalizedDimension] = []
        for dimension in item.get("dimensions", []) or []:
            if isinstance(dimension, Mapping):
                dims.append(cls._normalize_dimension(dimension, normalized_name))
        confidence = 0.0
        if dims:
            confidence = max(float(dim.confidence) for dim in dims)
        needs_engineer_confirmation = any(dim.needs_engineer_confirmation for dim in dims)
        notes = []
        if feature_name == "unclassified linear dimension":
            notes.append("Linear dimension was re-classified by dimensional heuristics.")
        return NormalizedFeature(
            feature=normalized_name,
            feature_class=default_class,
            dimensions=dims,
            confidence=confidence,
            needs_engineer_confirmation=needs_engineer_confirmation,
            notes=notes,
        )

    @classmethod
    def _normalize_dimension(cls, dimension: Mapping[str, Any], feature_name: str) -> NormalizedDimension:
        callout = str(dimension.get("callout") or dimension.get("value") or "")
        value = cls._coerce_float(dimension.get("value"))
        units = str(dimension.get("units") or "mm")
        symbol = str(dimension.get("symbol") or "LINEAR")
        dimension_type = str(dimension.get("type") or "linear").lower()
        normalized_callout = cls._normalize_dimension_callout(callout, symbol, dimension_type)
        if not normalized_callout:
            normalized_callout = callout
        classification = cls._classify_dimension(feature_name, value, callout, dimension_type)

        tolerance = None
        upper_deviation = None
        lower_deviation = None
        fit_value = None
        fit_match = re.search(r"\b([A-HJ-NP-Za-hj-np-z]\d)\b", callout, re.IGNORECASE)
        if fit_match:
            fit_value = fit_match.group(1).upper()
        if re.search(r"[+-]\s*\d", callout):
            match = re.search(r"([+-]\s*\d+(?:[.,]\d+)?)\s*(?:[+-]\s*\d+(?:[.,]\d+)?)?", callout)
            if match:
                tolerance = match.group(1)
        if callout and ("+" in callout or "-" in callout):
            deviations = re.findall(r"([+-]\s*\d+(?:[.,]\d+)?)", callout)
            if len(deviations) >= 2:
                upper_deviation = deviations[0].replace(" ", "")
                lower_deviation = deviations[-1].replace(" ", "")
            elif len(deviations) == 1:
                upper_deviation = deviations[0].replace(" ", "")
                lower_deviation = upper_deviation

        if fit_value:
            normalized_callout = f"{cls._canonical_symbol(symbol)}{value or ''} {fit_value}"
        return NormalizedDimension(
            feature=feature_name,
            dimension_type=dimension_type,
            value=value,
            units=units,
            symbol=cls._canonical_symbol(symbol),
            callout=callout,
            normalized_callout=normalized_callout,
            tolerance=tolerance,
            upper_deviation=upper_deviation,
            lower_deviation=lower_deviation,
            confidence=float(dimension.get("confidence") or 0.0),
            needs_engineer_confirmation=bool(dimension.get("needs_engineer_confirmation")),
            semantic_source=str(dimension.get("semantic_source") or "normalized"),
            classification=classification,
            bounding_box=dict(dimension.get("bounding_box") or {}),
        )

    @staticmethod
    def _normalize_feature_name(feature_name: str) -> str:
        lowered = feature_name.strip().lower()
        synonyms = {
            "unclassified linear dimension": "outer diameter / shoulder length",
            "unresolved": "outer diameter / shoulder length",
            "diameter": "outer diameter",
            "bore diameter": "bore diameter",
            "radius": "fillet or relief radius",
            "fillet or relief radius": "fillet or relief radius",
            "slot": "slot",
            "slots": "slots",
            "chamfer": "chamfer",
            "thread size & pitch": "thread size & pitch",
            "linear dimension with limit deviations": "linear dimension with limit deviations",
            "head outer diameter": "head outer diameter",
            "head length / thickness": "head length / thickness",
            "thread length": "thread length",
            "hex socket size": "hex socket size",
        }
        return synonyms.get(lowered, lowered)

    @staticmethod
    def _normalize_dimension_callout(callout: str, symbol: str, dimension_type: str) -> str | None:
        if not callout:
            return None
        text = str(callout).strip()
        if not text:
            return None
        if dimension_type in {"diameter", "thread"} or "Ø" in text or "PHI" in text.upper() or "DIA" in text.upper():
            return text.replace("PHI", "Ø").replace("⌀", "Ø").replace("∅", "Ø")
        if "R" in text.upper() or dimension_type == "radius":
            return text
        if "°" in text or re.search(r"\d+\s*°", text):
            return text
        return text

    @staticmethod
    def _canonical_symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        mapping = {
            "Ø": "Ø",
            "PHI": "Ø",
            "DIA": "Ø",
            "LINEAR": "LINEAR",
            "R": "R",
            "RAD": "R",
            "ANGLE": "°",
            "DEG": "°",
        }
        return mapping.get(value, value or "LINEAR")

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            candidate = value.strip().replace(",", "")
            match = re.search(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", candidate)
            if match:
                return float(match.group(0))
        return None

    @classmethod
    def _classify_dimension(cls, feature_name: str, value: float | None, callout: str, dimension_type: str) -> str:
        normalized = feature_name.lower()
        if "diameter" in normalized or "bore" in normalized or "od" in normalized or "outer" in normalized:
            return "turning"
        if "slot" in normalized or "pocket" in normalized:
            return "milling"
        if "chamfer" in normalized or "fillet" in normalized or "radius" in normalized or "relief" in normalized:
            return "form"
        if "thread" in normalized:
            return "turning"
        if re.search(r"°|angle", callout, re.IGNORECASE):
            return "form"
        if value is not None and value < 1.0 and "R" in callout.upper():
            return "form"
        return "turning" if dimension_type != "linear" else "turning"

    @classmethod
    def _extract_material_specification(cls, payload: Mapping[str, Any], metadata: Sequence[Any]) -> str | None:
        direct = payload.get("metadata_and_notes")
        if isinstance(direct, Sequence):
            for item in direct:
                if isinstance(item, Mapping):
                    material = item.get("material")
                    if material:
                        return str(material)
        if isinstance(metadata, Sequence):
            for item in metadata:
                if isinstance(item, Mapping):
                    material = item.get("material")
                    if material:
                        return str(material)
        for line in (payload.get("raw_text", ""), payload.get("text", "")):
            if isinstance(line, str):
                match = re.search(r"\b(?:AL|ALUMINUM|SS|STAINLESS|STEEL|6061|304|316)[\w\- ]+", line, re.IGNORECASE)
                if match:
                    return match.group(0).strip()
        return None

    @staticmethod
    def _material_family(material_specification: str | None) -> str | None:
        if not material_specification:
            return None
        normalized = material_specification.strip().lower().replace(" ", "-")
        for token, family in FeatureNormalizer._material_family_map.items():
            if token in normalized:
                return family
        if "al" in normalized:
            return "aluminum"
        if "ss" in normalized:
            return "stainless steel"
        return normalized.replace("-", " ")

    @classmethod
    def _normalize_feature_classification(cls, feature_name: str) -> str:
        lowered = feature_name.lower()
        if any(token in lowered for token in ("slot", "pocket", "milling")):
            return "milling"
        if any(token in lowered for token in ("chamfer", "fillet", "radius", "relief", "angle")):
            return "form"
        return "turning"

    @classmethod
    def _normalize_feature_entry(cls, feature_name: str) -> str:
        return cls._normalize_feature_name(feature_name)


# Compatibility helpers

def normalize_feature_extraction(raw_data: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    return FeatureNormalizer.normalize(raw_data)


def normalize_feature_extraction_to_model(raw_data: Mapping[str, Any] | str | Path) -> FeatureNormalizationResult:
    payload = FeatureNormalizer._load_payload(raw_data)
    return FeatureNormalizer._normalize_payload(payload)
