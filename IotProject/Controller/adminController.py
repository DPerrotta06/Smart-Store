import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, render_template, request, current_app
from sqlalchemy import func

from Database.db import db
from Model.checkoutModels import Product, StockReception, CartItem  # swap to the merged models later
from Hardware import rfid_reader
from GeneralFunction.adminAuth import requireAdmin

# No session here either: /admin only serves the page. Every /admin/api call needs the admin token.
admin_bp = Blueprint("admin_bp", __name__, template_folder="../View/html")  # CSS comes from customer_bp.static

UPC_RE = re.compile(r"\d{1,13}")
EPC_RE = re.compile(r"[0-9A-F]{22}")
LOW_STOCK = 3   # a product type with this many units or fewer counts as "running low"


def error(message, status=400):
    return jsonify(error=message), status


def clean_epc(value):
    return str(value or "").strip().upper()


def read_type_fields(data):
    """Validate the fields shared by every unit of a type. Returns (fields, error message)."""
    name = str(data.get("name") or "").strip()
    category = str(data.get("category") or "").strip()
    producer = str(data.get("producer_company") or "").strip()
    if not name or len(name) > 100:
        return None, "Enter a product name (100 characters at most)."
    if not category or len(category) > 50:
        return None, "Enter a category (50 characters at most)."
    if not producer or len(producer) > 100:
        return None, "Enter the producer company (100 characters at most)."
    try:
        price = Decimal(str(data.get("price"))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None, "Enter the price as a number, for example 2.50."
    if price < 0 or price > Decimal("100000"):
        return None, "The price must be between 0 and 100000."
    return {"name": name, "category": category, "producer_company": producer, "price": float(price)}, None


def live_units(upc):
    return Product.query.filter_by(upc=upc, active=True)


def representative(upc):
    """The first unit of a type. Receptions point at it."""
    return Product.query.filter_by(upc=upc).order_by(Product.product_id).first()


def type_rows():
    """Active units grouped into product types, in the order they were registered."""
    types = {}
    for unit in Product.query.filter_by(active=True).order_by(Product.product_id):
        t = types.setdefault(unit.upc, {
            "upc": unit.upc, "name": unit.name, "category": unit.category, "price": unit.price,
            "producer_company": unit.producer_company, "in_stock": 0, "epcs": []})
        if not unit.sold:
            t["in_stock"] += 1
        t["epcs"].append({"epc": unit.epc, "sold": bool(unit.sold)})
    return list(types.values())


@admin_bp.route("/admin", methods=["GET"])
def adminPage():
    return render_template("admin.html")


@admin_bp.route("/admin/api/products", methods=["GET"])
@requireAdmin
def list_products():
    return jsonify(products=type_rows())


@admin_bp.route("/admin/api/products", methods=["POST"])
@requireAdmin
def add_product():
    """Register a new product type together with its first unit (one UPC, one EPC) and record it as a reception of 1."""
    data = request.get_json(silent=True) or {}
    fields, problem = read_type_fields(data)
    if problem:
        return error(problem)
    upc, epc = str(data.get("upc") or "").strip(), clean_epc(data.get("epc"))
    if not UPC_RE.fullmatch(upc):
        return error("The UPC must be 1 to 13 digits.")
    if not EPC_RE.fullmatch(epc):
        return error("The EPC must be exactly 22 characters (0-9 and A-F).")
    if live_units(upc).first():
        return error("This UPC is already registered. Use Receive stock to add more units.", 409)
    if Product.query.filter_by(epc=epc).first():
        return error("This EPC is already registered to another unit.", 409)

    unit = Product(upc=upc, epc=epc, sold=False, active=True, **fields)
    db.session.add(unit)
    db.session.flush()
    # the first unit counts as a delivery of 1, so every unit has a reception
    reception = StockReception(stock_quantity=1, date_received=date.today().isoformat(), product_id=unit.product_id)
    db.session.add(reception)
    db.session.flush()
    unit.reception_id = reception.reception_id
    db.session.commit()
    return jsonify(message=f"{fields['name']} added.", products=type_rows()), 201


@admin_bp.route("/admin/api/products/<upc>", methods=["PUT"])
@requireAdmin
def edit_product(upc):
    """Edit a product type. The change applies to every unit that shares the UPC."""
    units = live_units(upc).all()
    if not units:
        return error("That product no longer exists.", 404)
    fields, problem = read_type_fields(request.get_json(silent=True) or {})
    if problem:
        return error(problem)
    for unit in units:
        for key, value in fields.items():
            setattr(unit, key, value)
    db.session.commit()
    return jsonify(message=f"{fields['name']} updated.", products=type_rows())


@admin_bp.route("/admin/api/products/<upc>", methods=["DELETE"])
@requireAdmin
def delete_product(upc):
    """Soft delete: the units stop being sold, and past receipts keep their own copy of the details."""
    units = Product.query.filter_by(upc=upc, active=True).all()
    if not units:
        return error("That product no longer exists.", 404)
    name = units[0].name
    ids = [u.product_id for u in units]
    for unit in units:
        unit.active = False
    # take the deleted units out of any basket that has not been paid
    CartItem.query.filter(CartItem.product_id.in_(ids), CartItem.receipt_id.is_(None)) \
        .delete(synchronize_session=False)
    db.session.commit()
    return jsonify(message=f"{name} deleted.", products=type_rows())


@admin_bp.route("/admin/api/scan", methods=["POST"])
@requireAdmin
def scan_tags():
    """Read every tag on the reader and say which ones are already registered."""
    try:
        _, epcs = rfid_reader.scan_tags()
    except Exception as e:
        current_app.logger.warning("Scanner error: %s", e)
        return error("The reader is not responding. Check the cable and try again.", 500)
    known = {p.epc for p in Product.query.filter(Product.epc.in_(epcs))} if epcs else set()
    return jsonify(epcs=epcs, known=sorted(known))


@admin_bp.route("/admin/api/receive", methods=["POST"])
@requireAdmin
def receive_stock():
    """Record one delivery: one reception row, and one new unit per tag scanned."""
    data = request.get_json(silent=True) or {}
    upc = str(data.get("upc") or "").strip()
    template = live_units(upc).order_by(Product.product_id).first() if UPC_RE.fullmatch(upc) else None
    if template is None:
        return error("No registered product has that UPC. Register it under Products first.", 404)

    try:
        date_received = datetime.strptime(str(data.get("date_received") or ""), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return error("Choose the date the stock was received.")

    epcs = [clean_epc(e) for e in (data.get("epcs") or [])]
    if not epcs:
        return error("Scan at least one tag.")
    if len(set(epcs)) != len(epcs):
        return error("The same tag appears twice in the list.")
    bad = [e for e in epcs if not EPC_RE.fullmatch(e)]
    if bad:
        return error(f"{len(bad)} tag(s) are not valid 22-character EPCs.")
    taken = [p.epc for p in Product.query.filter(Product.epc.in_(epcs))]
    if taken:
        return error(f"{len(taken)} tag(s) are already registered, for example {taken[0]}.", 409)

    reception = StockReception(stock_quantity=len(epcs), date_received=date_received,
                               product_id=representative(upc).product_id)
    db.session.add(reception)
    db.session.flush()
    for epc in epcs:
        db.session.add(Product(upc=upc, epc=epc, name=template.name, category=template.category,
                               price=template.price, producer_company=template.producer_company,
                               sold=False, active=True, reception_id=reception.reception_id))
    db.session.commit()
    return jsonify(message=f"Received {len(epcs)} unit(s) of {template.name}.", products=type_rows()), 201


@admin_bp.route("/admin/api/inventory", methods=["GET"])
@requireAdmin
def inventory():
    types = type_rows()
    receptions = []
    query = (db.session.query(StockReception, Product.upc)
             .join(Product, StockReception.product_id == Product.product_id)
             .order_by(StockReception.date_received.desc(), StockReception.reception_id.desc()))
    names = {t["upc"]: t["name"] for t in types}
    last = {}
    for rec, upc in query:
        last.setdefault(upc, {"date": rec.date_received, "quantity": rec.stock_quantity})
        if upc in names and len(receptions) < 20:
            receptions.append({"date": rec.date_received, "name": names[upc], "upc": upc,
                               "quantity": rec.stock_quantity})
    rows = [{"name": t["name"], "upc": t["upc"], "in_stock": t["in_stock"],
             "last_received": last.get(t["upc"])} for t in types]
    return jsonify(
        stats={"types": len(types), "units": sum(t["in_stock"] for t in types),
               "low": sum(1 for t in types if t["in_stock"] <= LOW_STOCK), "low_limit": LOW_STOCK},
        rows=rows, receptions=receptions)