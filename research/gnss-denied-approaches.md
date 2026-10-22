# Vehicle positioning on a phone without GNSS: known approaches

Research for issue #3. The question: what approaches exist, in the literature and in shipped navigation apps, for estimating a car's position when GNSS drops out, using phone sensors and external info that can reasonably be assumed? For each one this note gives the expected accuracy over a 0.5–5 km outage, the assumptions it needs, and how it fails.

Scope reminder: single-lane tunnel, 500 m to 5 km. The app has to show position, call out an exit inside the tunnel on time (so **along-track error is what matters**), and recover cleanly at the exit.

## How to read the numbers

- **Sourced** numbers come from the cited paper or document and are marked with a reference.
- **Derived** numbers are back-of-envelope calculations from stated assumptions. They are marked "derived" and are meant to be checked in the simulator, not trusted as measurements.
- Reference speed for derived numbers is 80 km/h (22.2 m/s). At that speed, 0.5 km takes 22.5 s and 5 km takes 225 s.
- Timing intuition: at 80 km/h, 22 m of along-track error is 1 s of callout timing error. 100 m is about 4.5 s.

---

## 1. Raw IMU dead reckoning (accelerometer double integration)

**Idea.** Rotate phone accelerometer readings into the vehicle/navigation frame with the gyroscope, remove gravity, integrate twice.

**Accuracy (derived).** A constant residual accelerometer bias *b* along the direction of travel gives a position error of ½·b·T².

| Residual along-track bias | 0.5 km (22.5 s) | 5 km (225 s) |
|---|---|---|
| 0.01 m/s² | 2.5 m | 253 m |
| 0.05 m/s² | 13 m | 1.27 km |
| 0.17 m/s² (= 1° pitch error leaking gravity, g·sin 1°) | 43 m | 4.3 km |

The last row is the real problem. A 1° error in the estimated pitch of the phone relative to the road leaks about 0.17 m/s² of gravity into the forward axis. Tunnels are often on a grade, and the phone sits in a holder at an unknown angle, so pitch errors of that size are easy to get.

**Assumptions.** Known phone-to-vehicle mounting (boresight), well-calibrated bias, accurate attitude.

**Failure modes.** Quadratic error growth. Phone moved in its holder (the mounting has to be re-estimated). Bumps and vibration. Unknown tunnel grade.

**Verdict.** Unusable on its own beyond a few tens of seconds. It is still a useful *input* to a filter that has a speed constraint (sections 2–5).

## 2. INS + vehicle motion constraints (NHC, ZUPT) in an EKF/UKF

**Idea.** A car does not slide sideways or jump vertically. The **non-holonomic constraint (NHC)** feeds "lateral velocity ≈ 0, vertical velocity ≈ 0" into a Kalman filter as pseudo-measurements. A **zero-velocity update (ZUPT)** feeds "velocity = 0" when stillness is detected (low accelerometer/gyro variance), for example in stop-and-go traffic. An extended or unscented Kalman filter (EKF/UKF) carries attitude, velocity, position, sensor biases and the phone-to-vehicle misalignment.

**Accuracy (sourced).**
- Smartphone in a holder at an arbitrary angle, 3,555 m tunnel, 233 s GNSS outage, EKF with NHC plus estimation of misalignment, lever arm and GNSS time lag: **109.8 m horizontal error at the tunnel exit, 3.1% of distance travelled**. The authors made a manoeuvre before the tunnel so that the misalignment and lever arm would converge. [Li et al. 2022]
- With a learned (neural-network) noise model feeding an invariant EKF, IMU-only dead reckoning reached **1.10% average translational error** on the KITTI odometry benchmark. KITTI uses a high-grade vehicle-mounted IMU, not a phone, so treat this as an upper bound on what the approach can do. [Brossard et al., AI-IMU]
- Simulation of a commercial IMU through Norwegian road tunnels found that inertial-only solutions become unreliable in long tunnels because the errors build up over time. [Martin Rodriguez & Khademi 2023, abstract only]

**Accuracy over 0.5–5 km (derived from the 3.1% figure).** About 15 m at 0.5 km and about 155 m at 5 km. Note that NHC mostly constrains *lateral and vertical* error. In a single-lane tunnel the map already removes lateral error (section 3), so what is left is the along-track part, and NHC does nothing to stop that from drifting.

