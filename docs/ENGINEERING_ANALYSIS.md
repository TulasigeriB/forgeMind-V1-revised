# Engineering Analysis Strategy

## STEP pipeline

1. Validate extension, file signature/parseability, size, and resource limits.
2. Load with the selected CAD kernel in a bounded execution context.
3. Determine unit metadata; if absent or ambiguous, record the ambiguity rather than silently assuming millimetres.
4. Validate shape/topology and detect null/invalid geometry where supported.
5. Extract supported properties: bounding dimensions, volume, surface area, and counts/areas of supported planar/cylindrical surfaces.
6. Recognize only features with explicit, testable geometric criteria; candidate features are not manufacturing truth.
7. Persist result, source file version, kernel/pipeline version, units, warnings, and entity references where stable.
8. Send uncertain/unsupported results to engineer review.

## PDF drawing pipeline

Start with direct PDF text and vector extraction. Preserve page number, text/geometry coordinates, raw text, parsed value, unit, tolerance, and extraction method. OCR may be introduced only where direct extraction fails and after fixture evaluation. Dimension-to-feature association is a separate stage; a number on a page is not automatically a measurement of a specific model feature.

## STEP/PDF cross-checking

Compare only compatible quantities with normalized units and documented tolerances. Report conflicts as review items. Drawing nominal dimensions and model measurements can differ for legitimate reasons; never silently choose one source.

## Provenance and review

Every extracted observation should identify source file version, analysis run, method/software version, normalized value/unit, and relevant source entity/page/coordinates. Engineer corrections are separate records with author, timestamp, reason, and approval state. Preserve original extraction.

## Test fixtures and evaluation

Create a small checked-in or safely generated fixture set with known expected dimensions/units/volume/surface area, invalid files, missing-unit cases, and supported feature cases. Document expected numerical tolerances and kernel version. Measure feature detection against labeled fixtures before making accuracy claims. For drawing extraction, track per-field precision/recall and association errors on a labeled set.

## Known limitations at planning stage

No CAD library has been compatibility-tested yet. No fixture corpus exists yet. Supported STEP entities, tolerance thresholds, and feature-recognition scope must be decided after a technical spike. General drawing interpretation is not guaranteed.
