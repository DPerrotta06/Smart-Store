from flask import Blueprint, jsonify, render_template, request
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

from Model.customerModel import Customer
from Model.receiptModel import Receipt
from Database.db import db
from Hardware import rfid_reader
from Model.checkoutModels import Cart, CartItem, Product  # swap to teammate's models after merge

checkout_bp = Blueprint("checkout_bp", __name__, template_folder="../View")


# ---------- helpers ----------

def send_receipt_email(receipt, customer_email):
    # Fetch credentials securely from the .env file
    store_email = os.getenv("STORE_EMAIL")
    app_password = os.getenv("APP_PASSWORD")

    try:
        msg = MIMEMultipart()
        msg['From'] = store_email
        msg['To'] = customer_email
        msg['Subject'] = f"Your Receipt from Smart Store (Order #{receipt.receipt_id})"

        body = "Thank you for shopping at Smart Store!\n\n"
        body += "----------------------------------------\n"
        body += f"Total Paid: ${receipt.total:.2f}\n"
        body += f"Points Earned: {receipt.points_earned}\n"
        body += "----------------------------------------\n"
        body += "Items Purchased:\n"
        
        for item in getattr(receipt, 'items', []):
            body += f" - {item.name} (Qty: {item.quantity}) @ ${item.price:.2f}\n"
            
        body += "\nWe hope to see you again soon!"
        
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(store_email, app_password)
        server.send_message(msg)
        server.quit()

        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)

def get_active_cart():
    # The kiosk has one open cart at a time. Reuse it, or open a new one.
    cart = Cart.query.filter_by(session_status="active").first()
    if cart is None:
        cart = Cart(session_status="active")
        db.session.add(cart)
        db.session.commit()
    return cart


def cart_payload(cart):
    items = []
    total = 0.0
    for item in cart.items:
        line_total = round(item.unit_price * item.item_quantity, 2)
        total += line_total
        items.append({
            "cart_item_id": item.cart_item_id,
            "name": item.product.name,
            "unit_price": item.unit_price,
            "quantity": item.item_quantity,
            "line_total": line_total,
        })
    return {"cart_id": cart.cart_id, "items": items, "total": round(total, 2)}


# ---------- pages ----------

@checkout_bp.route("/checkout", methods=["GET"])
def checkout_page():
    return render_template("checkout.html")


# ---------- API used by checkout.html ----------

@checkout_bp.route("/api/cart", methods=["GET"])
def get_cart():
    return jsonify(cart_payload(get_active_cart()))


@checkout_bp.route("/api/scan", methods=["POST"])
def scan():
    # Scan every tag in range at once and add the matching products to the cart.
    try:
        raw_hex, epcs = rfid_reader.scan_tags()
    except Exception as e:
        return jsonify({"error": f"Scanner error: {e}", **cart_payload(get_active_cart())}), 500

    cart = get_active_cart()
    in_cart = {item.product_id for item in cart.items}
    added, unknown = [], []

    for epc in epcs:
        product = Product.query.filter_by(epc=epc).first()
        if product is None:
            unknown.append(epc)
        elif product.product_id not in in_cart:
            db.session.add(CartItem(
                cart_id=cart.cart_id,
                product_id=product.product_id,
                item_quantity=1,
                unit_price=product.price,
            ))
            in_cart.add(product.product_id)
            added.append(product.name)

    db.session.commit()
    db.session.refresh(cart)
    return jsonify({"raw_hex": raw_hex, "added": added, "unknown": unknown, **cart_payload(cart)})


@checkout_bp.route("/api/cart/<int:cart_item_id>", methods=["DELETE"])
def remove_item(cart_item_id):
    cart = get_active_cart()
    item = CartItem.query.filter_by(cart_item_id=cart_item_id, cart_id=cart.cart_id).first()
    if item is None:
        return jsonify({"error": "Item not in cart", **cart_payload(cart)}), 404
    db.session.delete(item)
    db.session.commit()
    db.session.refresh(cart)
    return jsonify(cart_payload(cart))

#Manually inputting items since I dont have the scanner at home