**Assumptions.** The phone is rigidly fixed in the car. Misalignment and biases were estimated while GNSS was still available before the tunnel (this needs some driving dynamics: turns, speed changes). Reasonable gyro bias stability.

**Failure modes.** Phone handled or moved during the tunnel. Not enough excitation before the tunnel for the misalignment to converge. Speed drift still grows with time. Without stops there is no ZUPT; with long stops the filter does well only if stillness is detected correctly. Engine vibration at idle can make stillness detection fail.

## 3. Map matching: a road-constrained 1D along-track estimate

**Idea.** In a single-lane tunnel the car is on a known polyline, so the 2D problem collapses to a 1D state: arc length *s* along the tunnel, plus speed *v* (and possibly a bias term). Map-matching literature covers projecting noisy positions onto the network [Quddus et al. 2007]. Particle filters that combine a road map with wheel speed or inertial data are a standard formulation for car positioning [Gustafsson et al. 2002].

What the map adds:
- **Lateral error removed** for free.
- **Hard bounds**: 0 ≤ s ≤ tunnel length. If the estimate reaches the exit before GNSS returns, clamp it and widen the uncertainty instead of letting it run past.
- **Grade/elevation profile**: lets the filter remove the gravity component that comes from road slope (the 0.17 m/s²-per-degree problem in section 1).
- **Curvature landmarks**: if the tunnel curves, the gyroscope yaw rate (and the integrated heading change) can be matched against the map's curvature profile. That gives an along-track fix at each bend. Magnetic-field fingerprints are the same idea using the magnetometer: a tunnel-specific database matched with subsequence dynamic time warping, tested in a real long tunnel [Shin et al. 2021; full text and numbers not retrieved].
- **Exit/branch positions**: the callout targets themselves.

**Accuracy.** Map matching alone gives no along-track information on a straight tunnel. It turns the problem into "how well do I know distance travelled". Accuracy is whatever the speed source provides (sections 4–5), reset at each curvature landmark. Derived: on a straight tunnel, the same as the speed source. On a curved one, error is bounded roughly by the spacing between distinctive features times the speed-error fraction.

**Assumptions.** An accurate tunnel geometry (polyline, length, exit positions, optionally grade). The car follows the mapped lane (true for single-lane). The car entered the tunnel the map says it entered.

**Failure modes.** Map length or exit positions wrong (directly becomes along-track error). Straight tunnels have no landmarks. Wrong tunnel or wrong direction. Curvature matching needs a rigid mount and a calibrated gyro bias.

## 4. Speed priors: pre-tunnel speed, map speed limit, traffic

**Idea.** Assume the car keeps roughly the speed it had at the tunnel entrance, or the posted limit, or the current traffic speed. Integrate along the 1D track. Use the accelerometer (with grade compensation from the map) only for *changes* in speed, and ZUPT for stops.

**Accuracy (derived).** Along-track error as a fraction of distance equals the relative error in average speed.

| Average speed error | 0.5 km | 5 km |
|---|---|---|
| 2% | 10 m | 100 m |
| 5% | 25 m | 250 m |
| 10% (e.g. assumed 80, true average 72 km/h) | 50 m | 500 m |
| Car stops for 60 s, estimate keeps moving at 80 km/h | +1.3 km | +1.3 km |

**Assumptions.** Free-flowing traffic, steady speed. Drivers in tunnels often hold steady speeds because overtaking is impossible in a single lane, which helps.

**Failure modes.** Congestion, incidents, stop-and-go. A pre-tunnel speed taken while the car was braking into the portal. Speed-limit changes inside the tunnel. Error is unbounded in time if the car stops and the stop is not detected. Accelerometer-sensed speed changes help, but they come with the bias/grade problem from section 1.

**This is effectively the baseline behaviour of a phone nav app with no extra sensors**: keep moving the puck along the route at the last known speed. I found no primary-source documentation of exactly what the major apps do here, so this is a hypothesis to check in the simulator, not a sourced fact.

## 5. Vehicle speed from the car (OBD-II, Android Auto/Automotive, CarPlay)

**Idea.** Replace the speed prior with measured wheel speed. Integrating wheel speed is odometry: error grows *linearly with distance* (scale factor), not with time, and it is immune to stops.

