# Costing Rules (Proposed)

## Principles

- Deterministic calculation first; every input has a unit and provenance.
- No invented material prices, machine rates, cutting parameters, or operation times.
- Distinguish user/shop-configured values, engineering estimates, measured actuals, and system-derived values.
- Save calculation-engine version, input snapshot, formulas, assumptions, rounding rules, and output lines for every estimate revision.
- If required inputs are absent, return an incomplete estimate with a list of missing inputs; do not imply a complete quote-ready result.

## Suggested line-item structure

- Material cost = purchased stock quantity × configured material rate, adjusted by an explicitly configured utilization/waste model.
- Setup cost = setup hours × configured machine/setup rate; allocation across batch quantity must be explicit.
- Machining cost = estimated cycle hours × configured machine-hour rate × quantity, with setup treated separately to avoid double-counting.
- Labor = labor hours × configured labor rate when not already included in machine rate.
- Add explicit lines for tooling/consumables, outside processing, inspection, packaging/freight if used, overhead, scrap/risk allowance, and commercial adjustments.
- Apply margin and taxes using a documented order of operations. Margin and markup are not interchangeable; UI labels and formulas must be explicit.

## Inputs requiring configuration or review

Material grade and stock dimensions; material price and effective date; utilization/waste assumptions; setup and cycle times; machine-hour rate; labor inclusion policy/rate; tooling and consumables; outside-process quotes; inspection effort; overhead method; scrap/risk allowance; profit margin/markup; currency; tax treatment; rounding precision; commercial discounts.

## Validation

- Reject negative or nonsensical quantities, times, and rates unless a specifically modeled credit/adjustment permits them.
- Require compatible units and explicit conversions.
- Test each formula with hand-calculated examples and boundary cases.
- Recalculate from stored inputs and assert reproducibility.
- Compare quoted versus actual cost only when data definitions and allocation bases match.

## Multi-currency requirements

- Every monetary value must carry an ISO 4217 currency code; never infer currency from a symbol alone.
- Preserve the original rate/cost currency and the estimate/quotation currency where they differ.
- Any conversion must record the source currency, target currency, numeric rate, rate source, effective timestamp/date, and any manual override/approver.
- Historical estimates and issued quotations must use their saved conversion snapshot; later rate changes must not mutate them.
- Never fetch or assume an exchange rate silently. If conversion is required but no approved rate is available, mark the estimate incomplete or request user input.
- Define rounding at explicit calculation boundaries and test conversions, rounding, and cross-currency totals.

## Open decisions

Business approval is required for the supported currency list; company base currency; quote currency selection; exchange-rate source, refresh cadence, and manual overrides; tax jurisdictions and tax-inclusive/exclusive behavior; currency precision and rounding mode/stage; material stock optimization; overhead allocation; and whether margin is applied per line or at subtotal. These decisions must be recorded before the relevant costing behavior is implemented.
