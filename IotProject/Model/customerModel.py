from Database.db import db
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from GeneralFunction.generalFunction import normalizeEmail



class Customer(db.Model):
    __tablename__ = "Customer"
    membership_number = db.Column(db.Integer, primary_key=True, autoincrement=True)   # internal id
    card_number = db.Column(db.String, unique=True)    # the random number on the membership card
    last_name = db.Column(db.String, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    tel_number = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    customer_address = db.Column(db.String, nullable=False)
    member_since = db.Column(db.String, nullable=False, server_default=func.now())
    points = db.Column(db.Integer,server_default="0")
    password = db.Column(db.LargeBinary, nullable=False, unique=True)
    
    
    


def selectCustomerByEmail(user_email: str): #change name
        stmt=select(Customer).filter_by(email=user_email)
        userCheck=db.session.execute(stmt).scalar_one_or_none()
        if userCheck is None:
                    return False
        return True

def getPassword(user_email: str): #fix
        stmt=select(Customer).filter_by(email=user_email)
        userCheck=db.session.execute(stmt).scalar_one_or_none()
        return userCheck.password

def saveCustomer(customer: Customer):
        try:
            db.session.add(customer)
            db.session.commit()
            return True
        except IntegrityError as e:
            print(e)
            db.session.rollback()
            return False