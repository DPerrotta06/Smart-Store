from Database.db import db
from datetime import date

class Customer(db.Model):
    __tablename__ = "Customer"

    customer_id= db.Column(db.Integer, primary_key=True, unique=True)
    last_name= db.Column(db.String, nullable=False)
    first_name= db.Column(db.String, nullable=False)
    tel_number= db.Column(db.String, nullable=False)
    email= db.Column(db.String, nullable=False)
    customer_address= db.Column(db.String, nullable=False)
    member_since = db.Column(db.String, nullable=False, default=lambda: str(date.today()))


    def save(self):
        db.session.add(self)
        db.session.commit()
        