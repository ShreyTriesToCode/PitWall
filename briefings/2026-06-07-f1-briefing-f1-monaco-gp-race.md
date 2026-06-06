# F1 Race Briefing: F1 Monaco GP - Race

Generated: Sunday, 07 June 2026, 12:56 AM IST

## Event

- Target: Race
- Start: Sunday, 07 June 2026, 06:30 PM IST
- Circuit: Circuit de Monaco
- Location: Monte Carlo, Monaco

## Prediction

1. Andrea Kimi Antonelli, score 72.0, confidence 50%, qualifying and grid position; car performance; ML podium probability; team-track fit; neural lap-time forecast
2. Lewis Hamilton, score 70.3, confidence 43%, qualifying and grid position; car performance; team-track fit; track trait fit; ML podium probability
3. Charles Leclerc, score 67.2, confidence 33%, qualifying and grid position; car performance; team-track fit; track trait fit; official timing car performance
4. Max Verstappen, score 67.1, confidence 64%, qualifying and grid position; car performance; team-track fit; ML podium probability; same-circuit history
5. George Russell, score 65.7, confidence 64%, car performance; qualifying and grid position; team-track fit; neural lap-time forecast; regulation-era fit
6. Oscar Piastri, score 58.8, confidence 56%, qualifying and grid position; car performance; team-track fit; track trait fit; same-circuit history
7. Isack Hadjar, score 56.0, confidence 69%, qualifying and grid position; car performance; team-track fit; neural lap-time forecast; track trait fit
8. Lando Norris, score 55.4, confidence 61%, qualifying and grid position; car performance; team-track fit; track trait fit; same-circuit history
9. Liam Lawson, score 43.5, confidence 61%, qualifying and grid position; car performance; team-track fit; pit-stop execution; track trait fit
10. Pierre Gasly, score 42.7, confidence 59%, qualifying and grid position; team-track fit; ML finish-position model; regulation-era fit

## Track and weather

- Key car trait: high downforce, slow-corner traction, kerb compliance
- Track profile: traction and braking dominant
- Overtaking: medium
- Tyre stress: medium
- Safety car/DNF risk proxy: high
- Weather: 22.9°C, rain 0%, wind 10.5 km/h
- Weather impact: dry baseline more likely

## Strategy

- Baseline: one-stop or two-stop depending on safety car and tyre delta
- Pit window: Lap 18-32 for normal dry strategy.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. Ferrari
3. Red Bull
4. McLaren
5. RB F1 Team

## Upgrade impact

- No trusted upgrade-package signal found for this event.

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.9%
- ml podium probability: 6.5%
- car performance: 6.5%
- ml finish position score: 4.7%
- team track fit: 4.3%

## Model accuracy audit

- Finish-position MAE: 3.22; RMSE: 4.11
- Neural lap-time MAE: 4.66s; RMSE: 6.08s
- Backtest winner hit: 30.9%; top-3 recall: 61.8%; top-5 recall: 74.4%
- Win model AUC/Brier: 0.963 / 0.032
- Podium model AUC/Brier: 0.934 / 0.073

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
