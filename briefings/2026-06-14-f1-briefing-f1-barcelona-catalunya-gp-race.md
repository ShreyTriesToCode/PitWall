# F1 Race Briefing: F1 Barcelona Catalunya GP - Race

Generated: Sunday, 14 June 2026, 12:55 AM IST

## Event

- Target: Race
- Start: Sunday, 14 June 2026, 06:30 PM IST
- Circuit: Circuit de Barcelona-Catalunya
- Location: Barcelona, Spain

## Prediction

1. George Russell, score 71.9, confidence 50%, qualifying and grid position; ML podium probability; car performance; ML finish-position model; pit-stop execution
2. Lewis Hamilton, score 71.7, confidence 68%, qualifying and grid position; ML finish-position model; pit-stop execution; car performance; ML podium probability
3. Andrea Kimi Antonelli, score 64.8, confidence 55%, qualifying and grid position; car performance; driver form; pit-stop execution; ML finish-position model
4. Lando Norris, score 62.5, confidence 66%, qualifying and grid position; ML finish-position model; car performance; pit-stop execution; official timing car performance
5. Oscar Piastri, score 61.2, confidence 62%, qualifying and grid position; pit-stop execution; car performance; ML finish-position model; official timing car performance
6. Max Verstappen, score 60.8, confidence 73%, qualifying and grid position; pit-stop execution; ML finish-position model; reliability; same-circuit history
7. Isack Hadjar, score 59.5, confidence 73%, qualifying and grid position; pit-stop execution; ML finish-position model; reliability; car performance
8. Charles Leclerc, score 57.9, confidence 61%, qualifying and grid position; pit-stop execution; car performance; neural lap-time forecast; reliability
9. Liam Lawson, score 50.8, confidence 66%, qualifying and grid position; pit-stop execution; reliability; ML finish-position model; weather adaptation
10. Nico Hülkenberg, score 47.4, confidence 66%, qualifying and grid position; pit-stop execution; reliability; neural lap-time forecast; weather adaptation

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium
- Tyre stress: medium-high
- Safety car/DNF risk proxy: medium-high
- Weather: 29.0°C, rain 0%, wind 17.2 km/h
- Weather impact: dry baseline more likely; heat may increase degradation and cooling demand; wind may affect braking stability and aero balance; cloud cover may reduce track-temperature growth

## Strategy

- Baseline: two-stop risk if degradation appears in long runs
- Pit window: Lap 16-28, with safety car flexibility.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. Ferrari
3. McLaren
4. Red Bull
5. RB F1 Team

## Upgrade impact

- Audi: 40.0/100, straight line, power efficiency
- Cadillac: 40.0/100, tyre management, power efficiency
- Ferrari: 40.0/100, power efficiency

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.6%
- ml podium probability: 6.2%
- ml finish position score: 4.5%
- car performance: 4.5%
- race pace: 4.5%

## Model accuracy audit

- Finish-position MAE: 3.20; RMSE: 4.04
- Neural lap-time MAE: 4.05s; RMSE: 5.44s
- Backtest winner hit: 46.4%; top-3 recall: 64.3%; top-5 recall: 76.4%
- Win model AUC/Brier: 0.953 / 0.038
- Podium model AUC/Brier: 0.935 / 0.068

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