@checkout_bp.route("/api/manual_scan", methods=["POST"])
def manual_scan():
    try:
        data = request.get_json()
        epc = data.get("epc", "").strip()
        
        cart = get_active_cart()
        
        if not epc:
            return jsonify({"error": "Please enter an EPC.", **cart_payload(cart)}), 400

        # Look up the exact EPC in the database
        product = Product.query.filter_by(epc=epc).first()
        
        if product is None:
            # Changed from 404 to 400 so Flask doesn't replace this with an HTML error page
            return jsonify({"error": f"Tag '{epc}' is not in the store catalog.", **cart_payload(cart)}), 400
            
        in_cart = {item.product_id for item in cart.items}
        
        if product.product_id in in_cart:
            return jsonify({"error": f"{product.name} is already in the cart.", **cart_payload(cart)}), 400
            
        # Add the manually entered item to the cart
        db.session.add(CartItem(
            cart_id=cart.cart_id,
            product_id=product.product_id,
            item_quantity=1,
            unit_price=product.price,
        ))
        db.session.commit()
        db.session.refresh(cart)
        
        return jsonify({"added": [product.name], **cart_payload(cart)})
        
    except Exception as e:
        # Catch any unexpected Python crashes and send them as JSON instead of HTML
        return jsonify({"error": f"System error: {str(e)}", **cart_payload(get_active_cart())}), 400


@checkout_bp.route("/api/pay", methods=["POST"])
def process_payment():
    data = request.get_json()
    # Grab the membership number instead of the UUID
    member_num_str = data.get("membership_number", "").strip()
    
    cart = get_active_cart()
    if not cart.items:
        return jsonify({"error": "Cart is empty"}), 400

    total_price = sum(item.unit_price * item.item_quantity for item in cart.items)
    
    purchased_items = [
        {"name": item.product.name, "quantity": item.item_quantity, "price": float(item.unit_price)} 
        for item in cart.items
    ]
    order_summary = {"items": purchased_items, "total": float(total_price)}

    # ==========================================
    # 1. GUEST CHECKOUT
    # ==========================================
    if not member_num_str:
        for item in cart.items:
            db.session.delete(item)
            
        cart.session_status = "checked_out"
        db.session.commit()
        
        return jsonify({
            "message": "Guest payment processed successfully!",
            "email_status": "",
            "order_summary": order_summary
        })

    # ==========================================
    # 2. MEMBER CHECKOUT
    # ==========================================
    # Convert the string from the web form into an integer
    try:
        member_num = int(member_num_str)
    except ValueError:
        return jsonify({"error": "Membership number must be a number."}), 400

    # Search by the primary key (membership_number)
    customer = Customer.query.filter_by(membership_number=member_num).first()
    if not customer:
        return jsonify({"error": f"Membership number {member_num} not found. Check the ID or checkout as guest."}), 404
    
    # Calculate 10% points (Duplication removed)
    points_earned = round(float(total_price) * 0.10, 2)
    customer.points = (customer.points or 0) + points_earned
    db.session.add(customer)

    new_receipt = Receipt(
        total=total_price,
        points_earned=points_earned,
        membership_number=customer.membership_number
    )
    db.session.add(new_receipt)
    db.session.flush()

    class EmailItemMock:
        def __init__(self, name, qty, price):
            self.name = name; self.quantity = qty; self.price = price
            
    email_items = []
    for item in cart.items:
        email_items.append(EmailItemMock(item.product.name, item.item_quantity, float(item.unit_price)))
        item.receipt_id = new_receipt.receipt_id 
        db.session.add(item)
        
    new_receipt.items = email_items
    cart.session_status = "checked_out"
    db.session.commit()

    email_status = "No email on file."
    if customer.email:
        ok, email_msg = send_receipt_email(new_receipt, customer.email)
        email_status = "Receipt emailed!" if ok else f"Email failed: {email_msg}"

    return jsonify({
        "message": "Member payment successful!",
        "email_status": email_status,
        "order_summary": order_summary
    })

@checkout_bp.route("/thank_you", methods=["GET"])
def thank_you_page():
    return render_template("thank_you.html")