**What is actually available.**
- **OBD-II**: standard PID 0x0D reports vehicle speed as one byte in km/h (1 km/h resolution) [SAE J1979]. You need a dongle (usually Bluetooth ELM327-class) and a native app. Poll rates are a few Hz and add latency.
- **Android Auto / Android Automotive (Car App Library)**: `CarInfo.addSpeedListener` delivers a `Speed` object with `getRawSpeedMetersPerSecond()` and `getDisplaySpeedMetersPerSecond()`. The docs note the display value "is the value expected to be displayed on the speedometer. Some cars may display a slightly higher speed than the actual speed." `CarInfo.addMileageListener` gives the odometer. `CarSensors` offers car accelerometer, gyroscope, compass and car-hardware location, but on Android Automotive OS those sensor APIs "are currently not implemented" and return `STATUS_UNIMPLEMENTED`. [Android Car App Library: CarInfo, Speed, CarSensors]
- **CarPlay (iOS)**: there is no documented third-party vehicle-speed API. Core Location can, however, deliver locations produced by the vehicle: `CLLocationSourceInformation.isProducedByAccessory` is true when the location came "from an external accessory attached to the device, such as a Made for iPhone GPS dongle or CarPlay." If the car's own navigation unit does wheel-speed dead reckoning, the phone may receive those positions in the tunnel. Whether a given car does this is not documented. [Core Location docs]
- **Speedometer bias by regulation**: UN Regulation No. 39 requires that the speed shown "shall not be less than the true speed", with 0 ≤ (V1 − V2) ≤ 0.1·V2 + 4 km/h (V1 shown, V2 true). So *displayed* speed can be up to 10% + 4 km/h high, which is 15% at 80 km/h. Use raw speed, or calibrate against GNSS. [UN R39 Rev.2, §5.4]

**Accuracy (derived).**
- Uncalibrated display speed: up to +15% at 80 km/h (that is 75 m at 0.5 km, 750 m at 5 km). Do not use it uncalibrated.
- Raw wheel speed: the scale factor depends on tyre radius (wear, pressure, load), typically around 1–3%: 5–15 m at 0.5 km, 50–150 m at 5 km.
- **Scale factor calibrated against GNSS for a few km before the tunnel**: around 0.5% or better is plausible, giving ≤ 3 m at 0.5 km and ≤ 25 m at 5 km. The OBD 1 km/h quantisation is random and averages out over minutes.
- The accuracy holds through congestion and stops, which is the main advantage over section 4.

**Assumptions.** A connection to the car (dongle, projection, or built-in OS) and a native app with permission. A pre-tunnel calibration window.

**Failure modes.** No connection (most phone-only drives). Latency and dropouts on Bluetooth dongles. Wheel slip on wet surfaces (small). Display-vs-raw confusion. On iOS, no direct access at all.

## 6. Tunnel infrastructure: BLE beacons, cellular, Wi-Fi

**BLE beacons (shipped).** A crowd-sourced navigation app runs a tunnel beacon program. Battery-powered BLE beacons broadcast Eddystone UID and TLM packets. The app logs TX power, RSSI and a timestamp, ignores UIDs outside the program's namespace, and needs Bluetooth turned on (it prompts the driver at route start if a beacon tunnel is on the route). Other navigation apps may use the technology for free [beacon program help page]. Community documentation gives the spacing as **every 30–40 m**, with more than 14,500 beacons over more than 500 km of tunnels [program overview]. The Eddystone frame formats are public [Eddystone spec].
- **Accuracy**: no official figure. Derived: proximity to beacons 30–40 m apart gives errors bounded at roughly 10–20 m, *independent of tunnel length*. An independent field study of BLE positioning in road tunnels reports a **median error of 15–20 m** [Brož & Tichý 2024, abstract]. A multi-criteria comparison of tunnel positioning alternatives by the same group rated BLE best overall, mainly on cost and ease of deployment [Brož, Tichý, Pirník 2025].
- **Assumptions**: the tunnel is equipped, beacon IDs are mapped to positions, Bluetooth is on, and there is a native app (see web-app note below).
- **Failure modes**: dead batteries (not replaceable, only swappable), missing or moved beacons, RSSI fading from other vehicles. Unequipped tunnels get nothing.

