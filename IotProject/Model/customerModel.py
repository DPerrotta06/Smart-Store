from Database.db import db
from sqlalchemy import func

class Customer(db.Model):
    __tablename__ = "Customer"
    customer_id= db.Column(db.Integer, primary_key=True)
    last_name= db.Column(db.String, nullable=False)
    first_name= db.Column(db.String, nullable=False)
    tel_number= db.Column(db.String, nullable=False)
    email= db.Column(db.String, nullable=False, unique=True)
    customer_address= db.Column(db.String, nullable=False)
    member_since= db.Column(db.String, server_default= func.now())
    customer_uuid=db.Column(db.String, nullable=False, unique=True)
    


    def save(self): #should be outside of class function that checks if user exists based on email
        db.session.add(self)
        db.session.commit()





        