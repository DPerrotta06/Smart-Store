import json
import os
import time
import threading
from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import socketio

app = Flask(
    __name__,
    template_folder=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "View", "html")
    ),
)
THRESHOLD_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "thresholds.json")
)
socket = socketio.Client()
PATREO_SOCKET_URL = os.getenv("PATREO_SOCKET_URL", "http://localhost:3001")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
BLE_ID = os.getenv("BLE_ID", "").strip().lower()

# Stores the latest live readings in memory for the gauges
sensor_data = {
    "Frig1": {"temperature": 0.0, "humidity": 0.0},
    "Frig2": {"temperature": 0.0, "humidity": 0.0}
}
ble_data = {
    "BLE": 
        {
            "device_id": None, "temperature": None, "humidity": None,
            "illuminance": None, "motion": None, "last_motion": None,
            "battery": None, "last_seen": None
        }
}

# --- JSON File Helper Functions ---
def read_thresholds():
    if not os.path.exists(THRESHOLD_FILE):
        default_data = {"Frig1": 25.0, "Frig2": 25.0}
        write_thresholds(default_data)
        return default_data
    with open(THRESHOLD_FILE, "r") as f:
        return json.load(f)

def write_thresholds(data):
    with open(THRESHOLD_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- MQTT Setup ---
def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("Frig1")
    client.subscribe("Frig2")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if msg.topic in sensor_data:
            sensor_data[msg.topic]["temperature"] = payload.get("temperature", 0.0)
            sensor_data[msg.topic]["humidity"] = payload.get("humidity", 0.0)
    except Exception as e:
        print(f"Error parsing MQTT message: {e}")

def start_patreo():
    while True:
        try:
            socket.connect(PATREO_SOCKET_URL)
            socket.wait()
        except Exception as e:
            print("Connection failed: ", e)
            time.sleep(7)

@socket.on('dynamb')
def on_dynamb(data):
    device_id = str(data.get("deviceId", "")).strip()
    if BLE_ID and device_id.lower() != BLE_ID:
        return
    ble = ble_data["BLE"]
    if device_id:
        ble["device_id"] = device_id
    if "temperature" in data:
        ble["temperature"] = data["temperature"]
    if "relativeHumidity" in data:
        ble["humidity"] = data["relativeHumidity"]
    if "illuminance" in data:
        ble["illuminance"] = data["illuminance"]
    if "batteryPercentage" in data:
        ble["battery"] = data["batteryPercentage"]
    motion = data.get(
        "isMotionDetected", data.get("isMotionDetectd", data.get("motion"))
    )
    if motion is not None:
        if isinstance(motion, list):
            motion = motion[0] if motion else False
        if isinstance(motion, str):
            motion = motion.strip().lower() in {"true", "1", "yes"}
        ble["motion"] = bool(motion)
        if ble["motion"]:
            ble["last_motion"] = time.time()
    ble["last_seen"] = time.time()

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect_async(MQTT_HOST, 1883, 60)
mqtt_client.loop_start()

# --- Flask Routes ---
@app.route("/")
def index():
    thresholds = read_thresholds()
    return render_template("dhtDashboard.html", thresholds=thresholds)

@app.route("/api/sensors", methods=["GET"])
def get_sensors():
    return jsonify(sensor_data)

@app.route("/api/thresholds", methods=["POST"])
def update_thresholds():
    new_data = request.json
    thresholds = read_thresholds()
    
    if "Frig1" in new_data:
        thresholds["Frig1"] = float(new_data["Frig1"])
    if "Frig2" in new_data:
        thresholds["Frig2"] = float(new_data["Frig2"])
        
    write_thresholds(thresholds)
    return jsonify({"status": "saved", "thresholds": thresholds})

@app.route("/api/ble", methods=["GET"])
def get_ble_data():
    ble = ble_data["BLE"]
    isOnline = ble["last_seen"] is not None and time.time() - ble["last_seen"] < 30
    return jsonify({"BLE": {**ble, 'online':isOnline}})


if __name__ == "__main__":
    threading.Thread(target=start_patreo, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)