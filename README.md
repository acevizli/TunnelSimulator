# TunnelSimulator

Estimating a car's position on a smartphone while GPS is unavailable inside a tunnel, with a visual simulator to evaluate the approach.

## The problem

A driver follows turn-by-turn directions on a phone. The road enters a long tunnel (single lane, 500 m – 5 km), GPS fades out and stays unusable for minutes. The navigation app still needs to:

- show where the car is,
- call out an exit *inside* the tunnel at the right moment,
- recover cleanly when the car comes out.

## Goals

1. Propose one or more approaches for estimating position while GPS is unreliable, using sensors available on a modern smartphone (plus anything else reasonably assumed available, justified).
2. Build a visual simulator: a road with a tunnel, one or more cars driving through it, the sensor data the phone would record, and the true position shown next to the estimate.
3. Use the simulator to evaluate the approach: how well it works, where it breaks, and why.

## Running it

Needs [uv](https://docs.astral.sh/uv/) and Node.js.

```sh
uv sync                                              # Python 3.12 + core + server
uv run pytest                                        # core tests
uv run uvicorn tunnelsim_server.app:app --port 8000 --reload --reload-dir core --reload-dir server  # API on :8000

cd web && npm install && npm run dev                 # UI on http://localhost:5173
```

After changing any Pydantic model in the core, regenerate the UI's types with `cd web && npm run gen:api`.

## Layout

| Path | What lives there |
|---|---|
| `core/tunnelsim/` | Everything that matters: road, scenario, ground truth, sensors, estimators, evaluation. No UI code. |
| `core/tunnelsim/run.py` | Plays one scenario end to end; the best place to start reading. |
| `core/tunnelsim/estimators/map_filter.py` | The main estimator; its docstring lists every step it takes, including branch hypotheses at exits. |
| `core/tunnelsim/callouts.py` | What the driver hears: exit callouts and the missed-exit call, worked out the same way for every estimator. |
| `server/` | Thin FastAPI layer: lists scenarios, computes runs. No logic. |
| `web/` | React + TypeScript replay view. Types generated from the server's schema. |
| `scenarios/` | Scenario files (JSON). |
| `tests/` | pytest tests for the core. |

## Status

In progress. Decisions and work are tracked as GitHub issues (see the `wayfinder:map` issue).
