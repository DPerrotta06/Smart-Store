import json
import os
from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt

app = Flask(__name__)
THRESHOLD_FILE = "thresholds.json"

# Stores the latest live readings in memory for the gauges
sensor_data = {
    "Frig1": {"temperature": 0.0, "humidity": 0.0},
    "Frig2": {"temperature": 0.0, "humidity": 0.0}
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
def on_connect(client, userdata, flags, rc):
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

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("10.0.0.148", 1883, 60)
mqtt_client.loop_start()

# --- Flask Routes ---
@app.route("/")
def index():
    thresholds = read_thresholds()
    # Renders HTML with initial threshold values via Jinja
    return render_template("index.html", thresholds=thresholds)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)