"""The map filter: the main estimator (see docs/adr/0001-map-constrained-1d-ekf.md).

The car can only be somewhere on the known road, so the filter tracks one
position number, how far along the road the car is, plus what it needs to keep
that number honest. Its state:

    s    along-track distance (m)
    v    speed (m/s)
    b_a  accelerometer bias along the car's forward axis (m/s²)
    b_g  gyroscope bias about the car's up axis (rad/s)
    yaw  how far our idea of "forward" is turned to the left of the car's real
         forward (rad). Harmless on straights; in curves it leaks the sideways
         acceleration into the forward one, which is what makes it learnable there.
    k_g  gyroscope scale error (fraction): the gyro reads every turn rate 1-2 % off,
         which matters in long tight curves, where turn rate is used to measure speed.
    k_v  with the vehicle-speed add-on: the car reports (1 + k_v) × speed + b_v. Both are
    b_v  learned only while GPS is trusted, and frozen in the tunnel: there the other
         corrections share small errors of their own (the accelerometer's scale error)
         that would teach them wrong. If the car drove only one speed before the tunnel,
         the two can't be told apart; the band carries that doubt.

Before the tunnel it works out how the phone sits in the car (alignment). At the
tunnel entrance it redoes the alignment with everything seen so far and replays
the drive with it, so by then GPS has taught it both biases.

Every 0.1 s:
  1. phone moved?  a loose phone turning in its holder shows up as rotation the car
                   can't make; we follow it with the gyro and stop trusting the bias.
  2. predict       move s and v on by the forward acceleration the phone measured,
                   minus the bias, minus the sideways acceleration a yaw error leaks
                   into it, minus the gravity the road's slope leaks into it.
  3. stopped?      road vibration nearly vanishes when the car stands still: speed = 0.
  4. curve         turn rate = speed × map curvature (× the gyro's scale error, plus its
                   bias). In a curve this measures speed; on a straight, the gyro bias.
  5. grade         climb rate (barometer) = speed × map grade. On a slope this measures speed.
  6. landmark      the gyro or barometer just saw a curve start or end, or a grade change,
                   that the map has nearby: this measures position.
  7. vehicle speed (add-on) the car's own reading measures speed, through k_v and b_v.
Whenever a GPS fix arrives:
  8. GPS           checked against the prediction; never used inside a tunnel. Once
                   inside, GPS is only trusted again after three fixes outside agree
                   with each other; the shown position then slides over, not jumps.
                   Ten agreeing fixes overrule the filter however sure it is, so it
                   can never get stuck believing something wrong.
Whenever a beacon is heard (add-on):
  9. beacon        the map says where it is: a position fix, checked against the prediction
                   like GPS (a pass can be heard late). Three in a row that disagree with
                   us overrule us. A beacon on another branch puts the car on that branch.

Exits: where the road splits, the car could go either way, so the filter splits
too. Shortly before its band reaches a split it starts a copy that follows the
other branch (a branch hypothesis). Each copy runs everything above against its
own branch's map, and each tick loses weight by how badly its map explains what
the gyro and barometer just measured: the turn rate and climb rate its branch
allows anywhere we might be, against what was read. A copy a hundred times less
likely than the best is dropped. Before any evidence, the branch the route takes
is a little more likely. The estimate shown is the most likely copy's.
"""

import copy
from collections import deque
from dataclasses import replace

import numpy as np

from tunnelsim.estimators.alignment import Alignment, align, rotation_from_rates
from tunnelsim.estimators.estimate import Estimate
from tunnelsim.estimators.kalman import Kalman
from tunnelsim.estimators.landmarks import StepWatcher, find_landmarks
from tunnelsim.road import STEP_M, Path, Road
from tunnelsim.sensors.addons import Beacon, on_path
from tunnelsim.sensors.source import (AccelSample, BaroSample, BeaconSample, GnssFix, GyroSample, Sample,
                                     VehicleSpeedSample)

TICK_S = 0.1
G = 9.80665
PA_PER_M = 12.0  # air pressure falls ~12 Pa per metre of climb near sea level
DEG = np.pi / 180

