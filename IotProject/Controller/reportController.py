
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from Database.db import db
from Model.customerModel import Customer
from Model.receiptModel import Receipt, ReceiptLine
from Model.checkoutModels import CartItem, Product   
from GeneralFunction.adminAuth import requireAdmin
from GeneralFunction.generalFunction import readToken

report_bp = Blueprint("report_bp", __name__)

MAX_DAYS = 366   # longest range a report accepts

local_time = func.datetime(Receipt.purchased_at, "localtime")
local_day = func.date(Receipt.purchased_at, "localtime")


def error(message, status=400):
    return jsonify(error=message), status


def money(value):
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def read_range():
    """(start, end) dates from ?start=YYYY-MM-DD&end=YYYY-MM-DD, or an error message.
    One day is start = end. With nothing given: the last 30 days, today included."""
    today = date.today()
    try:
        end = datetime.strptime(request.args.get("end") or today.isoformat(), "%Y-%m-%d").date()
        start = datetime.strptime(request.args.get("start") or (end - timedelta(days=29)).isoformat(), "%Y-%m-%d").date()
    except ValueError:
        return None, None, "Dates must look like 2026-11-25."
    if start > end:
        return None, None, "The start date is after the end date."
    if (end - start).days >= MAX_DAYS:
        return None, None, f"Choose a range of {MAX_DAYS} days or less."
    return start, end, None


def days_between(start, end):
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def in_range(query, start, end):
    return query.filter(local_day >= start.isoformat(), local_day <= end.isoformat())


# ------------------------------------------------------------------ admin: sales

@report_bp.route("/admin/api/reports/sales", methods=["GET"])
@requireAdmin
def sales_report():
    """Units sold per product, best and worst sellers, and revenue per day, for a date range.
    Each sold unit is a Cart_Item row linked to its receipt, so products are grouped by UPC."""
    start, end, msg = read_range()
    if msg:
        return error(msg)

    rows = in_range(db.session.query(Product.upc, func.max(Product.name), func.max(Product.category),
                                     func.sum(CartItem.item_quantity),
                                     func.sum(CartItem.item_quantity * CartItem.unit_price))
                    .join(CartItem, CartItem.product_id == Product.product_id)
                    .join(Receipt, CartItem.receipt_id == Receipt.receipt_id), start, end) \
        .group_by(Product.upc).all()
    products = sorted(({"upc": upc, "name": name, "category": category, "sold": int(qty or 0),
                        "revenue": money(rev)} for upc, name, category, qty, rev in rows),
                      key=lambda p: (-p["sold"], p["name"]))

    # Products still in the catalog that sold nothing in this period
    sold_upcs = {p["upc"] for p in products}
    unsold = sorted({name for upc, name in db.session.query(Product.upc, Product.name)
                     .filter(Product.active == True).distinct() if upc not in sold_upcs})   # noqa: E712

    most = least = []
    if products:
        top, bottom = products[0]["sold"], products[-1]["sold"]
        most = [p["name"] for p in products if p["sold"] == top]
        least = [p["name"] for p in products if p["sold"] == bottom]

    per_day = {d: {"date": d, "revenue": 0.0, "receipts": 0, "units": 0} for d in days_between(start, end)}
    for day, total, count in in_range(db.session.query(local_day, func.sum(Receipt.total), func.count(Receipt.receipt_id)),
                                      start, end).group_by(local_day):
        per_day[day].update(revenue=money(total), receipts=int(count))
    for day, units in in_range(db.session.query(local_day, func.sum(CartItem.item_quantity))
                               .join(CartItem, CartItem.receipt_id == Receipt.receipt_id), start, end).group_by(local_day):
        per_day[day]["units"] = int(units or 0)
    days = list(per_day.values())

    totals = in_range(db.session.query(func.count(Receipt.receipt_id), func.sum(Receipt.subtotal),
                                       func.sum(Receipt.gst), func.sum(Receipt.qst),
                                       func.sum(Receipt.discount), func.sum(Receipt.total)), start, end).one()
    return jsonify(
        start=start.isoformat(), end=end.isoformat(),
        products=products, unsold=unsold,
        most_sold={"names": most, "units": products[0]["sold"] if products else 0},
        least_sold={"names": least, "units": products[-1]["sold"] if products else 0},
        days=days,
        totals={"receipts": int(totals[0] or 0), "units": sum(p["sold"] for p in products),
                "subtotal": money(totals[1]), "gst": money(totals[2]), "qst": money(totals[3]),
                "discount": money(totals[4]), "revenue": money(totals[5])},
    )


# ------------------------------------------------------------------ admin: customers

