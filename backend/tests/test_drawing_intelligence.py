import fitz

from app.services.drawing_intelligence import (
    DrawingIntelligenceService,
    DrawingTextLine,
    VectorLine,
)


def make_line(text, x=10, y=10, confidence=1.0, page=1, source="pdf_text"):
    return DrawingTextLine(
        text=text,
        bbox=(x, y, x + max(len(text), 4) * 4, y + 8),
        page=page,
        confidence=confidence,
        source=source,
    )


def test_extracts_fit_slots_form_features_and_metadata():
    lines = [
        make_line("DESCRIPTION: SHAFT"),
        make_line("PART NUMBER: 28215L-01"),
        make_line("MATERIAL: SS-304"),
        make_line("DIMENSIONS ARE IN MILLIMETERS"),
        make_line("Ø5.000 h6 +0.000 -0.008", y=50),
        make_line("M5x0.8 THREAD", y=70),
        make_line("14 SLOTS EQUISPACED", y=90),
        make_line("25.71° REF", y=110),
        make_line("R0.25 (UNDERCUT)", y=130),
        make_line("0.10 x 45° TYP", y=150),
        make_line("BREAK ALL SHARP CORNERS WITH 0.1 X 45", y=170),
    ]
    vectors = [VectorLine(page=1, start=(0, y + 10), end=(200, y + 10)) for y in range(40, 180, 20)]

    result = DrawingIntelligenceService.analyze_text_lines(
        lines=lines,
        vector_lines=vectors,
        fallback_part_number="fallback",
    )

    assert result["part_identifier"] == "28215L-01"
    assert result["units"] == "mm"
    assert result["metadata_and_notes"][0]["material"] == "SS-304"
    assert result["manufacturing_operations"]["turning"][0]["dimensions"][0]["callout"] == "Ø5.000 h6 +0.000 -0.008"
    assert result["precision_fits"][0]["fit"] == "h6"
    assert result["precision_fits"][0]["upper_deviation"] == "+0.000"
    assert result["precision_fits"][0]["lower_deviation"] == "-0.008"
    assert result["manufacturing_operations"]["milling"][0]["quantity"] == 14
    assert any(feature["feature"] == "chamfer" for feature in result["form_features"])
    assert any(feature["feature"] == "fillet or relief radius" for feature in result["form_features"])
    assert all(0 <= item["confidence"] <= 1 for item in result["precision_fits"])


def test_merges_stacked_tolerance_lines_with_parent_dimension():
    merged = DrawingIntelligenceService._merge_stacked_tolerances([
        make_line("Ø32.000 n6", x=50, y=20),
        make_line("+0.033", x=52, y=30),
        make_line("+0.017", x=52, y=40),
    ])

    assert len(merged) == 1
    assert merged[0].text == "Ø32.000 n6 +0.033 +0.017"


def test_marks_callout_without_nearby_vector_for_engineer_review():
    result = DrawingIntelligenceService.analyze_text_lines(
        lines=[make_line("Ø32.000 n6 +0.033 +0.017")],
        vector_lines=[],
        fallback_part_number="part",
    )

    dimension = result["manufacturing_operations"]["turning"][0]["dimensions"][0]
    assert dimension["confidence"] < 0.7
    assert dimension["needs_engineer_confirmation"] is True
    assert result["precision_fits"][0]["needs_engineer_confirmation"] is True


def test_extracts_searchable_pdf_text_and_vector_lines(tmp_path):
    pdf_path = tmp_path / "test-drawing.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 50), "DESCRIPTION: TEST BRACKET")
    page.insert_text((50, 70), "MATERIAL: AL-6061")
    page.insert_text((50, 90), "DIA 12.50")
    page.draw_line((40, 100), (120, 100))
    document.save(pdf_path)
    document.close()

    lines, vectors, pages = DrawingIntelligenceService._extract_pdf(pdf_path)
    analysis = DrawingIntelligenceService.analyze_text_lines(
        lines=lines,
        vector_lines=vectors,
        fallback_part_number="TEST-001",
        source_names=[pdf_path.name],
        page_count=pages,
    )

    assert pages == 1
    assert vectors
    assert analysis["metadata_and_notes"][0]["drawing_description"] == "TEST BRACKET"
    assert analysis["manufacturing_operations"]["turning"][0]["dimensions"][0]["value"] == 12.5


