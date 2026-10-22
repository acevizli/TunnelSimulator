"""A minimal extended Kalman filter: a belief and the two ways it changes.

The belief is a state vector `x` (our best guess) and a covariance `P` (how
unsure we are about each part of it, and how those doubts are linked).

  predict  move the belief forward in time with a motion model; doubt grows.
  update   compare one measurement with what the belief says it should read,
           and move the belief toward it, weighted by how much each is trusted.

Every measurement here is a single number, which keeps the algebra to a few lines.
"""

import numpy as np


class Kalman:
    def __init__(self, x: np.ndarray, P: np.ndarray):
        self.x = np.asarray(x, dtype=float)
        self.P = np.asarray(P, dtype=float)

    def predict(self, x_next: np.ndarray, F: np.ndarray, Q: np.ndarray) -> None:
        """`x_next` is where the motion model moves the state; `F` is how it moves
        small errors in the state; `Q` is the doubt the step itself adds."""
        self.x = x_next
        self.P = F @ self.P @ F.T + Q

    def innovation(self, z: float, z_pred: float, H: np.ndarray, r: float) -> tuple[float, float]:
        """How far the measurement is from the prediction, and how far it could
        reasonably be (variance of that gap, from our doubt plus the sensor's)."""
        return z - z_pred, float(H @ self.P @ H) + r

    def update(self, z: float, z_pred: float, H: np.ndarray, r: float, gate: float | None = 3.0) -> bool:
        """Take in measurement `z` with noise variance `r`, where `z_pred` is what
        the current belief predicts and `H` how that prediction changes with the state.

        With a `gate`, a measurement more than `gate` standard deviations away from
        the prediction is treated as wrong and ignored. Returns whether it was used.
        """
        y, S = self.innovation(z, z_pred, H, r)
        if gate is not None and y * y > gate * gate * S:
            return False
        K = self.P @ H / S  # Kalman gain: how much each state moves per unit of surprise
        self.x = self.x + K * y
        I_KH = np.eye(len(self.x)) - np.outer(K, H)
        self.P = I_KH @ self.P @ I_KH.T + r * np.outer(K, K)  # "Joseph form": stays symmetric and positive
        return True
