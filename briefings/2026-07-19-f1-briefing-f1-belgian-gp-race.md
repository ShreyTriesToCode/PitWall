# F1 Race Briefing: F1 Belgian GP - Race

Generated: Sunday, 19 July 2026, 11:47 AM IST

## Event

- Target: Race
- Start: Sunday, 19 July 2026, 06:30 PM IST
- Circuit: Circuit de Spa-Francorchamps
- Location: Spa, Belgium

## Prediction

1. Andrea Kimi Antonelli, score 68.8, confidence 33%, qualifying and grid position; car performance; official upgrade package impact; track trait fit; pit-stop execution
2. George Russell, score 68.6, confidence 15%, qualifying and grid position; car performance; official upgrade package impact; track trait fit; pit-stop execution
3. Charles Leclerc, score 66.2, confidence 10%, qualifying and grid position; car performance; track trait fit; pit-stop execution; team-track fit
4. Lewis Hamilton, score 66.0, confidence 33%, qualifying and grid position; car performance; track trait fit; pit-stop execution; team-track fit
5. Max Verstappen, score 64.3, confidence 51%, qualifying and grid position; car performance; team-track fit; track trait fit; ML finish-position model
6. Lando Norris, score 64.0, confidence 51%, qualifying and grid position; car performance; team-track fit; track trait fit; pit-stop execution
7. Oscar Piastri, score 57.3, confidence 43%, qualifying and grid position; car performance; team-track fit; track trait fit; pit-stop execution
8. Isack Hadjar, score 50.3, confidence 56%, qualifying and grid position; car performance; team-track fit; track trait fit; pit-stop execution
9. Liam Lawson, score 50.2, confidence 43%, qualifying and grid position; official upgrade package impact; pit-stop execution; car performance; reliability
10. Arvid Lindblad, score 46.2, confidence 48%, qualifying and grid position; official upgrade package impact; pit-stop execution; car performance; neural lap-time forecast

## Track and weather

- Key car trait: high-speed downforce, aero efficiency, tyre load control
- Track profile: aero-efficiency dominant
- Overtaking: medium
- Tyre stress: medium-high
- Safety car/DNF risk proxy: low-medium
- Weather: 18.1°C, rain 33%, wind 9.0 km/h
- Weather impact: moderate rain risk, radar should influence pit timing; wind may affect braking stability and aero balance

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

- Haas: 83.5/100, aero balance, brake cooling, corner entry stability
- RB F1 Team: 83.5/100, aero efficiency, brake cooling, cooling
- Williams: 83.1/100, aero efficiency, brake cooling, braking stability

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.3%
- ml podium probability: 5.9%
- car performance: 5.9%
- ml finish position score: 4.3%
- race pace: 4.3%

## Model accuracy audit

- Finish-position MAE: 3.23; RMSE: 4.05
- Neural lap-time MAE: 4.10s; RMSE: 5.56s
- Backtest winner hit: 46.4%; top-3 recall: 65.5%; top-5 recall: 77.9%
- Win model AUC/Brier: 0.955 / 0.037
- Podium model AUC/Brier: 0.936 / 0.065

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_timing_no_completed_sessions_yet;openf1_skipped_optional_no_token
- FastF1 sessions: ['R', 'Q', 'FP3', 'FP2', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
