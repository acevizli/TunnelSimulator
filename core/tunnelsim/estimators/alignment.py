"""Alignment: working out how the phone sits in the car, from the drive before the tunnel.

The estimator is never told the mount. What it needs is a matrix that turns a
reading in phone axes into car axes (forward, left, up):

  up       gravity dominates the accelerometer, so its average reading points up.
  forward  a direction in the level plane. Along it the accelerometer should read what GPS
           says the car did: speeding up and slowing down (change of GPS speed),
           and in curves a sideways reading (speed² × map curvature). We pick the
           direction that matches best. If the car drove too steadily to tell, we
           assume the screen faces the driver, so "into the screen" is forward.

The accelerometer's own bias tilts "up" slightly; whatever that leaves along
"forward" is learned afterwards by the filter as one accelerometer bias.
"""

from dataclasses import dataclass

import numpy as np

from tunnelsim.road import Path
from tunnelsim.sensors.source import GnssFix

WINDOW_S = 5  # compare accelerometer and GPS over 5 s stretches: GPS speed is too noisy second by second
MIN_SIGNAL = 3.0  # how much the motion must stand out from GPS noise before we trust the fitted forward


@dataclass
class Alignment:
    matrix: np.ndarray  # rows: car forward, left, up, written in phone axes; car = matrix @ phone
    from_motion: bool  # False when forward was assumed from the screen direction

    def to_car(self, phone_vector: np.ndarray) -> np.ndarray:
        return self.matrix @ phone_vector

    def up(self) -> np.ndarray:
        return self.matrix[2]

    def turned(self, rotation: np.ndarray) -> "Alignment":
        """The alignment after the phone itself turned by `rotation` (new phone axes in old ones)."""
        return Alignment(self.matrix @ rotation, self.from_motion)


def align(accel_t_s: np.ndarray, accel: np.ndarray, fixes: list[GnssFix], path: Path) -> Alignment:
    """Alignment from phone accelerometer readings (n, 3) and the GPS fixes over the same time."""
    up = accel.mean(axis=0)
    up /= np.linalg.norm(up)
    e1 = _level(-np.array([0.0, 0, 1]), up)  # into the screen
    if np.linalg.norm(e1) < 0.3:  # phone lying nearly flat: use its top instead
        e1 = _level(np.array([0.0, 1, 0]), up)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)  # 90° to the left of e1

    measured, did = _windows(accel_t_s, accel, fixes, path)
    if len(did) < 3:
        return _from(up, e1, 0.0, from_motion=False)
    measured = measured @ e1 + 1j * (measured @ e2)  # level-plane readings as complex numbers: e1 + i·e2
    measured, did = measured - measured.mean(), did - did.mean()  # constant parts are bias, not motion
    match = np.sum(measured * np.conj(did))
    noise = len(did) * 2 * 0.2**2 / WINDOW_S**2  # what GPS speed noise alone (≈0.2 m/s) would put into `did`
    if np.sum(np.abs(did) ** 2) < MIN_SIGNAL * noise:
        return _from(up, e1, 0.0, from_motion=False)
    return _from(up, e1, float(np.angle(match)), from_motion=True)


def _from(up: np.ndarray, e1: np.ndarray, heading: float, from_motion: bool) -> Alignment:
    """Forward is `heading` radians to the left of e1 in the level plane."""
    e2 = np.cross(up, e1)
    forward = np.cos(heading) * e1 + np.sin(heading) * e2
    return Alignment(np.vstack([forward, np.cross(up, forward), up]), from_motion)


def _level(v: np.ndarray, up: np.ndarray) -> np.ndarray:
    return v - (v @ up) * up


def _windows(accel_t_s, accel, fixes, path):
    """Per stretch of WINDOW_S seconds: the mean accelerometer reading (phone axes), and what the
    car did according to GPS and the map, as forward + i·leftward acceleration."""
    measured, did = [], []
    s_prev = None
    for a, b in zip(fixes[:-WINDOW_S:WINDOW_S], fixes[WINDOW_S::WINDOW_S]):
        inside = (accel_t_s >= a.t_s) & (accel_t_s < b.t_s)
        if not inside.any():
            continue
        s_a, _ = path.project(a.x_m, a.y_m, near_s=s_prev)
        s_b, _ = path.project(b.x_m, b.y_m, near_s=s_a)
        s_prev = s_b
        speed = (a.speed_mps + b.speed_mps) / 2
        curvature = float(np.mean(path.lookup(path.curvature, np.linspace(s_a, s_b, 10))))
        measured.append(accel[inside].mean(axis=0))
        did.append((b.speed_mps - a.speed_mps) / (b.t_s - a.t_s) + 1j * speed**2 * curvature)
    return np.array(measured).reshape(-1, 3), np.array(did)


def rotation_from_rates(rates: np.ndarray, dt_s: float) -> np.ndarray:
    """How far the phone turned, from gyro rates (n, 3) one `dt_s` apart: new phone axes in old ones."""
    total = np.eye(3)
    for w in rates:
        angle = np.linalg.norm(w) * dt_s
        if angle == 0:
            continue
        k = w / np.linalg.norm(w)
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        total = total @ (np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K)  # Rodrigues' formula
    return total
