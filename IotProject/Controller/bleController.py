"""Phase 4: Minew MSP01 BLE room sensor (temperature, humidity, light and motion).

The MSP01 is read by Pareto Anywhere (with barnowl-hci), which streams the decoded readings as
"dynamb" events over Socket.IO at localhost:3001. This file listens to that stream, keeps the
latest values in memory, and gives them to the dashboard through /ble (admins only).

Needs:  pip install "python-socketio[client]"   and Pareto Anywhere running on the Pi.
Set BLE_ID (in .env or the environment) to your sensor's device ID so other nearby
Bluetooth sensors are ignored. Without it, any sensor that reports these values is shown.
"""
import os
import threading
import time

from flask import Blueprint, jsonify

from GeneralFunction.adminAuth import requireAdmin

try:
    import socketio
except ImportError:          # the store still runs; the dashboard says the BLE sensor is unavailable
    socketio = None

ble_bp = Blueprint("ble_bp", __name__)

PARETO_SOCKET_URL = os.getenv("PARETO_SOCKET_URL", "http://localhost:3001")
BLE_ID = os.getenv("BLE_ID", "").strip().lower()
ONLINE_SECONDS = 30          # "online" = a reading arrived in the last 30 seconds
RETRY_SECONDS = 7            # wait between connection attempts to Pareto Anywhere

# The latest reading from the sensor, kept in memory like the fridge readings
ble_data = {
    "device_id": None, "temperature": None, "humidity": None,
    "illuminance": None, "motion": None, "last_motion": None,
    "battery": None, "last_seen": None,
}
listener = {"connected": False, "error": None}
_lock = threading.Lock()
_started = False

SENSOR_FIELDS = ("temperature", "relativeHumidity", "illuminance", "isMotionDetected")


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def handle_dynamb(data):
    """One dynamb (dynamic ambient data) event from Pareto Anywhere."""
    if not isinstance(data, dict):
        return
    device_id = str(data.get("deviceId", "")).strip()
    if BLE_ID and device_id.lower() != BLE_ID:
        return                                   # another Bluetooth device nearby
    if not any(field in data for field in SENSOR_FIELDS):
        return                                   # e.g. a phone that only reports its battery
    with _lock:
        if device_id:
            ble_data["device_id"] = device_id
        if "temperature" in data:
            ble_data["temperature"] = _number(data["temperature"])
        if "relativeHumidity" in data:
            ble_data["humidity"] = _number(data["relativeHumidity"])
        if "illuminance" in data:
            ble_data["illuminance"] = _number(data["illuminance"])
        if "batteryPercentage" in data:
            ble_data["battery"] = _number(data["batteryPercentage"])
        # Pareto Anywhere sends motion as a list of booleans, e.g. [true]
        motion = data.get("isMotionDetected", data.get("motion"))
        if motion is not None:
            if isinstance(motion, list):
                motion = any(bool(m) for m in motion)
            if isinstance(motion, str):
                motion = motion.strip().lower() in {"true", "1", "yes"}
            ble_data["motion"] = bool(motion)
            if ble_data["motion"]:
                ble_data["last_motion"] = time.time()
        ble_data["last_seen"] = time.time()


def _listen():
    client = socketio.Client(reconnection=True)

    @client.event
    def connect():
        listener.update(connected=True, error=None)
        print("Connected to Pareto Anywhere")

    @client.event
    def disconnect(*args):
        listener["connected"] = False

    client.on("dynamb", handle_dynamb)
    while True:
        try:
            client.connect(PARETO_SOCKET_URL, wait_timeout=10)
            client.wait()                        # returns if the connection is lost for good
        except Exception as error:               # Pareto Anywhere not running yet: keep trying
            listener.update(connected=False, error=str(error) or "not reachable")
            try:
                client.disconnect()
            except Exception:
                pass
            time.sleep(RETRY_SECONDS)


def start():
    """Start listening to Pareto Anywhere in the background (called once from app.py)."""
    global _started
    if _started:
        return
    _started = True
    if socketio is None:
        listener["error"] = 'python-socketio is not installed (pip install "python-socketio[client]")'
        print("BLE sensor off:", listener["error"])
        return
    threading.Thread(target=_listen, daemon=True).start()


@ble_bp.route("/ble", methods=["GET"])
@requireAdmin
def get_ble_data():
    with _lock:
        data = dict(ble_data)
    online = data["last_seen"] is not None and time.time() - data["last_seen"] < ONLINE_SECONDS
    return jsonify({"BLE": {**data, "online": online,
                            "pareto_connected": listener["connected"], "error": listener["error"]}})