# What we assume about an ordinary phone: datasheet-level knowledge, not this phone's actual errors.
ACCEL_BIAS_PRIOR = 0.2  # m/s² (about 20 mg)
GYRO_BIAS_PRIOR = 0.25 * DEG  # rad/s
YAW_PRIOR = {True: 1 * DEG, False: 10 * DEG}  # alignment forward fitted from motion / assumed from the screen
GYRO_SCALE_PRIOR = 0.01
VEHICLE_SCALE_PRIOR = 0.05  # a car's speed reading is a few % off (tyre size, wear, pressure)...
VEHICLE_OFFSET_PRIOR = 0.5  # m/s ...plus a small offset
ACCEL_NOISE = 0.05  # m/s² per √Hz: sensor noise plus road vibration plus small misalignment
ACCEL_BIAS_DRIFT = 2e-4  # m/s² per √s
GYRO_BIAS_DRIFT = 2e-5  # rad/s per √s
STILL_VIBRATION = 0.03  # m/s²: vertical shaking below this over one second...
STILL_ACCEL = 0.2  # m/s²: ...and no forward acceleration (vibration alone lags a pull-away) = standing still

# How much each correction is trusted (1 sigma)
STOP_SPEED_NOISE = 0.05  # m/s
TURN_RATE_NOISE = 0.003  # rad/s, gyro over one tick, allowing for small map imperfections
CLIMB_RATE_NOISE = 0.07  # m/s, barometer over one second, allowing for pressure drift
GPS_SPEED_NOISE = 0.3  # m/s
MIN_GPS_SIGMA = 5.0  # m: never trust a fix more than this, whatever the phone claims
LANDMARK_NOISE = {"curve": (3.0, 0.1), "grade": (3.0, 0.25)}  # m + s × speed: timing of the step
VEHICLE_SPEED_NOISE = 0.15  # m/s, one reading
BEACON_NOISE = 10.0  # m: where along the road a beacon is heard (field studies: 15-20 m median error)
OVERRULING_BEACONS = 3  # this many in a row that disagree with us overrule our own belief

SHIFT_RATE = 3 * DEG  # rad/s: the phone turning against the car faster than this means it moved
SHIFT_BIAS_PER_RAD = 0.4  # m/s² of doubt about the forward bias per radian the phone tips
SHIFT_YAW_PER_RAD = 0.02  # rad of doubt about the yaw per radian the phone turns (gyro scale error)
AGREEING_FIXES = 3  # fixes that must agree before GPS is trusted again after a tunnel
OVERRULING_FIXES = 10  # this many agreeing fixes overrule our own belief, however sure it is
BLEND_S = 1.5  # time constant of the slide over to GPS at the exit

# Branch hypotheses
SPLIT_AHEAD_M = 50.0  # start a copy for the other branch when our band gets this close to a split
ROUTE_PRIOR = 0.7  # before any evidence, how likely the car follows its route at a split
MAX_SURPRISE = 1.0  # the most one reading can count against a branch: one odd reading can't decide alone
DROP_BELOW = 0.01  # a branch this many times less likely than the best is ruled out


