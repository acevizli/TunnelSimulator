"""What every estimator reports, and the shape every estimator has."""

from dataclasses import dataclass
from typing import Protocol

from tunnelsim.sensors.source import Sample


@dataclass(frozen=True)
class Estimate:
    s_m: float  # believed along-track distance
    v_mps: float  # believed speed
    sigma_m: float | None  # 1-sigma along-track uncertainty; None if the estimator has no notion of it


class Estimator(Protocol):
    name: str

    def update(self, sample: Sample) -> None:
        """Take in one sensor sample."""
        ...

    def estimate(self, t_s: float) -> Estimate | None:
        """Current belief at time t_s, or None before the estimator has any information."""
        ...
