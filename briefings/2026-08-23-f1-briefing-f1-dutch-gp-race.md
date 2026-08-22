# F1 Race Briefing: F1 Dutch GP - Race

Generated: Sunday, 23 August 2026, 12:04 AM IST

## Event

- Target: Race
- Start: Sunday, 23 August 2026, 06:30 PM IST
- Circuit: Circuit Park Zandvoort
- Location: Zandvoort, Netherlands

## Prediction

1. George Russell, score 65.2, confidence 23%, qualifying and grid position; car performance; neural lap-time forecast; pit-stop execution; official upgrade package impact
2. Andrea Kimi Antonelli, score 65.2, confidence 23%, qualifying and grid position; car performance; pit-stop execution; driver form; neural lap-time forecast
3. Lando Norris, score 62.2, confidence 23%, qualifying and grid position; official upgrade package impact; car performance; pit-stop execution; ML finish-position model
4. Max Verstappen, score 61.6, confidence 44%, qualifying and grid position; pit-stop execution; same-circuit history; car performance; official upgrade package impact
5. Lewis Hamilton, score 60.5, confidence 36%, qualifying and grid position; official upgrade package impact; car performance; neural lap-time forecast; ML finish-position model
6. Oscar Piastri, score 58.9, confidence 41%, qualifying and grid position; official upgrade package impact; car performance; pit-stop execution; ML finish-position model
7. Charles Leclerc, score 57.4, confidence 36%, qualifying and grid position; official upgrade package impact; car performance; neural lap-time forecast; constructor form
8. Isack Hadjar, score 56.2, confidence 36%, pit-stop execution; car performance; official upgrade package impact; same-circuit history; ML finish-position model
9. Pierre Gasly, score 44.5, confidence 35%, qualifying and grid position; official upgrade package impact; neural lap-time forecast; pit-stop execution; ML finish-position model
10. Franco Colapinto, score 43.5, confidence 35%, official upgrade package impact; pit-stop execution; qualifying and grid position; neural lap-time forecast; team strategy gain

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: medium-high
- Weather: 17.0°C, rain 17%, wind 9.7 km/h
- Weather impact: dry baseline more likely; cloud cover may reduce track-temperature growth

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

- qualifying: 6.5%
- ml podium probability: 6.1%
- race pace: 6.1%
- ml finish position score: 4.5%
- car performance: 4.5%

## Model accuracy audit

- Finish-position MAE: 3.28; RMSE: 4.15
- Neural lap-time MAE: 3.78s; RMSE: 5.18s
- Backtest winner hit: 39.3%; top-3 recall: 65.5%; top-5 recall: 75.7%
- Win model AUC/Brier: 0.964 / 0.037
- Podium model AUC/Brier: 0.929 / 0.067

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
