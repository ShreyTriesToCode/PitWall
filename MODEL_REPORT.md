# Prediction methodology and evaluation

## Objective and production algorithm

`qualifying-order-v1` predicts **final classification rank after qualifying**.
It orders unique entrants by published qualifying position, with a complete
ordinal field required. Top 10 is exactly the first ten rows of the full grid.
It has no trained parameters, random numbers, calibrated probabilities or
statistical confidence intervals. Lower ranking score means earlier qualifying
position; the score is not a probability.

Inputs: validated Jolpica qualifying classification plus a current calendar event
identified as `season:round:race`. Capture must occur before the event's scheduled
UTC start. If qualifying is missing, malformed, incomplete, or scheduled in the
future, the forecast is unavailable. There is no roster/driver/team fallback.

The previous engine mixed learned outputs with arbitrary feature scores, synthetic
Gaussian race simulations and hand-assigned confidence/source percentages. Target
race lap/pit missingness leaked into historical features, export normalized past
predictions again, and training wrote its model before checking promotion. These
outputs were withdrawn. The old functions and original datasets remain for research;
`train_ml_model` refuses to train or promote that model. The published API cannot
read the old contracts or debug files.

## Reproducibility and capture

Each immutable record stores:

- Race ID, season/round, event start and target type.
- Model and feature versions, objective and stage.
- Actual capture timestamp and latest input retrieval time as data cutoff.
- Original qualifying inputs, SHA-256 of the event and qualifying data, sources
  and retrieval evidence.
- Ordered full grid and derived Top 10.

An identical input hash reuses the first capture. Changed inputs create a new
record before the race. Atomic hard-link publication refuses to overwrite an
existing record, including concurrent writes. Record corruption stops publication.
`training_data_cutoff` is null because this baseline has no training dataset;
it does not mean the forecast can use future data.

Before capture/publication, validation reconstructs the deterministic prediction
from its saved event and qualifying inputs. Input hash, prediction identity,
versions, cutoffs, full ranking and derived Top 10 must agree. The frontend contract
independently checks these fields; a stored record is not trusted solely because
it parses as JSON. Non-object or inconsistent ledger records block publication.

The source retrieval timestamp does not claim when the provider originally
published or revised a classification. Forecasts are only genuine captures if
saved before the race. A rescheduled start invalidates the frontend's match to
an earlier forecast. The final captured forecast per event is selected for a
future consolidated dataset so repeated revisions cannot overweight a race.

## Retrospective comparison protocol

Implemented in `pitwall/models/backtest.py`, using original Jolpica JSON caches:

1. Validate complete qualifying and result classifications, unique drivers,
   matching entrant fields and provider pagination.
2. Sort events by UTC race start (not random rows or independent season/round maxima).
3. Use 2018 for initial history; 2019–2023 is development; 2024–2025 is the reserved
   comparison period. Do not include 2026 in this report.
4. Predict each event before appending its result to history. Neither target-race
   finish/status/points nor future races enter the predictor.
5. Evaluate both algorithms on the same eligible races. The candidate needs prior
   results for every entrant; excluded races and missing files are listed.

The candidate is `qualifying-recent5-equal-rank-v1`: the average of qualifying
rank and rank of mean classified finish over each driver's previous five races.
Ties use qualifying position and stable driver ID. The equal weights are an
explicit hypothesis, not fitted coefficients. They were not optimized on the
reserved period. This is a deterministic comparison, not evidence that a
sophisticated ML system works.

### Measured report from the executed reconstruction

See `data_cache/ranking-backtest.json` for every race, source URL/hash, exclusion,
model versions, actual creation timestamp and dataset hash.

| Metric, reserved 2024–2025 period | Qualifying baseline | Recent-form candidate |
|---|---:|---:|
| Eligible races | 39 | 39 |
| Mean absolute classification error | 3.07193 places | 3.19082 places |
| Mean per-race RMSE | 4.22489 places | 4.32171 places |
| Mean Spearman rank correlation | 0.705668 | 0.692764 |
| Winner ranked first | 53.8462% | 43.5897% |
| Winner included in first three ranks | 87.1795% | 92.3077% |

132 races have paired development/test evaluations; 24 exclusion records include
invalid cached inputs and races lacking a complete comparable field/history.
An input-error record and excluded race can refer to the same event; that count
is **not** a count of unique excluded races. These are macro averages by race.

The candidate's classification MAE is worse and its rank correlation lower.
**It was not promoted.** Better winner top-three coverage does not compensate
for regression on the declared classification objective.

### Why these metrics

MAE expresses the error in finishing places and is the primary classification
objective. RMSE exposes large misses. Spearman measures full-field ordering;
with unique complete positions the ordinal formula is valid. Winner-first and
winner-top-three are secondary coverage summaries only. Brier score, log loss and
calibration are inappropriate because this model publishes no probabilities.
A DNF, DNS or DSQ retains the provider's classified position; it is not erased
from the metric. A substituted entrant or incomplete result blocks evaluation.

### Scientific limits

These cached classifications were retrieved later. Their historical publication
and correction timestamps were not saved. Although the features are logically
pre-race, **this is a retrospective reconstruction**, not an audited archive of
real-time forecasts. Retrospective source revisions and the complete-field filter
can introduce selection bias. There is no significance, calibration, or guaranteed
future-performance claim. Coverage includes only available validated records.
Qualifying order does not represent grid penalties, pit-lane starts, mechanical
risk, race weather, track evolution, strategy or sprint performance.

## Post-race comparison

The publisher retrieves results for captured past events. It requires matching
race and driver identities and a complete ordinal classification. Evaluation
records contain the result hash/source, model version, actual evaluation timestamp,
classification and defined metrics. Re-running the same result reuses its record;
a corrected result creates another immutable revision. Prediction bytes never
change. Legacy briefings lack adequate provenance and never contribute to these
metrics. There are currently zero prospective captures from this replacement
pipeline; the UI states that explicitly.

## Candidate development and promotion

`data_cache/evaluated-dataset.json` exports each event's final captured qualifying
inputs and latest evaluated classification. It is the basis for future dataset
updates. Production publication does not retrain or mutate parameters.

Before a candidate is eligible for review it must have:

- At least 30 paired held-out races spanning at least two seasons.
- At least 5% lower MAE than the baseline.
- No per-season MAE regression and no rank-correlation regression.
- Reproducible, leakage-free feature generation and identical evaluation cohorts.

Eligibility does not promote automatically. A reviewed code/model version change,
artifact/input hashes, untouched evaluation data and a rollback plan are required.
Repeated tuning against 2024–2025 would turn it into development data; a new future
test period would then be required. Zero new prospective races is insufficient
for adaptive learning. Evaluation infrastructure is implemented first.