class MapFilter:
    def __init__(self, road: Road, planned_path: str, vehicle_speed: bool = False, beacons: list[Beacon] | None = None):
        """`vehicle_speed` and `beacons` switch the add-ons on; `beacons` is the map's list of them."""
        self.name = "map filter" + " + vehicle speed" * vehicle_speed + " + beacons" * (beacons is not None)
        self._road = road
        self._planned = planned_path
        self._vehicle_speed = vehicle_speed
        self._beacons = {b.id: b for b in beacons or []}
        self._tunnel_start = road.path(planned_path).tunnel_spans()[0].start_m
        self._recorded: list[Sample] = []  # everything seen until the final alignment
        self._ekf: _AlongTrackFilter | None = None
        self._aligned = False
        self._hypotheses: list[_AlongTrackFilter] = []  # after the final alignment: one per possible branch
        self._considered = {planned_path}  # branches that have had a hypothesis, so none is started twice

    def update(self, sample: Sample) -> None:
        if self._aligned:
            for hypothesis in self._hypotheses:
                hypothesis.update(sample)
            if isinstance(sample, AccelSample):
                self._branch_out()
                self._rule_out()
            return
        self._recorded.append(sample)
        if self._ekf is None:
            if sample.t_s >= 1.0:  # a first, rough alignment from one second of gravity
                self._restart()
            return
        self._ekf.update(sample)
        if self._ekf.s_m is not None and self._ekf.s_m >= self._tunnel_start:
            self._restart()  # final alignment from the whole drive before the tunnel
            self._aligned = True
            self._recorded = []
            self._hypotheses = [self._ekf]

    def _restart(self) -> None:
        """Align from everything recorded so far, then replay it through a fresh filter."""
        accel = [x for x in self._recorded if isinstance(x, AccelSample)]
        fixes = [x for x in self._recorded if isinstance(x, GnssFix)]
        alignment = align(np.array([a.t_s for a in accel]), np.array([[a.x, a.y, a.z] for a in accel]),
                          fixes, self._road.path(self._planned))
        self._ekf = _AlongTrackFilter(self._road, self._planned, alignment, self._vehicle_speed, self._beacons)
        for sample in self._recorded:
            self._ekf.update(sample)

    # ---- branch hypotheses -------------------------------------------------------------------

    def _branch_out(self) -> None:
        """Start a hypothesis for every branch our band is about to reach."""
        for hypothesis in list(self._hypotheses):
            here, s, reach = hypothesis.path, hypothesis.s_m, 3 * hypothesis.sigma_m
            for other in hypothesis.paths:
                split = self._road.split_m(here.name, other.name)
                if other.name in self._considered or split is None:
                    continue
                if s + reach + SPLIT_AHEAD_M >= split and s - reach < split:
                    self._considered.add(other.name)
                    stay, leave = self._route_odds(here.name, other.name, split)
                    twin = hypothesis.branch_to(other)
                    twin.log_weight = hypothesis.log_weight + np.log(leave)
                    hypothesis.log_weight += np.log(stay)
                    self._hypotheses.append(twin)

    def _route_odds(self, here: str, other: str, split: float) -> tuple[float, float]:
        """Prior chances of staying on `here` or taking `other` at their split: the one
        that keeps to the planned route is a little more likely."""
        def prior(path: str) -> float:
            on_route = path == self._planned or self._road.split_m(path, self._planned) > split
            return ROUTE_PRIOR if on_route else 1 - ROUTE_PRIOR
        a, b = prior(here), prior(other)
        return a / (a + b), b / (a + b)

    def _rule_out(self) -> None:
        """Drop hypotheses the evidence has ruled out, and duplicates (GPS can move one
        hypothesis onto another's branch); keep the numbers small."""
        by_weight = sorted(self._hypotheses, key=lambda h: -h.log_weight)
        best = by_weight[0].log_weight
        kept: dict[str, _AlongTrackFilter] = {}
        for hypothesis in by_weight:
            if hypothesis.log_weight - best >= np.log(DROP_BELOW):
                kept.setdefault(hypothesis.path.name, hypothesis)
        for hypothesis in kept.values():
            hypothesis.log_weight -= best
        self._hypotheses = list(kept.values())

    def estimate(self, t_s: float) -> Estimate | None:
        if not self._aligned:
            return None if self._ekf is None else self._ekf.estimate(t_s)
        best = self._hypotheses[0]  # _rule_out keeps them most likely first
        if len(self._hypotheses) == 1:
            return best.estimate(t_s)
        weights = np.exp([h.log_weight for h in self._hypotheses])
        weights /= weights.sum()
        branches = {h.path.name: round(float(w), 3) for h, w in zip(self._hypotheses, weights)}
        return replace(best.estimate(t_s), branches=branches)


