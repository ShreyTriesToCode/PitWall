# F1 Race Briefing: F1 Austrian GP - Race

Generated: Sunday, 21 June 2026, 05:06 PM IST

## Event

- Target: Race
- Start: Sunday, 28 June 2026, 06:30 PM IST
- Circuit: Red Bull Ring
- Location: Spielberg, Austria

## Prediction

1. Lewis Hamilton, score 63.6, confidence 16%, car performance; same-circuit history; driver form; reliability; pit-stop execution
2. George Russell, score 58.5, confidence 6%, car performance; same-circuit history; driver form; reliability; constructor form
3. Charles Leclerc, score 56.2, confidence 6%, car performance; same-circuit history; reliability; pit-stop execution; regulation-era fit
4. Oscar Piastri, score 54.0, confidence 30%, car performance; same-circuit history; pit-stop execution; reliability; weather adaptation
5. Max Verstappen, score 53.7, confidence 35%, pit-stop execution; car performance; same-circuit history; reliability; neural lap-time forecast
6. Andrea Kimi Antonelli, score 52.6, confidence 35%, car performance; driver form; constructor form; current-season car performance; regulation-era fit
7. Lando Norris, score 52.0, confidence 35%, car performance; same-circuit history; reliability; pit-stop execution; regulation-era fit
8. Isack Hadjar, score 47.4, confidence 47%, car performance; pit-stop execution; neural lap-time forecast; ML finish-position model; same-circuit history
9. Liam Lawson, score 46.6, confidence 29%, same-circuit history; reliability; car performance; pit-stop execution; weather adaptation
10. Pierre Gasly, score 40.2, confidence 34%, reliability; neural lap-time forecast; pit-stop execution; weather adaptation

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 34.1°C, rain 14%, wind 7.2 km/h
- Weather impact: dry baseline more likely; heat may increase degradation and cooling demand; wind may affect braking stability and aero balance

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
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
