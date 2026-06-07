# F1 Race Briefing: F1 Monaco GP - Race

Generated: Sunday, 07 June 2026, 01:13 PM IST

## Event

- Target: Race
- Start: Sunday, 07 June 2026, 06:30 PM IST
- Circuit: Circuit de Monaco
- Location: Monte Carlo, Monaco

## Prediction

1. Andrea Kimi Antonelli, score 67.5, confidence 35%, qualifying and grid position; car performance; ML podium probability; track trait fit; team-track fit
2. Lewis Hamilton, score 64.5, confidence 27%, qualifying and grid position; car performance; team-track fit; track trait fit; ML podium probability
3. Max Verstappen, score 62.1, confidence 35%, qualifying and grid position; car performance; team-track fit; ML podium probability; track trait fit
4. Charles Leclerc, score 61.0, confidence 40%, qualifying and grid position; car performance; team-track fit; track trait fit; regulation-era fit
5. George Russell, score 61.0, confidence 48%, qualifying and grid position; car performance; track trait fit; team-track fit; neural lap-time forecast
6. Oscar Piastri, score 54.7, confidence 40%, qualifying and grid position; car performance; team-track fit; track trait fit; same-circuit history
7. Lando Norris, score 53.6, confidence 40%, qualifying and grid position; car performance; team-track fit; track trait fit; same-circuit history
8. Isack Hadjar, score 53.2, confidence 53%, qualifying and grid position; car performance; team-track fit; track trait fit; neural lap-time forecast
9. Liam Lawson, score 41.3, confidence 39%, qualifying and grid position; team-track fit; track trait fit; car performance; pit-stop execution
10. Pierre Gasly, score 39.2, confidence 44%, qualifying and grid position; team-track fit; ML finish-position model; track trait fit

## Track and weather

- Key car trait: high downforce, slow-corner traction, kerb compliance
- Track profile: traction and braking dominant
- Overtaking: medium
- Tyre stress: medium
- Safety car/DNF risk proxy: high
- Weather: 22.4°C, rain 0%, wind 11.9 km/h
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

- Alpine: 40.0/100, power efficiency
- Audi: 40.0/100, straight line, power efficiency
- Cadillac: 40.0/100, power efficiency

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.7%
- ml podium probability: 6.3%
- car performance: 6.3%
- ml finish position score: 4.6%
- team track fit: 4.2%

## Model accuracy audit

- Finish-position MAE: 3.22; RMSE: 4.11
- Neural lap-time MAE: 4.66s; RMSE: 6.08s
- Backtest winner hit: 30.9%; top-3 recall: 61.8%; top-5 recall: 74.4%
- Win model AUC/Brier: 0.963 / 0.032
- Podium model AUC/Brier: 0.934 / 0.073

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
