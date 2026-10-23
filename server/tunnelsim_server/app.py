"""HTTP layer: hands scenarios to the core and returns its results. No logic here."""

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from tunnelsim.metrics import EstimatorMetrics, measure
from tunnelsim.run import Run, run_scenario
from tunnelsim.scenario import Scenario, load_scenarios
from tunnelsim.sensors.specs import SENSOR_ASSUMPTIONS, SensorAssumption

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"

app = FastAPI(title="Tunnel Simulator")


@app.get("/api/scenarios")
def list_scenarios() -> list[Scenario]:
    return load_scenarios(SCENARIOS_DIR)


@app.post("/api/runs")
def create_run(scenario: Scenario) -> Run:
    return run_scenario(scenario)


class MeasuredRun(BaseModel):
    """PROTOTYPE (replay layout): a run with its metrics, for the metrics table."""

    run: Run
    metrics: list[EstimatorMetrics]


@app.post("/api/prototype/runs")
def create_measured_run(scenario: Scenario) -> MeasuredRun:
    run = run_scenario(scenario)
    return MeasuredRun(run=run, metrics=measure(run))


@app.get("/api/sensor-assumptions")
def sensor_assumptions() -> list[SensorAssumption]:
    return SENSOR_ASSUMPTIONS
