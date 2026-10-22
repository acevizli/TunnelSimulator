"""Simulated GPS: 1 Hz fixes from ground truth, none inside a tunnel."""

import numpy as np

from tunnelsim.scenario import CleanGps
from tunnelsim.sensors.source import GnssFix
from tunnelsim.truth import Truth

FIX_INTERVAL_S = 1.0


def simulate_gnss(truth: Truth, spec: CleanGps, rng: np.random.Generator) -> list[GnssFix]:
    fixes = []
    for t in np.arange(0, truth.t_s[-1], FIX_INTERVAL_S):
        i = int(np.searchsorted(truth.t_s, t))
        if truth.in_tunnel[i]:
            continue
        fixes.append(
            GnssFix(
                t_s=float(truth.t_s[i]),
                x_m=float(truth.x_m[i] + rng.normal(0, spec.noise_m)),
                y_m=float(truth.y_m[i] + rng.normal(0, spec.noise_m)),
                speed_mps=float(truth.v_mps[i] + rng.normal(0, spec.speed_noise_mps)),
                accuracy_m=spec.noise_m,
            )
        )
    return fixes
