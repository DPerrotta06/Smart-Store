import json
import os
import threading
import paho.mqtt.client as mqtt
import time
from Hardware.fan import fan
from Hardware.alert_email import send_email, wait_for_reply

COOLDOWN = 600
pending = set()
last_asked = {}



#mosquitto_pub -h localhost -t "Frig1" -m '{"temperature": 30, "humidity": 55.0}'

 
TOPICS = ("Frig1", "Frig2")
 

THRESHOLD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thresholds.json")
DEFAULT_LIMIT = 25.0
 
# Latest live readings, None until the first message arrives
sensor_data = {t: {"temperature": None, "humidity": None} for t in TOPICS}
 
file_lock = threading.Lock()


def _ask_admin(fridge, temp, turn_on):
    question = ("Would you like to turn ON the fan? (YES or NO)" if turn_on
                else "Temperature is back under the limit. Turn OFF the fan? (YES or NO)")
    try:
        send_email(fridge, temp, question)
        if wait_for_reply(fridge):
            fan.on() if turn_on else fan.off()
    finally:
        last_asked[fridge] = time.time()
        pending.discard(fridge)


def _all_under_limit():
    limits = read_thresholds()
    for t in TOPICS:
        temp = sensor_data[t]["temperature"]
        if temp is not None and temp > limits[t]:
            return False
    return True

 
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
    if msg.topic in pending or time.time() - last_asked.get(msg.topic, 0) < COOLDOWN:
        return
    limit = read_thresholds()[msg.topic]
    if temperature > limit and not fan.is_on():
        turn_on = True
    elif fan.is_on() and _all_under_limit():
        turn_on = False
    else:
        return
    pending.add(msg.topic)
    threading.Thread(target=_ask_admin, args=(msg.topic, temperature, turn_on), daemon=True).start()


 
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
 
 
def start():
    client.connect("localhost", 1883)
    client.loop_start()