@report_bp.route("/admin/api/reports/customers", methods=["GET"])
@requireAdmin
def customer_report():
    """How many members bought, new vs returning, and the busiest and quietest days.
    New = their first purchase ever is inside the range. Returning = they had bought before it."""
    start, end, msg = read_range()
    if msg:
        return error(msg)

    buyers = {n for (n,) in in_range(db.session.query(Receipt.membership_number).distinct(), start, end)
              .filter(Receipt.membership_number.isnot(None))}
    first_day = dict(db.session.query(Receipt.membership_number, func.min(local_day))
                     .filter(Receipt.membership_number.in_(buyers)).group_by(Receipt.membership_number)) if buyers else {}
    new = [n for n in buyers if first_day.get(n, "") >= start.isoformat()]

    per_day = {d: {"date": d, "customers": 0, "receipts": 0} for d in days_between(start, end)}
    for day, customers, receipts in in_range(db.session.query(local_day, func.count(Receipt.membership_number.distinct()),
                                                              func.count(Receipt.receipt_id)), start, end).group_by(local_day):
        per_day[day].update(customers=int(customers), receipts=int(receipts))
    days = list(per_day.values())

    busiest = quietest = {"dates": [], "customers": 0}
    if days:
        hi, lo = max(d["customers"] for d in days), min(d["customers"] for d in days)
        busiest = {"dates": [d["date"] for d in days if d["customers"] == hi], "customers": hi}
        quietest = {"dates": [d["date"] for d in days if d["customers"] == lo], "customers": lo}

    # top customers in the range, by money spent
    top = (in_range(db.session.query(Customer.first_name, Customer.last_name, Customer.card_number,
                                     func.count(Receipt.receipt_id), func.sum(Receipt.total))
                    .join(Customer, Customer.membership_number == Receipt.membership_number), start, end)
           .group_by(Customer.membership_number).order_by(func.sum(Receipt.total).desc()).limit(10).all())
    return jsonify(
        start=start.isoformat(), end=end.isoformat(),
        totals={"customers": len(buyers), "new": len(new), "returning": len(buyers) - len(new)},
        busiest=busiest, quietest=quietest, days=days,
        top_customers=[{"name": f"{f} {l}", "card_number": c, "visits": int(v), "spent": money(s)}
                       for f, l, c, v, s in top],
    )


# ------------------------------------------------------------------ customer side

def member_or_error():
    """The logged-in member from 'Authorization: Bearer <token>', or (None, error reply)."""
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    number = readToken(token)
    customer = db.session.get(Customer, number) if number else None
    if customer is None:
        return None, error("Log in again to see your purchases.", 401)
    return customer, None


def receipt_json(r):
    return {"receipt_id": r.receipt_id, "purchased_at": r.local_time,
            "subtotal": money(r.Receipt.subtotal), "gst": money(r.Receipt.gst), "qst": money(r.Receipt.qst),
            "discount": money(r.Receipt.discount), "points_used": money(r.Receipt.points_used),
            "points_earned": money(r.Receipt.points_earned), "total": money(r.Receipt.total),
            "lines": [{"name": l.name, "quantity": l.quantity, "unit_price": money(l.unit_price),
                       "line_total": money(l.unit_price * l.quantity)} for l in r.Receipt.lines]}


@report_bp.route("/api/me/receipts", methods=["GET"])
def my_receipts():
    """The member's receipts in a date range, with items, the total spent and spending per day."""
    customer, fail = member_or_error()
    if fail:
        return fail
    start, end, msg = read_range()
    if msg:
        return error(msg)
    rows = in_range(db.session.query(Receipt, local_time.label("local_time"), Receipt.receipt_id)
                    .filter(Receipt.membership_number == customer.membership_number), start, end) \
        .order_by(Receipt.purchased_at.desc()).all()
    receipts = [receipt_json(r) for r in rows]
    per_day = {d: 0.0 for d in days_between(start, end)}
    for r in receipts:
        day = r["purchased_at"][:10]
        per_day[day] = round(per_day.get(day, 0) + r["total"], 2)
    return jsonify(start=start.isoformat(), end=end.isoformat(), receipts=receipts,
                   total_spent=money(sum(r["total"] for r in receipts)),
                   days=[{"date": d, "spent": v} for d, v in per_day.items()])


@report_bp.route("/api/me/item_search", methods=["GET"])
def my_item_search():
    """Every time the member bought an item whose name contains the search text:
    how many times, when, and at what price (for the price history / inflation chart)."""
    customer, fail = member_or_error()
    if fail:
        return fail
    q = (request.args.get("q") or "").strip()[:100]
    if len(q) < 2:
        return error("Type at least 2 letters of the item's name.")
    safe = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = (db.session.query(ReceiptLine, local_time.label("local_time"))
            .join(Receipt, Receipt.receipt_id == ReceiptLine.receipt_id)
            .filter(Receipt.membership_number == customer.membership_number,
                    ReceiptLine.name.ilike(f"%{safe}%", escape="\\"))
            .order_by(Receipt.purchased_at, ReceiptLine.line_id).all())
    items = {}
    for line, when in rows:
        item = items.setdefault(line.name, {"name": line.name, "times": 0, "quantity": 0, "purchases": []})
        item["times"] += 1
        item["quantity"] += line.quantity
        item["purchases"].append({"purchased_at": when, "receipt_id": line.receipt_id,
                                  "quantity": line.quantity, "unit_price": money(line.unit_price)})
    for item in items.values():
        prices = [p["unit_price"] for p in item["purchases"]]
        first = prices[0]
        item["first_price"], item["last_price"] = first, prices[-1]
        item["change"] = round(prices[-1] - first, 2)
        item["change_percent"] = round((prices[-1] - first) / first * 100, 1) if first else 0.0
        for p in item["purchases"]:
            p["change_from_first"] = round(p["unit_price"] - first, 2)
    return jsonify(query=q, items=sorted(items.values(), key=lambda i: (-i["times"], i["name"])))