"""Judging estimates against ground truth."""

from tunnelsim.estimators.estimate import Estimate
from tunnelsim.road import Road


def along_track_error(estimate: Estimate, truth_s_m: float, truth_path: str, road: Road) -> float:
    """Estimate minus truth; positive when the estimate is ahead of the car.

    Along-track distances on two branches can't be compared: 300 m past the
    split on one branch is nowhere near 300 m past it on the other. So when the
    estimate and the car are on different branches, both past the split, the
    error is how far apart they are along the road (back to the split and out
    the other branch), counted as positive.
    """
    split = road.split_m(estimate.path, truth_path)
    if split is not None and estimate.s_m > split and truth_s_m > split:
        return (estimate.s_m - split) + (truth_s_m - split)
    return estimate.s_m - truth_s_m


def on_wrong_branch(estimate: Estimate, truth_path: str, road: Road) -> bool:
    """Is the estimate shown past a split, on a branch the car isn't driving?"""
    split = road.split_m(estimate.path, truth_path)
    return split is not None and estimate.s_m > split
