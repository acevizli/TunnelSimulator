"""Ground truth: where the car really is at every moment.

The car drives along its path following the speed profile's target speed,
smoothly (limited acceleration and braking) and never faster than the curves
allow. Every sensor is later derived from this.
"""

import math
from dataclasses import dataclass

import numpy as np

from tunnelsim.road import STEP_M, Path
from tunnelsim.speed_profiles import SpeedProfileSpec

DT_S = 0.01  # 100 Hz, the rate of the phone's motion sensors
MAX_ACCEL_MPS2 = 2.0
MAX_BRAKE_MPS2 = 3.0
RESPONSE_S = 2.0  # how quickly the driver closes the gap to the target speed
MAX_LATERAL_MPS2 = 2.0  # comfortable sideways acceleration in curves
BRAKING_FOR_CURVES_MPS2 = 1.5
STOPPING_MPS2 = 1.0
MAX_DURATION_S = 3600.0


@dataclass
class Truth:
    path: Path  # the path the car actually drove
    t_s: np.ndarray  # time since start
    s_m: np.ndarray  # along-track distance
    v_mps: np.ndarray  # speed along the road
    a_mps2: np.ndarray  # acceleration along the road
    x_m: np.ndarray  # map position
    y_m: np.ndarray
    z_m: np.ndarray  # height above the start
    heading_rad: np.ndarray
    yaw_rate_rps: np.ndarray  # how fast the car turns = speed x curvature
    grade: np.ndarray  # slope, metres up per metre along
    in_tunnel: np.ndarray


def simulate_truth(speed: SpeedProfileSpec, path: Path, rng: np.random.Generator) -> Truth:
    spans = path.tunnel_spans()
    target_speed = speed.driver(spans[0].start_m, spans[-1].end_m)
    ceiling = speed_ceiling(path).tolist()
    wobble = _wobble(speed.wobble_kmh / 3.6, rng)

    t, s = 0.0, 0.0
    v = min(target_speed(0, 0, 0), ceiling[0])
    ts, ss, vs = [], [], []
    while s < path.length_m and t < MAX_DURATION_S:
        ts.append(t)
        ss.append(s)
        vs.append(v)
        target = target_speed(t, s, v)
        if target > 0:
            target = max(target + wobble(t), 0.0)
        limit = _between(ceiling, s / STEP_M)
        target = min(target, limit)
        a = min(max((target - v) / RESPONSE_S, -MAX_BRAKE_MPS2), MAX_ACCEL_MPS2)
        if target == 0:
            a = min(a, -STOPPING_MPS2)  # brake firmly to a standstill rather than creep
        # The ceiling already includes braking ahead of curves, so following it is smooth.
        v = min(max(v + a * DT_S, 0.0), limit)
        s += v * DT_S
        t += DT_S

    s_arr, v_arr = np.array(ss), np.array(vs)
    curvature = path.lookup(path.curvature, s_arr)
    return Truth(
        path=path,
        t_s=np.array(ts),
        s_m=s_arr,
        v_mps=v_arr,
        a_mps2=np.gradient(v_arr, DT_S),
        x_m=path.lookup(path.x, s_arr),
        y_m=path.lookup(path.y, s_arr),
        z_m=path.lookup(path.z, s_arr),
        heading_rad=path.lookup(path.heading, s_arr),
        yaw_rate_rps=v_arr * curvature,
        grade=path.lookup(path.grade, s_arr),
        in_tunnel=path.in_tunnel(s_arr),
    )


def speed_ceiling(path: Path) -> np.ndarray:
    """Fastest comfortable speed at each metre: slow enough for every curve, braking early for them."""
    with np.errstate(divide="ignore"):
        ceiling = np.sqrt(MAX_LATERAL_MPS2 / np.abs(path.curvature))  # inf on straights
    # Walk backwards so the car starts braking before a curve, not inside it.
    for i in range(len(ceiling) - 2, -1, -1):
        ceiling[i] = min(ceiling[i], np.sqrt(ceiling[i + 1] ** 2 + 2 * BRAKING_FOR_CURVES_MPS2 * STEP_M))
    return ceiling


def _wobble(amplitude_mps: float, rng: np.random.Generator):
    """A slow, smooth speed variation: two sine waves with random periods and phases."""
    (p1, p2), (f1, f2) = rng.uniform(20, 60, size=2), rng.uniform(0, 2 * math.pi, size=2)
    return lambda t: amplitude_mps / 2 * (math.sin(2 * math.pi * t / p1 + f1) + math.sin(2 * math.pi * t / p2 + f2))


def _between(table: list[float], i: float) -> float:
    """Linear interpolation into a per-metre table (fast for single values)."""
    lo = min(int(i), len(table) - 2)
    frac = min(i - lo, 1.0)
    return table[lo] + frac * (table[lo + 1] - table[lo])
