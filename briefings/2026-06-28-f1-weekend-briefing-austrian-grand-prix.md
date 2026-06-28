# F1 Race Briefing: F1 Austrian GP - Race

Generated: Sunday, 28 June 2026, 03:24 PM IST

## Event

- Target: Race
- Start: Sunday, 28 June 2026, 06:30 PM IST
- Circuit: Red Bull Ring
- Location: Spielberg, Austria

## Prediction

1. Lewis Hamilton, score 68.8, confidence 29%, qualifying and grid position; car performance; official upgrade package impact; ML finish-position model; neural lap-time forecast
2. George Russell, score 65.5, confidence 21%, qualifying and grid position; car performance; official upgrade package impact; neural lap-time forecast; constructor form
3. Charles Leclerc, score 64.5, confidence 21%, qualifying and grid position; car performance; official upgrade package impact; neural lap-time forecast; ML finish-position model
4. Max Verstappen, score 59.8, confidence 42%, qualifying and grid position; official upgrade package impact; pit-stop execution; neural lap-time forecast; car performance
5. Andrea Kimi Antonelli, score 57.9, confidence 40%, qualifying and grid position; car performance; official upgrade package impact; driver form; neural lap-time forecast
6. Lando Norris, score 57.8, confidence 52%, qualifying and grid position; official upgrade package impact; ML finish-position model; car performance; pit-stop execution
7. Oscar Piastri, score 57.2, confidence 40%, qualifying and grid position; official upgrade package impact; car performance; pit-stop execution; same-circuit history
8. Isack Hadjar, score 53.0, confidence 52%, qualifying and grid position; official upgrade package impact; pit-stop execution; neural lap-time forecast; ML finish-position model
9. Liam Lawson, score 48.9, confidence 44%, qualifying and grid position; official upgrade package impact; neural lap-time forecast; pit-stop execution; same-circuit history
10. Pierre Gasly, score 44.3, confidence 39%, qualifying and grid position; official upgrade package impact; neural lap-time forecast; ML finish-position model; car performance

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 35.0°C, rain 25%, wind 5.8 km/h
- Weather impact: moderate rain risk, radar should influence pit timing; heat may increase degradation and cooling demand

## Strategy

- Baseline: two-stop risk if degradation appears in long runs
- Pit window: Lap 16-28, with safety car flexibility.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Ferrari
2. Mercedes
3. McLaren
4. Red Bull
5. RB F1 Team

## Upgrade impact

- Cadillac: 83.5/100, aero efficiency, brake cooling, cooling
- Audi: 83.5/100, aero balance, aero efficiency, brake cooling
- Red Bull: 83.5/100, aero efficiency, brake cooling, cooling

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

- Finish-position MAE: 3.20; RMSE: 4.06
- Neural lap-time MAE: 3.74s; RMSE: 5.08s
- Backtest winner hit: 50.0%; top-3 recall: 67.9%; top-5 recall: 76.4%
- Win model AUC/Brier: 0.947 / 0.038
- Podium model AUC/Brier: 0.939 / 0.069

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
