# F1 Race Briefing: Canadian Grand Prix Race

Generated: Sunday, 24 May 2026, 12:13 PM IST

## Event

- Target: Race
- Start: Monday, 25 May 2026, 01:30 AM IST
- Circuit: Circuit Gilles Villeneuve
- Location: Montreal, Canada

## Prediction

1. George Russell, score 76.6, confidence 76%, qualifying and grid position; ML podium probability; car performance; pit-stop execution; official timing car performance
2. Andrea Kimi Antonelli, score 76.3, confidence 76%, qualifying and grid position; car performance; pit-stop execution; driver form; ML podium probability
3. Lewis Hamilton, score 62.2, confidence 76%, qualifying and grid position; car performance; reliability; official timing car performance; same-circuit history
4. Lando Norris, score 61.8, confidence 76%, qualifying and grid position; ML podium probability; car performance; ML finish-position model; official timing car performance
5. Oscar Piastri, score 61.6, confidence 76%, qualifying and grid position; neural lap-time forecast; car performance; reliability; pit-stop execution
6. Max Verstappen, score 58.5, confidence 76%, qualifying and grid position; same-circuit history; reliability; ML finish-position model; weather adaptation
7. Charles Leclerc, score 58.1, confidence 76%, qualifying and grid position; car performance; team strategy gain; reliability; official timing car performance
8. Isack Hadjar, score 46.6, confidence 78%, qualifying and grid position; pit-stop execution; ML finish-position model; car performance; official timing car performance
9. Nico Hülkenberg, score 40.6, confidence 76%, qualifying and grid position; pit-stop execution; team strategy gain; reliability; weather adaptation
10. Franco Colapinto, score 40.5, confidence 63%, qualifying and grid position; pit-stop execution; ML finish-position model; team strategy gain; reliability

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 12.4°C, rain 10%, wind 18.2 km/h
- Weather impact: dry baseline more likely; wind may affect braking stability and aero balance; cloud cover may reduce track-temperature growth

## Strategy

- Baseline: two-stop risk if degradation appears in long runs
- Pit window: Lap 16-28, with safety car flexibility.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. McLaren
3. Ferrari
4. Red Bull
5. Audi

## Upgrade impact

- Audi: 40.0/100, straight line, power efficiency
- Ferrari: 40.0/100, downforce, aero efficiency, traction
- McLaren: 40.0/100, downforce, aero efficiency, cooling

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- qualifying: 6.4%
- ml podium probability: 6.0%
- race pace: 6.0%
- ml finish position score: 4.4%
- car performance: 4.4%

## Model accuracy audit

- Finish-position MAE: 3.22; RMSE: 4.11
- Neural lap-time MAE: 4.67s; RMSE: 6.17s
- Backtest winner hit: 29.4%; top-3 recall: 61.3%; top-5 recall: 74.4%
- Win model AUC/Brier: 0.963 / 0.032
- Podium model AUC/Brier: 0.934 / 0.074

## Source status

- Stage: Race prediction, Post-qualifying prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
