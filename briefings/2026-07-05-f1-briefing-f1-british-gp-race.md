# F1 Race Briefing: F1 British GP - Race

Generated: Sunday, 05 July 2026, 02:26 PM IST

## Event

- Target: Race
- Start: Sunday, 05 July 2026, 07:30 PM IST
- Circuit: Silverstone Circuit
- Location: Silverstone, UK

## Prediction

1. Lewis Hamilton, score 67.5, confidence 36%, qualifying and grid position; car performance; ML finish-position model; track trait fit; same-circuit history
2. Andrea Kimi Antonelli, score 65.7, confidence 48%, qualifying and grid position; car performance; ML finish-position model; track trait fit; driver form
3. Lando Norris, score 64.1, confidence 26%, qualifying and grid position; car performance; team-track fit; official upgrade package impact; track trait fit
4. George Russell, score 62.8, confidence 48%, qualifying and grid position; car performance; track trait fit; neural lap-time forecast; ML finish-position model
5. Charles Leclerc, score 62.5, confidence 59%, qualifying and grid position; car performance; ML finish-position model; track trait fit; official upgrade package impact
6. Oscar Piastri, score 62.0, confidence 54%, qualifying and grid position; car performance; team-track fit; official upgrade package impact; track trait fit
7. Max Verstappen, score 58.9, confidence 59%, qualifying and grid position; car performance; official upgrade package impact; ML finish-position model; neural lap-time forecast
8. Isack Hadjar, score 51.4, confidence 59%, qualifying and grid position; car performance; official upgrade package impact; ML finish-position model; team-track fit
9. Arvid Lindblad, score 44.8, confidence 51%, qualifying and grid position; official upgrade package impact; car performance; ML finish-position model; neural lap-time forecast
10. Liam Lawson, score 43.0, confidence 59%, qualifying and grid position; official upgrade package impact; car performance; neural lap-time forecast; track trait fit

## Track and weather

- Key car trait: high-speed downforce, aero efficiency, tyre load control
- Track profile: aero-efficiency dominant
- Overtaking: medium-good
- Tyre stress: medium
- Safety car/DNF risk proxy: medium-high
- Weather: 24.5°C, rain 0%, wind 10.4 km/h
- Weather impact: dry baseline more likely; wind may affect braking stability and aero balance

## Strategy

- Baseline: one-stop or two-stop depending on safety car and tyre delta
- Pit window: Lap 18-32 for normal dry strategy.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. Ferrari
3. McLaren
4. Red Bull
5. RB F1 Team

## Upgrade impact

- RB F1 Team: 83.1/100, aero efficiency, brake cooling, diffuser feed
- McLaren: 77.7/100, aero efficiency, brake cooling, braking stability
- Red Bull: 69.5/100, aero efficiency, brake cooling, cooling

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.3%
- ml podium probability: 5.9%
- car performance: 5.9%
- ml finish position score: 4.4%
- race pace: 4.4%

## Model accuracy audit

- Finish-position MAE: 3.29; RMSE: 4.12
- Neural lap-time MAE: 3.86s; RMSE: 5.37s
- Backtest winner hit: 46.4%; top-3 recall: 63.1%; top-5 recall: 75.7%
- Win model AUC/Brier: 0.951 / 0.038
- Podium model AUC/Brier: 0.937 / 0.067

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
