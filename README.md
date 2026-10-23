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

The write-up (approach, assumptions, simulation, results, limitations, next steps, AI usage) is [docs/write-up.pdf](docs/write-up.pdf); its source is [docs/write-up.md](docs/write-up.md).

## Running it

### With Docker only

```sh
docker run --rm -p 8000:8000 ghcr.io/acevizli/tunnelsimulator      # replay page and API on http://localhost:8000
```

Scenarios saved from the page live inside the container and go away with it; to keep them, add `-v "$PWD/saved:/app/scenarios/saved"`.

The measurement command runs from the same image, writing its report into the current folder's `results/`:

```sh
docker run --rm -v "$PWD/results:/app/results" ghcr.io/acevizli/tunnelsimulator tunnelsim-measure
```

The image is rebuilt and published from `main` by [.github/workflows/docker.yml](.github/workflows/docker.yml), for both Intel/AMD and ARM machines. To build it yourself: `docker build -t tunnelsimulator .` (needs BuildKit, the default builder in Docker Desktop; elsewhere install the `buildx` plugin).

### For development

Needs [uv](https://docs.astral.sh/uv/) and Node.js.

```sh
uv sync                                              # Python 3.12 + core + server
uv run pytest                                        # core tests
uv run tunnelsim-measure                             # 8 test scenarios x 20 seeds -> results/measurements.md (~3 min)
uv run uvicorn tunnelsim_server.app:app --port 8000 --reload --reload-dir core --reload-dir server  # API on :8000

cd web && npm install && npm run dev                 # UI on http://localhost:5173
```

After changing any Pydantic model in the core, regenerate the UI's types with `cd web && npm run gen:api`.

After editing `docs/write-up.md`, rebuild the PDF (uses the installed Google Chrome) with `uv run --with markdown --with playwright python docs/build_pdf.py`.

## Layout

| Path | What lives there |
|---|---|
| `core/tunnelsim/` | Everything that matters: road, scenario, ground truth, sensors, estimators, evaluation. No UI code. |
| `core/tunnelsim/run.py` | Plays one scenario end to end; the best place to start reading. |
| `core/tunnelsim/estimators/map_filter.py` | The main estimator; its docstring lists every step it takes, including branch hypotheses at exits. |
| `core/tunnelsim/sensors/addons.py` | The add-ons, switched on per scenario: the car's own speed reading and tunnel beacons. Each one on adds a "map filter + …" estimator. |
| `core/tunnelsim/callouts.py` | What the driver hears: exit callouts and the missed-exit call, worked out the same way for every estimator. |
| `core/tunnelsim/metrics.py` | Measuring a run: every metric per estimator, and where, when and in which phase it was worst. |
| `core/tunnelsim/measure.py` | The measurement command: many seeds per scenario, written to a Markdown report. |
| `docs/` | The write-up (Markdown source and PDF), its build script, and the decision record (`docs/adr/`). |
| `results/measurements.md` | The latest measurement report. Its worst seeds can be typed into the replay page. |
| `server/` | Thin FastAPI layer: lists and saves scenarios, computes runs with their metrics. No logic. |
| `web/` | React + TypeScript replay page: the replay, error plots, every metric (each worst value jumps to its moment), sensor plots and assumptions, and a scenario editor. Types generated from the server's schema. |
| `scenarios/` | The 8 test scenarios (JSON). `scenarios/saved/` holds the ones saved from the page's editor; tests and the measurement command use only the 8. |
| `tests/` | pytest tests for the core. |
| `Dockerfile`, `.github/workflows/docker.yml` | The one-port image (built page served by the API) and the workflow that publishes it. |

## Status

In progress. Decisions and work are tracked as GitHub issues (see the `wayfinder:map` issue).
