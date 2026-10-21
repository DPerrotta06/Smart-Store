import atexit
from flask import Blueprint, jsonify
from Hardware.fan import fan

fan_bp = Blueprint('fan_bp', __name__)

# Stop the motor and release the GPIO pins when the app shuts down
atexit.register(fan.cleanup)


@fan_bp.route('/fan/status', methods=['GET'])
def fan_status():
    # The dashboard can poll this to update the ON/OFF icon
    return jsonify({"fan": fan.status()})


@fan_bp.route('/fan/on', methods=['POST'])
def fan_on():
    fan.on()
    return jsonify({"fan": fan.status()})


@fan_bp.route('/fan/off', methods=['POST'])
def fan_off():
    fan.off()
    return jsonify({"fan": fan.status()})