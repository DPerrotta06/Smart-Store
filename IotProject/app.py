from flask import Flask
from Database.db import db
from Controller.customerController import customer_bp, js_bp
from Controller.adminController import admin_bp
from Controller.checkoutController import checkout_bp
from Controller.reportController import report_bp
from Controller.bleController import ble_bp
from Controller import bleController
import os
import mosquitto
import secrets
from Controller.fanController import fan_bp


app= Flask(__name__)

app.secret_key=os.environ['SECRET_KEY']



basedir=os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir,'Database','smart_store.db')
db.init_app(app)

app.register_blueprint(customer_bp)
app.register_blueprint(js_bp)
app.register_blueprint(checkout_bp)
app.register_blueprint(fan_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(report_bp)
app.register_blueprint(ble_bp)
# Phase 2: listen for the fridge sensors. If the MQTT broker is not running, the store still works.
try:
    mosquitto.start()
except OSError as error:
    print(f"MQTT broker not reachable, fridge readings are off: {error}")

# Phase 4: BLE room sensor (Minew MSP01) through Pareto Anywhere. Keeps retrying in the background.
bleController.start()
if __name__=='__main__':
    app.run(debug=True,use_reloader=False)
