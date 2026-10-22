"""Ground truth: where the car really is at every moment.

The car's speed comes from the scenario's speed profile; integrating it
gives the along-track distance. Every sensor is later derived from this.
"""

from dataclasses import dataclass

import numpy as np

from tunnelsim.road import Road
from tunnelsim.scenario import Scenario

DT_S = 0.01  # 100 Hz, the rate of the phone's motion sensors


@dataclass
class Truth:
    t_s: np.ndarray  # time since start
    s_m: np.ndarray  # along-track distance
    v_mps: np.ndarray  # speed along the road
    a_mps2: np.ndarray  # acceleration along the road


def simulate_truth(scenario: Scenario, road: Road, rng: np.random.Generator) -> Truth:
    """Drive the car from the start of the road to its end."""
    base_mps = scenario.speed.speed_kmh / 3.6
    wobble_mps = scenario.speed.wobble_kmh / 3.6
    period_s = rng.uniform(20, 60)
    phase = rng.uniform(0, 2 * np.pi)

    # Long enough to reach the end even at the slowest point of the wobble.
    duration_s = road.length_m / max(base_mps - wobble_mps, 1.0) + 1
    t = np.arange(0, duration_s, DT_S)
    v = base_mps + wobble_mps * np.sin(2 * np.pi * t / period_s + phase)
    s = np.concatenate([[0.0], np.cumsum(v[:-1] * DT_S)])
    a = np.gradient(v, DT_S)

    end = np.searchsorted(s, road.length_m) + 1
    return Truth(t_s=t[:end], s_m=s[:end], v_mps=v[:end], a_mps2=a[:end])
