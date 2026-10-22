# Estimate along-track distance with a map-constrained 1D EKF, not a 3D inertial navigator

Inside a tunnel the car can only be somewhere on the known road, and the error that matters for exit callouts is how far along the road it is. So the main estimator tracks a single along-track distance (plus speed and accelerometer bias) in an extended Kalman filter, using the road map's curvature and grade as landmarks, stop detection for zero-speed updates, and one filter per branch hypothesis at exits. A full 3D strapdown inertial navigator on phone-grade sensors drifts by hundreds of metres to kilometres over a 5 km tunnel (bias and tilt leaking gravity into the forward axis), and its sideways accuracy buys nothing in a single-lane tunnel.

## Considered Options

- **3D inertial navigation without the map**: rejected; the map is assumed available, and phone IMU drift dominates.
- **Particle filter**: handles branches naturally, but random, slower and harder to explain line by line; a bank of EKFs, one per branch, covers the same need.
- **Speed extrapolation only**: kept as the baseline to compare against, not as the approach.

## Consequences

- The approach depends on an accurate road map; a wrong map is a failure mode, not a handled case.
- A straight, flat tunnel offers no landmarks, so accuracy there rests on speed alone. This is reported as a known weak spot.
