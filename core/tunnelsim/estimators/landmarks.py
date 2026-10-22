"""Landmarks: places on the road map that the phone's own sensors can recognise.

A landmark is where the road starts or stops curving, or changes how steeply it
climbs. The gyroscope sees the first (turn rate ÷ speed = curvature) and the
barometer the second (climb rate ÷ speed = grade). When one of those signals
steps from the value the map has just before a landmark to the value just after
it, and the map has such a landmark near where we believe we are, we know
where we are: "the turn just started, the map says this turn starts at 1840 m".

A straight, flat tunnel has no landmarks at all; there the estimate rests on
speed alone.
"""

from collections import deque
from dataclasses import dataclass

import numpy as np

from tunnelsim.road import STEP_M, Path

MIN_CHANGE = {"curve": 1 / 3000, "grade": 0.01}  # smaller steps drown in sensor noise
RECENT_S = 0.5  # the signal must have settled at the "after" value this long...
EARLIER_S = (2.5, 2.0)  # ...and been at the "before" value this long ago (seconds back)
TOLERANCE = 0.3  # how close to the map's before/after values counts as a match, as a fraction of the step


@dataclass(frozen=True)
class Landmark:
    kind: str  # "curve" or "grade"
    s_m: float  # where it is along the path
    before: float  # curvature (1/m) or grade (m/m) just before it
    after: float  # ... and just after it


def find_landmarks(path: Path) -> list[Landmark]:
    found = []
    for kind, table in (("curve", path.curvature), ("grade", path.grade)):
        for i in np.flatnonzero(np.abs(np.diff(table)) >= MIN_CHANGE[kind]):
            found.append(Landmark(kind, float(path.s[i] + STEP_M / 2), float(table[i]), float(table[i + 1])))
    return sorted(found, key=lambda lm: lm.s_m)


class StepWatcher:
    """Watches one sensor signal (curvature from the gyro, or grade from the barometer)
    for a step that matches a landmark of its kind on the map."""

    def __init__(self, kind: str, landmarks: list[Landmark], lag_s: float):
        self.kind = kind
        self._landmarks = [lm for lm in landmarks if lm.kind == kind]
        self._lag_s = lag_s  # how far behind the car the signal runs (it is averaged over time)
        self._history: deque[tuple[float, float, float]] = deque()  # (time, believed s, signal value)
        self._used: set[Landmark] = set()

    def add(self, t_s: float, s_m: float, value: float) -> None:
        self._history.append((t_s, s_m, value))
        while self._history[0][0] < t_s - EARLIER_S[0]:
            self._history.popleft()

    def passed(self, t_s: float, s_m: float, search_m: float) -> tuple[Landmark, float] | None:
        """A landmark the car has just passed, and how far it has travelled since
        (by our own estimate), or None."""
        recent = [v for t, _, v in self._history if t >= t_s - RECENT_S]
        earlier = [v for t, _, v in self._history if t_s - EARLIER_S[0] <= t <= t_s - EARLIER_S[1]]
        if len(recent) < 3 or len(earlier) < 3:
            return None
        now, then = float(np.mean(recent)), float(np.mean(earlier))
        for lm in sorted(self._landmarks, key=lambda lm: abs(lm.s_m - s_m)):
            if abs(lm.s_m - s_m) > search_m:
                break
            tol = TOLERANCE * abs(lm.after - lm.before)
            if lm not in self._used and abs(now - lm.after) < tol and abs(then - lm.before) < tol:
                self._used.add(lm)
                return lm, s_m - self._believed_s_at_step(lm)
        return None

    def _believed_s_at_step(self, lm: Landmark) -> float:
        """Our believed position when the car passed the landmark. Readings past the midpoint
        of the step count how long ago it was; the signal's own lag is taken off."""
        middle = (lm.before + lm.after) / 2
        since = self._history[-1][0] - EARLIER_S[1]
        beyond = [t for t, _, v in self._history if t > since and (v - middle) * (lm.after - lm.before) > 0]
        if not beyond:
            return self._history[-1][1]
        t_step = beyond[0] - self._lag_s
        times, positions = zip(*[(t, s) for t, s, _ in self._history])
        return float(np.interp(t_step, times, positions))
