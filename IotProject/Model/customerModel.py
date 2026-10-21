from Database.db import db
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from GeneralFunction.generalFunction import normalizeEmail



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
    


def selectCustomerByEmail(user_email: str):
        stmt=select(Customer).filter_by(email=user_email)
        userCheck=db.session.execute(stmt).scalar_one_or_none()
        if userCheck is None:
                    return False
        return True

def saveCustomer(customer: Customer):
        try:
            db.session.add(customer)
            db.session.commit()
            return True
        except IntegrityError:
            db.session.rollback()
            return False





        