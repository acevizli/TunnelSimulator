# Smartphone sensor characteristics for in-car dead reckoning

Research for issue #2. Question: what do consumer smartphone sensors actually deliver for in-vehicle dead reckoning, and what parameter ranges should the simulator use?

Scope: a car in a single-lane tunnel 500 m to 5 km long, with GNSS lost. At 50 to 100 km/h that is roughly 18 s to 6 min without GNSS (5 km at 80 km/h is 225 s). Along-track error matters most, because it decides when the in-tunnel exit callout fires.

Each number below names its source. Values marked **derived** are arithmetic on cited numbers, not figures taken from a source. Values marked **unverified** have no primary source yet.

## Summary

- Phone IMU **white noise is not the problem**. Datasheet gyro noise is 0.0028 to 0.010 °/s/√Hz and accelerometer noise is 70 to 160 µg/√Hz. Over a few minutes, the errors that dominate are **residual bias** (left over after the last GNSS-aided calibration), **gravity leaking through tilt or mount errors**, and **scale factor**.
- **Turn-on bias is large and varies a lot between phones.** Across 116 phones, the median gyro bias was about 0.2 °/s and the 95th percentile about 2 °/s. The median accelerometer bias was 10 to 19 mg and the 95th percentile 44 to 71 mg. That is why the bias must be estimated while GNSS is still available, before the tunnel.
- **Bias instability from Allan variance** on five recent phones: gyro 2 to 28 °/h, accelerometer 22 to 136 µg. This is the floor a filter can reach after calibration.
- **Double-integrating the accelerometer is not viable for along-track position.** A residual 1 mg bias gives about 250 m of error after 225 s (derived). A real 3.5 km tunnel test with an arbitrarily mounted phone and a vehicle motion constraint ended **110 m off (3.1 % of distance)**. Use that figure as the realistic baseline to beat.
- **Magnetometer:** the platform specs allow large offsets (hard iron up to 700 µT against an Earth field of 20 to 60 µT), and in-vehicle disturbance is a known issue. I found **no primary in-tunnel measurement**. Treat it as unreliable inside the tunnel.
- **Barometer:** the best relative measure is about ±3 Pa (±0.25 m), and noise ranges from 0.02 to 3.7 Pa depending on filtering. It is useful for grade or altitude change, and gives along-track information only if the tunnel has a known vertical profile.
- **GNSS through fused location APIs:** 1 Hz updates. Accuracy is reported as a 68 % radius on Android; iOS reports a radius without stating a confidence level. Open-sky accuracy is within 20 m at 95 %, and urban accuracy is 7 to 13 m. A re-fix is required within 5 s after an outage. There is about 1.3 s of GNSS latency relative to the IMU.
- **Mount misalignment is arbitrary and must be estimated.** Pitch misalignment directly feeds g·sin(δθ) into forward acceleration: 1° is about 17 mg (derived), which is far above the sensor bias.

## 1. Accelerometer

| Parameter | Range for simulator | Source |
|---|---|---|
| Noise density (datasheet) | 70 µg/√Hz (ICM-42688-P), 160 µg/√Hz (BMI270, normal mode) | [ICM-42688-P DS], [BMI270 DS] |
| Noise density (measured in phone, VRW) | 1.0e-3 to 7.8e-3 (m/s²)/√Hz, about **100 to 790 µg/√Hz** (5-phone means) | [Capuano 2023] Table 4 |
| Platform noise limit | SD ≤ 0.05 m/s² per axis at fastest rate; hifi: noise ≤ 400 µg/√Hz | [Android CDD 16] 7.3.1 C-1-6, 7.3.9 C-2-1 |
| Bias instability | 2.2e-4 to 1.3e-3 m/s², about **22 to 136 µg** | [Capuano 2023] Table 4 |
| Turn-on / zero-g offset (datasheet) | ±20 mg | [BMI270 DS], [ICM-42688-P DS] |
| Turn-on bias (measured, 116 phones) | median 10 to 18.5 mg; 90th pct 30 to 60 mg; 95th pct 44 to 71 mg (per axis, Z worst) | [Kos 2016] Table 1 |
| Turn-on bias (6-position test) | 0.019 to 0.21 m/s² (2 to 21 mg) mean per phone | [Capuano 2023] Table 6 |
| Offset temperature drift | ±0.15 mg/K (ICM), ±0.25 mg/K (BMI270); hifi SHOULD ≤ ±1 mg/°C | datasheets, [Android CDD 16] 7.3.9 |
| Scale factor error | ±0.4 % (BMI270), ±0.5 % (ICM) datasheet; **0.1 to 0.7 %** measured | datasheets, [Capuano 2023] Table 6 |
| Cross-axis | 1 % | [BMI270 DS], [ICM-42688-P DS] |
| Nonlinearity | 0.1 to 0.5 %FS | datasheets |

