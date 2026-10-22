"""Simulated GPS: 1 Hz fixes, degrading around tunnel portals.

The phases a fix can be in (from research/tunnels-and-gnss.md):
  open         normal noise
  fade         approaching an entrance: noise grows, the reported accuracy doesn't
  multipath    just inside the entrance: some fixes bounce off walls and land behind the car
  coast        the phone keeps reporting positions extrapolated at the last speed: fake fixes
  (dark)       deeper inside: no fixes at all
  reacquiring  just after the exit: still no fix
  exit_bias    the first fixes after the exit, pulled along the road by tens of metres
  converging   noise shrinks back to normal; the reported accuracy is optimistic
A short open-air gap between two tunnels simply runs through these again.
`clean` switches all of it off: a perfect cut-out at the entrance, normal fixes from the exit.
"""

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field

from tunnelsim.road import Span
from tunnelsim.sensors.source import GnssFix
from tunnelsim.truth import Truth

FIX_INTERVAL_S = 1.0
COAST_ACCURACY_GROWTH_MPS = 2.0  # how fast a coasting phone inflates its accuracy claim


class Fade(BaseModel):
    enabled: bool = True
    distance_m: float = Field(50, gt=0, description="Starts this far before the entrance")
    factor: float = Field(3, ge=1, description="Noise multiplier at the entrance")


class Multipath(BaseModel):
    enabled: bool = True
    zone_m: float = Field(30, ge=0, description="How far into the tunnel fixes still appear")
    probability: float = Field(0.3, ge=0, le=1, description="Chance a fix there is a bounced outlier")
    bias_min_m: float = 10
    bias_max_m: float = 50


class Coast(BaseModel):
    enabled: bool = True
    duration_s: float = Field(3, ge=0, description="Seconds of fake extrapolated fixes after the last real one")


class ExitBias(BaseModel):
    enabled: bool = True
    first_fix_s: float = Field(1, ge=0, description="Delay before the first fix after the exit")
    bad_fixes: int = Field(2, ge=0, description="How many of the first fixes are biased")
    bias_m: float = Field(30, ge=0, description="Along-track bias of those fixes; worst cases reach 180 m")


class Converge(BaseModel):
    enabled: bool = True
    duration_s: float = Field(5, gt=0)
    factor: float = Field(3, ge=1, description="Noise multiplier at the start of converging")
    optimism: float = Field(0.5, gt=0, le=1, description="Reported accuracy = optimism x actual noise")


class GpsSpec(BaseModel):
    clean: bool = Field(False, description="Ignore all portal effects")
    noise_m: float = Field(4.0, ge=0, description="Open-sky position noise, 1 sigma per axis")
    speed_noise_mps: float = Field(0.2, ge=0)
    fade: Fade = Fade()
    multipath: Multipath = Multipath()
    coast: Coast = Coast()
    exit_bias: ExitBias = ExitBias()
    converge: Converge = Converge()


@dataclass
class GnssReadings:
    fixes: list[GnssFix]
    phases: list[str]  # which phase each fix came from; known to the simulator, never to estimators


@dataclass
class _Plan:
    """How to make one fix: noise size, what accuracy to claim, how far to push it along the road."""

    phase: str
    sigma_m: float = 0.0
    reported_m: float = 0.0
    along_shift_m: float = 0.0


def simulate_gnss(truth: Truth, spec: GpsSpec, rng: np.random.Generator) -> GnssReadings:
    spans = truth.path.tunnel_spans()
    leave_times = [float(np.interp(span.end_m, truth.s_m, truth.t_s)) for span in spans]
    exit_sign = rng.choice([-1.0, 1.0], size=len(spans))  # which way each exit's bias pulls

    readings = GnssReadings(fixes=[], phases=[])
    last_real: GnssFix | None = None
    fixes_after_exit = [0] * len(spans)  # fixes made since leaving each tunnel

    for t in np.arange(0, truth.t_s[-1], FIX_INTERVAL_S):
        i = int(np.searchsorted(truth.t_s, t))
        exits_passed = sum(lt <= t for lt in leave_times)
        if truth.in_tunnel[i]:
            plan = _inside(spec, truth.s_m[i], spans, t, last_real, rng)
        else:
            since_exit = t - leave_times[exits_passed - 1] if exits_passed else None
            sign = exit_sign[exits_passed - 1] if exits_passed else 0.0
            count = fixes_after_exit[exits_passed - 1] if exits_passed else 0
            plan = _outside(spec, truth.s_m[i], spans, since_exit, count, sign)

        if plan.phase == "coast":
            fix = _extrapolate(last_real, float(truth.t_s[i]))
        elif plan.phase in ("dark", "reacquiring"):
            fix = None
        else:
            fix = _measure(truth, i, plan, spec.speed_noise_mps, rng)

        if fix is not None:
            readings.fixes.append(fix)
            readings.phases.append(plan.phase)
            if plan.phase != "coast":
                last_real = fix
            if not truth.in_tunnel[i] and exits_passed:
                fixes_after_exit[exits_passed - 1] += 1

    return readings


