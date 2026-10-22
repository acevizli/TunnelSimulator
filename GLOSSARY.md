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

**Baseline**:
The comparison estimator that extrapolates the last GPS speed through the tunnel.
_Avoid_: Naive, dumb

**Add-on**:
An optional information source from outside the phone (vehicle speed, tunnel beacons) that can be switched on to measure how much it improves the estimate.
_Avoid_: Aid, plugin, extra sensor

**Callout**:
The moment the app announces an upcoming exit to the driver, triggered from the estimate.
_Avoid_: Instruction, alert, prompt

**Beacon**:
A short-range radio transmitter fixed at a known along-track distance on a tunnel wall; passing it gives a position fix. Used only as an add-on.
_Avoid_: Tag, marker

**Vehicle speed**:
The speed the car itself reports to the phone, which carries its own systematic error. Used only as an add-on.
_Avoid_: Odometry, wheel speed, speedometer

**Branch hypothesis**:
One candidate for which road the car is on after an exit, tracked until the evidence rules it out.
_Avoid_: Mode, track

**Mounting**:
How the phone sits in the car: fixed in a mount, or loose and free to shift.
_Avoid_: Placement, holder
