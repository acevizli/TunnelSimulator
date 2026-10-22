"""Baseline: keep moving at the last GPS speed. What an app does with no other sensors."""

from tunnelsim.estimators.estimate import Estimate
from tunnelsim.road import Road
from tunnelsim.sensors.source import GnssFix, Sample


class Baseline:
    name = "baseline"

    def __init__(self, road: Road):
        self._road = road
        self._last_fix_s_m: float | None = None
        self._last_fix_t_s = 0.0
        self._speed_mps = 0.0

    def update(self, sample: Sample) -> None:
        if isinstance(sample, GnssFix):
            self._last_fix_s_m = self._road.project(sample.x_m, sample.y_m)
            self._last_fix_t_s = sample.t_s
            self._speed_mps = sample.speed_mps

    def estimate(self, t_s: float) -> Estimate | None:
        if self._last_fix_s_m is None:
            return None
        s = self._last_fix_s_m + self._speed_mps * (t_s - self._last_fix_t_s)
        # The baseline has no model of its own error, so it reports no uncertainty band.
        return Estimate(s_m=min(s, self._road.length_m), v_mps=self._speed_mps, sigma_m=None)