def test_resolves_legacy_relative_upload_path_from_configured_upload_directory(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    drawing_path = upload_dir / "legacy-drawing.pdf"
    drawing_path.write_bytes(b"test")
    monkeypatch.setattr(
        "app.services.drawing_intelligence.settings.UPLOAD_DIR",
        str(upload_dir),
    )

    resolved = DrawingIntelligenceService._resolve_storage_path(
        "uploads\\legacy-drawing.pdf"
    )

    assert resolved == drawing_path.resolve()


def test_extracts_inch_dimensions_and_fractional_unified_thread_callout():
    lines = [
        make_line("0.375in", x=100, y=40),
        make_line('5/16"-18 UNRC', x=100, y=70),
        make_line('1/4"', x=100, y=100),
    ]

    result = DrawingIntelligenceService.analyze_text_lines(
        lines=lines,
        vector_lines=[],
        fallback_part_number="SOCKET-HEAD-SCREW",
    )

    assert result["units"] == "inches"
    dimensions = [
        dimension
        for feature in result["manufacturing_operations"]["turning"]
        for dimension in feature["dimensions"]
    ]
    assert any(dimension["callout"] == "0.375in" and dimension["value"] == 0.375 for dimension in dimensions)
    thread = next(dimension for dimension in dimensions if dimension["type"] == "thread")
    assert thread["callout"] == '5/16"-18 UNRC'
    assert thread["value"] == 0.3125
    assert thread["thread_standard"] == "UNRC"
    assert thread["threads_per_inch"] == 18
    assert any(dimension["callout"] == '1/4"' and dimension["value"] == 0.25 for dimension in dimensions)


def test_extracts_fastener_metadata_and_labeled_dimensions():
    lines = [
        make_line("PART", x=100, y=10),
        make_line("NUMBER", x=95, y=16),
        make_line("92200A620", x=150, y=12),
        make_line("Mil. Spec. 18-8 Stainless", x=100, y=30),
        make_line("Steel Socket Head Screw", x=100, y=40),
        make_line("HEAD OD 0.469in", x=100, y=60),
        make_line("HEAD THICKNESS 0.313in", x=100, y=80),
        make_line('HEX SOCKET 1/4"', x=100, y=100),
        make_line("THREAD LENGTH 0.375in", x=100, y=120),
        make_line('5/16"-18 UNRC', x=100, y=140),
        make_line("DIAMETRAL KNURLING", x=100, y=160),
    ]

    result = DrawingIntelligenceService.analyze_text_lines(
        lines=lines,
        vector_lines=[],
        fallback_part_number="fallback",
    )

    metadata = result["metadata_and_notes"][0]
    assert result["part_identifier"] == "92200A620"
    assert metadata["material"] == "Mil. Spec. 18-8 Stainless Steel"
    assert metadata["drawing_description"] == "Steel Socket Head Screw"
    assert metadata["component_type"] == "socket_head_screw"
    features = {
        feature["feature"]: feature
        for group in result["manufacturing_operations"].values()
        for feature in group
    }
    assert features["head outer diameter"]["dimensions"][0]["value"] == 0.469
    assert features["head length / thickness"]["dimensions"][0]["value"] == 0.313
    assert features["hexagonal socket size"]["dimensions"][0]["value"] == 0.25
    assert features["thread length"]["dimensions"][0]["value"] == 0.375
    assert result["form_features"][0]["feature"] == "perimeter knurling"


def test_classifies_unlabeled_socket_head_screw_dimensions_by_drawing_layout():
    lines = [
        make_line("SOCKET HEAD SCREW", x=40, y=300),
        make_line('0.469"', x=100, y=50),
        make_line('0.313"', x=220, y=50),
        make_line('0.375"', x=340, y=50),
        make_line('1/4"', x=460, y=100),
        make_line('5/16"-18 UNRC', x=500, y=140),
    ]
    vectors = [
        VectorLine(page=1, start=(90, 40), end=(140, 40)),
        VectorLine(page=1, start=(210, 40), end=(260, 40)),
        VectorLine(page=1, start=(330, 40), end=(380, 40)),
        VectorLine(page=1, start=(450, 90), end=(490, 90)),
    ]

    result = DrawingIntelligenceService.analyze_text_lines(
        lines=lines,
        vector_lines=vectors,
        fallback_part_number="92200A620",
    )
    features = {
        feature["feature"]: feature
        for group in result["manufacturing_operations"].values()
        for feature in group
    }

    assert features["head outer diameter"]["dimensions"][0]["value"] == 0.469
    assert features["head length / thickness"]["dimensions"][0]["value"] == 0.313
    assert features["thread length"]["dimensions"][0]["value"] == 0.375
    assert features["hexagonal socket size"]["dimensions"][0]["value"] == 0.25
    assert features["thread size & pitch"]["dimensions"][0]["thread_standard"] == "UNRC"
    assert all(
        dimension["needs_engineer_confirmation"]
        for feature in features.values()
        for dimension in feature["dimensions"]
        if feature["feature"] in {
            "head outer diameter",
            "head length / thickness",
            "thread length",
            "hexagonal socket size",
        }
    )


def test_recognizes_gd_t_surface_finish_hardness_and_treatment_callouts():
    result = DrawingIntelligenceService.analyze_text_lines(
        lines=[
            make_line("POSITION ⌖ 0.1 | A | B", y=20),
            make_line("Ra 1.6 µm", y=40),
            make_line("HRC 48-52", y=60),
            make_line("PASSIVATION", y=80),
        ],
        vector_lines=[],
        fallback_part_number="QUALITY-001",
    )

    assert result["geometric_tolerances"][0]["feature"] == "position"
    assert result["geometric_tolerances"][0]["datum_references"] == ["A", "B"]
    assert result["metadata_and_notes"][0]["surface_specifications"][0]["value"] == 1.6
    assert result["metadata_and_notes"][0]["heat_treatments"][0]["hardness_specification"] == "HRC 48-52"
    assert result["metadata_and_notes"][0]["surface_treatments"][0]["treatment"] == "passivation"
    assert result["inspection_checklist"]
    assert result["quality_document_templates"]["ppap"]["status"] == "draft"


def test_does_not_infer_knurling_without_explicit_callout():
    result = DrawingIntelligenceService.analyze_text_lines(
        lines=[make_line("Steel Socket Head Screw"), make_line('0.469"', y=30)],
        vector_lines=[],
        fallback_part_number="SOCKET-SCREW",
    )

    assert not any(
        "knurl" in str(feature.get("feature", "")).lower()
        for feature in result["form_features"]
    )
    assert any("No explicit knurl callout" in flag["issue"] for flag in result["review_flags"])
