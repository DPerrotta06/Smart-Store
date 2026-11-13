import time
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from threading import Lock
from flask import Blueprint, jsonify, request, current_app
from Database.db import db
from Model.customerModel import Customer
from Model.receiptModel import Receipt, ReceiptLine
from Model.checkoutModels import Cart, CartItem, Product  # swap to the merged models later
from Hardware import rfid_reader
from GeneralFunction.generalFunction import readToken
from GeneralFunction.cardNumber import isValidCardNumber
from Receipts.receipt_email import send_receipt_email

checkout_bp = Blueprint("checkout_bp", __name__)

POINTS_RATE = Decimal("0.10")  # points earned: 10% of what is paid
POINT_VALUE = Decimal("1.00")  # dollars taken off per point spent

# Wrong membership numbers are limited, so numbers cannot be guessed one after another.
# Kept in memory: nothing is stored about the customer, and a restart clears it.
MAX_WRONG_CARDS = 5
WRONG_CARD_WINDOW = 600   # seconds
_wrong_cards = {}
_wrong_cards_lock = Lock()


def card_lock_seconds(client):
    """Seconds left before this device may try a membership number again (0 = allowed)."""
    now = time.time()
    with _wrong_cards_lock:
        recent = [t for t in _wrong_cards.get(client, []) if now - t < WRONG_CARD_WINDOW]
        _wrong_cards[client] = recent
        return int(WRONG_CARD_WINDOW - (now - recent[0])) + 1 if len(recent) >= MAX_WRONG_CARDS else 0


def note_wrong_card(client):
    with _wrong_cards_lock:
        _wrong_cards.setdefault(client, []).append(time.time())


def mask_email(address):
    name, _, domain = address.partition("@")
    return f"{name[:2]}***@{domain}"


