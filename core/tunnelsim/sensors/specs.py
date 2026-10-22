"""The phone's sensor quality: one fixed "typical" preset.

Numbers come from research/phone-sensors.md (datasheets, platform specs and
measured phones). They are not editable on purpose: the point is to judge the
method on an ordinary phone, not to tune the phone.
"""

import math

from pydantic import BaseModel

G = 9.80665  # m/s², standard gravity
MG = G / 1000  # one milli-g
DEG = math.pi / 180

IMU_HZ = 100
MAG_HZ = 50
BARO_HZ = 25

# Accelerometer
ACCEL_NOISE_DENSITY = 200e-6 * G  # (m/s²)/√Hz; 150-300 µg/√Hz
ACCEL_TURN_ON_BIAS = 20 * MG  # 1 sigma per axis, drawn once per drive
ACCEL_BIAS_INSTABILITY = 50e-6 * G  # slow wander of the bias
ACCEL_SCALE_ERROR = 0.0075  # 1 sigma per axis; 0.5-1 %

# Gyroscope
GYRO_NOISE_DENSITY = 0.01 * DEG  # (rad/s)/√Hz
GYRO_TURN_ON_BIAS = 0.25 * DEG  # rad/s, 1 sigma per axis
GYRO_BIAS_INSTABILITY = 7.5 * DEG / 3600  # rad/s; 5-10 °/h
GYRO_SCALE_ERROR = 0.0075

# Barometer
BARO_NOISE_PA = 1.0  # RMS per sample; 0.02-3.7 Pa depending on filtering
BARO_DRIFT_PA_PER_SQRT_MIN = 2.0  # weather, ventilation, traffic piston effect (unverified)
PA_PER_M = 12.0  # pressure falls ~12 Pa per metre of climb near sea level

# Magnetometer (simulated but not used by the estimators)
EARTH_FIELD_UT = (18.0, 0.0, -46.0)  # north, east, up components; mid-latitude
CABIN_OFFSET_UT = 30.0  # car's own steel and electrics (5-50 µT, unverified)
MAG_NOISE_UT = 0.5
TUNNEL_ANOMALY_UT = 10.0  # rebar and fans (1-20 µT, unverified)
TUNNEL_ANOMALY_LENGTH_M = 20.0

# Road vibration felt by the phone, grows with speed and nearly vanishes when stopped
VIBRATION_IDLE = 0.02  # m/s², engine idle
VIBRATION_PER_MPS = 0.012  # m/s² per m/s of speed, vertical; half that sideways and forward


class SensorAssumption(BaseModel):
    sensor: str
    quantity: str
    value: str
    source: str


SENSOR_ASSUMPTIONS = [
    SensorAssumption(sensor="Accelerometer", quantity="Rate", value="100 Hz", source="Android CDD 16; Apple Core Motion"),
    SensorAssumption(sensor="Accelerometer", quantity="Noise", value="200 µg/√Hz", source="Datasheets 70-160, measured phones 100-790"),
    SensorAssumption(sensor="Accelerometer", quantity="Bias at power-on", value="20 mg (1σ per axis)", source="Measured phones, Capuano 2023"),
    SensorAssumption(sensor="Accelerometer", quantity="Bias wander", value="50 µg", source="Datasheet bias instability"),
    SensorAssumption(sensor="Accelerometer", quantity="Scale error", value="0.75 %", source="Datasheets 0.5-1 %"),
    SensorAssumption(sensor="Gyroscope", quantity="Rate", value="100 Hz", source="Android CDD 16; Apple Core Motion"),
    SensorAssumption(sensor="Gyroscope", quantity="Noise", value="0.01 °/s/√Hz", source="Datasheets 0.003-0.01"),
    SensorAssumption(sensor="Gyroscope", quantity="Bias at power-on", value="0.25 °/s (1σ per axis)", source="Measured phones, Capuano 2023"),
    SensorAssumption(sensor="Gyroscope", quantity="Bias wander", value="7.5 °/h", source="Datasheets 5-10 °/h"),
    SensorAssumption(sensor="Gyroscope", quantity="Scale error", value="0.75 %", source="Datasheets 0.5-1 %"),
    SensorAssumption(sensor="Barometer", quantity="Rate", value="25 Hz", source="Android CDD 16 (≥ 5 Hz)"),
    SensorAssumption(sensor="Barometer", quantity="Noise", value="1 Pa ≈ 8 cm", source="BMP390 datasheet 0.02-3.7 Pa"),
    SensorAssumption(sensor="Barometer", quantity="Drift", value="2 Pa per √minute", source="Assumed (weather, ventilation)"),
    SensorAssumption(sensor="Magnetometer", quantity="Rate / noise", value="50 Hz / 0.5 µT", source="Android CDD 16"),
    SensorAssumption(sensor="Magnetometer", quantity="Disturbance", value="30 µT cabin, 10 µT in tunnel", source="Assumed; not used by estimators"),
    SensorAssumption(sensor="Road vibration", quantity="Vertical", value="0.02 + 0.012·speed m/s²", source="Assumed; drops when stopped"),
    SensorAssumption(sensor="GPS", quantity="Rate / open-sky noise", value="1 Hz / 4 m", source="Android CDD 16; urban 7-13 m"),
]
