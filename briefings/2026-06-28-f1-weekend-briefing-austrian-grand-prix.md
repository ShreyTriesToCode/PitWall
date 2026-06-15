# F1 Race Briefing: F1 Austrian GP - Race

Generated: Monday, 15 June 2026, 08:22 PM IST

## Event

- Target: Race
- Start: Sunday, 28 June 2026, 06:30 PM IST
- Circuit: Red Bull Ring
- Location: Spielberg, Austria

## Prediction

1. Lewis Hamilton, score 67.7, confidence 39%, car performance; same-circuit history; driver form; reliability; pit-stop execution
2. George Russell, score 62.5, confidence 29%, car performance; same-circuit history; driver form; reliability; official timing car performance
3. Charles Leclerc, score 60.0, confidence 29%, car performance; same-circuit history; reliability; pit-stop execution; official timing car performance
4. Oscar Piastri, score 58.5, confidence 52%, car performance; same-circuit history; pit-stop execution; official timing car performance; reliability
5. Andrea Kimi Antonelli, score 58.1, confidence 57%, car performance; driver form; official timing car performance; constructor form; regulation-era fit
6. Max Verstappen, score 57.0, confidence 57%, car performance; pit-stop execution; same-circuit history; reliability; official timing car performance
7. Lando Norris, score 56.5, confidence 55%, car performance; same-circuit history; reliability; pit-stop execution; official timing car performance
8. Isack Hadjar, score 53.1, confidence 70%, car performance; pit-stop execution; official timing car performance; neural lap-time forecast; ML finish-position model
9. Liam Lawson, score 49.7, confidence 50%, same-circuit history; reliability; car performance; pit-stop execution; weather adaptation
10. Pierre Gasly, score 45.1, confidence 55%, car performance; reliability; neural lap-time forecast; pit-stop execution; official timing car performance

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 22.1°C, rain 33%, wind 4.6 km/h
- Weather impact: moderate rain risk, radar should influence pit timing; wind may affect braking stability and aero balance

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

- race pace: 6.2%
- car performance: 5.8%
- ml podium probability: 4.9%
- driver form: 4.1%
- upgrade package impact: 4.1%

## Model accuracy audit

- Finish-position MAE: 3.20; RMSE: 4.06
- Neural lap-time MAE: 3.74s; RMSE: 5.08s
- Backtest winner hit: 50.0%; top-3 recall: 67.9%; top-5 recall: 76.4%
- Win model AUC/Brier: 0.947 / 0.038
- Podium model AUC/Brier: 0.939 / 0.069

## Source status

- Stage: Race prediction, Pre-weekend prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