**Higher-grade infrastructure (research).** RFID tags about 6 m apart plus in-vehicle sensors gave 1.44 m RMS position error (3.18 m with RFID alone) in a simulated tunnel set up outdoors [Hybrid RFID strategy]. GNSS/INS/odometer with lane-line and lateral-distance constraints reports less than 0.6 m longitudinal error at the midpoint of a 4.6 km tunnel, using dedicated hardware [Tunnel GNSS/INS/OD, MDPI 2024]. Roadside units (V2I) have been proposed for the same purpose [Hoang et al. 2017]. Camera plus distributed acoustic sensing (DAS) has been proposed as "track continuity" anchored at the portals [Saad Saoud et al. 2026, position paper, no numbers]. None of this is phone-only.

**Cellular / Wi-Fi.** Tunnels often have repeaters or leaky-feeder cables, so serving-cell IDs are usually the same along long stretches or show up as one site. Network location from a fused provider (which "intelligently combines different signals" such as GPS and Wi-Fi [Fused Location Provider]) is therefore coarse, hundreds of metres or worse, and may jump. Wi-Fi APs are rare in road tunnels. I found no primary source with tunnel cellular accuracy figures, so this paragraph is *low confidence*. Treat these fixes as outliers to reject, not as measurements.

## 7. What the platforms give you

- **Android Fused Location Provider**: high-level priority/accuracy requests that manage "the underlying location technology"; no numeric accuracy guarantees are documented [FLP docs].
- **iOS Core Location**: `CLActivityType.automotiveNavigation` for "positioning in an automobile following a road network", which may pause updates when the vehicle is not moving. `speedAccuracy` returns a negative value when speed is invalid. `isSimulatedBySoftware` and `isProducedByAccessory` describe where the location came from [Core Location docs].
- **Neither platform documents a public "tunnel mode"** or what the fused or system location does during a GNSS outage. An app should do its own along-track estimation and not rely on what the platform reports in the tunnel.

