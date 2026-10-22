"""The road map: the known geometry of the route the car drives.

A road is a main line plus any number of exits. Each line is a list of
segments, and each segment has a constant curve, a constant grade, and is
either inside a tunnel or in the open.

A *path* is one way through the road from its start: the main line, or the
main line up to an exit and then that exit's branch. Along-track distance `s`
is measured in metres from the start of the road along a path, so every path
shares the same `s` up to the point where it splits off.
"""

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field

MAIN = "main"  # name of the path that never leaves the main line
STEP_M = 1.0  # resolution at which a path's geometry is tabulated


class Segment(BaseModel):
    length_m: float = Field(gt=0)
    radius_m: float | None = Field(None, description="None = straight; positive turns left, negative turns right")
    grade_pct: float = Field(0, description="Climb in % (metres up per 100 m along); negative is downhill")
    tunnel: bool = False

    @property
    def curvature(self) -> float:
        """1 / radius, in 1/m. Turn rate = speed x curvature."""
        return 0.0 if self.radius_m is None else 1.0 / self.radius_m


class Exit(BaseModel):
    name: str
    at_m: float  # along-track distance on the main line where the branch splits off
    branch: list[Segment]


class Road(BaseModel):
    main: list[Segment]
    exits: list[Exit] = []

    def exit(self, name: str) -> Exit:
        return next(e for e in self.exits if e.name == name)

    def path(self, exit_name: str | None = None) -> "Path":
        """The main line, or the way out through the named exit."""
        if exit_name is None or exit_name == MAIN:
            return Path(MAIN, self.main)
        exit = self.exit(exit_name)
        return Path(exit.name, _cut(self.main, exit.at_m) + exit.branch)

    def paths(self) -> list["Path"]:
        return [self.path(MAIN)] + [self.path(e.name) for e in self.exits]

    def split_m(self, a: str, b: str) -> float | None:
        """Along-track distance where paths `a` and `b` part ways; None if they are the same path."""
        if a == b:
            return None
        return min(self.exit(name).at_m for name in (a, b) if name != MAIN)


def _cut(segments: list[Segment], at_m: float) -> list[Segment]:
    """The segments covering the first `at_m` metres."""
    kept, start = [], 0.0
    for seg in segments:
        if start + seg.length_m >= at_m:
            kept.append(seg.model_copy(update={"length_m": at_m - start}))
            return kept
        kept.append(seg)
        start += seg.length_m
    raise ValueError(f"exit at {at_m} m is beyond the end of the road")


@dataclass
class Span:
    start_m: float
    end_m: float


class Path:
    """The geometry of one path, tabulated every metre for fast lookup."""

    def __init__(self, name: str, segments: list[Segment]):
        self.name = name
        lengths = [seg.length_m for seg in segments]
        self.length_m = float(sum(lengths))
        self._segment_ends = np.cumsum(lengths)
        self._segments = segments

        self.s = np.arange(0, self.length_m + STEP_M, STEP_M)
        seg_index = self._segment_index(self.s)
        self.curvature = np.array([segments[i].curvature for i in seg_index])
        self.grade = np.array([segments[i].grade_pct / 100 for i in seg_index])
        self.tunnel = np.array([segments[i].tunnel for i in seg_index])

        # Walk the path a metre at a time: turn by curvature, climb by grade.
        heading_steps = np.concatenate([[0.0], self.curvature[:-1] * STEP_M])
        self.heading = np.cumsum(heading_steps)  # radians, 0 = east, counter-clockwise
        self.x = np.concatenate([[0.0], np.cumsum(np.cos(self.heading[:-1]) * STEP_M)])
        self.y = np.concatenate([[0.0], np.cumsum(np.sin(self.heading[:-1]) * STEP_M)])
        self.z = np.concatenate([[0.0], np.cumsum(self.grade[:-1] * STEP_M)])

    def _segment_index(self, s: np.ndarray) -> np.ndarray:
        return np.minimum(np.searchsorted(self._segment_ends, s, side="right"), len(self._segments) - 1)

    def lookup(self, table: np.ndarray, s: np.ndarray | float) -> np.ndarray:
        """Value of a tabulated quantity (self.x, self.heading, ...) at distance(s) s."""
        return np.interp(s, self.s, table)

    def in_tunnel(self, s: np.ndarray | float) -> np.ndarray:
        # Rounded down, so this agrees exactly with tunnel_spans(): start <= s < end.
        i = np.clip(np.floor(np.asarray(s) / STEP_M).astype(int), 0, len(self.s) - 1)
        return self.tunnel[i]

    def tunnel_spans(self) -> list[Span]:
        spans, start = [], None
        for s, inside in zip(self.s, self.tunnel):
            if inside and start is None:
                start = s
            if not inside and start is not None:
                spans.append(Span(float(start), float(s)))
                start = None
        if start is not None:
            spans.append(Span(float(start), self.length_m))
        return spans

    def project(self, x: float, y: float, near_s: float | None = None, window_m: float = 300) -> tuple[float, float]:
        """Map matching: (along-track distance, distance off the road) of the closest point.

        `near_s` limits the search to a window around a believed position, so that
        overlapping parts of the road (the loops of a spiral) don't get confused.
        """
        lo, hi = 0, len(self.s)
        if near_s is not None:
            near_s = min(max(near_s, 0.0), self.length_m)
            lo = max(0, int((near_s - window_m) / STEP_M))
            hi = min(len(self.s), int((near_s + window_m) / STEP_M) + 1)
        d2 = (self.x[lo:hi] - x) ** 2 + (self.y[lo:hi] - y) ** 2
        i = int(np.argmin(d2))
        return float(self.s[lo + i]), float(np.sqrt(d2[i]))
