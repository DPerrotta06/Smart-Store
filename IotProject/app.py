from flask import Flask
from Database.db import db
from Controller.customerController import customer_bp
from Controller.fanController import fan_bps
from Controller.checkoutController import checkout_bp
import os
import mosquitto
from Controller.fanController import fan_bp

app= Flask(__name__)
basedir=os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir,'Database','smart_store.db')
db.init_app(app)
app.register_blueprint(customer_bp)
app.register_blueprint(fan_bp)
app.register_blueprint(checkout_bp)

with app.app_context():       
    db.create_all()

mosquitto.start()

if __name__=='__main__':
    app.run(debug=True,use_reloader=False)