## 2. Gyroscope

| Parameter | Range for simulator | Source |
|---|---|---|
| Noise density (datasheet) | 0.0028 °/s/√Hz (ICM-42688-P); 0.007 (BMI270 performance) / 0.010 (normal) | [ICM-42688-P DS], [BMI270 DS] |
| Noise density (measured, ARW) | 1.9e-4 to 1.45e-3 (rad/s)/√Hz, about **0.011 to 0.083 °/s/√Hz** (0.65 to 5 °/√h) | [Capuano 2023] Table 5 |
| Platform noise limit | variance ≤ 1e-7 rad²/s²/Hz (≈ 0.018 °/s/√Hz, derived); hifi ≤ 0.014 °/s/√Hz, SHOULD ≤ 0.007 | [Android CDD 16] 7.3.4 C-1-7, 7.3.9 C-2-3 |
| Bias instability | 9.6e-6 to 1.34e-4 rad/s, about **2 to 28 °/h** (Pixel 7 Pro ≈ 2, Samsung A53 ≈ 2, OnePlus 7 Pro ≈ 4.5, iPhone XR ≈ 19, Vivo X60 Pro ≈ 28) | [Capuano 2023] Table 5 |
| Turn-on ZRO (datasheet) | ±0.5 °/s | [BMI270 DS], [ICM-42688-P DS] |
| Turn-on bias (measured, 116 phones) | median 2.8 to 4.3 mrad/s (**0.16 to 0.25 °/s**); 95th pct 28 to 40 mrad/s (**1.6 to 2.3 °/s**) | [Kos 2016] Table 1 |
| Calibrated residual (platform) | SHOULD < 0.01 rad/s (0.57 °/s) stationary; hifi SHOULD < 0.002 rad/s (0.11 °/s) at 10 to 40 °C | [Android CDD 16] 7.3.4 C-SR-2, 7.3.9 |
| ZRO temperature drift | ±0.005 °/s/K (ICM), ±0.015 °/s/K (BMI270); hifi SHOULD ≤ ±0.05 °/s/°C | datasheets, [Android CDD 16] |
| Scale factor | ±0.5 % (ICM), ±2 % (BMI270, 0.4 % after on-chip CRT) datasheet; measured **0.05 to 2.6 %** at 10 °/s, up to 12 % on one phone at 40 °/s | datasheets, [Capuano 2023] Tables 7 and 8 |
| Cross-axis | 0.2 % (BMI270), ±1.25 % (ICM) | datasheets |
| g-sensitivity | hifi SHOULD < 0.1 °/s/g | [Android CDD 16] 7.3.9 |

Android requires the gyroscope to be calibrated while in use and temperature compensated [CDD 7.3.4 C-1-5, C-1-6]. Apps reading `TYPE_GYROSCOPE` therefore see a bias that is already partly removed. `TYPE_GYROSCOPE_UNCALIBRATED` exposes the raw value. The simulator should offer both.

## 3. Sample rates exposed to apps

| Platform | Rate | Source |
|---|---|---|
| Android minimum | accel and gyro ≥ 50 Hz (handheld: ≥ 100 Hz), SHOULD ≥ 200 Hz; magnetometer ≥ 10 Hz (SHOULD 50); barometer ≥ 5 Hz | [Android CDD 16] 7.3.x, 2.2.1 |
| Android cap (target API 31+) | `registerListener` limited to **200 Hz** unless `HIGH_SAMPLING_RATE_SENSORS` is declared; direct channel limited to `RATE_NORMAL` (≈ 50 Hz) | [Android sensors overview] |
| Android delay constants | NORMAL 200 ms, UI 60 ms, GAME 20 ms, FASTEST 0 (the delay is "only a suggested delay") | [Android sensors overview] |
| iOS | max is "hardware-dependent but is usually at least 100 Hz"; check timestamps for the true interval | [Apple Core Motion] |
| Survey | 20 to 300 Hz typical maximum; GNSS 1 Hz | [Wahlström 2017] |
| Hifi timing | accel/gyro/mag timestamps within 2.5 ms; delivery latency ≤ 5 ms | [Android CDD 16] 7.3.9 C-2-13, C-2-15 |

