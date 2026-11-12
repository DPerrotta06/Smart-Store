from Database.db import db
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


class Receipt(db.Model):
    __tablename__ = "Receipt"
    receipt_id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    points_earned = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    points_used = db.Column(db.Numeric(10, 2), nullable=False, default=0)  
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)      
    purchased_at = db.Column(db.Text, nullable=False, server_default=func.now())
    membership_number = db.Column(db.Integer, db.ForeignKey("Customer.membership_number"), nullable=True)
    lines = db.relationship("ReceiptLine", backref="receipt", cascade="all, delete-orphan",
                            order_by="ReceiptLine.line_id")


class ReceiptLine(db.Model):
    """What was bought, copied at payment time so a receipt never changes when a product does."""
    __tablename__ = "Receipt_Line"
    line_id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("Receipt.receipt_id"), nullable=False)
    name = db.Column(db.String, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)


def saveCustomerReceipt(receipt: Receipt):
    try:
        db.session.add(receipt)
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False

def getCustomerReceipt(membership_number: int, receipt_id: int):
    stmt = select(Receipt).filter_by(membership_number=membership_number, receipt_id=receipt_id)
    return db.session.execute(stmt).scalar_one_or_none()

def getAllCustomerReceipts(membership_number: int):
    stmt = select(Receipt).filter_by(membership_number=membership_number).order_by(Receipt.purchased_at.desc())
    return db.session.execute(stmt).scalars().all()