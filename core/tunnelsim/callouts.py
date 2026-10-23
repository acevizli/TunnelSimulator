"""What the app tells the driver, worked out from an estimator's estimates.

The same rules run on every estimator, so they are compared on equal terms.

  callout      "exit in 400 m". Announced when the cautious edge of the estimate
               (the far end of its ±2σ band: the car could already be that far
               along) reaches that distance before the route's exit. A little
               early is fine; late is not. An estimator without a band uses its
               estimate as it is.
  missed exit  the estimate puts the car past the split, on a branch the route
               doesn't take, and no longer keeps the route's branch as a possibility.
"""

from pydantic import BaseModel

from tunnelsim.estimators.estimate import Estimate
from tunnelsim.road import Road

BAND_SIGMAS = 2


class Callout(BaseModel):
    distance_m: float  # what was announced: "exit in <distance> m"
    t_s: float
    truth_to_exit_m: float  # how far from the exit the car really was; more than distance_m = early


class MissedExitCall(BaseModel):
    t_s: float
    path: str  # the branch the estimate put the car on
    truth_past_split_m: float  # where the car really was then (negative: it hadn't reached the split)


def callouts(estimates: list[Estimate | None], t_s: list[float], truth_s_m: list[float], road: Road,
             planned_path: str, distances_m: list[float]) -> list[Callout]:
    """Each callout once, at the first moment the estimate's cautious edge reaches it."""
    exit_m = road.exit(planned_path).at_m
    pending = sorted(distances_m, reverse=True)
    made = []
    for e, t, truth in zip(estimates, t_s, truth_s_m):
        if e is None or _left_the_route(e, road, planned_path):
            continue
        cautious = e.s_m + BAND_SIGMAS * (e.sigma_m or 0.0)
        while pending and cautious >= exit_m - pending[0]:
            made.append(Callout(distance_m=pending.pop(0), t_s=t, truth_to_exit_m=round(exit_m - truth, 1)))
    return made


def missed_exit_call(estimates: list[Estimate | None], t_s: list[float], truth_s_m: list[float], road: Road,
                     planned_path: str) -> MissedExitCall | None:
    """The first moment the estimate says the car has left the route."""
    exit_m = road.exit(planned_path).at_m
    for e, t, truth in zip(estimates, t_s, truth_s_m):
        if e is not None and _left_the_route(e, road, planned_path) and planned_path not in (e.branches or {}):
            return MissedExitCall(t_s=t, path=e.path, truth_past_split_m=round(truth - exit_m, 1))
    return None


def _left_the_route(e: Estimate, road: Road, planned_path: str) -> bool:
    split = road.split_m(e.path, planned_path)
    return split is not None and e.s_m > split