Simulator default: IMU at 100 Hz (selectable 50 / 100 / 200), magnetometer at 50 Hz, barometer at 10 to 25 Hz, GNSS at 1 Hz. Add timestamp jitter, which is **unverified** for magnitude; Apple's own documentation tells developers to check delivered timestamps.

## 4. Magnetometer

| Parameter | Value | Source |
|---|---|---|
| Earth field | typically 20,000 to 60,000 nT (20 to 60 µT) | [NOAA NCEI WMM] |
| Range | ≥ ±900 µT | [Android CDD 16] 7.3.2 C-1-4 |
| Hard-iron offset | MUST < 700 µT, SHOULD < 200 µT; online hard-iron calibration required | [Android CDD 16] 7.3.2 C-1-5, C-1-7 |
| Noise | SD MUST ≤ 1.5 µT, SHOULD ≤ 0.5 µT; hifi ≤ 0.5 µT | [Android CDD 16] 7.3.2 C-1-9, 7.3.9 |
| Resolution | ≤ 0.6 µT; example part 0.15 µT/LSB, range ±4912 µT, initial offset ±2000 LSB (±300 µT) | [Android CDD 16], [AK09918C DS] |
| Heading accuracy (pedestrian) | mean absolute error of 10 to 30° | [Wahlström 2017] citing its ref. [96] |
| In-vehicle | "further constrained by magnetic disturbances caused by the vehicle engine" | [Wahlström 2017] |

**Tunnel behaviour: unverified.** I found no peer-reviewed measurement of smartphone magnetometer heading error inside road tunnels. Reinforced concrete, steel linings, ventilation fans, power cables and passing vehicles are plausible disturbance sources. The cabin offset itself also changes when the phone or mount moves. Suggested simulator model: true field plus a constant cabin offset of 5 to 50 µT, plus spatially varying tunnel anomalies (for example 1 to 20 µT with a 5 to 50 m correlation length), plus vehicle transients. All of these magnitudes are **unverified**, so treat them as sweep parameters. A single-lane tunnel has a known map heading, so the estimator should need little magnetometer heading.

## 5. Barometer

| Parameter | Value | Source |
|---|---|---|
| Relative accuracy | ±3 Pa ≈ ±0.25 m (700 to 1100 hPa, 25 to 40 °C) | [BMP390 DS] |
| Absolute accuracy | ±50 Pa (full range); ±0.33 hPa at 25 °C | [BMP390 DS] |
| RMS noise | 0.9 Pa (unfiltered, highest oversampling) to 0.02 Pa (heaviest IIR); 3.7 Pa ultra-low-power unfiltered | [BMP390 DS] Table 8 |
| Temperature coefficient of offset | ±0.6 Pa/K | [BMP390 DS] |
| Long-term stability | ±0.16 hPa / 12 months; solder drift < ±0.8 hPa | [BMP390 DS] |
| Platform | ≥ 5 Hz; SHOULD absolute 1 hPa, relative 0.12 hPa over 20 hPa; Android 16 high-quality: relative 0.15 hPa over 100 hPa, stable within ±0.15 hPa under RF and walking; smoothing time constant ≤ 300 ms; hifi noise ≤ 2 Pa/√Hz | [Android CDD 16] 7.3.5, 7.3.9 |
| iOS | `CMAltimeter` delivers relative and absolute altitude change events | [Apple CMAltimeter] |

Conversion: about 12 Pa per metre near sea level (derived from the ±3 Pa ≈ ±0.25 m figure). Over minutes, the drift is dominated by weather, by tunnel ventilation and the piston effect of traffic, and by cabin HVAC. These magnitudes are **unverified**. Model them as a random-walk pressure offset plus step events (doors, fans).

## 6. GNSS as reported by fused location APIs

