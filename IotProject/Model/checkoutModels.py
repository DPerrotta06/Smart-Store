"""TEMPORARY stand-in for the teammate's models.

Tables and columns follow Smart_Store_ERD.drawio exactly. Once his branch is
merged, delete this file and point the imports in checkoutController.py at his
model files (same class/column names). Customer is not defined here on purpose:
it comes from his branch.
"""
from sqlalchemy import func

from Database.db import db


class StockReception(db.Model):
    __tablename__ = "Stock_Reception"
    reception_id = db.Column(db.Integer, primary_key=True)
    stock_quantity = db.Column(db.Integer, nullable=False)
    date_received = db.Column(db.String, nullable=False, server_default=func.current_date())
    product_id = db.Column(db.Integer, db.ForeignKey("Product.product_id"), nullable=False)

class Product(db.Model):
    __tablename__ = "Product"
    product_id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String)
    price = db.Column(db.Float, nullable=False)
    epc = db.Column(db.String, unique=True, nullable=False)
    producer_company = db.Column(db.String)
    upc = db.Column(db.String)
    name = db.Column(db.String, nullable=False)
    sold = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    reception_id = db.Column(db.Integer, db.ForeignKey("Stock_Reception.reception_id"), nullable=True)

class Cart(db.Model):
    __tablename__ = "Cart"
    cart_id = db.Column(db.Integer, primary_key=True)
    session_status = db.Column(db.String, nullable=False, default="active")  # active / checked_out
    session_created_at = db.Column(db.String, server_default=func.now())
    membership_number = db.Column(db.Integer, nullable=True)  # FK to Customer once merged
    items = db.relationship("CartItem", backref="cart", cascade="all, delete-orphan")


class CartItem(db.Model):
    __tablename__ = "Cart_Item"
    cart_item_id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("Cart.cart_id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("Product.product_id"), nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False, default=1)
    cart_item_added_at = db.Column(db.String, server_default=func.now())
    unit_price = db.Column(db.Float, nullable=False)  # price at scan time
    receipt_id = db.Column(db.Integer, db.ForeignKey("Receipt.receipt_id"), nullable=True)
    product = db.relationship("Product")