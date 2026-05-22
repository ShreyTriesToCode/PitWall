# F1 Weekend Briefing: Canadian Grand Prix Sprint + Race

Generated: Friday, 22 May 2026, 10:19 PM IST

Output mode: weekend

This briefing deliberately outputs only Sprint and Race predictions. Practice, Qualifying, Sprint Qualifying, weather, upgrades, F1 timing, OpenF1, FastF1, Jolpica, track traits, regulations, and historical cache data are used as supporting inputs only.

## Output targets

- Sprint: F1 Canadian GP - Sprint Race at Saturday, 23 May 2026, 09:30 PM IST
- Race: F1 Canadian GP - Race at Monday, 25 May 2026, 01:30 AM IST

---

## Sprint Target: F1 Canadian GP - Sprint Race

## Event

- Target: Sprint
- Start: Saturday, 23 May 2026, 09:30 PM IST
- Circuit: Circuit Gilles Villeneuve
- Location: Montreal, Canada

## Prediction

1. Andrea Kimi Antonelli, score 79.4, confidence 80%, ML podium probability; car performance; pit-stop execution; driver form; ML finish-position model
2. George Russell, score 75.1, confidence 80%, car performance; ML podium probability; pit-stop execution; ML finish-position model; constructor form
3. Charles Leclerc, score 67.8, confidence 80%, ML podium probability; car performance; ML finish-position model; official timing car performance; team strategy gain
4. Lewis Hamilton, score 64.0, confidence 80%, car performance; same-circuit history; ML finish-position model; official timing car performance; regulation-era fit
5. Lando Norris, score 62.4, confidence 80%, ML podium probability; ML finish-position model; car performance; official timing car performance; ML top 10 probability
6. Oscar Piastri, score 62.4, confidence 80%, ML finish-position model; car performance; official timing car performance; pit-stop execution; ML top 10 probability
7. Max Verstappen, score 59.3, confidence 80%, same-circuit history; pit-stop execution; ML finish-position model; ML top 10 probability; official timing car performance
8. Pierre Gasly, score 47.5, confidence 76%, team strategy gain; pit-stop execution; car performance; official timing car performance; regulation-era fit
9. Franco Colapinto, score 45.3, confidence 76%, pit-stop execution; team strategy gain; car performance; official timing car performance; regulation-era fit
10. Isack Hadjar, score 43.2, confidence 80%, pit-stop execution; car performance; team strategy gain; neural lap-time forecast; ML finish-position model

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

- Ferrari: 40.0/100, downforce, aero efficiency, traction
- McLaren: 40.0/100, downforce, aero efficiency, cooling
- Mercedes: 40.0/100, downforce, aero efficiency, traction

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- race pace: 6.3%
- ml podium probability: 5.1%
- car performance: 4.6%
- fastf1 race pace: 4.6%
- upgrade package impact: 4.2%

## Model accuracy audit

- Finish-position MAE: 3.92; RMSE: 4.91
- Neural lap-time MAE: 7.38s; RMSE: 9.17s
- Backtest winner hit: 25.0%; top-3 recall: 66.7%; top-5 recall: 80.0%
- Win model AUC/Brier: 1.000 / 0.024
- Podium model AUC/Brier: 0.942 / 0.073

## Source status

- Stage: Sprint prediction, Practice-aware race-weekend prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.
## Race Target: F1 Canadian GP - Race

## Event

- Target: Race
- Start: Monday, 25 May 2026, 01:30 AM IST
- Circuit: Circuit Gilles Villeneuve
- Location: Montreal, Canada

## Prediction

1. Andrea Kimi Antonelli, score 79.7, confidence 82%, weather adaptation; reliability; ML podium probability; car performance; pit-stop execution
2. George Russell, score 74.8, confidence 82%, weather adaptation; reliability; car performance; ML podium probability; pit-stop execution
3. Charles Leclerc, score 68.6, confidence 82%, weather adaptation; ML podium probability; reliability; team strategy gain; car performance
4. Lewis Hamilton, score 65.9, confidence 82%, weather adaptation; reliability; team strategy gain; car performance; same-circuit history
5. Oscar Piastri, score 63.4, confidence 82%, reliability; weather adaptation; ML finish-position model; car performance; official timing car performance
6. Lando Norris, score 62.1, confidence 82%, reliability; weather adaptation; ML podium probability; ML finish-position model; car performance
7. Max Verstappen, score 61.9, confidence 82%, weather adaptation; reliability; team strategy gain; same-circuit history; pit-stop execution
8. Pierre Gasly, score 50.5, confidence 78%, team strategy gain; weather adaptation; reliability; pit-stop execution; car performance
9. Franco Colapinto, score 46.5, confidence 78%, team strategy gain; weather adaptation; reliability; pit-stop execution; car performance
10. Isack Hadjar, score 44.1, confidence 82%, team strategy gain; reliability; weather adaptation; pit-stop execution; car performance

## Track and weather

- Key car trait: balanced aero, traction, braking, and tyre management
- Track profile: balanced speed profile
- Overtaking: medium-good
- Tyre stress: medium-high
- Safety car/DNF risk proxy: high
- Weather: 9.4°C, rain 67%, wind 15.8 km/h
- Weather impact: high rain risk, mixed strategy possible; wind may affect braking stability and aero balance; cloud cover may reduce track-temperature growth

## Strategy

- Baseline: two-stop risk if degradation appears in long runs
- Pit window: Delay fixed dry-tyre stops. Watch radar and react to rain onset.
- Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.

## Team fit

1. Mercedes
2. Ferrari
3. McLaren
4. Red Bull
5. Alpine F1 Team

## Upgrade impact

- Ferrari: 40.0/100, downforce, aero efficiency, traction
- McLaren: 40.0/100, downforce, aero efficiency, cooling
- Mercedes: 40.0/100, downforce, aero efficiency, traction

## Regulation context

Era: 2026+ active-aero and new power-unit era

- The FIA/F1 2026 rules introduce smaller, lighter cars, reduced drag/downforce targets, active aerodynamics, more electrical power, sustainable fuels, and Manual Override Mode.
- Prediction should reward efficient aero switching, straight-line efficiency, energy deployment, traction, braking stability, reliability, and driver adaptability.

## Main model signals

- race pace: 5.8%
- weather adaptation: 5.4%
- ml podium probability: 4.6%
- team strategy: 4.6%
- reliability: 4.6%

## Model accuracy audit

- Finish-position MAE: 3.92; RMSE: 4.91
- Neural lap-time MAE: 7.38s; RMSE: 9.17s
- Backtest winner hit: 25.0%; top-3 recall: 66.7%; top-5 recall: 80.0%
- Win model AUC/Brier: 1.000 / 0.024
- Podium model AUC/Brier: 0.942 / 0.073

## Source status

- Stage: Race prediction, Practice-aware race-weekend prediction
- ML model: loaded
- F1 timing: official_f1_live_timing_static_used
- FastF1 sessions: ['R', 'Q', 'SQ', 'S', 'FP1']
- Calendar check: official_f1_calendar_page_reachable

---

Predictions are estimates, not guaranteed race results.

---

Generated by PitWall. Predictions are model estimates, not guaranteed race results.
