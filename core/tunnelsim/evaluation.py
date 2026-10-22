"""Judging estimates against ground truth."""

from tunnelsim.estimators.estimate import Estimate


def along_track_error(estimates: list[Estimate | None], truth_s_m: list[float]) -> list[float | None]:
    """Estimate minus truth at each moment; positive when the estimate is ahead of the car."""
    return [None if e is None else e.s_m - s for e, s in zip(estimates, truth_s_m)]
