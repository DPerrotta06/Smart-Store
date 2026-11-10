from flask import Flask, render_template, jsonify
import serial
import time
import re

app = Flask(__name__)

PORT = "/dev/ttyUSB0"
BAUD = 115200
COMMAND = bytes.fromhex("0008220000000022")

def read_bulk_rfid():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.2)
        ser.reset_input_buffer() 
        
        start_time = time.time()
        last_poll = 0
        raw_hex_stream = ""
        
        while time.time() - start_time < 2.0:
            if time.time() - last_poll > 0.1:
                ser.write(COMMAND)
                last_poll = time.time()
                
            if ser.in_waiting > 0:
                raw_hex_stream += ser.read(ser.in_waiting).hex().upper()
                
        ser.close()
        return raw_hex_stream 
    except Exception as e:
        print(f"Hardware Error: {e}")
        return ""

@app.route('/')
def index():
    # Serves the index.html file from the /templates folder
    return render_template('index.html')

@app.route('/api/scan')
def api_scan():
    raw_hex_stream = read_bulk_rfid()
    
    # Extract tags and apply the filter to ONLY keep tags starting with '000000'
    found_epcs = [epc for epc in set(re.findall(r'(?:A0|E0)([A-F0-9]{22})', raw_hex_stream)) if epc.startswith("000000")]
    
    return jsonify({
        "raw_hex": raw_hex_stream,
        "tags": found_epcs
    })

if __name__ == "__main__":
    print("🚀 Starting RFID Test Server...")
    print("👉 Open a web browser and go to: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)