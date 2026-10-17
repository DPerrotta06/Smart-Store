from Database.db import db
from datetime import date
import uuid

class Customer(db.Model):
    __tablename__ = "Customer"

    customer_id= db.Column(db.Integer, primary_key=True, unique=True)
    last_name= db.Column(db.String, nullable=False)
    first_name= db.Column(db.String, nullable=False)
    tel_number= db.Column(db.String, nullable=False)
    email= db.Column(db.String, nullable=False)
    customer_address= db.Column(db.String, nullable=False)
    customer_uuid=db.Column(db.String, nullable=False, unique=True)
    


    def save(self):
        db.session.add(self)
        db.session.commit()
        