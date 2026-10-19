# ForgeMind inspection workspace update

## Included in this update
- Review list presents sequential characteristic identifiers.
- Inspectors can add missing characteristics with a type, exact notation, and source-location note.
- Manual characteristics are saved with the review using the existing extraction document record.
- CSV export includes characteristic number, type, notation, source, confidence, and review status.
- Existing extraction review, RFQ linking, and organization scoping are retained.

## Important scope boundary
This is a workflow foundation, not full SOLIDWORKS Inspection parity. This update does not yet render the original PDF with coordinate-accurate balloons, perform scanned-PDF OCR, infer feature associations, or generate a ballooned PDF/Excel report. The sequential numbers in the list are not drawn balloons. Users must record and verify source locations manually until the drawing viewer/overlay is implemented.

## Apply
Back up the project first. Copy the files from this package into the corresponding paths in the existing project. Preserve `.env` and local configuration.

Backend:
    python -m pytest -q

Frontend:
    npm ci
    npm test
    npm run build

No database schema migration is included in this update.