**Web-app note (relevant to this project's simulator).** A browser exposes `DeviceMotionEvent` (acceleration with and without gravity, rotation rate, sampling interval). Precision is limited to 0.1 m/s² and 0.1 deg/s. On some browsers the page has to call `DeviceMotionEvent.requestPermission()` after a user gesture, in a secure context [W3C DeviceOrientation CRD 2025]. That 0.1 m/s² quantisation is the same size as the biases in section 1, so a *web* implementation can do even less with raw inertial data than a native one. Passive BLE beacon scanning from a browser is only an experimental community draft and is not generally available, and OBD and car-API speed need native code. For a web simulator this is fine: simulate those sources. Just label them as "native-app only" in the evaluation.

## 8. Recovering at the exit

None of the sources address this directly. Practical points (derived):
- The size of the jump at the exit equals the along-track error accumulated, so section 4 alone can jump by hundreds of metres on a 5 km tunnel.
- The first GNSS fixes after the portal are often poor (reacquisition, multipath off the portal walls). Gate them on reported accuracy and consistency with the predicted state.
- Blend the estimate toward GNSS over a few seconds instead of snapping, unless the error is large enough that a snap is clearer to the driver.
- Use the exit as a free measurement: GNSS returning near the mapped portal confirms s ≈ tunnel length. Feed the error back to update the speed scale-factor estimate for the next tunnel.

---

## Comparison

Along-track error at the tunnel exit. "Free-flow" means steady speed; "congested" means stops or large speed changes.

| Approach | 0.5 km | 5 km | Congestion-robust? | Needs | Main failure mode | Source quality |
|---|---|---|---|---|---|---|
| 1. Raw IMU double integration | 3–40 m | 0.25–4 km | No | Phone | Gravity leakage, quadratic drift | Derived |
| 2. INS + NHC/ZUPT (EKF) | ~15 m | ~155 m | Partly (ZUPT) | Phone, rigid mount, pre-tunnel calibration | Along-track drift, phone moved | Sourced (3.1%, one test) |
| 3. Map matching (1D) | = speed source | = speed source; resets at curves | n/a | Tunnel geometry | Straight tunnel has no landmarks; map errors | Literature + derived |
| 4. Speed prior (pre-tunnel speed / limit) | 10–50 m | 100–500 m | **No** (unbounded on stops) | Phone + map | Traffic changes, undetected stops | Derived |
| 5a. Vehicle speed, uncalibrated display | up to 75 m | up to 750 m | Yes | Car link | Speedometer bias (UN R39) | Sourced bias + derived |
| 5b. Vehicle speed, GNSS-calibrated raw | ≤ 3–15 m | ≤ 25–150 m | **Yes** | Car link, native app | No link; latency | Derived |
| 6. BLE beacons every 30–40 m | ~10–20 m | ~10–20 m (bounded) | Yes | Equipped tunnel, Bluetooth, native app | Missing/dead beacons | Sourced (median 15–20 m) |
| 6b. RFID / lane-constraint / V2I | ~0.5–1.5 m | ~0.5–1.5 m | Yes | Dedicated infrastructure/hardware | Not phone-feasible | Sourced |
| 6c. Cellular / Wi-Fi in tunnel | 100s m | 100s m | — | Coverage | Repeaters, jumps | Low confidence |

## Which setups look most promising

**Phone only (no map data beyond the route line).** Approach 2 (INS + NHC + ZUPT) with a pre-tunnel speed prior. Expect a few percent of distance in free flow, about 150 m or more at 5 km, and much worse in congestion. Good enough for short tunnels. Not good enough to time an exit callout deep inside a 5 km tunnel.

**Phone + map (tunnel geometry, length, exits, grade).** This is the realistic default and the main candidate for the simulator: a **1D along-track filter** (state s, v, accelerometer bias) with
- speed prior from pre-tunnel GNSS speed, the accelerometer for speed changes (gravity removed using the map grade), and ZUPT for stops,
- curvature/heading landmarks where the tunnel bends,
- hard bounds on s and an honest uncertainty that grows with time, shown in the UI and used to time callouts conservatively (call early, never late).
Expected: about 2–5% of distance in free flow (10–25 m at 0.5 km, 100–250 m at 5 km), better on curved tunnels. Stop-and-go traffic is the main weakness and should be a key simulator scenario.

**Phone + vehicle speed.** The best along-track performance without infrastructure: a GNSS-calibrated raw wheel speed fused with the same 1D map filter. Expect well under 1% of distance (≤ 25 m at 5 km), and it holds up in congestion. Practical limits: needs a native app and a car link (Android Auto/Automotive have a documented speed API; iOS/CarPlay do not, though CarPlay can pass vehicle-produced locations). If BLE beacons exist in the tunnel, they put a hard bound on any of the above and are worth fusing as absolute fixes.

**Suggested simulator scenarios that follow from this:** steady speed, braking at the portal, stop-and-go congestion, straight vs curved tunnel, wrong map length, phone moved mid-tunnel, speedometer display bias, beacons present/absent, and noisy first GNSS fixes at the exit.

---

## Sources

- [Li et al. 2022] L. Li, Q. Huang, K. Xu, G. Guo, R. Chen, "Vehicle positioning in underground space using a smart phone," ISPRS Archives XLVI-3/W1-2022, UPINLBS 2022. https://isprs-archives.copernicus.org/articles/XLVI-3-W1-2022/81/2022/ (peer-reviewed; tunnel test §6.1).
- [Brossard et al., AI-IMU] M. Brossard, A. Barrau, S. Bonnabel, "AI-IMU Dead-Reckoning," arXiv:1904.06064. https://arxiv.org/abs/1904.06064
- [Martin Rodriguez & Khademi 2023] "Evaluation Study of Inertial Positioning in Road Tunnels for Cooperative ITS Applications," IEEE ITSC 2023. https://uis.brage.unit.no/uis-xmlui/handle/11250/3117550 (abstract only).
- [Quddus et al. 2007] M. Quddus, W. Ochieng, R. Noland, "Current map-matching algorithms for transport applications: State-of-the art and future research directions," Transportation Research Part C 15(5), 2007. https://doi.org/10.1016/j.trc.2007.05.002
- [Gustafsson et al. 2002] F. Gustafsson et al., "Particle filters for positioning, navigation, and tracking," IEEE Trans. Signal Processing 50(2), 2002. https://doi.org/10.1109/78.978396
- [Shin et al. 2021] "Magnetic Field-Based Vehicle Positioning System in Long Tunnel Environment," Applied Sciences 11(24):11641, 2021. https://doi.org/10.3390/app112411641 (full text blocked; numbers not retrieved).
- [Android Car App Library] CarInfo: https://developer.android.com/reference/androidx/car/app/hardware/info/CarInfo · Speed: https://developer.android.com/reference/androidx/car/app/hardware/info/Speed · CarSensors: https://developer.android.com/reference/androidx/car/app/hardware/info/CarSensors
- [Core Location docs] CLLocationSourceInformation: https://developer.apple.com/documentation/corelocation/cllocationsourceinformation · isProducedByAccessory: https://developer.apple.com/documentation/corelocation/cllocationsourceinformation/isproducedbyaccessory · CLActivityType.automotiveNavigation: https://developer.apple.com/documentation/corelocation/clactivitytype/automotivenavigation · speedAccuracy: https://developer.apple.com/documentation/corelocation/cllocation/speedaccuracy
- [FLP docs] Fused Location Provider API: https://developers.google.com/location-context/fused-location-provider · https://developer.android.com/develop/sensors-and-location/location/retrieve-current
- [UN R39 Rev.2, §5.4] UN Regulation No. 39 (speedometer and odometer), E/ECE/324/Rev.1/Add.38/Rev.2, 2018. Index: https://unece.org/transport/vehicle-regulations-wp29/standards/addenda-1958-agreement-regulations-21-40
- [SAE J1979] SAE J1979 / ISO 15031-5, E/E diagnostic test modes (OBD-II), PID 0x0D vehicle speed. https://www.sae.org/standards/content/j1979_201702/
- [Beacon program help page] "How Beacons work" (navigation-app partner help): https://support.google.com/waze/partners/answer/9416071
- [Program overview] Beacons program overview (community guide): https://www.waze.com/discuss/t/waze-beacons-program-overview-all-you-need-to-know/411647 (community-authored; spacing and totals not independently verified).
- [Eddystone spec] Eddystone BLE frame formats: https://github.com/google/eddystone
- [Brož & Tichý 2024] J. Brož, T. Tichý, "Road Tunnel Positioning: Enabling Location-Based Services in GNSS-Denied Environments," IEEE Access 12, 2024. https://doi.org/10.1109/ACCESS.2024.3479278 (abstract; median 15–20 m).
- [Brož, Tichý, Pirník 2025] multi-criteria evaluation of tunnel positioning alternatives, in *Road Traffic Research, Analysis, and Modeling* (Springer), 2025 (search-snippet only).
- [Hybrid RFID strategy] "A Hybrid Positioning Strategy for Vehicles in a Tunnel Based on RFID and In-Vehicle Sensors," Sensors 14(12):23095–23118, 2014. https://pmc.ncbi.nlm.nih.gov/articles/PMC4299054
- [Tunnel GNSS/INS/OD, MDPI 2024] "Study of Tunnel Vehicle GNSS/INS/OD Combination Position Based on Lateral Distance Measurement and Lane Line Constraint," Applied Sciences 14(10):4309, 2024. https://www.mdpi.com/2076-3417/14/10/4309
- [Hoang et al. 2017] "Robust data fusion for cooperative vehicular localization in tunnels," IEEE IV 2017. https://www.eurecom.fr/en/node/4902490
- [Saad Saoud et al. 2026] "Beyond Dead Reckoning: A Point of View on Camera–DAS–GNSS Continuity in Road Tunnels," arXiv:2609.14748. https://arxiv.org/abs/2609.14748
- [W3C DeviceOrientation CRD 2025] DeviceOrientation Event Specification, W3C Candidate Recommendation Draft, 12 Feb 2025. https://www.w3.org/TR/orientation-event/
- Web Bluetooth Scanning (community draft, not generally shipped): https://webbluetoothcg.github.io/web-bluetooth/scanning.html

### Gaps / open items
- No primary documentation of how major nav apps behave in tunnels *without* beacons (assumed: extrapolate along route at last speed). Verify by observation if needed.
- Full-text numbers for the magnetic-fingerprint study and the tunnel inertial simulation study were not retrieved (sites blocked).
- Tyre scale-factor (1–3%) and post-calibration (≤0.5%) figures are engineering estimates, not sourced measurements.
