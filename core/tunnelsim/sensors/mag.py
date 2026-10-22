"""Simulated magnetometer. Recorded so the data set is complete, but no estimator uses it:
inside a car and a tunnel the Earth's field is buried under the car's own
magnetism and the tunnel's steel.

Map axes: x east, y north, z up.
"""

from dataclasses import dataclass

import numpy as np

from tunnelsim.sensors import specs
from tunnelsim.truth import Truth


@dataclass
class MagReadings:
    t_s: np.ndarray
    field_ut: np.ndarray  # (n, 3) µT, phone axes


def simulate_mag(truth: Truth, mount_matrices: np.ndarray, rng: np.random.Generator) -> MagReadings:
    every = round(1 / (specs.MAG_HZ * (truth.t_s[1] - truth.t_s[0])))
    t, heading, s = truth.t_s[::every], truth.heading_rad[::every], truth.s_m[::every]
    north, east, up = specs.EARTH_FIELD_UT

    # The Earth's field seen from a car heading `heading` (0 = east, counter-clockwise).
    forward = east * np.cos(heading) + north * np.sin(heading)
    left = -east * np.sin(heading) + north * np.cos(heading)
    field_car = np.column_stack([forward, left, np.full_like(t, up)])

    field_car += rng.normal(0, 1, 3) / np.sqrt(3) * specs.CABIN_OFFSET_UT
    field_car += _tunnel_anomaly(truth, s, rng)

    field_phone = np.einsum("nij,nj->ni", mount_matrices[::every], field_car)
    return MagReadings(t_s=t, field_ut=field_phone + rng.normal(0, specs.MAG_NOISE_UT, field_phone.shape))


def _tunnel_anomaly(truth: Truth, s: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """A field that varies smoothly along the tunnel (steel in the walls) and is zero outside."""
    path = truth.path
    smooth = int(specs.TUNNEL_ANOMALY_LENGTH_M)
    raw = rng.normal(0, 1, (len(path.s) + smooth, 3))
    kernel = np.ones(smooth) / np.sqrt(smooth)
    along = np.column_stack([np.convolve(raw[:, k], kernel, mode="valid")[: len(path.s)] for k in range(3)])
    along *= specs.TUNNEL_ANOMALY_UT * path.tunnel[:, None]
    index = np.clip(s.astype(int), 0, len(path.s) - 1)
    return along[index]