def cents(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def get_active_cart():
    cart = Cart.query.filter_by(session_status="active").first()
    if cart is None:
        cart = Cart(session_status="active")
        db.session.add(cart)
        db.session.commit()
    return cart


def group_items(cart_items):
    """Group the scanned units into one line per product. Every tag is still its own row in the
    database (so each unit can be marked sold), but two cans with the same UPC and price show as
    one line with quantity 2. Order follows the first time each product was scanned."""
    groups = {}
    for item in cart_items:
        key = (item.product.upc, cents(item.unit_price))
        groups.setdefault(key, []).append(item)
    return [{"name": units[0].product.name, "unit_price": key[1], "units": units}
            for key, units in groups.items()]


def cart_payload(cart):
    items, total = [], Decimal("0")
    for group in group_items(cart.items):
        quantity = sum(u.item_quantity for u in group["units"])
        line_total = group["unit_price"] * quantity
        total += line_total
        items.append({"cart_item_id": group["units"][-1].cart_item_id,   # "Remove 1" takes out the latest unit
                      "name": group["name"], "unit_price": float(group["unit_price"]),
                      "quantity": quantity, "line_total": float(line_total)})
    return {"cart_id": cart.cart_id, "items": items, "total": float(cents(total)),
            "points": float(cents(total * POINTS_RATE))}


def add_epc(cart, epc, in_cart):
    """Returns ('added' | 'duplicate' | 'unknown' | 'sold', label)."""
    product = Product.query.filter_by(epc=epc).first()
    if product is None or not product.active:
        return "unknown", epc
    if product.sold:
        return "sold", product.name
    if product.product_id in in_cart:
        return "duplicate", product.name
    db.session.add(CartItem(cart_id=cart.cart_id, product_id=product.product_id,
                            item_quantity=1, unit_price=product.price))
    in_cart.add(product.product_id)
    return "added", product.name


@checkout_bp.route("/api/cart", methods=["GET"])
def get_cart():
    return jsonify(cart_payload(get_active_cart()))


@checkout_bp.route("/api/scan", methods=["POST"])
def scan():
    cart = get_active_cart()
    try:
        _, epcs = rfid_reader.scan_tags()
    except Exception as e:
        current_app.logger.warning("Scanner error: %s", e)
        return jsonify({"error": "The reader is not responding. Check the cable and try again.",
                        **cart_payload(cart)}), 500
    in_cart = {i.product_id for i in cart.items}
    added, unknown, sold = [], [], []
    for epc in epcs:
        outcome, label = add_epc(cart, epc, in_cart)
        if outcome == "added":
            added.append(label)
        elif outcome == "unknown":
            unknown.append(label)
        elif outcome == "sold":
            sold.append(label)
    db.session.commit()
    db.session.refresh(cart)
    return jsonify({"added": added, "unknown": unknown, "sold": sold, **cart_payload(cart)})


@checkout_bp.route("/api/manual_scan", methods=["POST"])
def manual_scan():
    """Testing without the reader. Only works while Flask runs in debug mode."""
    if not current_app.debug:
        return jsonify({"error": "Not available."}), 404
    cart = get_active_cart()
    epc = ((request.get_json(silent=True) or {}).get("epc") or "").strip()
    if not epc:
        return jsonify({"error": "Enter an EPC.", **cart_payload(cart)}), 400
    outcome, label = add_epc(cart, epc, {i.product_id for i in cart.items})
    if outcome != "added":
        msg = {"unknown": f"Tag '{label}' is not in the store catalog.",
               "sold": f"{label} was already sold."}.get(outcome, f"{label} is already in the basket.")
        return jsonify({"error": msg, **cart_payload(cart)}), 400
    db.session.commit()
    db.session.refresh(cart)
    return jsonify({"added": [label], **cart_payload(cart)})


@checkout_bp.route("/api/cart/<int:cart_item_id>", methods=["DELETE"])
def remove_item(cart_item_id):
    cart = get_active_cart()
    item = CartItem.query.filter_by(cart_item_id=cart_item_id, cart_id=cart.cart_id).first()
    if item is None:
        return jsonify({"error": "That item is not in the basket.", **cart_payload(cart)}), 404
    db.session.delete(item)
    db.session.commit()
    db.session.refresh(cart)
    return jsonify(cart_payload(cart))


@checkout_bp.route("/api/pay", methods=["POST"])
def process_payment():
    """Pay for the basket. The membership card is optional.
    With a membership number: the member earns points and the receipt is emailed to them.
    Without one: a guest purchase, with no points and no email.
    Spending points also needs the login token, because a membership number alone is easy to guess."""
    data = request.get_json(silent=True) or {}
    raw = data.get("card_number")
    raw = str(raw).strip() if raw is not None else ""
    use_points = data.get("use_points") is True
    customer = None
    if raw:
        client = request.remote_addr or "unknown"
        wait = card_lock_seconds(client)
        if wait:
            return jsonify({"error": f"Too many wrong membership numbers. Try again in {wait // 60 + 1} minute(s), or pay without a card.",
                            "field": "card_number"}), 429
        if not isValidCardNumber(raw):     # typo or made-up number: caught without asking the database
            note_wrong_card(client)
            return jsonify({"error": "That membership number is not valid. Check the digits.",
                            "field": "card_number"}), 400
        customer = Customer.query.filter_by(card_number=raw).first()
        if customer is None:
            note_wrong_card(client)
            return jsonify({"error": "We could not find that membership number. Check the card, or pay without one.",
                            "field": "card_number"}), 404
    if use_points:
        if customer is None:
            return jsonify({"error": "Enter your membership number to use points.", "field": "points"}), 400
        if readToken(str(data.get("token") or "")) != customer.membership_number:
            return jsonify({"error": "Log in to this membership account to spend its points.",
                            "field": "points"}), 401

    cart = get_active_cart()
    if not cart.items:
        return jsonify({"error": "Your basket is empty."}), 400
    unavailable = [i.product.name for i in cart.items if i.product.sold or not i.product.active]
    if unavailable:
        return jsonify({"error": f"No longer available: {', '.join(unavailable)}. Remove it and try again."}), 409

    subtotal = cents(cart_payload(cart)["total"])
    discount = points_used = Decimal("0.00")
    if use_points:   # all the points they have, but never more than the basket is worth
        balance = Decimal(str(customer.points or 0)).quantize(Decimal("0.01"), ROUND_DOWN)
        discount = min((balance * POINT_VALUE).quantize(Decimal("0.01"), ROUND_DOWN), subtotal)
        points_used = (discount / POINT_VALUE).quantize(Decimal("0.01"), ROUND_HALF_UP)
    paid = subtotal - discount
    earned = cents(paid * POINTS_RATE) if customer else Decimal("0.00")   # points are earned on what was paid
    number = customer.membership_number if customer else None

    receipt = Receipt(total=paid, points_earned=earned, points_used=points_used, discount=discount,
                      membership_number=number)
    db.session.add(receipt)
    db.session.flush()
    for group in group_items(cart.items):
        db.session.add(ReceiptLine(receipt_id=receipt.receipt_id, name=group["name"],
                                   quantity=sum(u.item_quantity for u in group["units"]),
                                   unit_price=group["unit_price"]))
        for unit in group["units"]:
            unit.receipt_id = receipt.receipt_id
            unit.product.sold = True   # this exact unit can never be bought again
    if customer:
        customer.points = float(cents(Decimal(str(customer.points or 0)) - points_used + earned))
    cart.membership_number = number
    cart.session_status = "checked_out"
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Payment failed")
        return jsonify({"error": "Payment failed. Nothing was charged."}), 500
    db.session.refresh(receipt)

    if customer:
        ok, detail = send_receipt_email(receipt)   # goes to the member whose card was used
        if not ok:
            current_app.logger.warning("Receipt email failed: %s", detail)
        email_sent = ok
        email_status = (f"A copy was sent to {mask_email(customer.email)}." if ok
                        else f"Payment complete, but the receipt was not emailed. {detail}")
    else:
        email_sent = None
        email_status = "Paid without a membership card: no points were added and no receipt was emailed."
    return jsonify({
        "message": "Payment complete.",
        "email_sent": email_sent,
        "email_status": email_status,
        "receipt": {"receipt_id": receipt.receipt_id, "purchased_at": str(receipt.purchased_at),
                    "membership_number": receipt.membership_number,
                    "subtotal": float(subtotal), "discount": float(receipt.discount),
                    "points_used": float(receipt.points_used),
                    "total": float(receipt.total), "points_earned": float(receipt.points_earned),
                    "lines": [{"name": l.name, "quantity": l.quantity, "unit_price": float(l.unit_price),
                               "line_total": float(l.unit_price * l.quantity)}
                              for l in receipt.lines]},
    })