"""Simulated barometer: air pressure falls as the car climbs.

Near sea level pressure drops about 12 Pa per metre of height, so the
barometer sees the road's slope. Weather, tunnel ventilation and traffic
push the pressure around slowly; that is modelled as a random walk.
"""

from dataclasses import dataclass

import numpy as np

from tunnelsim.sensors import specs
from tunnelsim.truth import Truth

SEA_LEVEL_PA = 101_325.0


@dataclass
class BaroReadings:
    t_s: np.ndarray
    pressure_pa: np.ndarray


def simulate_baro(truth: Truth, rng: np.random.Generator) -> BaroReadings:
    every = round(1 / (specs.BARO_HZ * (truth.t_s[1] - truth.t_s[0])))
    t, height = truth.t_s[::every], truth.z_m[::every]
    dt = 1 / specs.BARO_HZ
    drift = np.cumsum(rng.normal(0, specs.BARO_DRIFT_PA_PER_SQRT_MIN * np.sqrt(dt / 60), len(t)))
    noise = rng.normal(0, specs.BARO_NOISE_PA, len(t))
    return BaroReadings(t_s=t, pressure_pa=SEA_LEVEL_PA - specs.PA_PER_M * height + drift + noise)


def pressure_to_height(pressure_pa: np.ndarray, reference_pa: float) -> np.ndarray:
    """Height in metres above wherever `reference_pa` was read."""
    return (reference_pa - pressure_pa) / specs.PA_PER_M
