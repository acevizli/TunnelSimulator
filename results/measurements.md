# Measurements

8 scenarios × 20 seeds (seed k is the scenario's own seed + k), every estimator fed the same sensor data. Nothing here is graded: these are measurements, not pass/fail.

Each cell is the median over the seeds, then the 95th percentile: 1 run in 20 is worse than that. For honesty, where lower is worse, it is the 5th percentile instead. "never" means it never happened (no recovery, no callout, no decision). Worst runs name their seed, to open in the replay.

Phases: before the tunnel, entering (its first 200 m), inside, stopped, exiting (200 m either side of the end), between tunnels, after the tunnel.

## What each metric means

- **largest error inside**: the largest along-track error while the car is in a tunnel
- **largest error inside, % of tunnel**: the same, as a share of the total tunnel length
- **error at the exit**: the along-track error as the car leaves the last tunnel
- **honesty**: share of the time in the tunnel that the car is inside the uncertainty band; about 95% is honest, lower means the band is too narrow, 100% can mean it is wider than it needs to be
- **recovery after the exit**: seconds after the last tunnel until the estimate is within 10 m of the car and stays there
- **largest jump**: the largest sudden move of the shown position in one tick, beyond the car's own motion
- **callout <d> m, late by**: how far past the announced point the car already was when "exit in <d> m" was said; negative = early
- **branch decided**: how far past a split the car was when the estimate settled on the branch the car took; negative = before the car got there (the estimate was ahead)
- **on the wrong branch**: seconds the estimate was shown on a branch the car isn't driving
- **missed exit called**: how far past the split the car was when the app said the exit was missed
- **false missed exit**: runs where the app said the exit was missed although the car took it

## Summary: largest error inside

| Scenario | baseline | map filter | map filter + vehicle speed | map filter + beacons |
|---|---|---|---|---|
| 1 · Straight + free flow | 35 m / 61 m (worst 76 m, seed 8) | 7.2 m / 20 m (worst 21 m, seed 16) | – | – |
| 2 · Straight 5 km + stop-and-go | 4248 m / 4329 m (worst 4331 m, seed 8) | 23 m / 54 m (worst 67 m, seed 5) | – | – |
| 3 · Two exits + slowdown | 665 m / 713 m (worst 750 m, seed 7) | 12 m / 27 m (worst 31 m, seed 17) | – | – |
| 4 · Fork + missed exit | 4999 m / 4999 m (worst 5000 m, seed 22) | 14 m / 26 m (worst 33 m, seed 18) | – | – |
| 5 · Long grade + loose phone | 70 m / 137 m (worst 154 m, seed 8) | 9.0 m / 20 m (worst 23 m, seed 18) | – | – |
| 6 · Spiral + free flow | 879 m / 991 m (worst 1005 m, seed 8) | 6.7 m / 23 m (worst 24 m, seed 19) | – | – |
| 7 · Long grade + speed change + vehicle speed | 938 m / 1024 m (worst 1102 m, seed 22) | 10 m / 16 m (worst 17 m, seed 25) | 4.3 m / 6.7 m (worst 7.4 m, seed 25) | – |
| 8 · Straight 5 km + stop-and-go + beacons | 4248 m / 4329 m (worst 4331 m, seed 8) | 15 m / 50 m (worst 78 m, seed 23) | – | 8.2 m / 10 m (worst 13 m, seed 14) |

## 1 · Straight + free flow

The easy case: flat, straight 2 km tunnel at a steady 80 km/h.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 35 m | 61 m | 76 m | seed 8: ahead, 4000 m along, t = 180.0 s, exiting |
| largest error inside | map filter | 7.2 m | 20 m | 21 m | seed 16: behind, 4000 m along, t = 180.0 s, exiting |
| largest error inside, % of tunnel | baseline | 1.7 % | 3.0 % | 3.8 % | seed 8: 4000 m along, t = 180.0 s, exiting |
| largest error inside, % of tunnel | map filter | 0.4 % | 1.0 % | 1.0 % | seed 16: 4000 m along, t = 180.0 s, exiting |
| error at the exit | baseline | 21 m | 59 m | 61 m | seed 18: behind, 4002 m along, t = 180.0 s, exiting |
| error at the exit | map filter | 7.2 m | 20 m | 21 m | seed 16: behind, 4002 m along, t = 180.1 s, exiting |
| honesty | map filter | 100 % | 92 % | 90 % | seed 6: furthest out: error 1.4× the band, 2000 m along, t = 90.1 s, entering |
| recovery after the exit | baseline | 9.0 s | 42.2 s | 44.4 s | seed 18: 4991 m along, t = 224.4 s, after the tunnel |
| recovery after the exit | map filter | 0.0 s | 7.0 s | 7.4 s | seed 16: 4170 m along, t = 187.5 s, exiting |
| largest jump | baseline | 45 m | 74 m | 75 m | seed 20: 4044 m along, t = 182.1 s, exiting |
| largest jump | map filter | 3.3 m | 6.5 m | 7.4 m | seed 5: 4152 m along, t = 187.1 s, exiting |

## 2 · Straight 5 km + stop-and-go

Where things break: a long tunnel with no landmarks and repeated stops.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 4248 m | 4329 m | 4331 m | seed 8: ahead, 3669 m along, t = 390.3 s, stopped |
| largest error inside | map filter | 23 m | 54 m | 67 m | seed 5: behind, 7000 m along, t = 1006.0 s, exiting |
| largest error inside, % of tunnel | baseline | 85 % | 87 % | 87 % | seed 8: 3669 m along, t = 390.3 s, stopped |
| largest error inside, % of tunnel | map filter | 0.5 % | 1.1 % | 1.3 % | seed 5: 7000 m along, t = 1006.0 s, exiting |
| error at the exit | baseline | 1000 m | 1000 m | 1000 m | seed 20: ahead, 7000 m along, t = 1005.3 s, exiting |
| error at the exit | map filter | 23 m | 54 m | 67 m | seed 5: behind, 7000 m along, t = 1006.1 s, exiting |
| honesty | map filter | 100 % | 98 % | 97 % | seed 18: furthest out: error 1.6× the band, 2000 m along, t = 90.0 s, entering |
| recovery after the exit | baseline | 8.8 s | 42.5 s | 45.7 s | seed 18: 7967 m along, t = 1052.1 s, after the tunnel |
| recovery after the exit | map filter | 6.8 s | 8.1 s | 8.4 s | seed 5: 7135 m along, t = 1014.5 s, exiting |
| largest jump | baseline | 1007 m | 1024 m | 1033 m | seed 19: 7011 m along, t = 1008.1 s, exiting |
| largest jump | map filter | 4.0 m | 6.9 m | 9.4 m | seed 5: 7106 m along, t = 1013.1 s, exiting |

## 3 · Two exits + slowdown

Callout timing: two exits 400 m apart, the route takes the second, traffic slows at the entrance.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 665 m | 713 m | 750 m | seed 7: behind, 3898 m along, t = 207.5 s, exiting |
| largest error inside | map filter | 12 m | 27 m | 31 m | seed 17: ahead, 3071 m along, t = 168.9 s, inside |
| largest error inside, % of tunnel | baseline | 35 % | 38 % | 39 % | seed 7: 3898 m along, t = 207.5 s, exiting |
| largest error inside, % of tunnel | map filter | 0.6 % | 1.4 % | 1.6 % | seed 17: 3071 m along, t = 168.9 s, inside |
| error at the exit | baseline | 666 m | 714 m | 751 m | seed 7: behind, 3900 m along, t = 207.6 s, exiting |
| error at the exit | map filter | 2.0 m | 3.2 m | 3.6 m | seed 13: behind, 3900 m along, t = 207.4 s, exiting |
| honesty | map filter | 100 % | 95 % | 84 % | seed 17: furthest out: error 1.2× the band, 3334 m along, t = 180.9 s, inside |
| recovery after the exit | baseline | 4.5 s | 36.7 s | 44.0 s | seed 4: 4878 m along, t = 251.1 s, after the tunnel |
| recovery after the exit | map filter | 0.0 s | 0.0 s | 0.0 s | seed 3: 3902 m along, t = 207.6 s, exiting |
| largest jump | baseline | 678 m | 739 m | 739 m | seed 7: 3933 m along, t = 209.1 s, exiting |
| largest jump | map filter | 5.6 m | 18 m | 30 m | seed 17: 3210 m along, t = 175.3 s, inside |
| callout 400 m, late by | baseline | 634 m | 728 m | 733 m | seed 7: 3933 m along, t = 209.1 s, exiting |
| callout 400 m, late by | map filter | -34 m | -21 m | -19 m | seed 6: 3181 m along, t = 173.7 s, inside |
| callout 100 m, late by | baseline | 437 m | 442 m | 446 m | seed 4: 3946 m along, t = 209.1 s, exiting |
| callout 100 m, late by | map filter | -10 m | -5.3 m | 1.5 m | seed 17: 3502 m along, t = 188.4 s, inside |
| branch decided | baseline | 634 m | 728 m | 733 m | seed 7: at the Exit A split, 3933 m along, t = 209.1 s, exiting |
| branch decided | map filter | 8.0 m | 10 m | 11 m | seed 22: at the Exit A split, 3211 m along, t = 175.3 s, inside |
| on the wrong branch | baseline | 0.0 s | 0.0 s | 0.0 s | seed 3 |
| on the wrong branch | map filter | 0.0 s | 0.0 s | 0.0 s | seed 3 |
| false missed exit | baseline |  |  | 0 of 20 runs |  |
| false missed exit | map filter |  |  | 0 of 20 runs |  |

## 4 · Fork + missed exit

Branch decision: the route says fork right, the driver stays left.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 4999 m | 4999 m | 5000 m | seed 22: ahead, 7550 m along, t = 388.2 s, exiting |
| largest error inside | map filter | 14 m | 26 m | 33 m | seed 18: ahead, 7548 m along, t = 388.3 s, exiting |
| largest error inside, % of tunnel | baseline | 88 % | 88 % | 88 % | seed 22: 7550 m along, t = 388.2 s, exiting |
| largest error inside, % of tunnel | map filter | 0.2 % | 0.5 % | 0.6 % | seed 18: 7548 m along, t = 388.3 s, exiting |
| error at the exit | baseline | 5001 m | 5001 m | 5002 m | seed 22: ahead, 7552 m along, t = 388.3 s, exiting |
| error at the exit | map filter | 13 m | 26 m | 33 m | seed 18: ahead, 7550 m along, t = 388.4 s, exiting |
| honesty | map filter | 100 % | 95 % | 87 % | seed 18: furthest out: error 2.1× the band, 4383 m along, t = 225.2 s, entering |
| recovery after the exit | baseline | 12.7 s | 51.0 s | never | seed 14 |
| recovery after the exit | map filter | 6.2 s | 7.8 s | 8.2 s | seed 18: 7712 m along, t = 396.6 s, exiting |
| largest jump | baseline | 5010 m | 5069 m | 5069 m | seed 13: 7586 m along, t = 390.1 s, exiting |
| largest jump | map filter | 10 m | 16 m | 20 m | seed 18: 4859 m along, t = 249.9 s, inside |
| callout 400 m, late by | baseline | 10 m | 27 m | 31 m | seed 9: 4481 m along, t = 230.6 s, inside |
| callout 400 m, late by | map filter | -14 m | 3.4 m | 11 m | seed 18: 4461 m along, t = 229.3 s, inside |
| callout 100 m, late by | baseline | 14 m | 30 m | 38 m | seed 9: 4788 m along, t = 246.4 s, inside |
| callout 100 m, late by | map filter | -21 m | -1.7 m | 8.2 m | seed 18: 4758 m along, t = 244.8 s, inside |
| branch decided | baseline | 2735 m | 2740 m | 2740 m | seed 15: at the Fork right split, 7590 m along, t = 390.1 s, exiting |
| branch decided | map filter | 11 m | 12 m | 12 m | seed 6: at the Fork right split, 4862 m along, t = 250.1 s, inside |
| on the wrong branch | baseline | 140.1 s | 142.0 s | 142.2 s | seed 16: from its first moment there, 4818 m along, t = 247.9 s, inside |
| on the wrong branch | map filter | 0.0 s | 0.6 s | 0.8 s | seed 21: from its first moment there, 4836 m along, t = 248.5 s, inside |
| missed exit called | baseline | 2735 m | 2740 m | 2740 m | seed 15: 7590 m along, t = 390.1 s, exiting |
| missed exit called | map filter | 11 m | 12 m | 12 m | seed 6: 4862 m along, t = 250.1 s, inside |

## 5 · Long grade + loose phone

Re-learning how the phone sits after it slides 20° mid-tunnel.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 70 m | 137 m | 154 m | seed 8: ahead, 4849 m along, t = 251.3 s, exiting |
| largest error inside | map filter | 9.0 m | 20 m | 23 m | seed 18: ahead, 4456 m along, t = 229.1 s, inside |
| largest error inside, % of tunnel | baseline | 2.3 % | 4.4 % | 5.0 % | seed 8: 4849 m along, t = 251.3 s, exiting |
| largest error inside, % of tunnel | map filter | 0.3 % | 0.6 % | 0.7 % | seed 18: 4456 m along, t = 229.1 s, inside |
| error at the exit | baseline | 57 m | 121 m | 154 m | seed 8: ahead, 4851 m along, t = 251.4 s, exiting |
| error at the exit | map filter | 1.0 m | 2.5 m | 3.2 m | seed 12: behind, 4851 m along, t = 251.3 s, exiting |
| honesty | map filter | 100 % | 94 % | 93 % | seed 18: furthest out: error 1.6× the band, 1750 m along, t = 90.0 s, entering |
| recovery after the exit | baseline | 5.5 s | 42.7 s | 45.7 s | seed 5: 5738 m along, t = 297.1 s, after the tunnel |
| recovery after the exit | map filter | 0.0 s | 0.0 s | 0.0 s | seed 5: 4852 m along, t = 251.4 s, exiting |
| largest jump | baseline | 66 m | 123 m | 142 m | seed 10: 4887 m along, t = 253.1 s, exiting |
| largest jump | map filter | 5.8 m | 13 m | 19 m | seed 18: 4458 m along, t = 229.2 s, inside |
| callout 400 m, late by | baseline | 12 m | 72 m | 125 m | seed 22: 4175 m along, t = 214.7 s, inside |
| callout 400 m, late by | map filter | -13 m | -7.5 m | -5.4 m | seed 17: 4045 m along, t = 208.1 s, inside |
| callout 100 m, late by | baseline | 11 m | 79 m | 134 m | seed 22: 4484 m along, t = 230.8 s, inside |
| callout 100 m, late by | map filter | -19 m | -11 m | -8.0 m | seed 17: 4342 m along, t = 223.4 s, inside |
| branch decided | baseline | 6.2 m | 71 m | 128 m | seed 22: at the Exit split, 4578 m along, t = 236.2 s, inside |
| branch decided | map filter | 6.1 m | 8.3 m | 8.6 m | seed 11: at the Exit split, 4459 m along, t = 229.3 s, inside |
| on the wrong branch | baseline | 0.0 s | 0.0 s | 0.0 s | seed 5 |
| on the wrong branch | map filter | 0.0 s | 0.0 s | 0.0 s | seed 5 |
| false missed exit | baseline |  |  | 0 of 20 runs |  |
| false missed exit | map filter |  |  | 0 of 20 runs |  |

## 6 · Spiral + free flow

Six tight climbing turns: the most for curve and grade fixes to work with.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 879 m | 991 m | 1005 m | seed 8: ahead, 2895 m along, t = 271.2 s, exiting |
| largest error inside | map filter | 6.7 m | 23 m | 24 m | seed 19: ahead, 2899 m along, t = 272.1 s, exiting |
| largest error inside, % of tunnel | baseline | 53 % | 60 % | 61 % | seed 8: 2895 m along, t = 271.2 s, exiting |
| largest error inside, % of tunnel | map filter | 0.4 % | 1.4 % | 1.4 % | seed 19: 2899 m along, t = 272.1 s, exiting |
| error at the exit | baseline | 879 m | 991 m | 1000 m | seed 8: ahead, 2900 m along, t = 271.6 s, exiting |
| error at the exit | map filter | 6.3 m | 23 m | 24 m | seed 19: ahead, 2900 m along, t = 272.2 s, exiting |
| honesty | map filter | 100 % | 78 % | 66 % | seed 19: furthest out: error 2.8× the band, 2899 m along, t = 272.1 s, exiting |
| recovery after the exit | baseline | 6.7 s | 56.0 s | 65.7 s | seed 23: 3817 m along, t = 338.1 s, after the tunnel |
| recovery after the exit | map filter | 0.0 s | 7.3 s | 7.5 s | seed 7: 3005 m along, t = 280.1 s, exiting |
| largest jump | baseline | 901 m | 958 m | 987 m | seed 10: 2922 m along, t = 273.1 s, exiting |
| largest jump | map filter | 4.6 m | 16 m | 18 m | seed 19: 2703 m along, t = 257.2 s, exiting |

## 7 · Long grade + speed change + vehicle speed

Vehicle speed learned at one speed before the tunnel (70 km/h) and used at 100 km/h inside: with one speed, its scale and offset can't be told apart.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 938 m | 1024 m | 1102 m | seed 22: behind, 6248 m along, t = 273.5 s, exiting |
| largest error inside | map filter | 10 m | 16 m | 17 m | seed 25: ahead, 6250 m along, t = 273.6 s, exiting |
| largest error inside | map filter + vehicle speed | 4.3 m | 6.7 m | 7.4 m | seed 25: ahead, 5666 m along, t = 252.6 s, inside |
| largest error inside, % of tunnel | baseline | 21 % | 23 % | 24 % | seed 22: 6248 m along, t = 273.5 s, exiting |
| largest error inside, % of tunnel | map filter | 0.2 % | 0.3 % | 0.4 % | seed 25: 6250 m along, t = 273.6 s, exiting |
| largest error inside, % of tunnel | map filter + vehicle speed | 0.1 % | 0.1 % | 0.2 % | seed 25: 5666 m along, t = 252.6 s, inside |
| error at the exit | baseline | 939 m | 1024 m | 1103 m | seed 22: behind, 6251 m along, t = 273.6 s, exiting |
| error at the exit | map filter | 3.8 m | 12 m | 17 m | seed 25: ahead, 6252 m along, t = 273.7 s, exiting |
| error at the exit | map filter + vehicle speed | 2.2 m | 4.1 m | 4.6 m | seed 18: behind, 6251 m along, t = 273.5 s, exiting |
| honesty | map filter | 100 % | 100 % | 96 % | seed 18: furthest out: error 1.6× the band, 1750 m along, t = 90.0 s, entering |
| honesty | map filter + vehicle speed | 100 % | 65 % | 53 % | seed 18: furthest out: error 1.8× the band, 1834 m along, t = 94.4 s, entering |
| recovery after the exit | baseline | 3.7 s | 35.4 s | 35.5 s | seed 12: 7242 m along, t = 309.1 s, after the tunnel |
| recovery after the exit | map filter | 0.0 s | 5.9 s | 6.8 s | seed 25: 6441 m along, t = 280.5 s, exiting |
| recovery after the exit | map filter + vehicle speed | 0.0 s | 0.0 s | 0.0 s | seed 7: 6250 m along, t = 273.7 s, exiting |
| largest jump | baseline | 940 m | 1047 m | 1086 m | seed 22: 6293 m along, t = 275.1 s, exiting |
| largest jump | map filter | 5.1 m | 9.3 m | 10.0 m | seed 16: 3563 m along, t = 176.9 s, inside |
| largest jump | map filter + vehicle speed | 2.9 m | 4.9 m | 6.1 m | seed 14: 6429 m along, t = 280.1 s, exiting |
| branch decided | baseline | 576 m | 672 m | 761 m | seed 22: at the Exit split, 5211 m along, t = 236.2 s, inside |
| branch decided | map filter | 9.6 m | 11 m | 11 m | seed 15: at the Exit split, 4461 m along, t = 209.2 s, inside |
| branch decided | map filter + vehicle speed | 9.6 m | 11 m | 11 m | seed 15: at the Exit split, 4461 m along, t = 209.2 s, inside |
| on the wrong branch | baseline | 0.0 s | 0.0 s | 0.0 s | seed 7 |
| on the wrong branch | map filter | 0.0 s | 0.0 s | 0.0 s | seed 7 |
| on the wrong branch | map filter + vehicle speed | 0.0 s | 0.0 s | 0.0 s | seed 7 |

## 8 · Straight 5 km + stop-and-go + beacons

Scenario 2's tunnel and traffic (straight, flat, 5 km, stop-and-go), now with beacons on the walls every 35 m. With no curves or slopes to recognise, the phone alone can only add up its own motion, so its error grows the further it drives. Each beacon heard tells it where it is to within about 10 m, so the error stays at a few metres however long the tunnel is.

| Metric | Estimator | Median | 95th percentile | Worst | Worst run |
|---|---|---|---|---|---|
| largest error inside | baseline | 4248 m | 4329 m | 4331 m | seed 8: ahead, 3669 m along, t = 390.3 s, stopped |
| largest error inside | map filter | 15 m | 50 m | 78 m | seed 23: behind, 7000 m along, t = 1005.8 s, exiting |
| largest error inside | map filter + beacons | 8.2 m | 10 m | 13 m | seed 14: behind, 2911 m along, t = 248.3 s, inside |
| largest error inside, % of tunnel | baseline | 85 % | 87 % | 87 % | seed 8: 3669 m along, t = 390.3 s, stopped |
| largest error inside, % of tunnel | map filter | 0.3 % | 1.0 % | 1.6 % | seed 23: 7000 m along, t = 1005.8 s, exiting |
| largest error inside, % of tunnel | map filter + beacons | 0.2 % | 0.2 % | 0.3 % | seed 14: 2911 m along, t = 248.3 s, inside |
| error at the exit | baseline | 999 m | 1000 m | 1000 m | seed 20: ahead, 7000 m along, t = 1005.3 s, exiting |
| error at the exit | map filter | 15 m | 50 m | 78 m | seed 23: behind, 7001 m along, t = 1005.9 s, exiting |
| error at the exit | map filter + beacons | 2.1 m | 4.2 m | 5.4 m | seed 20: ahead, 7000 m along, t = 1005.3 s, exiting |
| honesty | map filter | 100 % | 100 % | 97 % | seed 18: furthest out: error 1.6× the band, 2000 m along, t = 90.0 s, entering |
| honesty | map filter + beacons | 99 % | 90 % | 89 % | seed 18: furthest out: error 1.6× the band, 2000 m along, t = 90.0 s, entering |
| recovery after the exit | baseline | 8.8 s | 35.9 s | 45.7 s | seed 18: 7967 m along, t = 1052.1 s, after the tunnel |
| recovery after the exit | map filter | 6.5 s | 8.1 s | 8.1 s | seed 14: 7130 m along, t = 1014.3 s, exiting |
| recovery after the exit | map filter + beacons | 0.0 s | 0.0 s | 0.0 s | seed 8: 7000 m along, t = 1006.0 s, exiting |
| largest jump | baseline | 1010 m | 1023 m | 1033 m | seed 19: 7011 m along, t = 1008.1 s, exiting |
| largest jump | map filter | 2.9 m | 5.7 m | 6.6 m | seed 17: 2224 m along, t = 115.2 s, stopped |
| largest jump | map filter + beacons | 3.9 m | 6.0 m | 7.1 m | seed 17: 2224 m along, t = 115.2 s, stopped |