def _inside(spec: GpsSpec, s: float, spans: list[Span], t: float, last_real: GnssFix | None,
            rng: np.random.Generator) -> _Plan:
    if spec.clean:
        return _Plan("dark")
    depth = s - next(sp for sp in spans if sp.start_m <= s <= sp.end_m).start_m
    mp = spec.multipath
    if mp.enabled and depth < mp.zone_m:
        if rng.random() < mp.probability:  # bounced off the walls: lands behind the car
            return _Plan("multipath", spec.noise_m, spec.noise_m, -rng.uniform(mp.bias_min_m, mp.bias_max_m))
        return _Plan("multipath", spec.noise_m * spec.fade.factor, spec.noise_m)
    if spec.coast.enabled and last_real is not None and t - last_real.t_s <= spec.coast.duration_s:
        return _Plan("coast")
    return _Plan("dark")


def _outside(spec: GpsSpec, s: float, spans: list[Span], since_exit: float | None,
             fixes_since_exit: int, exit_sign: float) -> _Plan:
    nominal = spec.noise_m
    if since_exit is not None and not spec.clean:
        ex, cv = spec.exit_bias, spec.converge
        delay = ex.first_fix_s if ex.enabled else 0.0
        if since_exit < delay:
            return _Plan("reacquiring")
        if ex.enabled and fixes_since_exit < ex.bad_fixes:
            return _Plan("exit_bias", nominal, nominal, exit_sign * ex.bias_m)
        if cv.enabled and since_exit < delay + cv.duration_s:
            sigma = nominal * (1 + (cv.factor - 1) * np.exp(-3 * (since_exit - delay) / cv.duration_s))
            return _Plan("converging", sigma, cv.optimism * sigma)

    ahead = [sp.start_m - s for sp in spans if sp.start_m > s]
    fd = spec.fade
    if not spec.clean and fd.enabled and ahead and min(ahead) < fd.distance_m:
        sigma = nominal * (1 + (fd.factor - 1) * (1 - min(ahead) / fd.distance_m))
        return _Plan("fade", sigma, nominal)
    return _Plan("open", nominal, nominal)


def _measure(truth: Truth, i: int, plan: _Plan, speed_noise: float, rng: np.random.Generator) -> GnssFix:
    heading = float(truth.heading_rad[i])
    dx, dy = rng.normal(0, plan.sigma_m, 2)
    return GnssFix(
        t_s=float(truth.t_s[i]),
        x_m=float(truth.x_m[i] + plan.along_shift_m * np.cos(heading) + dx),
        y_m=float(truth.y_m[i] + plan.along_shift_m * np.sin(heading) + dy),
        speed_mps=float(max(truth.v_mps[i] + rng.normal(0, speed_noise), 0.0)),
        bearing_rad=heading,
        accuracy_m=plan.reported_m,
    )


def _extrapolate(last: GnssFix, t_s: float) -> GnssFix:
    """A fake fix: the last real one moved on at its speed and bearing."""
    dt = t_s - last.t_s
    return GnssFix(
        t_s=t_s,
        x_m=last.x_m + last.speed_mps * dt * np.cos(last.bearing_rad),
        y_m=last.y_m + last.speed_mps * dt * np.sin(last.bearing_rad),
        speed_mps=last.speed_mps,
        bearing_rad=last.bearing_rad,
        accuracy_m=last.accuracy_m + COAST_ACCURACY_GROWTH_MPS * dt,
    )
