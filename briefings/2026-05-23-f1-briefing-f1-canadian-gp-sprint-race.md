# F1 Sprint Briefing: F1 Canadian GP - Sprint Race

Generated: Saturday, 23 May 2026, 01:16 AM IST

## Event

- Target: Sprint
- Start: Saturday, 23 May 2026, 09:30 PM IST
- Circuit: Circuit Gilles Villeneuve
- Location: Montreal, Canada

## Prediction

1. Andrea Kimi Antonelli, score 82.6, confidence 75%, car performance; ML podium probability; pit-stop execution; driver form; ML finish-position model
2. George Russell, score 79.4, confidence 75%, car performance; ML podium probability; pit-stop execution; ML finish-position model; official timing car performance
3. Charles Leclerc, score 68.2, confidence 75%, ML podium probability; car performance; ML finish-position model; team strategy gain; official timing car performance
4. Lewis Hamilton, score 66.5, confidence 75%, car performance; official timing car performance; same-circuit history; ML finish-position model; regulation-era fit
5. Oscar Piastri, score 62.6, confidence 75%, ML finish-position model; car performance; pit-stop execution; ML top 10 probability; official timing car performance
6. Lando Norris, score 60.9, confidence 75%, ML podium probability; ML finish-position model; car performance; ML top 10 probability; official timing car performance
7. Max Verstappen, score 58.5, confidence 75%, same-circuit history; pit-stop execution; ML finish-position model; ML top 10 probability; team strategy gain
8. Pierre Gasly, score 43.7, confidence 75%, team strategy gain; pit-stop execution; car performance; ML finish-position model; neural lap-time forecast
9. Isack Hadjar, score 42.4, confidence 75%, pit-stop execution; car performance; team strategy gain; neural lap-time forecast; ML finish-position model
10. Carlos Sainz, score 40.0, confidence 75%, pit-stop execution; same-circuit history; team strategy gain; regulation-era fit; official timing car performance

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 21.0°C, rain 0%, wind 5.9 km/h
- Weather impact: dry baseline more likely; cloud cover may reduce track-temperature growth

## Strategy

- Baseline: two-stop risk if degradation appears in long runs
- Pit window: Lap 16-28, with safety car flexibility.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. Ferrari
3. McLaren
4. Red Bull
5. Alpine F1 Team

## Upgrade impact

- No trusted upgrade-package signal found for this event.

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- race pace: 6.5%
- ml podium probability: 5.2%
- car performance: 4.8%
- fastf1 race pace: 4.8%
- ml win probability: 3.5%

## Model accuracy audit

- Finish-position MAE: 3.92; RMSE: 4.91
- Neural lap-time MAE: 7.38s; RMSE: 9.17s
- Backtest winner hit: 25.0%; top-3 recall: 66.7%; top-5 recall: 80.0%
- Win model AUC/Brier: 1.000 / 0.024
- Podium model AUC/Brier: 0.942 / 0.073

## Source status

- Stage: Sprint prediction, Practice-aware race-weekend prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used+openf1_free_historical_timing_used
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
