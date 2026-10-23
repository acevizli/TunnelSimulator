# Tunnel Positioning

Estimating where a car is along its road while GPS is unavailable inside a tunnel, and judging that estimate against the truth in simulation.

## Language

### The road

**Road map**:
The known geometry of the route: centreline, length, curvature, grade, tunnel extent, exits and speed limits. Assumed available and correct.
_Avoid_: HD map, network

**Tunnel**:
A stretch of the road where GPS is unusable, 500 m to 5 km long, single lane.

**Along-track distance**:
How far along the road the car is, in metres from a fixed origin. The single quantity the main approach estimates.
_Avoid_: Odometer, chainage, s-coordinate

**Exit**:
A point inside a tunnel where a branch leaves the road the car is on.
_Avoid_: Ramp, off-ramp, fork

**Portal**:
A tunnel's entrance or exit mouth, where GPS fades out or comes back.
_Avoid_: Mouth, tunnel end

**Route**:
The path the driver is meant to take, naming which exit (if any) to leave by. What the car actually drives may differ.
_Avoid_: Plan, navigation, itinerary

**Missed exit**:
The car drives past the exit its route says to take.
_Avoid_: Wrong turn

**Car**:
The single simulated vehicle carrying the phone. There is exactly one per scenario.
_Avoid_: Vehicle, ego

**Traffic**:
The surrounding vehicles, never simulated individually; they exist only as the reason the car speeds up, slows down or stops.
_Avoid_: Other cars, agents

### The drive

**Scenario**:
One complete simulated drive, made of a road, a speed profile, a mounting, GPS behaviour at the portals, add-ons, a route and a seed.
_Avoid_: Test case, config, run

**Speed profile**:
How the car's speed changes over the drive, shaped by traffic.
_Avoid_: Driving pattern, velocity curve

**Seed**:
The number that fixes every random choice in a scenario, so the same seed always gives the same drive.

### Estimation

**Ground truth**:
The car's real position and motion, known only to the simulator and never to the estimator.
_Avoid_: Reference, actual

**Estimate**:
The estimator's belief about the car's along-track distance and speed, always paired with its uncertainty.
_Avoid_: Prediction, guess

**Along-track error**:
The estimate's along-track distance minus the ground truth's; positive when the estimate is ahead of the car. When the estimate is on a different branch from the car, both past the split, it is the distance between them along the road (back to the split and out the other branch), counted as positive.
_Avoid_: Position error, drift

**Uncertainty band**:
The range around the estimate within which the estimator claims the car is, with about 95% confidence.
_Avoid_: Error bar, confidence, accuracy

**Run**:
One scenario played once with one seed, with every estimator fed the same sensor data side by side.
_Avoid_: Simulation, trial

**Baseline**:
The comparison estimator that extrapolates the last GPS speed through the tunnel.
_Avoid_: Naive, dumb

**Map filter**:
The main estimator: follows the car's along-track distance on the road map, corrected by stops, curves, grade changes and GPS where it can be trusted.
_Avoid_: Main estimator, EKF, the model

**Alignment**:
Working out how the phone sits in the car (which way is forward, which way is up) from the drive before the tunnel, without being told.
_Avoid_: Calibration, mount estimation

**Landmark**:
A place on the road map the phone's own sensors can recognise: where a curve starts or ends, or the grade changes. Passing one tells the estimator where it is.
_Avoid_: Feature, anchor

**Add-on**:
An optional information source from outside the phone (vehicle speed, tunnel beacons) that can be switched on to measure how much it improves the estimate. Each one switched on adds a copy of the map filter that also uses it, run next to the plain map filter on the same data.
_Avoid_: Aid, plugin, extra sensor

**Callout**:
The moment the app announces an upcoming exit to the driver, triggered from the estimate. It fires when the cautious edge reaches the announced distance before the exit.
_Avoid_: Instruction, alert, prompt

**Cautious edge**:
The far end of the uncertainty band in the direction of travel: the furthest along the car could reasonably already be. Callouts use it so they come early rather than late.
_Avoid_: Upper bound, worst case

**Beacon**:
A short-range radio transmitter fixed at a known along-track distance on a tunnel wall; passing it gives a position fix. Used only as an add-on.
_Avoid_: Tag, marker

**Vehicle speed**:
The speed the car itself reports to the phone, which carries its own systematic error. Used only as an add-on.
_Avoid_: Odometry, wheel speed, speedometer

**Phase**:
Which part of the drive the car is in: before the tunnel, entering, inside, stopped, exiting, between tunnels, after the tunnel. Every worst value is reported with the phase it happened in.
_Avoid_: Stage, section

**Honesty**:
How often the car is really inside the uncertainty band while in the tunnel. About 95% matches what the band claims; less means it is too narrow.
_Avoid_: Consistency, calibration

**Recovery**:
How long after the tunnel the estimate takes to get within 10 m of the car and stay there.
_Avoid_: Reacquisition, convergence

**Jump**:
A sudden move of the shown position from one moment to the next, beyond the car's own motion; what the driver sees as the car snapping to a new place.
_Avoid_: Glitch, teleport

**Measurement**:
Every test scenario run over many seeds, with every metric collected into one report. Nothing in it is graded.
_Avoid_: Benchmark, evaluation run, test suite

**Branch hypothesis**:
One candidate for which road the car is on after an exit, tracked until the evidence rules it out. The app calls a missed exit only once the route's branch hypothesis has been ruled out.
_Avoid_: Mode, track

**Mounting**:
How the phone sits in the car: fixed in a mount, or loose and free to shift.
_Avoid_: Placement, holder
