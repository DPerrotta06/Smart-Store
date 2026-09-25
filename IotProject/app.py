from flask import Flask
from Database.db import db
from Controller.controller import customer_bp
import os

app= Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'Database', 'smart_store.db')

db.init_app(app)
app.register_blueprint(customer_bp)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)