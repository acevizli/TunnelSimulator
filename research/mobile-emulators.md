# Android emulator and iOS Simulator: what they offer for sensor emulation

Research for issue #6. Question: what the Android emulator and the iOS Simulator can emulate for location and motion sensors, how data gets in, whether either one models physics or only replays what it is given, and what that means for our sensor-source abstraction.

Sources are primary: Android developer docs, the emulator's own source in AOSP (`platform/external/qemu`, branch `emu-master-dev`), Apple developer docs, `xcrun simctl` help (Xcode 16.4), and the GnssLogger format spec in `google/gps-measurement-tools`. Links are at the end. Claims I could not confirm from a primary source are marked **unverified**.

## TL;DR

- **Android emulator.** It accepts injected GNSS fixes (`geo fix`, NMEA, GPX/KML route playback, gRPC `setGps`), raw GNSS measurements (`geo gnss`), and per-sensor values (`sensor set`, gRPC `setSensor`) for accelerometer, gyroscope, magnetometer, pressure and more. It has a small **physical model**: a rigid device pose that is eased toward a target, with gravity and a fixed magnetic field. Accelerometer, gyroscope and magnetometer readings are derived from that pose. The model has **no noise, no bias and no vehicle dynamics**, and GNSS is not coupled to motion. Everything car-related is **pure replay**.
- **iOS Simulator.** It does **location only**: a fixed point, built-in routes, GPX files, or `simctl location start` waypoint interpolation at a constant speed. Apple documents accelerometer, gyroscope and barometer as **not simulated**, and `simctl` has no motion command. For IMU work on iOS you need a real device.
- **Recommendation.** For the simulator itself, neither emulator adds anything over our own sensor model. Our model has to produce car kinematics, sensor noise, bias, mounting orientation and GNSS degradation, and the emulators provide none of these. An Android emulator becomes useful later for one job: end-to-end testing of a real Android app's sensor and location pipeline, fed by our generated stream through gRPC. Treat it as a **sink** for our stream, not a source of truth.
- **Interface.** Use a pull-based source of time-ordered, typed samples. Express them in SI units in the Android device frame on one monotonic clock, keep ground truth on a separate channel, and attach a capabilities descriptor. Details are in the [proposed interface](#proposed-sensor-source-interface) section.

## Android emulator

### Location and GNSS injection

| Path | What it carries | Notes |
|---|---|---|
| Console `geo fix <lon> <lat> [alt [sats [velocity]]]` | One fix | Longitude comes first. Altitude is in m, satellite count is 1–12, velocity is in **knots**. [console docs], [console.cpp] |
| Console `geo nmea <sentence>` | NMEA 0183 | Only `$GPGGA` and `$GPRMC` are accepted. [console.cpp] (The public docs page says "GPRCM", which is a typo.) |
| Console `geo gnss <sentence>` | **Raw GNSS measurements** | 8 clock fields, a count, then 9 fields per satellite: Svid, ConstellationType, State, ReceivedSvTimeNanos, ReceivedSvTimeUncertaintyNanos, Cn0DbHz, PseudorangeRate, its uncertainty, CarrierFrequencyHz. This field set is a subset of what Android's `GnssMeasurement` exposes. It is only in the source help text and not on the public docs page. [console.cpp] |
| Extended controls > Location | Single point, saved routes, GPX/KML import | Playback runs at 1x, 2x, 3x… of the recorded timing, optionally on repeat. [extended controls] |
| gRPC `setGps(GpsState)` / `getGps` | lat/lon (deg), altitude (m above WGS84 ellipsoid), speed (m/s), bearing (deg, direction of travel), satellites | Setting `passiveUpdate=false` stops the Location UI from overwriting the value. The proto notes that Android typically samples GPS at 1 Hz. There is no `streamGps`. [emulator_controller.proto] |
| On-device `LocationManager.addTestProvider` / `setTestProviderLocation` | Mock `Location` objects | Works on emulators and on real phones. It needs the mock-location app-op, and throws `SecurityException` without it. [LocationManager] |

None of these paths has a GNSS signal model. There is nothing for tunnel attenuation, multipath or fix accuracy degradation. A "tunnel" on the emulator means we stop sending fixes, or send fixes with degraded fields that we computed ourselves.

### Motion and environment sensors

The emulator's sensor list in `hw-sensors.h` is: `acceleration`, `gyroscope`, `magnetic-field`, `orientation`, `temperature`, `proximity`, `light`, `pressure`, `humidity`, `magnetic-field-uncalibrated`, `gyroscope-uncalibrated`, `acceleration-uncalibrated`, `hinge-angle0..2`, `heart-rate`, `rgbc-light`, `wrist-tilt`. [hw-sensors.h]

Ways to inject values:

- Console `sensor status | get <name> | set <name> a[:b[:c...]]`. [console.cpp], [console docs]
- gRPC `setSensor` / `getSensor` / `streamSensor` with `SensorValue`. The proto states the units: acceleration in m/s² including gravity, gyroscope in rad/s, magnetic field in µT, pressure in hPa. [emulator_controller.proto]
- gRPC `setPhysicalModel` / `streamPhysicalModel` with `PhysicalModelValue`. Its parameters are POSITION, ROTATION (degrees), VELOCITY, AMBIENT_MOTION, MAGNETIC_FIELD, PRESSURE, and others. The proto comment calls it "likely the one you are looking for when you wish to modify the device state". [emulator_controller.proto]
- Extended controls > Virtual sensors > Device Pose (yaw, pitch and roll sliders, plus X/Y move) and Additional sensors (manual values for pressure, magnetic field and the rest). [extended controls]
- `automation record|play <file>` records and replays device-state change macros. [console.cpp]

The sensor HAL delivers reports on a timer. The default period is 200 ms, the guest can request a period with `set-delay:<ms>`, and the period is clamped to at least 10 ms. That puts the **ceiling at about 100 Hz**. [hw-sensors.cpp]

### Physics vs. replay

What the physical model does (from the source):

- **Pose easing.** When a new position or rotation target is set, the model moves toward it along a smooth polynomial profile. It accelerates for the first half and decelerates for the second, the profile is continuous through the third derivative, and a change takes 0.05–0.5 s. Velocity and acceleration are zero when the move ends. [InertialModel.h]
- **Derived IMU readings.** In [PhysicalModel.cpp]:
  - accelerometer = `conj(rotation) * (acceleration − gravity)`
  - gyroscope = `conj(rotation) * rotationalVelocity`
  - magnetometer = `conj(rotation) * magneticField`
  
  So the readings are geometrically consistent with the pose.
- **Ambient constants.** Gravity defaults to (0, −9.81, 0) and the magnetic field to (0, 5.9, −48.4) µT in the model's world frame. Pressure, temperature and the other environment values are plain settable scalars with no altitude model behind them. [AmbientEnvironment.h]
- **No noise, no bias.** The model has no noise or bias terms. The uncalibrated getters return the same values as the calibrated ones, and the source comments that bias "will be added … on the guest side". **Unverified** whether the stock guest HAL adds any bias. [PhysicalModel.cpp]
- **Overrides win.** A value set with `setSensor` overrides the model for that sensor until the next physical target change, which clears every override. [PhysicalModel.cpp]
- **GNSS is decoupled.** Moving the physical model does not change the location, and playing a route does not produce IMU readings. Route playback steps through points at their recorded timing times the speed factor. [extended controls], [PhysicalModel.cpp]
- **Ground-truth recording.** `physics record-gt <file>` writes `timestamp_ns tx ty tz rx ry rz` (rotation in degrees), one line per pose query. It records pose only and has no matching replay command. [console.cpp], [PhysicalModel.cpp]

In short, the physics is a hand-held phone model: a rigid body being turned by a person, with gravity and a constant magnetic field. It is not a vehicle model. A car's longitudinal acceleration, turns, road vibration and mounting angle would all have to be generated outside and pushed in. The 0.05–0.5 s easing on targets would also distort a high-rate kinematic stream pushed through `setPhysicalModel`. A bridge should therefore use `setSensor` overrides for the IMU and `setGps` for location.

## iOS Simulator

- **Location.** The Debug/Features menu offers None, Custom Location, Apple, City Run, City Bicycle Ride and Freeway Drive. The last three are predefined routes. [Simulator guide (archived)] Xcode can also replay GPX files through the scheme's default location or the debug bar. **Unverified** against current Apple docs, because the page body did not load.
- **`xcrun simctl location <device>`** supports `set lat,lon`, `list` and `run <scenario>`, plus `start [--speed=m/s] [--distance=m | --interval=s] <wp1> <wp2> …`. With `start`, the Simulator interpolates along straight segments at a constant speed (20 m/s by default) and issues an update every second unless told otherwise. Waypoints can be read from stdin, so a live process could stream them. There are no fields for accuracy, altitude, bearing or speed noise. [simctl help]
- **Motion and environment.** Apple's Simulator guide lists "Motion support (accelerometer and gyroscope)", the barometer, the proximity sensor and the ambient light sensor as unsupported. [Simulator guide (archived)] `simctl` (Xcode 16.4) has no motion, sensor or barometer subcommand. Its device-state subcommands are `location`, `push` and `status_bar`. [simctl help] The guide is archived (iOS 8.2 era), but I found nothing newer that adds motion simulation. **Unverified** for the latest Xcode.
- **Detecting simulated locations.** iOS 15+ provides `CLLocationSourceInformation.isSimulatedBySoftware`. [CLLocationSourceInformation] Android's equivalent is `Location.isMock()`.

**Verdict:** the iOS Simulator is a location replayer with linear interpolation. It does no physics and offers no way to inject IMU data.

## Driving an emulator from our sensor stream

On Android this is possible. The bridge would be a small host process (Python or Node gRPC client, generated from `emulator_controller.proto`), started with the emulator's gRPC port. The console command `avd grpc` reports the port. [console.cpp]

1. For each IMU sample, call `setSensor(ACCELERATION | GYROSCOPE | MAGNETIC_FIELD, xyz)`. Our values must already be in the Android device frame and units. They do not need to be in the emulator's world frame, because overrides are reported as given.
2. For each barometer sample, call `setSensor(PRESSURE, hPa)`.
3. For each GNSS fix, call `setGps` with `passiveUpdate=false`. During the tunnel, send nothing. Optionally use `geo gnss` to show satellites dropping out.
4. Pace the calls in wall-clock time. The emulator has no notion of our simulation clock, so there is no faster-than-real-time and no seek. Readings reach the app at the HAL rate (100 Hz at most), and the app sees the **last value set** at each tick. Our sample timestamps are not carried through, so expect jitter and resampling.

On iOS, only step 3 is possible (`simctl location start` waypoints from stdin), and only for location.

The other direction, using the emulator as a **source**, gives us back only what we fed in (or the pose model). It has no value as a data source.

## Recording real-device traces

| Format | Contents | Fit for us |
|---|---|---|
| **GnssLogger CSV** (Google, `gps-measurement-tools`) | One file with row prefixes `Fix`, `Raw` (GnssMeasurement), `Status` (per-satellite C/N0, used-in-fix), `UncalAccel`/`Accel`, `UncalGyro`/`Gyro`, `UncalMag`/`Mag`, `OrientationDeg`, `NMEA`, `Nav`, `Agc`. Each sensor row has `utcTimeMillis` and `elapsedRealtimeNanos`. Units are in the column names (`Mps2`, `RadPerSec`, `MicroT`). | **Best starting point** for an Android trace importer. All sensors share one clock, and satellite status shows the tunnel outage directly. It has **no barometer** row, so pressure needs another logger or our own recorder. [LOGGING_FORMAT.md] |
| **RINEX** (IGS) | GNSS observation and navigation data only | Only useful for raw-GNSS positioning research. No IMU data. Out of scope for v1. [RINEX] |
| **GPX / KML** | Track points (lat, lon, ele, time) | Ground-truth or reference routes, and emulator/Simulator route playback. No IMU data. [GPX 1.1] |
| Generic sensor-logger CSV apps | Varies | Normalize these through an adapter. Do not let their schemas leak into the core. |

For iOS traces, the app has to record through Core Motion. Accelerometer data is in **g** (1 g = 9.81 m/s²), pressure from `CMAltitudeData` is in **kPa**, and timestamps are seconds since boot. [CMAcceleration], [CMAltitudeData.pressure], [CMLogItem.timestamp] Core Motion's axis and sign convention differs from Android's: a phone lying flat reads about −1 g on z. The importer must scale and negate. **Unverified** here (taken from Apple's older Event Handling Guide, not re-read in this pass).

## Proposed sensor-source interface

Design rules, based on what all four back ends (simulated, recorded trace, emulator bridge, live device) can honour:

- **One canonical frame and unit system: Android's.** The device frame has x right, y up and z out of the screen, in the natural orientation, and it does not rotate with the UI. Accelerometer readings are in m/s² *including gravity* (about +9.81 on z when flat and face up). Gyroscope is in rad/s, magnetometer in µT, pressure in hPa, positions in WGS84 degrees, altitude in m above the ellipsoid, speed in m/s, and bearing in degrees clockwise from true north. Adapters convert (iOS g→m/s², kPa→hPa, axis signs). [sensors overview], [SensorEvent], [emulator_controller.proto]
- **One monotonic clock per session.** Use `t` in seconds (float64) since the session starts, the same idea as `elapsedRealtimeNanos`. GNSS fixes may also carry `utcMs`. Trace adapters rebase `elapsedRealtimeNanos`; live adapters use the sensor event timestamp, not arrival time.
- **Pull-based and time-ordered.** Deterministic sources (simulated and trace) must support faster-than-real-time playback, pause and seek. Live sources and the emulator source wrap a push stream in a buffer. The estimator never sees wall-clock time.
- **No GNSS fix during an outage means no fix samples.** Do not send "null" fixes. Satellite status is optional, so a source that has it can show the fade.
- **Ground truth is a separate channel.** The estimator must not be able to read it. Only simulated sources and some traces (with a reference track) provide it.
- **A capabilities descriptor** says which sensor kinds exist, the nominal rates, whether the stream is calibrated or uncalibrated, and whether seek is supported.

```ts
type Vec3 = readonly [x: number, y: number, z: number];

type Sample =
  | { kind: 'accel'; t: number; v: Vec3; bias?: Vec3 }   // m/s², incl. gravity, device frame
  | { kind: 'gyro';  t: number; v: Vec3; bias?: Vec3 }   // rad/s, device frame
  | { kind: 'mag';   t: number; v: Vec3; bias?: Vec3 }   // µT, device frame
  | { kind: 'baro';  t: number; hPa: number }
  | { kind: 'gnssFix'; t: number; utcMs?: number;
      latDeg: number; lonDeg: number; altM?: number;     // WGS84 ellipsoid
      speedMps?: number; bearingDeg?: number;
      hAccM?: number; vAccM?: number; speedAccMps?: number; bearingAccDeg?: number;
      satsUsed?: number }
  | { kind: 'gnssStatus'; t: number;
      sats: ReadonlyArray<{ constellation: string; svid: number; cn0DbHz: number; usedInFix: boolean }> };

type SampleKind = Sample['kind'];

interface SourceCapabilities {
  kinds: ReadonlySet<SampleKind>;
  nominalRateHz: Partial<Record<SampleKind, number>>;
  calibrated: boolean;            // false => bias fields may be present
  seekable: boolean;              // simulated / trace: true; emulator / live: false
  durationS?: number;             // known for simulated / trace
}

interface SensorSource {
  readonly capabilities: SourceCapabilities;
  /** All samples with t in (previous cursor, untilT], ordered by t. Advances the cursor. */
  read(untilT: number): ReadonlyArray<Sample>;
  seek?(t: number): void;         // only when capabilities.seekable
  close(): void;
}

/** Separate channel, never passed to the estimator. */
interface GroundTruthSource {
  poseAt(t: number): { latDeg: number; lonDeg: number; altM: number;
                       speedMps: number; headingDeg: number; alongTrackM?: number } | undefined;
}

/** Optional: forward a stream to an external consumer (Android emulator via gRPC, a phone via test provider). */
interface SensorSink {
  write(samples: ReadonlyArray<Sample>): void;  // paced by the sink in wall-clock time
}
```

How each back end satisfies it:

| Back end | `SensorSource` | Ground truth | Notes |
|---|---|---|---|
| Simulated (v1) | Generates samples from car kinematics plus a noise/bias model. Seekable. | Yes, exact | The reference implementation. |
| Recorded trace | GnssLogger CSV adapter (others later). Rebases the clock. Seekable. | Only if a reference track exists | Adds `baro` only if the trace has it. |
| Android emulator | Source: `streamSensor` plus `getGps` polling. Not seekable, and it echoes what was injected. **Sink**: `setSensor` / `setGps` over gRPC. | No (the `record-gt` file holds the phone pose, not the car's) | Mainly a sink, for testing an Android client. |
| Live device | Phone app streams samples (for example over WebSocket) with event timestamps. Not seekable. | No | iOS adapter converts units and axes. Android needs no conversion. |

## Sources

- [console docs] Android emulator console commands: https://developer.android.com/studio/run/emulator-console
- [extended controls] Emulator extended controls (Location, Virtual sensors): https://developer.android.com/studio/run/emulator-extended-controls
- [console.cpp] Emulator console source (geo, sensor, automation, physics, avd grpc): https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-emu/android/console.cpp
- [hw-sensors.h] Emulator sensor list: https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-emu/android/hw-sensors.h
- [hw-sensors.cpp] Sensor HAL timing (200 ms default, 10 ms minimum): https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-emu/android/hw-sensors.cpp
- [emulator_controller.proto] Emulator gRPC API: https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-grpc/services/emulator-controller/proto/emulator_controller.proto
- [InertialModel.h] Pose easing: https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-emu/android/physics/InertialModel.h
- [PhysicalModel.cpp] Derived sensor values, overrides, ground-truth recording: https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-emu/android/physics/PhysicalModel.cpp
- [AmbientEnvironment.h] Default gravity and magnetic field: https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-master-dev/android/android-emu/android/physics/AmbientEnvironment.h
- [sensors overview] Android sensor coordinate system and units: https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview
- [SensorEvent] `timestamp` uses the `elapsedRealtimeNanos()` time base: https://developer.android.com/reference/android/hardware/SensorEvent
- [LocationManager] Test providers and the mock-location app-op: https://developer.android.com/reference/android/location/LocationManager
- [LOGGING_FORMAT.md] GnssLogger CSV format: https://github.com/google/gps-measurement-tools/blob/master/LOGGING_FORMAT.md
- [RINEX] IGS data formats: https://igs.org/formats-and-standards/
- [GPX 1.1] https://www.topografix.com/GPX/1/1/
- [Simulator guide (archived)] Testing and Debugging in Simulator: https://developer.apple.com/library/archive/documentation/IDEs/Conceptual/iOS_Simulator_Guide/TestingontheiOSSimulator/TestingontheiOSSimulator.html
- [simctl help] `xcrun simctl help location` and `xcrun simctl help`, Xcode 16.4 (run locally)
- [CLLocationSourceInformation] https://developer.apple.com/documentation/corelocation/cllocationsourceinformation
- [CMAcceleration] https://developer.apple.com/documentation/coremotion/cmacceleration
- [CMAltitudeData.pressure] https://developer.apple.com/documentation/coremotion/cmaltitudedata/pressure
- [CMLogItem.timestamp] https://developer.apple.com/documentation/coremotion/cmlogitem/timestamp
