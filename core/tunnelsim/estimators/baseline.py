"""Baseline: keep moving at the last GPS speed. What an app does with no other sensors.

It assumes the car follows the planned route until a GPS fix shows otherwise.
"""

from tunnelsim.estimators.estimate import Estimate
from tunnelsim.road import Road
from tunnelsim.sensors.source import GnssFix, Sample


class Baseline:
    name = "baseline"

    def __init__(self, road: Road, planned_path: str):
        self._paths = {p.name: p for p in road.paths()}
        self._path = self._paths[planned_path]
        self._last_fix_s_m: float | None = None
        self._last_fix_t_s = 0.0
        self._speed_mps = 0.0

    def update(self, sample: Sample) -> None:
        if isinstance(sample, GnssFix):
            self._path, self._last_fix_s_m = self._match(sample)
            self._last_fix_t_s = sample.t_s
            self._speed_mps = sample.speed_mps

    def _match(self, fix: GnssFix):
        """The path closest to the fix; the current one wins ties, as paths overlap before they split."""
        best = (self._path, *self._path.project(fix.x_m, fix.y_m))
        for path in self._paths.values():
            s, off = path.project(fix.x_m, fix.y_m)
            if off < best[2] - 1.0:
                best = (path, s, off)
        return best[0], best[1]

    def estimate(self, t_s: float) -> Estimate | None:
        if self._last_fix_s_m is None:
            return None
        s = self._last_fix_s_m + self._speed_mps * (t_s - self._last_fix_t_s)
        # The baseline has no model of its own error, so it reports no uncertainty band.
        return Estimate(path=self._path.name, s_m=min(s, self._path.length_m), v_mps=self._speed_mps, sigma_m=None)
