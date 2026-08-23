# F1 Race Briefing: F1 Dutch GP - Race

Generated: Sunday, 23 August 2026, 06:48 AM IST

## Event

- Target: Race
- Start: Sunday, 23 August 2026, 06:30 PM IST
- Circuit: Circuit Park Zandvoort
- Location: Zandvoort, Netherlands

## Prediction

1. George Russell, score 65.9, confidence 24%, qualifying and grid position; car performance; neural lap-time forecast; pit-stop execution; official upgrade package impact
2. Andrea Kimi Antonelli, score 65.8, confidence 24%, qualifying and grid position; car performance; pit-stop execution; driver form; neural lap-time forecast
3. Lando Norris, score 62.5, confidence 24%, qualifying and grid position; official upgrade package impact; car performance; pit-stop execution; ML finish-position model
4. Max Verstappen, score 62.5, confidence 45%, qualifying and grid position; pit-stop execution; same-circuit history; car performance; official upgrade package impact
5. Lewis Hamilton, score 61.2, confidence 37%, qualifying and grid position; official upgrade package impact; car performance; neural lap-time forecast; reliability
6. Oscar Piastri, score 59.7, confidence 42%, qualifying and grid position; official upgrade package impact; car performance; pit-stop execution; reliability
7. Charles Leclerc, score 58.0, confidence 37%, qualifying and grid position; official upgrade package impact; car performance; neural lap-time forecast; constructor form
8. Isack Hadjar, score 57.3, confidence 37%, pit-stop execution; car performance; official upgrade package impact; same-circuit history; reliability
9. Pierre Gasly, score 45.7, confidence 37%, qualifying and grid position; official upgrade package impact; neural lap-time forecast; reliability; pit-stop execution
10. Liam Lawson, score 44.8, confidence 42%, qualifying and grid position; reliability; ML finish-position model; car performance; weather adaptation

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: medium-high
- Weather: 18.9°C, rain 27%, wind 14.8 km/h
- Weather impact: moderate rain risk, radar should influence pit timing; wind may affect braking stability and aero balance

## Strategy

- Baseline: two-stop risk if degradation appears in long runs
- Pit window: Lap 16-28, with safety car flexibility.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. McLaren
3. Ferrari
4. Red Bull
5. Alpine

## Upgrade impact

- Alpine: 83.5/100, aero efficiency, brake cooling, cooling
- McLaren: 83.5/100, aero efficiency, brake cooling, braking stability
- Ferrari: 83.1/100, aero efficiency, diffuser interaction, downforce

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.4%
- ml podium probability: 6.0%
- race pace: 6.0%
- ml finish position score: 4.4%
- car performance: 4.4%

## Model accuracy audit

- Finish-position MAE: 3.29; RMSE: 4.16
- Neural lap-time MAE: 3.77s; RMSE: 5.18s
- Backtest winner hit: 39.3%; top-3 recall: 65.5%; top-5 recall: 76.4%
- Win model AUC/Brier: 0.965 / 0.037
- Podium model AUC/Brier: 0.929 / 0.067

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
