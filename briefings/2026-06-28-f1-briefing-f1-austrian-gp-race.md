# F1 Race Briefing: F1 Austrian GP - Race

Generated: Sunday, 28 June 2026, 12:51 PM IST

## Event

- Target: Race
- Start: Sunday, 28 June 2026, 06:30 PM IST
- Circuit: Red Bull Ring
- Location: Spielberg, Austria

## Prediction

1. Lewis Hamilton, score 67.9, confidence 48%, qualifying and grid position; car performance; ML finish-position model; neural lap-time forecast; pit-stop execution
2. George Russell, score 67.4, confidence 40%, qualifying and grid position; car performance; neural lap-time forecast; official timing car performance; ML finish-position model
3. Charles Leclerc, score 64.0, confidence 40%, qualifying and grid position; car performance; neural lap-time forecast; ML finish-position model; pit-stop execution
4. Andrea Kimi Antonelli, score 60.4, confidence 53%, qualifying and grid position; car performance; driver form; neural lap-time forecast; official timing car performance
5. Max Verstappen, score 59.9, confidence 66%, qualifying and grid position; pit-stop execution; neural lap-time forecast; car performance; ML finish-position model
6. Oscar Piastri, score 58.8, confidence 58%, qualifying and grid position; pit-stop execution; car performance; official timing car performance; same-circuit history
7. Lando Norris, score 58.1, confidence 71%, qualifying and grid position; ML finish-position model; car performance; pit-stop execution; official timing car performance
8. Isack Hadjar, score 52.5, confidence 71%, qualifying and grid position; pit-stop execution; neural lap-time forecast; ML finish-position model; car performance
9. Liam Lawson, score 51.0, confidence 56%, qualifying and grid position; neural lap-time forecast; pit-stop execution; same-circuit history; ML finish-position model
10. Pierre Gasly, score 44.7, confidence 56%, qualifying and grid position; neural lap-time forecast; ML finish-position model; official timing car performance; pit-stop execution

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 34.8°C, rain 28%, wind 4.1 km/h
- Weather impact: moderate rain risk, radar should influence pit timing; heat may increase degradation and cooling demand; cloud cover may reduce track-temperature growth

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

- Alpine: 40.0/100, downforce, braking, cooling
- Aston Martin: 40.0/100, downforce, braking, cooling
- Audi: 40.0/100, straight line, power efficiency

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
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
