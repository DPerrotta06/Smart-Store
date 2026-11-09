from flask import Blueprint, jsonify, render_template

from Database.db import db
from Hardware import rfid_reader
from Model.checkoutModels import Cart, CartItem, Product  # swap to teammate's models after merge

checkout_bp = Blueprint("checkout_bp", __name__, template_folder="../View")


# ---------- helpers ----------

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