"""Simulated GPS: 1 Hz fixes from ground truth, none inside the tunnel."""

import numpy as np

from tunnelsim.road import Road
from tunnelsim.scenario import CleanGps
from tunnelsim.sensors.source import GnssFix
from tunnelsim.truth import Truth

FIX_INTERVAL_S = 1.0


def simulate_gnss(truth: Truth, road: Road, spec: CleanGps, rng: np.random.Generator) -> list[GnssFix]:
    fixes = []
    for t in np.arange(0, truth.t_s[-1], FIX_INTERVAL_S):
        i = np.searchsorted(truth.t_s, t)
        s = truth.s_m[i]
        if road.in_tunnel(s):
            continue
        x, y = road.position(s)
        fixes.append(
            GnssFix(
                t_s=float(truth.t_s[i]),
                x_m=x + rng.normal(0, spec.noise_m),
                y_m=y + rng.normal(0, spec.noise_m),
                speed_mps=float(truth.v_mps[i] + rng.normal(0, spec.speed_noise_mps)),
                accuracy_m=spec.noise_m,
            )
        )
    return fixes
