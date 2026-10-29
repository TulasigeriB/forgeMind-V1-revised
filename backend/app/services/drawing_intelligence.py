import csv
import io
import logging
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pymupdf as fitz

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DrawingTextLine:
    text: str
    bbox: tuple[float, float, float, float]
    page: int
    confidence: float
    source: str
    page_width: float | None = None
    page_height: float | None = None


@dataclass(frozen=True)
class VectorLine:
    page: int
    start: tuple[float, float]
    end: tuple[float, float]


class DrawingIntelligenceService:
    _diameter_pattern = re.compile(r"(?:Ø|⌀|∅|%%c|\bDIA\.?)\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
    _radius_pattern = re.compile(r"\bR\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
    _thread_pattern = re.compile(r"\bM\s*\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*THREAD)?", re.IGNORECASE)
    _fractional_thread_pattern = re.compile(
        r"(?<![\w])(\d+\s*/\s*\d+)\s*[\"″]?\s*-\s*(\d+)\s*(UNRC|UNRF|UNC|UNF)\b",
        re.IGNORECASE,
    )
    _inch_dimension_pattern = re.compile(
        r"(?<![\w])(\d+(?:[.,]\d+)?|\d+\s*/\s*\d+)\s*(?:IN(?:CH(?:ES)?)?\b|[\"″])",
        re.IGNORECASE,
    )
    _material_spec_pattern = re.compile(
        r"\b(?:MIL\.?\s*SPEC\.?\s*)?(?:18-8|304|316)\s+STAINLESS(?:\s+STEEL)?\b",
        re.IGNORECASE,
    )
    _socket_head_screw_pattern = re.compile(
        r"\bSOCKET[\s-]+HEAD\s+(?:CAP\s+)?SCREW\b",
        re.IGNORECASE,
    )
    _chamfer_pattern = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*°", re.IGNORECASE)
    _angle_pattern = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*°")
    _fit_pattern = re.compile(r"\b([A-HJ-NP-Z]\d)\b", re.IGNORECASE)
    _signed_tolerance_pattern = re.compile(
        r"([+-]\s*\d+(?:[.,]\d+)?)\s*(?:/|\s)\s*([+-]?\s*\d+(?:[.,]\d+)?)"
    )
    _number_only_pattern = re.compile(
        r"^\s*(\d+(?:[.,]\d+)?)"
        r"(?:\s*[+-]?\s*\d+(?:[.,]\d+)?){0,2}"
        r"\s*(?:(REF|TYP)|=)?\s*$",
        re.IGNORECASE,
    )
    _gdt_pattern = re.compile(
        r"\b(?:POSITION|FLATNESS|STRAIGHTNESS|CIRCULARITY|CYLINDRICITY|"
        r"PERPENDICULARITY|PARALLELISM|ANGULARITY|RUNOUT|TOTAL RUNOUT|"
        r"PROFILE(?: OF A LINE| OF A SURFACE)?)\b|[⌖◎⌯⊥∥∠⌭⌒○↗]",
        re.IGNORECASE,
    )
    _surface_pattern = re.compile(
        r"\b(Ra|Rz|RMS)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(µm|μm|um|µin|μin|uin)?",
        re.IGNORECASE,
    )
    _heat_treatment_pattern = re.compile(
        r"\b(?:HRC|HRB|HB|BHN|HV)\s*[:=]?\s*\d+(?:\s*[-–]\s*\d+)?\b",
        re.IGNORECASE,
    )
    _surface_treatment_pattern = re.compile(
        r"\b(?:PASSIVAT(?:E|ED|ION)|CHROME\s+PLAT(?:E|ED|ING)|"
        r"NICKEL\s+PLAT(?:E|ED|ING)|ZINC\s+PLAT(?:E|ED|ING)|ANODIZ(?:E|ED|ING)|"
        r"BLACK\s+OXIDE|POWDER\s+COAT(?:ED|ING)?)\b",
        re.IGNORECASE,
    )
    _excluded_line_pattern = re.compile(
        r"\b(?:REV(?:ISION)?|SHEET|SCALE|DRAWN BY|APPROVED BY|DATE|WEIGHT|"
        r"DESCRIPTION|PART NUMBER|ITEM NUMBER|MATERIAL|CASTING TOL|MACHINING TOL|"
        r"TITLE BLOCK|FIRST ANGLE|THIRD ANGLE)\b",
        re.IGNORECASE,
    )
    # New patterns for Gear/Component recognition
    _gear_patterns = re.compile(
        r"\b(?:PITCH\s*DIA\.?|OUTER\s*DIA\.?|OD|MODULE|DIAMETRAL\s*PITCH|DP|PRESSURE\s*ANGLE)\b",
        re.IGNORECASE
    )

    @classmethod
    def analyze_files(
        cls,
        files: Iterable[Any],
        project_part_number: str,
        project_material: str | None,
    ) -> dict[str, Any]:
        lines: list[DrawingTextLine] = []
        vector_lines: list[VectorLine] = []
        review_flags: list[dict[str, Any]] = []
        source_names: list[str] = []
        page_count = 0

        for engineering_file in files:
            path = cls._resolve_storage_path(engineering_file.storage_path)
            source_names.append(path.name)
            if engineering_file.file_type.upper() != "PDF" or path.suffix.lower() != ".pdf":
                review_flags.append({
                    "issue": f"{path.name} is not a PDF drawing; STEP geometry extraction is not yet supported.",
                    "confidence": 1.0,
                    "needs_engineer_confirmation": True,
                })
                continue

            try:
                extracted_lines, extracted_vectors, pages = cls._extract_pdf(path)
            except (ValueError, RuntimeError, fitz.FileDataError) as exc:
                raise ValueError(
                    f"{path.name} is not a valid PDF drawing or could not be parsed for analysis. "
                    "Upload a searchable PDF file with valid drawing content."
                ) from exc

            lines.extend(extracted_lines)
            vector_lines.extend(extracted_vectors)
            page_count += pages

        if not lines:
            raise ValueError(
                "No readable drawing text was extracted. Provide a searchable PDF or install/configure Tesseract OCR."
            )

        result = cls.analyze_text_lines(
            lines=lines,
            vector_lines=vector_lines,
            fallback_part_number=project_part_number,
            fallback_material=project_material,
            source_names=source_names,
            page_count=page_count,
        )
        result["review_flags"].extend(review_flags)
        return result

    @staticmethod
    def _resolve_storage_path(storage_path: str) -> Path:
        stored_path = Path(storage_path).expanduser()
        if stored_path.is_absolute():
            return stored_path

        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        backend_dir = Path(__file__).resolve().parents[2]
        repository_dir = backend_dir.parent
        candidates = (
            upload_dir / stored_path.name,
            backend_dir / stored_path,
            repository_dir / stored_path,
        )
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()

        expected = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(
            f"Engineering drawing was not found: {storage_path}. Checked: {expected}"
        )

    @classmethod
    def _extract_pdf(cls, path: Path) -> tuple[list[DrawingTextLine], list[VectorLine], int]:
        if not path.is_file():
            raise FileNotFoundError(f"Engineering drawing was not found: {path}")

        document = fitz.open(path)
        try:
            lines: list[DrawingTextLine] = []
            vectors: list[VectorLine] = []
            for page_index in range(len(document)):
                page = document.load_page(page_index)
                page_lines = cls._extract_pdf_text_lines(page, page_index + 1)
                if len(" ".join(line.text for line in page_lines).split()) < 8:
                    page_lines = cls._run_ocr(page, page_index + 1)
                lines.extend(page_lines)
                vectors.extend(cls._extract_vector_lines(page, page_index + 1))
            return lines, vectors, len(document)
        finally:
            document.close()

    @staticmethod
    def _extract_pdf_text_lines(page: fitz.Page, page_number: int) -> list[DrawingTextLine]:
        grouped_words: dict[tuple[int, int], list[tuple[float, float, float, float, str]]] = {}
        for word in page.get_text("words"):
            x0, y0, x1, y1, text, block_number, line_number = word[:7]
            grouped_words.setdefault((int(block_number), int(line_number)), []).append(
                (float(x0), float(y0), float(x1), float(y1), str(text))
            )

        lines: list[DrawingTextLine] = []
        for words in grouped_words.values():
            words.sort(key=lambda word: word[0])
            text = " ".join(word[4] for word in words).strip()
            if not text:
                continue
            lines.append(DrawingTextLine(
                text=text,
                bbox=(
                    min(word[0] for word in words),
                    min(word[1] for word in words),
                    max(word[2] for word in words),
                    max(word[3] for word in words),
                ),
                page=page_number,
                confidence=1.0,
                source="pdf_text",
                page_width=float(page.rect.width),
                page_height=float(page.rect.height),
            ))

        return DrawingIntelligenceService._merge_stacked_tolerances(lines)

    @classmethod
    def _run_ocr(cls, page: fitz.Page, page_number: int) -> list[DrawingTextLine]:
        command = shutil.which(settings.TESSERACT_CMD)
        if command is None and Path(settings.TESSERACT_CMD).is_file():
            command = settings.TESSERACT_CMD
        if command is None:
            raise RuntimeError(
                "The PDF has no searchable text and Tesseract OCR is unavailable. "
                "Install Tesseract or set TESSERACT_CMD to its executable path."
            )

        image = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).tobytes("png")
        completed = subprocess.run(
            [command, "stdin", "stdout", "tsv"],
            input=image,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Tesseract OCR failed for page {page_number}: {error}")

        grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
        reader = csv.DictReader(io.StringIO(completed.stdout.decode("utf-8", errors="replace")), delimiter="\t")
        for row in reader:
            text = row.get("text", "").strip()
            try:
                confidence = float(row.get("conf", "-1"))
                if not text or confidence < 0:
                    continue
                key = (row["block_num"], row["par_num"], row["line_num"], row["page_num"])
                x0, y0 = int(row["left"]) / 3, int(row["top"]) / 3
                x1 = (int(row["left"]) + int(row["width"])) / 3
                y1 = (int(row["top"]) + int(row["height"])) / 3
            except (KeyError, TypeError, ValueError):
                continue
            grouped.setdefault(key, []).append({
                "text": text,
                "bbox": (x0, y0, x1, y1),
                "confidence": confidence / 100,
            })

        lines = []
        for words in grouped.values():
            words.sort(key=lambda word: word["bbox"][0])
            lines.append(DrawingTextLine(
                text=" ".join(word["text"] for word in words),
                bbox=(
                    min(word["bbox"][0] for word in words),
                    min(word["bbox"][1] for word in words),
                    max(word["bbox"][2] for word in words),
                    max(word["bbox"][3] for word in words),
                ),
                page=page_number,
                confidence=sum(word["confidence"] for word in words) / len(words),
                source="tesseract_ocr",
                page_width=float(page.rect.width),
                page_height=float(page.rect.height),
            ))
        return cls._merge_stacked_tolerances(lines)

    @staticmethod
    def _merge_stacked_tolerances(lines: list[DrawingTextLine]) -> list[DrawingTextLine]:
        merged: list[DrawingTextLine] = []
        tolerance_only = re.compile(r"^\s*(?:[+-]|±|�)?\s*\d+(?:[.,]\d+)?\s*$")
        for line in sorted(lines, key=lambda item: (item.page, item.bbox[1], item.bbox[0])):
            current_has_fit = bool(DrawingIntelligenceService._fit_pattern.search(line.text))
            current_is_tolerance = bool(tolerance_only.fullmatch(line.text))
            for index in range(len(merged) - 1, -1, -1):
                previous = merged[index]
                if previous.page != line.page:
                    continue
                vertical_gap = max(
                    0.0,
                    max(previous.bbox[1], line.bbox[1]) - min(previous.bbox[3], line.bbox[3]),
                )
                horizontal_overlap = min(previous.bbox[2], line.bbox[2]) - max(previous.bbox[0], line.bbox[0])
                horizontal_gap = max(
                    0.0,
                    max(previous.bbox[0], line.bbox[0]) - min(previous.bbox[2], line.bbox[2]),
                )
                if vertical_gap > 16 or (horizontal_overlap <= 0 and horizontal_gap > 10):
                    continue

                previous_is_nominal = bool(re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", previous.text))
                previous_is_tolerance = bool(tolerance_only.fullmatch(previous.text))
                previous_has_tolerance_callout = bool(
                    re.search(r"\b[A-HJ-NP-Z]\d\b|[+-]\s*\d", previous.text, re.IGNORECASE)
                )
                previous_is_nominal = bool(re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", previous.text))
                should_merge = (
                    current_has_fit and (previous_is_nominal or previous_is_tolerance)
                ) or (
                    current_is_tolerance and (
                        previous_has_tolerance_callout
                        or (
                            previous_is_nominal
                            and line.text.lstrip().startswith(("+", "-", "±", "�"))
                        )
                    )
                )
                if not should_merge:
                    continue

                merged_line = DrawingTextLine(
                    text=f"{previous.text} {line.text}",
                    bbox=(
                        min(previous.bbox[0], line.bbox[0]),
                        min(previous.bbox[1], line.bbox[1]),
                        max(previous.bbox[2], line.bbox[2]),
                        max(previous.bbox[3], line.bbox[3]),
                    ),
                    page=previous.page,
                    confidence=min(previous.confidence, line.confidence),
                    source=previous.source,
                    page_width=previous.page_width,
                    page_height=previous.page_height,
                )
                merged.pop(index)
                merged.append(merged_line)
                break
            else:
                merged.append(line)
        return merged

    @staticmethod
    def _extract_vector_lines(page: fitz.Page, page_number: int) -> list[VectorLine]:
        vectors: list[VectorLine] = []
        for drawing in page.get_drawings():
            for item in drawing["items"]:
                if item[0] == "l":
                    start, end = item[1], item[2]
                    vectors.append(VectorLine(
                        page=page_number,
                        start=(float(start.x), float(start.y)),
                        end=(float(end.x), float(end.y)),
                    ))
                elif item[0] == "re":
                    rect = item[1]
                    corners = [
                        (float(rect.x0), float(rect.y0)),
                        (float(rect.x1), float(rect.y0)),
                        (float(rect.x1), float(rect.y1)),
                        (float(rect.x0), float(rect.y1)),
                    ]
                    for index, start in enumerate(corners):
                        vectors.append(VectorLine(
                            page=page_number,
                            start=start,
                            end=corners[(index + 1) % len(corners)],
                        ))
        return vectors

    @classmethod
    def analyze_text_lines(
        cls,
        lines: list[DrawingTextLine],
        vector_lines: list[VectorLine],
        fallback_part_number: str,
        fallback_material: str | None = None,
        source_names: list[str] | None = None,
        page_count: int = 0,
    ) -> dict[str, Any]:
        lines = [
            DrawingTextLine(
                text=cls._normalize_text(line.text),
                bbox=line.bbox,
                page=line.page,
                confidence=line.confidence,
                source=line.source,
                page_width=line.page_width,
                page_height=line.page_height,
            )
            for line in lines
        ]
        all_text = "\n".join(line.text for line in lines)
        part_identifier = (
            cls._find_metadata_value(lines, r"\bPART\s*NUMBER\s*[:#]?\s*(.+)$")
            or cls._find_part_number(lines)
            or fallback_part_number
        )
        material = (
            cls._find_metadata_value(lines, r"\bMATERIAL\s*[:#]?\s*(.+)$")
            or cls._find_material(all_text)
            or fallback_material
        )
        description = (
            cls._find_metadata_value(lines, r"\bDESCRIPTION\s*[:#]?\s*(.+)$")
            or cls._find_product_description(all_text)
        )
        component_type = (
            "socket_head_screw"
            if cls._socket_head_screw_pattern.search(all_text)
            else None
        )
        explicit_inch_units = re.search(
            r"\bDIMENSIONS?\s+(?:ARE\s+)?IN\s+INCH(?:ES)?\b",
            all_text,
            re.IGNORECASE,
        )
        inch_callout = re.compile(
            r"(?<![\w])(?:\d+(?:[.,]\d+)?|\d+\s*/\s*\d+)\s*(?:IN(?:CH(?:ES)?)?\b|[\"″])",
            re.IGNORECASE,
        )
        units = "inches" if explicit_inch_units or inch_callout.search(all_text) else "mm"

        turning: list[dict[str, Any]] = []
        milling: list[dict[str, Any]] = []
        precision_fits: list[dict[str, Any]] = []
        geometric_tolerances: list[dict[str, Any]] = []
        form_features: list[dict[str, Any]] = []
        review_flags: list[dict[str, Any]] = []
        surface_specs: list[dict[str, Any]] = []
        heat_treatments: list[dict[str, Any]] = []
        surface_treatments: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        dimension_index = 0
        dimension_rows: list[tuple[int, float, int]] = []

        for line in lines:
            text = line.text.strip()
            if not text:
                continue
            if cls._gdt_pattern.search(text):
                geometric_tolerances.append(
                    cls._parse_geometric_tolerance(line, vector_lines)
                )
                review_flags.append(cls._review_flag(
                    f"Geometric tolerance callout requires engineer verification: {text}",
                    confidence=line.confidence * 0.65,
                    page=line.page,
                    bbox=line.bbox,
                ))

            surface_match = cls._surface_pattern.search(text)
            if surface_match:
                surface_vector, surface_alignment = cls._nearest_vector(line, vector_lines)
                surface_specs.append({
                    "feature": "surface roughness",
                    "parameter": surface_match.group(1).upper(),
                    "value": cls._float_value(surface_match.group(2)),
                    "units": surface_match.group(3),
                    "callout": text,
                    **cls._association_fields(line, quality=line.confidence, alignment=surface_alignment, vector=surface_vector),
                })
            heat_match = cls._heat_treatment_pattern.search(text)
            if heat_match:
                heat_treatments.append({
                    "callout": text,
                    "hardness_specification": heat_match.group(0),
                    **cls._association_fields(line, quality=line.confidence, alignment=0, vector=None),
                })
            treatment_match = cls._surface_treatment_pattern.search(text)
            if treatment_match:
                surface_treatments.append({
                    "callout": text,
                    "treatment": treatment_match.group(0).lower(),
                    **cls._association_fields(line, quality=line.confidence, alignment=0, vector=None),
                })

            if cls._excluded_line_pattern.search(text):
                continue
            if re.search(r"\b(?:REVISION|INITIAL DRAWING|DRAWING PRODUCED|TOLERANCE BLOCK)\b", text, re.IGNORECASE):
                continue

            # --- GEAR / COMPLEX COMPONENT RECOGNITION ---
            is_gear_related = bool(cls._gear_patterns.search(text))

            lower_text = text.lower()
            vector, alignment = cls._nearest_vector(line, vector_lines)
            quality = max(0.0, min(1.0, line.confidence))
            has_context = bool(
                cls._diameter_pattern.search(text)
                or cls._radius_pattern.search(text)
                or cls._thread_pattern.search(text)
                or cls._chamfer_pattern.search(text)
                or cls._angle_pattern.search(text)
            )

            def make_dimension(callout: str, kind: str, value: float | None = None) -> dict[str, Any]:
                nonlocal dimension_index
                dimension_index += 1
                score = round(min(0.9, 0.45 * quality + 0.35 * alignment + 0.20 * float(has_context)), 2)
                y_center = (line.bbox[1] + line.bbox[3]) / 2
                row = next(
                    (
                        row_id for page_number, row_y, row_id in dimension_rows
                        if page_number == line.page and abs(row_y - y_center) <= 5
                    ),
                    None,
                )
                if row is None:
                    row = dimension_index
                    dimension_rows.append((line.page, y_center, row))
                return {
                    "callout": callout,
                    "type": kind,
                    "symbol": cls._dimension_symbol(kind),
                    "value": value,
                    "units": units,
                    "dimension_line_ref": f"page-{line.page}-baseline-{row}",
                    "bounding_box": {
                        "page": line.page,
                        "x0": round(line.bbox[0], 2),
                        "y0": round(line.bbox[1], 2),
                        "x1": round(line.bbox[2], 2),
                        "y1": round(line.bbox[3], 2),
                        "page_width": line.page_width,
                        "page_height": line.page_height,
                    },
                    "vector_alignment_confidence": round(alignment, 2),
                    "nearest_vector_line": vector,
                    "confidence": score,
                    "needs_engineer_confirmation": score < 0.7,
                }

            # --- GEAR / COMPLEX COMPONENT RECOGNITION ---
            if is_gear_related:
                # Try to extract a diameter if present in the gear callout
                dia_match = cls._diameter_pattern.search(text)
                num_match = cls._number_only_pattern.fullmatch(text)
                val = None
                if dia_match: val = cls._float_value(dia_match.group(1))
                elif num_match: val = cls._float_value(num_match.group(1))

                dimension = make_dimension(text, "gear_dimension", val)
                dimension_key = (line.page, "gear", text)
                if dimension_key not in seen:
                    seen.add(dimension_key)
                    turning.append({"feature": "gear_parameter", "dimensions": [dimension]})

                # All gear callouts are critical for engineer review
                review_flags.append(cls._review_flag(
                    f"Gear specification detected: {text}. Verify against tooth profile standards.",
                    confidence=0.8,
                    page=line.page,
                    bbox=line.bbox,
                ))
                # We don't 'continue' here because the line might also be a diameter or thread

            thread_match = cls._thread_pattern.search(text)
            fractional_thread_match = cls._fractional_thread_pattern.search(text)
            if thread_match or fractional_thread_match:
                if fractional_thread_match:
                    thread_callout = fractional_thread_match.group(0)
                    thread_value = cls._fraction_value(fractional_thread_match.group(1))
                else:
                    thread_callout = thread_match.group(0) if thread_match else text
                    thread_value = None
                thread_dimension = make_dimension(thread_callout, "thread", thread_value)
                if fractional_thread_match:
                    thread_dimension.update({
                        "thread_standard": fractional_thread_match.group(3).upper(),
                        "threads_per_inch": int(fractional_thread_match.group(2)),
                    })
                key = (line.page, "thread", thread_callout.lower())
                if key not in seen:
                    seen.add(key)
                    category = milling if "hole" in lower_text or "slot" in lower_text else turning
                    category.append({
                        "feature": "thread size & pitch",
                        "dimensions": [thread_dimension],
                    })
                continue

            diameter_match = cls._diameter_pattern.search(text)
            fit_match = None if cls._radius_pattern.search(text) else cls._fit_pattern.search(text)
            deviations = cls._signed_tolerance_pattern.search(text)
            inferred_diameter = None
            numeric_candidates = list(re.finditer(r"(?<![\w.+-])(\d+(?:[.,]\d+)?)(?![\w])", text))
            if fit_match:
                before_fit = [candidate for candidate in numeric_candidates if candidate.end() <= fit_match.start()]
                after_fit = [candidate for candidate in numeric_candidates if candidate.start() >= fit_match.end()]
                inferred_diameter = before_fit[-1] if before_fit else (after_fit[0] if after_fit else None)
            diameter_value_match = diameter_match or inferred_diameter
            if diameter_value_match:
                value = cls._float_value(diameter_value_match.group(1))
                feature_label = "bore diameter" if (
                    re.search(r"\b(?:BORE|HOLE|ID|INTERNAL)\b", text, re.IGNORECASE)
                    or (fit_match and fit_match.group(1).upper().startswith("H"))
                ) else "diameter"
                dimension = make_dimension(text, "diameter", value)
                dimension_key = (
                    line.page,
                    "diameter",
                    text,
                    round(line.bbox[0], 2),
                    round(line.bbox[1], 2),
                )
                if dimension_key not in seen:
                    seen.add(dimension_key)
                    turning.append({"feature": feature_label, "dimensions": [dimension]})
                if fit_match or deviations:
                    signed_values = re.findall(r"(?<![\w.])[+-]\s*\d+(?:[.,]\d+)?", text) if fit_match else []
                    zero_tolerance = None
                    if fit_match and numeric_candidates:
                        zero_tolerance = next(
                            (
                                cls._float_value(candidate.group(1))
                                for candidate in numeric_candidates
                                if not math.isclose(cls._float_value(candidate.group(1)), value)
                                and math.isclose(cls._float_value(candidate.group(1)), 0.0, abs_tol=0.001)
                            ),
                            None,
                        )
                    if len(signed_values) >= 2:
                        upper_deviation = cls._signed_value(signed_values[0])
                        lower_deviation = cls._signed_value(signed_values[-1])
                    elif signed_values:
                        single_deviation = cls._signed_value(signed_values[0])
                        upper_deviation = (
                            single_deviation if single_deviation.startswith("+")
                            else "+0.000" if zero_tolerance is not None else None
                        )
                        lower_deviation = (
                            single_deviation if single_deviation.startswith("-")
                            else "+0.000" if zero_tolerance is not None else None
                        )
                    else:
                        upper_deviation = cls._signed_value(deviations.group(1)) if deviations else None
                        lower_deviation = cls._signed_value(deviations.group(2)) if deviations else None
                        if zero_tolerance is not None:
                            upper_deviation = "+0.000"
                    fit_key = (value, fit_match.group(1).lower() if fit_match else "")
                    existing_fit = next(
                        (item for item in precision_fits
                         if (item["nominal_size"], (item["fit"] or "").lower())
                         == (f"{value:.3f} {units}", fit_key[1])),
                        None,
                    )
                    if existing_fit is None:
                        precision_fits.append({
                        "feature": feature_label,
                        "callout": text,
                        "nominal_size": f"{value:.3f} {units}",
                        "fit": fit_match.group(1) if fit_match else None,
                        "upper_deviation": upper_deviation,
                        "lower_deviation": lower_deviation,
                        "confidence": dimension["confidence"],
                        "needs_engineer_confirmation": dimension["needs_engineer_confirmation"],
                        })
                    elif sum(value is not None for value in (upper_deviation, lower_deviation)) > sum(
                        value is not None for value in (
                            existing_fit["upper_deviation"],
                            existing_fit["lower_deviation"],
                        )
                    ):
                        existing_fit.update({
                            "callout": text,
                            "upper_deviation": upper_deviation,
                            "lower_deviation": lower_deviation,
                            "confidence": dimension["confidence"],
                            "needs_engineer_confirmation": dimension["needs_engineer_confirmation"],
                        })
                continue

            radius_match = cls._radius_pattern.search(text)
            if radius_match:
                form_features.append({
                    "feature": "fillet or relief radius",
                    "callout": text,
                    "value": cls._float_value(radius_match.group(1)),
                    "units": units,
                    **cls._association_fields(line, quality, alignment, vector),
                })
                continue

            knurl_match = re.search(r"\b(?:DIAMETRAL\s+)?KNURL(?:ED|ING)?\b", text, re.IGNORECASE)
            if knurl_match:
                form_features.append({
                    "feature": "perimeter knurling",
                    "callout": text,
                    **cls._association_fields(line, quality, alignment, vector),
                })
                continue

            chamfer_match = cls._chamfer_pattern.search(text)
            if chamfer_match:
                form_features.append({
                    "feature": "chamfer",
                    "callout": text,
                    "size": cls._float_value(chamfer_match.group(1)),
                    "angle_degrees": cls._float_value(chamfer_match.group(2)),
                    "units": units,
                    **cls._association_fields(line, quality, alignment, vector),
                })
                continue

            slot_pattern = re.search(r"\b(\d+)\s*SLOTS?\b", text, re.IGNORECASE)
            if slot_pattern:
                milling.append({
                    "feature": "equally spaced peripheral slots" if "EQUISPACED" in text.upper() else "slots",
                    "quantity": int(slot_pattern.group(1)),
                    "dimensions": [],
                    **cls._association_fields(line, quality, alignment, vector),
                })
                continue

            angle_match = cls._angle_pattern.search(text)
            if angle_match:
                dimension = make_dimension(text, "angle", cls._float_value(angle_match.group(1)))
                angle_feature = {
                    "feature": "angular indexing" if "REF" in text.upper() else "profile angle",
                    "dimensions": [dimension],
                }
                if cls._has_nearby_keyword(line, lines, r"\b(?:SLOTS?|PCD|POCKETS?)\b"):
                    milling.append(angle_feature)
                else:
                    form_features.append({
                        **angle_feature,
                        "callout": text,
                        **cls._association_fields(line, quality, alignment, vector),
                    })
                continue

            number_match = cls._number_only_pattern.fullmatch(text)
            if number_match:
                if cls._is_page_marginal_or_titleblock_number(line, text):
                    continue
                key = (
                    line.page,
                    "linear",
                    text,
                    round(line.bbox[0], 2),
                    round(line.bbox[1], 2),
                )
                if key in seen:
                    continue
                seen.add(key)
                dimension = make_dimension(text, "linear", cls._float_value(number_match.group(1)))
                feature_label, semantic_source = cls._infer_linear_feature_label(text, line, lines)
                dimension["semantic_source"] = semantic_source
                if feature_label == "unclassified linear dimension":
                    dimension["needs_engineer_confirmation"] = True
                    review_flags.append(cls._review_flag(
                        f"Linear dimension feature is unclassified: {text}",
                        confidence=dimension["confidence"],
                        page=line.page,
                        bbox=line.bbox,
                    ))
                turning.append({"feature": feature_label, "dimensions": [dimension]})
                deviations = cls._signed_tolerance_pattern.search(text)
                if deviations:
                    precision_fits.append({
                        "feature": "linear dimension with limit deviations",
                        "callout": text,
                        "nominal_size": f"{cls._float_value(number_match.group(1)):.3f} {units}",
                        "fit": None,
                        "upper_deviation": cls._signed_value(deviations.group(1)),
                        "lower_deviation": cls._signed_value(deviations.group(2)),
                        "confidence": dimension["confidence"],
                        "needs_engineer_confirmation": dimension["needs_engineer_confirmation"],
                    })
                if dimension["needs_engineer_confirmation"]:
                    review_flags.append(cls._review_flag(
                        f"Dimension association is uncertain: {text}",
                        confidence=dimension["confidence"],
                        page=line.page,
                        bbox=line.bbox,
                    ))
                continue

            inch_dimension_match = cls._inch_dimension_pattern.search(text)
            if inch_dimension_match:
                key = (
                    line.page,
                    "inch_linear",
                    text,
                    round(line.bbox[0], 2),
                    round(line.bbox[1], 2),
                )
                if key not in seen:
                    seen.add(key)
                    dimension_feature, semantic_source = cls._infer_linear_feature_label(text, line, lines)
                    dimension = make_dimension(
                        text,
                        "linear",
                        cls._fraction_value(inch_dimension_match.group(1)),
                    )
                    dimension["semantic_source"] = semantic_source
                    if dimension_feature == "unclassified linear dimension":
                        dimension["needs_engineer_confirmation"] = True
                        review_flags.append(cls._review_flag(
                            f"Linear dimension feature is unclassified: {text}",
                            confidence=dimension["confidence"],
                            page=line.page,
                            bbox=line.bbox,
                        ))
                    target_operations = (
                        milling
                        if dimension_feature == "hex socket size"
                        else turning
                    )
                    target_operations.append({
                        "feature": dimension_feature,
                        "dimensions": [dimension],
                    })
                    if dimension["needs_engineer_confirmation"]:
                        review_flags.append(cls._review_flag(
                            f"Dimension association is uncertain: {text}",
                            confidence=dimension["confidence"],
                            page=line.page,
                            bbox=line.bbox,
                        ))

        supplier = cls._find_supplier(all_text)
        component_classification = cls._classify_component(
            all_text,
            description,
            material,
            component_type,
        )
        if component_type == "socket_head_screw":
            cls._classify_socket_head_screw_dimensions(
                turning,
                milling,
                vector_lines,
                review_flags,
            )
        critical_operations, inspection_checklist = cls._derive_quality_checks(
            turning=turning,
            milling=milling,
            precision_fits=precision_fits,
            geometric_tolerances=geometric_tolerances,
            surface_specs=surface_specs,
            heat_treatments=heat_treatments,
            surface_treatments=surface_treatments,
        )

        metadata_and_notes: list[dict[str, Any]] = [{
            "part_identifier": part_identifier,
            "supplier": supplier,
            "drawing_description": description,
            "material": material,
            "component_type": component_type,
            "component_classification": component_classification,
            "heat_treatments": heat_treatments,
            "surface_treatments": surface_treatments,
            "units": units,
            "source_files": source_names or [],
            "page_count": page_count,
            "notes": cls._extract_notes(lines),
            "surface_specifications": surface_specs,
            "general_tolerance_callouts": [
                line.text for line in lines
                if re.search(r"\b(?:ANGULAR|TOLERANCE|XX\.X|XX±|XX\s+±)\b", line.text, re.IGNORECASE)
            ],
            "confidence": 0.92 if description or material else 0.68,
            "needs_engineer_confirmation": not bool(description and material),
        }]

        if not turning and not milling and not form_features:
            review_flags.append(cls._review_flag(
                "No manufacturing dimensions were confidently recognized. Verify that the drawing is readable and inspect it manually.",
                confidence=0.0,
            ))

        if component_type == "socket_head_screw":
            if not any(feature.get("feature") == "perimeter knurling" for feature in form_features):
                review_flags.append(cls._review_flag(
                    "No explicit knurl callout was found in drawing text; confirm additional surface features during engineer review.",
                    confidence=0.0,
                ))

        tolerance_lines = [
            line for line in lines
            if re.search(r"\b(?:ANGULAR|TOLERANCE|XX\.X|XX±|GENERAL TOL)\b", line.text, re.IGNORECASE)
        ]
        if tolerance_lines:
            review_flags.append(cls._review_flag(
                "General tolerance-block text was detected; confirm its scope and decimal-place rules against the drawing.",
                confidence=0.55,
                page=tolerance_lines[0].page,
                bbox=tolerance_lines[0].bbox,
            ))

        return {
            "part_identifier": part_identifier,
            "units": units,
            "manufacturing_operations": {"turning": turning, "milling": milling},
            "precision_fits": precision_fits,
            "geometric_tolerances": geometric_tolerances,
            "form_features": form_features,
            "critical_operations": critical_operations,
            "inspection_checklist": inspection_checklist,
            "quality_document_templates": {
                "first_article_inspection": {
                    "status": "draft",
                    "intended_use": "R&D / first production article",
                    "items": inspection_checklist,
                },
                "ppap": {
                    "status": "draft",
                    "requires_engineer_review": True,
                    "sections": cls._ppap_template_sections(),
                },
            },
            "metadata_and_notes": metadata_and_notes,
            "review_flags": review_flags,
        }

    @classmethod
    def _infer_linear_feature_label(
        cls,
        text: str,
        line: DrawingTextLine,
        lines: list[DrawingTextLine],
    ) -> tuple[str, str]:
        patterns = (
            (r"\b(?:HEAD\s*)?(?:OD|O\.D\.|OUTER\s+DIAMETER)\b", "head outer diameter"),
            (r"\bHEAD\b.*\b(?:THICKNESS|HEIGHT|LENGTH)\b", "head length / thickness"),
            (r"\b(?:HEX(?:AGONAL)?|SOCKET)\b", "hexagonal socket size"),
            (r"\bTHREAD\b.*\bLENGTH\b", "thread length"),
            (r"\bTHREAD\b.*\b(?:MAJOR\s+)?DIAMETER\b", "thread major diameter"),
            (r"\bOVERALL\b.*\bLENGTH\b", "overall length"),
            (r"\bSHANK\b.*\bLENGTH\b", "shank length"),
            (r"\b(?:BORE|HOLE)\b.*\b(?:DEPTH|DIA(?:METER)?)\b", "hole dimension"),
            (r"\bSLOT\b.*\b(?:WIDTH|LENGTH)\b", "slot dimension"),
        )
        for pattern, label in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return label, "explicit_callout"

        center = ((line.bbox[0] + line.bbox[2]) / 2, (line.bbox[1] + line.bbox[3]) / 2)
        nearby = []
        for candidate in lines:
            if candidate is line or candidate.page != line.page:
                continue
            candidate_center = (
                (candidate.bbox[0] + candidate.bbox[2]) / 2,
                (candidate.bbox[1] + candidate.bbox[3]) / 2,
            )
            distance = math.dist(center, candidate_center)
            if distance <= 80:
                nearby.append((distance, candidate.text))
        for _, context in sorted(nearby):
            for pattern, label in patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    return label, "nearby_drawing_text"
        return "unclassified linear dimension", "unresolved"

    @classmethod
    def _classify_socket_head_screw_dimensions(
        cls,
        turning: list[dict[str, Any]],
        milling: list[dict[str, Any]],
        vector_lines: list[VectorLine],
        review_flags: list[dict[str, Any]],
    ) -> None:
        entries: list[tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]] = []
        for collection in (turning, milling):
            for feature in collection:
                for dimension in feature.get("dimensions", []):
                    if dimension.get("type") == "linear":
                        entries.append((collection, feature, dimension))

        for collection, feature, dimension in entries:
            if dimension.get("value") is not None and "/" in dimension.get("callout", ""):
                cls._rename_feature_entry(
                    collection,
                    feature,
                    dimension,
                    "hexagonal socket size",
                    "socket_head_screw_fractional_socket",
                )
                if collection is turning:
                    turning.remove(feature)
                    milling.append(feature)

        unclassified = [
            item for item in entries
            if item[1].get("feature") == "unclassified linear dimension"
            and item[2].get("value") is not None
        ]
        by_page: dict[int, list[tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]]] = {}
        for item in unclassified:
            box = item[2].get("bounding_box", {})
            by_page.setdefault(int(box.get("page", 1)), []).append(item)

        for page_entries in by_page.values():
            rows: list[list[tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]]] = []
            for item in sorted(
                page_entries,
                key=lambda value: (
                    (value[2]["bounding_box"]["y0"] + value[2]["bounding_box"]["y1"]) / 2,
                    value[2]["bounding_box"]["x0"],
                ),
            ):
                box = item[2]["bounding_box"]
                center_y = (box["y0"] + box["y1"]) / 2
                row = next(
                    (
                        candidate_row for candidate_row in rows
                        if abs(
                            center_y
                            - (
                                candidate_row[0][2]["bounding_box"]["y0"]
                                + candidate_row[0][2]["bounding_box"]["y1"]
                            ) / 2
                        ) <= 22
                    ),
                    None,
                )
                if row is None:
                    rows.append([item])
                else:
                    row.append(item)
            top_row = max(rows, key=len, default=[])
            top_row.sort(key=lambda item: item[2]["bounding_box"]["x0"])
            labels = (
                "head outer diameter",
                "head length / thickness",
                "thread length",
            )
            if len(top_row) >= 3:
                for (_, feature, dimension), label in zip(top_row, labels):
                    cls._rename_feature_entry(
                        turning,
                        feature,
                        dimension,
                        label,
                        "socket_head_screw_orthographic_layout",
                    )

        thread_sizes = [
            dimension
            for feature in turning + milling
            if feature.get("feature") == "thread size & pitch"
            for dimension in feature.get("dimensions", [])
            if dimension.get("value") is not None
        ]
        for collection, feature, dimension in unclassified:
            if feature.get("feature") != "unclassified linear dimension":
                continue
            value = dimension.get("value")
            if (
                cls._dimension_axis(dimension, vector_lines) == "vertical"
                and any(abs(value - thread["value"]) <= 0.002 for thread in thread_sizes)
            ):
                cls._rename_feature_entry(
                    turning,
                    feature,
                    dimension,
                    "thread major diameter",
                    "thread_callout_and_dimension_geometry",
                )

        for collection in (turning, milling):
            collection[:] = [
                feature for feature in collection
                if feature.get("feature") != "unclassified linear dimension"
                or feature.get("dimensions")
            ]

        inferred_callouts = {
            dimension["callout"]
            for collection in (turning, milling)
            for feature in collection
            for dimension in feature.get("dimensions", [])
            if dimension.get("semantic_source", "").startswith("socket_head_screw")
            or dimension.get("semantic_source") == "thread_callout_and_dimension_geometry"
        }
        review_flags[:] = [
            flag for flag in review_flags
            if not (
                str(flag.get("issue", "")).startswith("Linear dimension feature is unclassified:")
                and any(callout in str(flag.get("issue", "")) for callout in inferred_callouts)
            )
        ]

    @staticmethod
    def _rename_feature_entry(
        collection: list[dict[str, Any]],
        feature: dict[str, Any],
        dimension: dict[str, Any],
        label: str,
        semantic_source: str,
    ) -> None:
        feature["feature"] = label
        dimension["semantic_source"] = semantic_source
        dimension["needs_engineer_confirmation"] = True
        dimension["confidence"] = min(float(dimension.get("confidence", 0.0)), 0.78)
        if not feature.get("dimensions"):
            collection.remove(feature)

    @staticmethod
    def _dimension_axis(dimension: dict[str, Any], vector_lines: list[VectorLine]) -> str | None:
        box = dimension.get("bounding_box", {})
        center = ((box.get("x0", 0) + box.get("x1", 0)) / 2, (box.get("y0", 0) + box.get("y1", 0)) / 2)
        candidates = []
        page = box.get("page")
        for vector in vector_lines:
            if vector.page != page:
                continue
            length = math.dist(vector.start, vector.end)
            if length < 18:
                continue
            distance = DrawingIntelligenceService._point_segment_distance(center, vector.start, vector.end)
            if distance <= 28:
                dx = abs(vector.end[0] - vector.start[0])
                dy = abs(vector.end[1] - vector.start[1])
                candidates.append((distance, "horizontal" if dx >= dy else "vertical"))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    @classmethod
    def _parse_geometric_tolerance(
        cls,
        line: DrawingTextLine,
        vector_lines: list[VectorLine],
    ) -> dict[str, Any]:
        text = line.text
        symbols = {
            "⌖": ("position", "⌖"),
            "⊥": ("perpendicularity", "⊥"),
            "∥": ("parallelism", "∥"),
            "∠": ("angularity", "∠"),
            "⌭": ("cylindricity", "⌭"),
            "⌒": ("profile", "⌒"),
            "○": ("circularity", "○"),
            "↗": ("circular runout", "↗"),
        }
        names = (
            "total runout", "perpendicularity", "parallelism", "cylindricity",
            "circularity", "straightness", "flatness", "position", "angularity",
            "profile of a surface", "profile of a line", "profile", "runout",
        )
        feature, symbol = "geometric tolerance", None
        for candidate_symbol, (candidate_feature, normalized_symbol) in symbols.items():
            if candidate_symbol in text:
                feature, symbol = candidate_feature, normalized_symbol
                break
        if symbol is None:
            match = next((name for name in names if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE)), None)
            if match:
                feature = match
                symbol = {
                    "position": "⌖",
                    "perpendicularity": "⊥",
                    "parallelism": "∥",
                    "angularity": "∠",
                    "cylindricity": "⌭",
                    "circularity": "○",
                    "flatness": "▱",
                    "straightness": "—",
                    "profile": "⌒",
                    "profile of a line": "⌒",
                    "profile of a surface": "⌒",
                    "runout": "↗",
                    "total runout": "↗",
                }.get(feature)
        _, alignment = cls._nearest_vector(line, vector_lines)
        values = re.findall(r"(?<![A-Z])\d+(?:[.,]\d+)?", text, re.IGNORECASE)
        datum_references = re.findall(r"(?:\||/)\s*([A-Z])\b", text)
        return {
            "feature": feature,
            "symbol": symbol,
            "callout": text,
            "tolerance_value": cls._float_value(values[0]) if values else None,
            "datum_references": datum_references,
            **cls._association_fields(line, line.confidence, alignment, cls._nearest_vector(line, vector_lines)[0]),
        }

    @staticmethod
    def _dimension_symbol(kind: str) -> str:
        return {
            "diameter": "Ø",
            "thread": "THREAD",
            "radius": "R",
            "angle": "°",
            "linear": "LINEAR",
        }.get(kind, kind.upper())

    @staticmethod
    def _find_supplier(all_text: str) -> str | None:
        if re.search(r"\bMcMASTER[- ]CARR\b|mcmaster\.com", all_text, re.IGNORECASE):
            return "McMaster-Carr"
        return None

    @staticmethod
    def _classify_component(
        all_text: str,
        description: str | None,
        material: str | None,
        component_type: str | None,
    ) -> dict[str, Any]:
        text = f"{description or ''}\n{all_text}".lower()
        if re.search(r"\b(?:shaft|screw|bolt|rod|pin|spacer)\b", text):
            shape = "round"
        elif re.search(r"\b(?:plate|sheet|flat bar)\b", text):
            shape = "flat"
        elif re.search(r"\b(?:bracket|housing|casting|weldment)\b", text):
            shape = "irregular"
        else:
            shape = "unclassified"
        material_text = (material or "").lower()
        if any(token in material_text for token in ("stainless", "steel", "alloy steel", "carbon steel")):
            material_family = "steel"
        elif "copper" in material_text:
            material_family = "copper"
        elif "brass" in material_text:
            material_family = "brass"
        elif "plastic" in material_text or any(token in material_text for token in ("nylon", "acetal", "delrin")):
            material_family = "plastic"
        else:
            material_family = "unclassified"
        stock_form_match = re.search(r"\b(cast(?:ing)?|forg(?:e|ed|ing)|weld(?:ed|ment)?)\b", text)
        stock_form = stock_form_match.group(1).lower() if stock_form_match else "not specified"
        is_supported = bool(component_type or description)
        return {
            "shape": shape,
            "material_family": material_family,
            "stock_form": stock_form,
            "evidence": {
                "description": description,
                "material": material,
                "component_type": component_type,
            },
            "confidence": 0.82 if is_supported and shape != "unclassified" else 0.4,
            "needs_engineer_confirmation": not is_supported or shape == "unclassified" or material_family == "unclassified",
        }

    @classmethod
    def _derive_quality_checks(
        cls,
        turning: list[dict[str, Any]],
        milling: list[dict[str, Any]],
        precision_fits: list[dict[str, Any]],
        geometric_tolerances: list[dict[str, Any]],
        surface_specs: list[dict[str, Any]],
        heat_treatments: list[dict[str, Any]],
        surface_treatments: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        critical_operations: list[dict[str, Any]] = []
        checklist: list[dict[str, Any]] = []

        for fit in precision_fits:
            critical_operations.append({
                "operation": "Precision machining and fit verification",
                "reason": fit["callout"],
                "needs_engineer_confirmation": fit.get("needs_engineer_confirmation", True),
            })
            checklist.append({
                "requirement": f"Verify fit/tolerance: {fit['callout']}",
                "category": "dimensional",
                "measurement_method": "Engineer-defined calibrated measurement",
                "source_callout": fit["callout"],
                "status": "planned",
            })
        for tolerance in geometric_tolerances:
            critical_operations.append({
                "operation": "Datum setup and geometric tolerance inspection",
                "reason": tolerance["callout"],
                "needs_engineer_confirmation": True,
            })
            checklist.append({
                "requirement": f"Inspect {tolerance['feature']}: {tolerance['callout']}",
                "category": "geometric_tolerance",
                "measurement_method": "Engineer-defined datum-based inspection",
                "source_callout": tolerance["callout"],
                "status": "planned",
            })
        for process_group in (turning, milling):
            for feature in process_group:
                for dimension in feature.get("dimensions", []):
                    if dimension.get("type") == "thread":
                        checklist.append({
                            "requirement": f"Verify thread: {dimension['callout']}",
                            "category": "thread",
                            "measurement_method": "Thread plug/ring gauge per engineer plan",
                            "source_callout": dimension["callout"],
                            "status": "planned",
                        })
        for spec in surface_specs:
            critical_operations.append({
                "operation": "Surface finishing and roughness verification",
                "reason": spec["callout"],
                "needs_engineer_confirmation": spec.get("needs_engineer_confirmation", True),
            })
            checklist.append({
                "requirement": f"Verify surface roughness {spec['callout']}",
                "category": "surface_finish",
                "measurement_method": "Surface profilometer",
                "source_callout": spec["callout"],
                "status": "planned",
            })
        for treatment in heat_treatments + surface_treatments:
            checklist.append({
                "requirement": f"Verify specified treatment: {treatment['callout']}",
                "category": "material_or_surface_treatment",
                "measurement_method": "Certificate and/or engineer-defined test",
                "source_callout": treatment["callout"],
                "status": "planned",
            })
        return critical_operations, checklist

    @staticmethod
    def _ppap_template_sections() -> list[str]:
        return [
            "Design and drawing revision records",
            "Process flow and manufacturing route",
            "Process risk analysis",
            "Control and inspection plan",
            "Dimensional and material test results",
            "Measurement equipment and calibration evidence",
            "Nonconformance and corrective-action records",
            "Customer approval and submission decision",
        ]

    @staticmethod
    def _find_part_number(lines: list[DrawingTextLine]) -> str | None:
        markers = [
            line for line in lines
            if re.fullmatch(r"\s*(?:PART|NUMBER)\s*:?\s*", line.text, re.IGNORECASE)
        ]
        if not markers:
            return None

        candidates: list[tuple[float, str]] = []
        for candidate in lines:
            value = candidate.text.strip()
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{4,19}", value, re.IGNORECASE):
                continue
            if not re.search(r"[A-Z]", value, re.IGNORECASE) or not re.search(r"\d", value):
                continue
            for marker in markers:
                if marker.page != candidate.page:
                    continue
                vertical_gap = max(
                    0.0,
                    max(marker.bbox[1], candidate.bbox[1]) - min(marker.bbox[3], candidate.bbox[3]),
                )
                horizontal_gap = max(
                    0.0,
                    max(marker.bbox[0], candidate.bbox[0]) - min(marker.bbox[2], candidate.bbox[2]),
                )
                if vertical_gap > 24 or horizontal_gap > 180:
                    continue
                distance = vertical_gap * 2 + horizontal_gap
                candidates.append((distance, value))
        return min(candidates, default=(0.0, None), key=lambda item: item[0])[1]

    @classmethod
    def _find_material(cls, all_text: str) -> str | None:
        match = cls._material_spec_pattern.search(all_text)
        if match:
            material = re.sub(r"\s+", " ", match.group(0)).strip()
            if re.search(r"\bstainless\b$", material, re.IGNORECASE):
                material = f"{material} Steel"
            return material
        return None

    @classmethod
    def _find_product_description(cls, all_text: str) -> str | None:
        match = re.search(
            r"\b(?:STEEL\s+)?SOCKET[\s-]+HEAD\s+(?:CAP\s+)?SCREW\b",
            all_text,
            re.IGNORECASE,
        )
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip().title()
        return None

    @classmethod
    def _association_fields(
        cls,
        line: DrawingTextLine,
        quality: float,
        alignment: float,
        vector: str | None,
    ) -> dict[str, Any]:
        confidence = round(min(0.9, 0.45 * quality + 0.35 * alignment + 0.20), 2)
        return {
            "page": line.page,
            "bounding_box": [round(value, 2) for value in line.bbox],
            "page_width": line.page_width,
            "page_height": line.page_height,
            "nearest_vector_line": vector,
            "confidence": confidence,
            "needs_engineer_confirmation": confidence < 0.7,
        }

    @staticmethod
    def _nearest_vector(
        line: DrawingTextLine,
        vector_lines: list[VectorLine],
    ) -> tuple[str | None, float]:
        center = ((line.bbox[0] + line.bbox[2]) / 2, (line.bbox[1] + line.bbox[3]) / 2)
        nearest_distance = float("inf")
        nearest_id = None
        for index, vector in enumerate(vector_lines):
            if vector.page != line.page:
                continue
            distance = DrawingIntelligenceService._point_segment_distance(center, vector.start, vector.end)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_id = f"page-{vector.page}-vector-{index + 1}"
        if nearest_id is None:
            return None, 0.0
        return nearest_id, max(0.0, 1.0 - nearest_distance / 60.0)

    @staticmethod
    def _point_segment_distance(
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        dx, dy = end[0] - start[0], end[1] - start[1]
        if dx == 0 and dy == 0:
            return math.dist(point, start)
        ratio = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)))
        projection = (start[0] + ratio * dx, start[1] + ratio * dy)
        return math.dist(point, projection)

    @staticmethod
    def _find_metadata_value(lines: list[DrawingTextLine], pattern: str) -> str | None:
        ordered_lines = sorted(lines, key=lambda item: (item.page, item.bbox[1], item.bbox[0]))
        for line in ordered_lines:
            match = re.search(pattern, line.text, re.IGNORECASE)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" :#")
                if value:
                    return value
                candidates: list[tuple[float, DrawingTextLine]] = []
                for candidate in ordered_lines:
                    if candidate is line or candidate.page != line.page:
                        continue
                    horizontal_overlap = min(line.bbox[2], candidate.bbox[2]) - max(line.bbox[0], candidate.bbox[0])
                    horizontal_gap = max(
                        0.0,
                        max(line.bbox[0], candidate.bbox[0]) - min(line.bbox[2], candidate.bbox[2]),
                    )
                    vertical_gap = max(
                        0.0,
                        max(line.bbox[1], candidate.bbox[1]) - min(line.bbox[3], candidate.bbox[3]),
                    )
                    same_row = vertical_gap <= 8 and horizontal_gap <= 18
                    below_label = horizontal_overlap > 0 and 0 < candidate.bbox[1] - line.bbox[3] <= 24
                    if same_row or below_label:
                        distance = vertical_gap * 2 + horizontal_gap
                        candidates.append((distance, candidate))

                for _, candidate in sorted(candidates, key=lambda item: item[0]):
                    value = candidate.text.strip(" :#")
                    if not value or DrawingIntelligenceService._excluded_line_pattern.search(value):
                        continue
                    if re.fullmatch(r"\d{1,2}-\d{1,2}-\d{2,4}", value):
                        continue
                    return value
        return None

    @staticmethod
    def _is_page_marginal_or_titleblock_number(line: DrawingTextLine, text: str) -> bool:
        if re.fullmatch(r"\s*\d{1,2}-\d{1,2}-\d{2,4}\s*", text):
            return True
        if re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?\s*", text):
            return True
        if re.fullmatch(r"\s*[1-9]\s*", text):
            return True
        if line.page_width and line.page_height:
            x0, y0, x1, y1 = line.bbox
            if x0 < 35 or x1 > line.page_width - 35 or y0 < 18 or y1 > line.page_height - 18:
                return True
            if y0 > line.page_height * 0.75:
                return True
        return False

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("�", "°") if re.search(r"\d\s*�\s*(?:=|$)", text) else text
        text = re.sub(r"(?<=\d)�(?=\s*(?:REF|TYP|=|$))", "°", text, flags=re.IGNORECASE)
        text = re.sub(r"\bXX\s+�\s*(\d)", r"XX ±\1", text, flags=re.IGNORECASE)
        text = re.sub(r"�(?=\d)", "Ø", text)
        return text

    @staticmethod
    def _has_nearby_keyword(
        line: DrawingTextLine,
        lines: list[DrawingTextLine],
        keyword_pattern: str,
        max_distance: float = 120,
    ) -> bool:
        center_x = (line.bbox[0] + line.bbox[2]) / 2
        center_y = (line.bbox[1] + line.bbox[3]) / 2
        return any(
            candidate.page == line.page
            and re.search(keyword_pattern, candidate.text, re.IGNORECASE)
            and math.dist(
                (center_x, center_y),
                ((candidate.bbox[0] + candidate.bbox[2]) / 2, (candidate.bbox[1] + candidate.bbox[3]) / 2),
            ) <= max_distance
            for candidate in lines
        )

    @staticmethod
    def _extract_notes(lines: list[DrawingTextLine]) -> list[str]:
        notes: list[str] = []
        for line in lines:
            text = line.text.strip()
            if re.search(r"\b(?:NOTE|NOTES|UNLESS OTHERWISE SPECIFIED|UNDIMENSIONED|BREAK ALL SHARP)\b", text, re.IGNORECASE):
                if text not in notes:
                    notes.append(text)
        return notes

    @staticmethod
    def _float_value(value: str) -> float:
        return float(value.replace(",", "."))

    @classmethod
    def _fraction_value(cls, value: str) -> float:
        normalized = re.sub(r"\s+", "", value)
        if "/" not in normalized:
            return cls._float_value(normalized)
        numerator, denominator = normalized.split("/", maxsplit=1)
        return float(numerator) / float(denominator)

    @staticmethod
    def _signed_value(value: str) -> str:
        return re.sub(r"\s+", "", value).replace(",", ".")

    @staticmethod
    def _review_flag(
        issue: str,
        confidence: float,
        page: int | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any]:
        flag: dict[str, Any] = {
            "issue": issue,
            "confidence": round(max(0.0, min(1.0, confidence)), 2),
            "needs_engineer_confirmation": True,
        }
        if page is not None:
            flag["page"] = page
        if bbox is not None:
            flag["bounding_box"] = [round(value, 2) for value in bbox]
        return flag
