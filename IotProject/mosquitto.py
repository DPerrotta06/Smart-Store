import json
import os
import threading
 
import paho.mqtt.client as mqtt
 
BROKER = "10.0.0.148"
PORT = 1883
TOPICS = ("Frig1", "Frig2")
 
# Absolute path next to this file, so it does not depend on where Flask is launched.
# To change it, set it from app.py before the app starts:
#   mqtt_service.THRESHOLD_FILE = os.path.join(app.root_path, "thresholds.json")
THRESHOLD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thresholds.json")
DEFAULT_LIMIT = 25.0
 
# Latest live readings, None until the first message arrives
sensor_data = {t: {"temperature": None, "humidity": None} for t in TOPICS}
 
file_lock = threading.Lock()
 
 
# --- JSON file helpers ---
 
def _write(data):
    with open(THRESHOLD_FILE, "w") as f:
        json.dump(data, f, indent=4)
 
 
def read_thresholds():
    with file_lock:
        try:
            with open(THRESHOLD_FILE, "r") as f:
                saved = json.load(f)
        except (OSError, ValueError):
            saved = {}
        if not isinstance(saved, dict):
            saved = {}
 
        data = {}
        for topic in TOPICS:
            try:
                data[topic] = float(saved.get(topic, DEFAULT_LIMIT))
            except (TypeError, ValueError):
                data[topic] = DEFAULT_LIMIT
 
        if not os.path.exists(THRESHOLD_FILE):
            _write(data)
        return data
 
 
def write_thresholds(data):
    with file_lock:
        _write(data)
 
 
def update_thresholds(new_data):
    """Validate and save limits, e.g. {"Frig1": 8}. Raises ValueError on bad input."""
    thresholds = read_thresholds()
    for topic in TOPICS:
        if topic in new_data:
            try:
                value = float(new_data[topic])
            except (TypeError, ValueError):
                raise ValueError(f"{topic}: limit must be a number")
            if not 0 <= value <= 50:
                raise ValueError(f"{topic}: limit must be between 0 and 50")
            thresholds[topic] = value
    write_thresholds(thresholds)
    return thresholds
 
 
def get_sensor_data():
    return {t: dict(v) for t, v in sensor_data.items()}
 
 
# --- MQTT ---
 
def on_connect(client, _userdata, _flags, _reason_code, _properties):
    # Subscribing here means the subscriptions come back after a reconnect
    for topic in TOPICS:
        client.subscribe(topic)
 
 
def on_message(_client, _userdata, msg):
    if msg.topic not in sensor_data:
        return
    try:
        payload = json.loads(msg.payload)
        temperature = float(payload["temperature"])
        humidity = float(payload["humidity"])
    except (ValueError, KeyError, TypeError):
        print(f"Bad payload on {msg.topic}: {msg.payload!r}")
        return
 
    sensor_data[msg.topic] = {"temperature": temperature, "humidity": humidity}
    # Alert email / fan logic can go here, using read_thresholds()
 
 
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
 
 
def start():
    client.connect("localhost", 1883)
    client.loop_start()