class _AlongTrackFilter:
    """The Kalman filter itself, for one alignment."""

    def __init__(self, road: Road, planned_path: str, alignment: Alignment, vehicle_speed: bool,
                 beacons: dict[str, Beacon]):
        self._road = road
        self._paths = {p.name: p for p in road.paths()}
        self._alignment = alignment
        self._uses_vehicle_speed = vehicle_speed
        self._beacons = beacons
        self._car_reading: VehicleSpeedSample | None = None  # the latest one, used at the end of the tick
        self._beacons_disagreeing = 0
        self._kf: Kalman | None = None  # starts at the first GPS fix
        self._t = 0.0  # time of the state
        self._next_tick = 1
        self._accel: list[list[float]] = []  # this tick's readings, phone axes
        self._gyro: list[list[float]] = []
        self._vertical: deque[float] = deque(maxlen=100)  # last second (100 Hz) of vertical acceleration
        self._baro: deque[tuple[float, float]] = deque()  # last second of (time, height)
        self._baro_reference: float | None = None
        self._next_climb_t = 1.0
        self._trusting_gps = True
        self._candidates: list[tuple[GnssFix, float, float, Path]] = []  # fixes waiting to agree: (fix, s, var, path)
        self._blend = (0.0, 0.0)  # (offset, since when) of the slide over to GPS
        self._accel_now = 0.0  # forward acceleration in the last tick, corrected
        self.log_weight = 0.0  # how likely this branch hypothesis is (log, relative to the others)
        self._follow(self._paths[planned_path])

    def _follow(self, path: Path) -> None:
        self._path = path
        landmarks = find_landmarks(path)
        self._curve_steps = StepWatcher("curve", landmarks, lag_s=TICK_S / 2)
        self._grade_steps = StepWatcher("grade", landmarks, lag_s=0.5)  # climb rate is fitted over 1 s

    @property
    def s_m(self) -> float | None:
        return None if self._kf is None else float(self._kf.x[0])

    @property
    def sigma_m(self) -> float:
        return self._sigma

    @property
    def path(self) -> Path:
        return self._path

    @property
    def paths(self) -> list[Path]:
        return list(self._paths.values())

    def branch_to(self, path: Path) -> "_AlongTrackFilter":
        """A copy of this filter that believes the car takes `path` where it splits off."""
        shared = [*self._paths.values(), self._road, self._beacons]  # the copy shares the map, not copies it
        shared_map = {id(x): x for x in shared}
        twin = copy.deepcopy(self, shared_map)
        twin._follow(path)
        return twin

    def update(self, sample: Sample) -> None:
        match sample:
            case AccelSample():
                if sample.t_s >= self._next_tick * TICK_S - 1e-9:
                    self._end_tick()
                self._accel.append([sample.x, sample.y, sample.z])
            case GyroSample():
                self._gyro.append([sample.x, sample.y, sample.z])
            case BaroSample():
                self._add_baro(sample)
            case GnssFix():
                self._gps(sample)
            case VehicleSpeedSample() if self._uses_vehicle_speed:
                self._car_reading = sample
            case BeaconSample():
                self._beacon(sample)

    # ---- every tick ------------------------------------------------------------------------

    def _end_tick(self) -> None:
        t = self._next_tick * TICK_S
        self._next_tick += 1
        accel, gyro = np.array(self._accel).reshape(-1, 3), np.array(self._gyro).reshape(-1, 3)
        self._accel, self._gyro = [], []
        self._vertical.extend(accel @ self._alignment.up())
        if self._kf is None or len(accel) == 0:
            self._t = t
            return
        self._kf.frozen = [] if self._trusting_gps else _VEHICLE_SPEED_STATES

        turn_rate = float(gyro.mean(axis=0) @ self._alignment.up()) if len(gyro) else None
        phone_moved = self._follow_phone(gyro)                       # 1
        self._predict(accel.mean(axis=0), t)                         # 2
        if self._standing_still():                                   # 3
            self._kf.update(0.0, self._v, _H_V, STOP_SPEED_NOISE**2, gate=None)
        if turn_rate is not None:                                    # 4
            # Scored even when the phone seems to have moved: a branch that needs the
            # phone to keep turning in its holder is a poor explanation of the gyro.
            self._score_turn(turn_rate)
            if not phone_moved:
                self._curve(turn_rate)
        self._grade(t)                                               # 5
        self._landmarks(t)                                           # 6
        if self._car_reading is not None:                            # 7
            self._car_speed(self._car_reading)
            self._car_reading = None

        if self._path.in_tunnel(self._s):
            self._trusting_gps = False

    def _follow_phone(self, gyro: np.ndarray) -> bool:
        """Did the phone turn in its holder? If so, turn the alignment with it."""
        if len(gyro) == 0:
            return False
        up = self._alignment.up()
        s, v, _, b_g, _, k_g, *_ = self._kf.x
        car_turn = ((1 + k_g) * v * self._path.lookup(self._path.curvature, s) + b_g) * up
        mean = gyro.mean(axis=0) - car_turn  # the phone's own rotation, on top of the car's
        tipping = np.linalg.norm(mean - (mean @ up) * up)
        sharpest_turn = v * np.abs(self._band(self._path.curvature)).max()
        if tipping < SHIFT_RATE and abs(mean @ up) < sharpest_turn + SHIFT_RATE:
            return False
        relative, dt = gyro - car_turn, TICK_S / len(gyro)
        self._alignment = self._alignment.turned(rotation_from_rates(relative, dt))
        turned = relative.sum(axis=0) * dt
        tipped = np.linalg.norm(turned - (turned @ up) * up)
        self._kf.P[2, 2] += (SHIFT_BIAS_PER_RAD * tipped) ** 2  # the bias we learned no longer fits
        self._kf.P[3, 3] += (GYRO_BIAS_PRIOR * np.linalg.norm(turned)) ** 2
        self._kf.P[4, 4] += (SHIFT_YAW_PER_RAD * np.linalg.norm(turned)) ** 2
        return True

    def _predict(self, accel: np.ndarray, t: float) -> None:
        dt = t - self._t
        self._t = t
        s, v, b_a, b_g, yaw, k_g, k_v, b_v = self._kf.x
        forward, left, _ = self._alignment.to_car(accel)
        a = forward - yaw * left - b_a - G * self._sin_slope(s)
        self._accel_now = a
        x_next = np.array([s + v * dt + a * dt**2 / 2, max(v + a * dt, 0.0),  # cars don't reverse
                           b_a, b_g, yaw, k_g, k_v, b_v])
        F = np.eye(8)
        F[0, 1] = dt
        F[0, 2], F[1, 2] = -dt**2 / 2, -dt  # a bias error turns into speed and position error
        F[0, 4], F[1, 4] = -left * dt**2 / 2, -left * dt  # so does a yaw error, in proportion to the sideways push
        Q = np.zeros((8, 8))
        Q[:2, :2] = ACCEL_NOISE**2 * np.array([[dt**3 / 3, dt**2 / 2], [dt**2 / 2, dt]])
        Q[2, 2] = ACCEL_BIAS_DRIFT**2 * dt
        Q[3, 3] = GYRO_BIAS_DRIFT**2 * dt
        self._kf.predict(x_next, F, Q)

    def _standing_still(self) -> bool:
        shaking = float(np.std(self._vertical)) if len(self._vertical) == self._vertical.maxlen else np.inf
        return shaking < STILL_VIBRATION and abs(self._accel_now) < STILL_ACCEL

    def _score_turn(self, turn_rate: float) -> None:
        """Could this branch's map explain the turn rate, anywhere we might be?"""
        _, v, _, b_g, _, k_g, *_ = self._kf.x
        curvatures = self._band(self._path.curvature)
        k = np.abs(curvatures).max()
        H = np.array([0, (1 + k_g) * k, 0, 1, 0, v * k, 0, 0])
        sigma = np.sqrt(H @ self._kf.P @ H + TURN_RATE_NOISE**2)  # our doubt about speed, bias, scale + noise
        self._explain(turn_rate - b_g, (1 + k_g) * v * curvatures, sigma)

    def _curve(self, turn_rate: float) -> None:
        s, v, _, b_g, _, k_g, *_ = self._kf.x
        if v > 2:
            self._curve_steps.add(self._t, s, (turn_rate - b_g) / ((1 + k_g) * v))
        if np.ptp(self._band(self._path.curvature)) == 0:  # no curve starts or ends anywhere we might be
            k = float(self._path.lookup(self._path.curvature, s))
            H = np.array([0, (1 + k_g) * k, 0, 1, 0, v * k, 0, 0])
            self._kf.update(turn_rate, (1 + k_g) * v * k + b_g, H, TURN_RATE_NOISE**2)

    def _grade(self, t: float) -> None:
        climb = self._climb_rate()
        if climb is None:
            return
        s, v = self._s, self._v
        if v > 3:
            self._grade_steps.add(t, s, climb / v)
        if t < self._next_climb_t:
            return
        self._next_climb_t = t + 1.0  # once a second, so the readings don't overlap
        grades = self._band(self._path.grade, centre=s - v * 0.5)  # the fit is centred half a second back
        sigma = np.hypot(CLIMB_RATE_NOISE, np.sqrt(self._kf.P[1, 1]) * np.abs(grades).max())
        self._explain(climb, v * grades, sigma)
        slope = self._sin_slope(s - v * 0.5)
        if slope != 0 and np.ptp(self._band(self._path.grade)) == 0:
            self._kf.update(climb, v * slope, np.array([0, slope, 0, 0, 0, 0, 0, 0.0]), CLIMB_RATE_NOISE**2)

    def _explain(self, measured: float, allowed: np.ndarray, sigma: float) -> None:
        """Lower this hypothesis's weight by how far a reading falls outside everything its
        map allows anywhere we might be (`allowed`), in units of the reading's noise."""
        gap = max(allowed.min() - measured, measured - allowed.max(), 0.0)
        self.log_weight -= min(0.5 * (gap / sigma) ** 2, MAX_SURPRISE)

    def _car_speed(self, reading: VehicleSpeedSample) -> None:
        """What the car says its speed is, through its own scale error and offset."""
        if reading.speed_mps == 0:
            return  # only says the car is slower than walking pace; the stop detection does the rest
        *_, k_v, b_v = self._kf.x
        v = self._v - self._accel_now * (self._t - reading.t_s)  # the reading is up to a tick older than the state
        H = np.array([0, 1 + k_v, 0, 0, 0, 0, v, 1])
        self._kf.update(reading.speed_mps, (1 + k_v) * v + b_v, H, VEHICLE_SPEED_NOISE**2, gate=None)

    def _landmarks(self, t: float) -> None:
        search = max(4 * self._sigma, 50.0)
        for watcher in (self._curve_steps, self._grade_steps):
            hit = watcher.passed(t, self._s, search)
            if hit is None:
                continue
            landmark, travelled = hit
            base, per_speed = LANDMARK_NOISE[landmark.kind]
            r = (base + per_speed * self._v) ** 2
            self._kf.update(landmark.s_m + travelled, self._s, _H_S, r, gate=4.0)

    # ---- beacons ---------------------------------------------------------------------------

    def _beacon(self, sample: BeaconSample) -> None:
        beacon = self._beacons.get(sample.beacon_id)
        if self._kf is None or beacon is None:
            return
        if not on_path(beacon, self._path.name, self._road):
            self._follow(self._paths[beacon.path])  # the beacon is on another branch, so the car is too
        s_heard = beacon.s_m + self._v * (self._t - sample.t_s)  # it was heard a moment after the state's time
        r = BEACON_NOISE**2
        if self._kf.update(s_heard, self._s, _H_S, r):
            self._beacons_disagreeing = 0
            return
        self._beacons_disagreeing += 1
        if self._beacons_disagreeing >= OVERRULING_BEACONS:
            self._kf.P[0, 0] += (s_heard - self._s) ** 2  # our own position is no better than the gap
            self._kf.update(s_heard, self._s, _H_S, r, gate=None)
            self._beacons_disagreeing = 0

    # ---- GPS -------------------------------------------------------------------------------

    def _gps(self, fix: GnssFix) -> None:
        if self._kf is None:
            s, _ = self._path.project(fix.x_m, fix.y_m)
            r = max(fix.accuracy_m, MIN_GPS_SIGMA) ** 2
            yaw_prior = YAW_PRIOR[self._alignment.from_motion]
            P = np.diag([r, 0.5**2, ACCEL_BIAS_PRIOR**2, GYRO_BIAS_PRIOR**2, yaw_prior**2, GYRO_SCALE_PRIOR**2,
                         VEHICLE_SCALE_PRIOR**2, VEHICLE_OFFSET_PRIOR**2])
            self._kf = Kalman(np.array([s, fix.speed_mps, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), P)
            self._t = fix.t_s
            return

        path, s_fix, off_road = self._match(fix)
        s_fix += self._v * (self._t - fix.t_s)  # the fix is a moment older than the state
        r = max(fix.accuracy_m, MIN_GPS_SIGMA) ** 2
        if path.in_tunnel(s_fix) or off_road > 3 * np.sqrt(r):
            return  # no real fix can come from inside a tunnel, or from off the road
        if self._trusting_gps and path is self._path:
            if self._kf.update(s_fix, self._s, _H_S, r):
                self._kf.update(fix.speed_mps, self._v, _H_V, GPS_SPEED_NOISE**2)
                self._candidates = []
                return
        self._candidates = self._candidates[-OVERRULING_FIXES + 1 :] + [(fix, s_fix, r, path)]
        if (self._fixes_agree(AGREEING_FIXES) and (self._trusting_gps or self._could_be_outside())
                or self._fixes_agree(OVERRULING_FIXES)):
            self._take_gps(path, s_fix, fix.speed_mps, r)

    def _match(self, fix: GnssFix) -> tuple[Path, float, float]:
        """The path closest to the fix, searched around where we believe we are (or, if
        nothing is close there, everywhere); the current path wins ties, as paths
        overlap before they split."""
        window = max(300.0, 4 * self._sigma + 100)
        best = self._closest(fix, near_s=self._s, window_m=window)
        if best[2] > 50:
            best = self._closest(fix, near_s=None, window_m=window)
        return best

    def _closest(self, fix: GnssFix, near_s: float | None, window_m: float) -> tuple[Path, float, float]:
        best = (self._path, *self._path.project(fix.x_m, fix.y_m, near_s=near_s, window_m=window_m))
        for path in self._paths.values():
            s, off = path.project(fix.x_m, fix.y_m, near_s=near_s, window_m=window_m)
            if off < best[2] - 1.0:
                best = (path, s, off)
        return best

    def _fixes_agree(self, count: int) -> bool:
        """Do the last `count` fixes tell the same story as each other: one after the other,
        on the same path, each as far on from the last as their reported speed says?"""
        last = self._candidates[-count:]
        if len(last) < count or len({id(p) for *_, p in last}) > 1:
            return False
        for (f1, s1, r1, _), (f2, s2, r2, _) in zip(last, last[1:]):
            dt = f2.t_s - f1.t_s
            moved = (f1.speed_mps + f2.speed_mps) / 2 * dt
            if dt > 2.5 or abs((s2 - s1) - moved) > 3 * np.sqrt(r1 + r2):
                return False
        return True

    def _could_be_outside(self) -> bool:
        """Does our own uncertainty band reach out of the tunnel?"""
        return not self._band(self._path.tunnel).all()

    def _take_gps(self, path: Path, s_fix: float, speed: float, r: float) -> None:
        """Trust GPS again: jump the filter to it, and let the shown position slide over."""
        shown_before = self._shown_s(self._t)
        if path is not self._path:
            self._follow(path)
        self._kf.P[0, 0] += (s_fix - self._s) ** 2  # our own position is no better than the gap
        self._kf.update(s_fix, self._s, _H_S, r, gate=None)
        self._kf.update(speed, self._v, _H_V, GPS_SPEED_NOISE**2, gate=None)
        self._blend = (shown_before - self._s, self._t)
        self._trusting_gps = True
        self._candidates = []

    # ---- helpers ---------------------------------------------------------------------------

    @property
    def _s(self) -> float:
        return float(self._kf.x[0])

    @property
    def _v(self) -> float:
        return float(self._kf.x[1])

    @property
    def _sigma(self) -> float:
        return float(np.sqrt(self._kf.P[0, 0]))

    def _band(self, table: np.ndarray, centre: float | None = None) -> np.ndarray:
        """Part of a per-metre map table covering everywhere we might be (±3 sigma)."""
        centre = self._s if centre is None else centre
        last = len(table) - 1
        lo = min(max(int((centre - 3 * self._sigma) / STEP_M), 0), last)
        hi = min(max(int((centre + 3 * self._sigma) / STEP_M), 0), last)
        return table[lo : hi + 1]

    def _sin_slope(self, s: float) -> float:
        grade = float(self._path.lookup(self._path.grade, s))
        return grade / np.sqrt(1 + grade**2)

    def _add_baro(self, sample: BaroSample) -> None:
        if self._baro_reference is None:
            self._baro_reference = sample.pressure_pa
        self._baro.append((sample.t_s, (self._baro_reference - sample.pressure_pa) / PA_PER_M))
        while self._baro[0][0] < sample.t_s - 1.0:
            self._baro.popleft()

    def _climb_rate(self) -> float | None:
        """Metres per second, from a straight-line fit to the last second of barometer heights."""
        if len(self._baro) < 10:
            return None
        t, h = np.array(self._baro).T
        t = t - t.mean()
        return float(t @ (h - h.mean()) / (t @ t))

    def _shown_s(self, t_s: float) -> float:
        offset, since = self._blend
        return self._s + self._v * (t_s - self._t) + offset * np.exp(-(t_s - since) / BLEND_S)

    def estimate(self, t_s: float) -> Estimate | None:
        if self._kf is None:
            return None
        offset, since = self._blend
        still_off = offset * np.exp(-(t_s - since) / BLEND_S)
        return Estimate(path=self._path.name, s_m=self._shown_s(t_s), v_mps=self._v,
                        sigma_m=float(np.sqrt(self._kf.P[0, 0] + still_off**2)))


_H_S = np.array([1.0, 0, 0, 0, 0, 0, 0, 0])  # measures position
_H_V = np.array([0, 1.0, 0, 0, 0, 0, 0, 0])  # measures speed
_VEHICLE_SPEED_STATES = [6, 7]  # k_v, b_v