| Parameter | Value | Source |
|---|---|---|
| Accuracy semantics (Android) | `getAccuracy()` is the horizontal radius at **68 %** confidence. Speed, bearing and vertical accuracy are also 68 %. | [Android Location] |
| Accuracy semantics (iOS) | `horizontalAccuracy` is the "radius of uncertainty" in metres; negative means invalid. No confidence level is stated. | [Apple CLLocation] |
| Update rate | ≥ 1 Hz on request | [Android CDD 16] 7.3.3 C-1-1, [Wahlström 2017] |
| Open-sky accuracy | position within 20 m and speed within 0.5 m/s, 95 % of the time | [Android CDD 16] 7.3.3 C-1-3 |
| Urban accuracy | 7 to 13 m mean horizontal error (iPhone 6, urban, multipath) | [Merry & Bettinger 2019] |
| Re-acquisition | TTFF ≤ 10 s with assistance; **re-fix within 5 s** when restarted up to 1 h after the last fix | [Android CDD 16] 7.3.3 C-1-2, C-1-6 |
| Latency vs. IMU | GNSS time lag converged to **-1.26 s** (> 1 s lag observed, varies with speed) | [Li 2022] |
| Raw measurements | pseudoranges and rates are STRONGLY RECOMMENDED; enough for 20 m / 0.2 m/s (95 %) | [Android CDD 16] 7.3.3 C-SR-7 |

How a fused provider behaves inside a tunnel is **unverified** from public documentation: whether it extrapolates, freezes, or reports growing accuracy values. The simulator should model the exit phase explicitly: 0 to 5 s with no fix, then a few fixes with inflated error (for example 10 to 30 m, **unverified**), then nominal fixes. The recovery logic should then be tested against reported accuracy values that are optimistic.

## 7. Phone-to-vehicle misalignment

- **The mount is arbitrary and unknown in advance.** The phone measures its own attitude. Converting to vehicle attitude needs the phone-to-vehicle rotation, which several stand-alone methods estimate: roll and pitch from the accelerometer at zero acceleration, and yaw from GNSS course versus forward acceleration [Wahlström 2017].
- **Real case:** a phone "mounted in a more arbitrary attitude" converged to a boresight misalignment of (16.5°, -63.0°, -118.1°). This required a maneuver before the tunnel, and continuous turning was needed for convergence. NHC lever-arm error was a few cm horizontally and about 5 times worse vertically [Li 2022].
- **Coarse alignment accuracy:** within 2° when the heading misalignment is under 45° [Mu & Zhao 2019, via the publisher abstract; not read in full].
- **Why it matters for along-track error (derived):** a residual pitch misalignment δθ adds g·sin(δθ) to forward acceleration. That is 1.7 mg at 0.1°, 17 mg at 1° and 35 mg at 2°, which is already above the turn-on accelerometer bias. A yaw misalignment δψ breaks the non-holonomic constraint at a rate of v·sin(δψ): 1° at 80 km/h is 0.39 m/s lateral.
- **Loose phone** (cup holder, seat, sliding): the misalignment changes abruptly and acceleration includes the phone's own motion. There are **no primary numbers**. Model it as step changes in the mount rotation (for example 5 to 90°) at random times, plus slip events, and flag them as a failure mode rather than a tuned case.

## 8. What this means for the simulator (derived)

Error budget for a 225 s outage (5 km at 80 km/h), using cited inputs:

| Error source | Value | Along-track position error |
|---|---|---|
| Accel residual bias (pure double integration) | 1 mg | ½·b·t² ≈ 250 m |
| Accel bias instability floor | 22 to 136 µg | 5.5 to 34 m |
| Pitch misalignment / tilt error 0.5° | 8.6 mg | ≈ 2.1 km |
| Gyro residual bias 0.01 °/s | heading error 2.25° at exit | small along-track; cross-track is constrained by the single lane |
| Measured INS+NHC, 3.5 km tunnel | | 110 m (3.1 % of distance) [Li 2022] |

Takeaways:
1. Along-track accuracy depends on how the filter constrains speed (NHC plus zero lateral and vertical velocity, map-known tunnel geometry, and any speed source). Raw sensor quality matters less. Accelerometer bias and tilt need to be estimated before entry, using GNSS while the car is still outside.
2. Offer sensor presets:
   - **Good:** ICM-42688-class sensor. Gyro 0.003 °/s/√Hz, bias instability 2 °/h, turn-on 0.1 °/s. Accel 70 µg/√Hz, bias instability 20 µg, turn-on 10 mg. Scale factor 0.2 %.
   - **Typical:** gyro 0.01 °/s/√Hz, bias instability 5 to 10 °/h, turn-on 0.25 °/s. Accel 150 to 300 µg/√Hz, bias instability 50 µg, turn-on 20 mg. Scale factor 0.5 to 1 %.
   - **Poor:** gyro 0.08 °/s/√Hz, bias instability 28 °/h, turn-on 2 °/s. Accel 800 µg/√Hz, bias instability 140 µg, turn-on 70 mg. Scale factor 2.5 %.
   Draw each preset's turn-on bias once per run, and apply temperature drift through the datasheet coefficients against a cabin temperature ramp (for example 5 to 15 K over a drive; magnitude **unverified**).
