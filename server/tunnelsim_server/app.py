"""HTTP layer: hands scenarios to the core and returns its results. No logic here."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tunnelsim.metrics import EstimatorMetrics, measure
from tunnelsim.run import Run, run_scenario
from tunnelsim.scenario import PieceChoices, Scenario, load_scenarios, piece_choices, save_scenario
from tunnelsim.sensors.specs import SENSOR_ASSUMPTIONS, SensorAssumption

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"
SAVED_DIR = SCENARIOS_DIR / "saved"  # "Save as" from the page; kept apart from the 8 test scenarios

app = FastAPI(title="Tunnel Simulator")


class MeasuredRun(BaseModel):
    run: Run
    metrics: list[EstimatorMetrics]


@app.get("/api/scenarios")
def list_scenarios() -> list[Scenario]:
    """The test scenarios, then the ones saved from the page."""
    return load_scenarios(SCENARIOS_DIR) + load_scenarios(SAVED_DIR)


@app.post("/api/scenarios")
def create_scenario(scenario: Scenario) -> Scenario:
    if scenario.name in {s.name for s in load_scenarios(SCENARIOS_DIR)}:
        raise HTTPException(409, f"{scenario.name!r} is a test scenario; save under another name")
    save_scenario(scenario, SAVED_DIR)
    return scenario


@app.get("/api/scenario-pieces")
def scenario_pieces() -> PieceChoices:
    return piece_choices()


@app.post("/api/runs")
def create_run(scenario: Scenario) -> MeasuredRun:
    run = run_scenario(scenario)
    return MeasuredRun(run=run, metrics=measure(run))


@app.get("/api/sensor-assumptions")
def sensor_assumptions() -> list[SensorAssumption]:
    return SENSOR_ASSUMPTIONS
