"""A sensor source that serves samples the simulator produced in advance."""

from tunnelsim.sensors.source import Sample


class SimulatedSource:
    def __init__(self, samples: list[Sample]):
        self._samples = sorted(samples, key=lambda sample: sample.t_s)
        self._next = 0

    def read(self, until_t_s: float) -> list[Sample]:
        start = self._next
        while self._next < len(self._samples) and self._samples[self._next].t_s <= until_t_s:
            self._next += 1
        return self._samples[start : self._next]
