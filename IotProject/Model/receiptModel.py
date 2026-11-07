from Database.db import db
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError

class Receipt(db.Model):
    __tablename__ = "Receipt"
    receipt_id=db.Column(db.Integer, primary_key=True)
    total=db.Column(db.Integer, nullable=False)
    points_earned=db.Column(db.Numeric, nullable=False)
    purchased_at=db.Column(db.Text, nullable=False, server_default= func.now())
    membership_number=db.Column(db.Integer, nullable=False, foreign_key=True)

def saveCustomerReceipt(receipt: Receipt):
    try:
        db.session.add(receipt)
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False

def getCustomerReceipt(membership_number: int, receipt_id: int):
    stmt=select(Receipt).filter_by()