3. Model the mount (fixed, with δ roll/pitch/yaw drawn from ±2° residual up to arbitrary) separately from the sensors. Model a loose phone as a separate scenario.

## Open questions

- In-tunnel magnetometer disturbance magnitudes (no primary data found).
- Fused location provider output inside and just after tunnels on Android and iOS (no public specification found).
- Timestamp jitter magnitudes at 100 to 200 Hz on real phones.
- The ST LSM6DSO datasheet (used in several phones in [Capuano 2023]) could not be downloaded, so its values are not included.

## Sources

- [BMI270 DS] Bosch Sensortec, *BMI270 Data sheet*, rev. 1.2 (06/2020). https://cdn.sparkfun.com/assets/9/a/2/9/6/bst-bmi270-ds000.pdf (product page: https://www.bosch-sensortec.com/products/motion-sensors/imus/bmi270/)
- [ICM-42688-P DS] TDK InvenSense, *ICM-42688-P Datasheet*, DS-000347 rev. 1.2. Copy read: https://static.chipdip.ru/lib/617/DOC014617647.pdf
- [BMP390 DS] Bosch Sensortec, *BMP390 Datasheet*, BST-BMP390-DS002-07 rev. 1.7 (03/2021). https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf
- [AK09918C DS] Asahi Kasei Microdevices, *AK09918C datasheet*. https://www.akm.com/content/dam/documents/products/electronic-compass/ak09918c/ak09918c-en-datasheet.pdf
- [Android CDD 16] Android 16 Compatibility Definition Document, §7.3 Sensors. https://source.android.com/docs/compatibility/16/android-16-cdd
- [Android sensors overview] https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview
- [Android Location] `android.location.Location` reference. https://developer.android.com/reference/android/location/Location
- [Apple Core Motion] *Getting raw accelerometer events*; `CMMotionManager`. https://developer.apple.com/documentation/coremotion/getting-raw-accelerometer-events
- [Apple CMAltimeter] https://developer.apple.com/documentation/coremotion/cmaltimeter
- [Apple CLLocation] `horizontalAccuracy`. https://developer.apple.com/documentation/corelocation/cllocation/horizontalaccuracy
- [NOAA NCEI WMM] World Magnetic Model product page. https://www.ncei.noaa.gov/products/world-magnetic-model
- [Capuano 2023] V. Capuano, L. Xu, J. Estrada Benavides, "Smartphone MEMS Accelerometer and Gyroscope Measurement Errors: Laboratory Testing and Analysis of the Effects on Positioning Performance," *Sensors* 23(17):7609, 2023. https://doi.org/10.3390/s23177609 (PMC10490716)
- [Kos 2016] A. Kos, S. Tomažič, A. Umek, "Evaluation of Smartphone Inertial Sensor Performance for Cross-Platform Mobile Applications," *Sensors* 16(4):477, 2016. https://doi.org/10.3390/s16040477 (PMC4850991)
- [Li 2022] L. Li, Q. Huang, K. Xu, G. Guo, R. Chen, "Vehicle Positioning in Underground Space Using a Smart Phone," *ISPRS Archives* XLVI-3/W1-2022, p. 81 ff., 2022. https://doi.org/10.5194/isprs-archives-XLVI-3-W1-2022-81-2022
- [Wahlström 2017] J. Wahlström, I. Skog, P. Händel, "Smartphone-Based Vehicle Telematics: A Ten-Year Anniversary," *IEEE Trans. Intelligent Transportation Systems* 18(10), 2017. Preprint: https://arxiv.org/abs/1611.03618
- [Merry & Bettinger 2019] K. Merry, P. Bettinger, "Smartphone GPS accuracy study in an urban environment," *PLOS ONE* 14(7):e0219890, 2019. https://doi.org/10.1371/journal.pone.0219890
- [Mu & Zhao 2019] "A GNSS/INS-integrated system for an arbitrarily mounted land vehicle navigation device," *GPS Solutions*, 2019. https://doi.org/10.1007/s10291-019-0901-8 (abstract only)
