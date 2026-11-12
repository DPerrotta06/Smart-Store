from flask import Blueprint, request, redirect, render_template, url_for, jsonify
from Model.customerModel import Customer, saveCustomer, selectCustomerByEmail
from Model.receiptModel import getAllCustomerReceipts
from GeneralFunction.generalFunction import normalizeEmail
from GeneralFunction.generalFunction import issueToken
from GeneralFunction.cardNumber import newCardNumber
from Database.db import db
from GeneralFunction.adminAuth import issueAdminToken
from Model.adminModel import isAdmin
import re
import bcrypt

# No Flask session: the store is a physical kiosk. Nothing is remembered between
# requests. A customer logs in on the page, the page holds the result in memory,
# and a reload, a log out or the idle timeout clears it.

customer_bp = Blueprint('customer_bp', __name__, template_folder='../View/html', static_folder='../View/css')

PATTERN_NAME = r"^[A-Z][a-z]+$"
PATTERN_PASSWORD = r"(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]).{8,30}"
PATTERN_TEL = r"^\d{3}-\d{3}-\d{4}$"
PATTERN_EMAIL = r"^(?=.{6,30}@)[a-zA-Z0-9]+(?:\.[a-z0-9]+)*@gmail\.com$"

MSG_EMAIL = "The email is incorrect: example.ch05@gmail.com or example@gmail.com\n"
MSG_PASSWORD = "8-30 characters, with at least one lowercase letter, one uppercase letter and one number\n"


def fail(message, status=400):
    return jsonify(ok=False, message=message.strip()), status


def freshCardNumber():
    """A random membership card number that no one else has."""
    while True:
        number = newCardNumber()
        if not Customer.query.filter_by(card_number=number).first():
            return number


@customer_bp.route('/', methods=['GET'])
@customer_bp.route('/store', methods=['GET'])
def showingform():
    return render_template('store.html')


# Kept so url_for() calls elsewhere in the project do not break. The dialogs live on the store page.
@customer_bp.route('/main', methods=['GET'])
@customer_bp.route('/login', methods=['GET'])
@customer_bp.route('/signup', methods=['GET'])
@customer_bp.route('/logout', methods=['GET', 'POST'])
def mainPage():
    return redirect(url_for('customer_bp.showingform'))


@customer_bp.route('/login', methods=['POST'])
def loginPage():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    message = ""
    if not re.fullmatch(PATTERN_EMAIL, email):
        message += MSG_EMAIL
    if not re.fullmatch(PATTERN_PASSWORD, password):
        message += MSG_PASSWORD
    if message:
        return fail(message)

    customer = Customer.query.filter_by(email=normalizeEmail(email)).first()
    if customer is None:
        return fail("Email does not exist")
    if not bcrypt.checkpw(password.encode('utf-8'), customer.password):
        return fail("Incorrect Password")

    # Customers listed in the Admin table go to the admin page. Everyone else gets the store.
    if isAdmin(customer.membership_number):
        return jsonify(ok=True, admin=True, token=issueAdminToken(customer.membership_number), url='/admin')

    if not customer.card_number:      # accounts made before card numbers existed get one at their next login
        customer.card_number = freshCardNumber()
        db.session.commit()
    receipts = getAllCustomerReceipts(customer.membership_number)
    return jsonify(
        ok=True,
        token=issueToken(customer.membership_number),
        customer={
            "membership_number": customer.membership_number,
            "card_number": customer.card_number,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "points": float(customer.points or 0),
        },
        receipts=[{
            "receipt_id": r.receipt_id,
            "purchased_at": str(r.purchased_at),
            "total": float(r.total),
            "points_earned": float(r.points_earned),
        } for r in receipts],
    )


@customer_bp.route('/signup', methods=['POST'])
def signupPage():
    print(1)
    data = request.get_json(silent=True) or {}
    field = lambda name: (data.get(name) or '').strip()
    first_name, last_name = field('first_name'), field('last_name')
    tel_number, email = field('tel_number'), field('email')
    customer_address = field('customer_address')
    password = data.get('password') or ''

    message = ""
    if not re.fullmatch(PATTERN_NAME, first_name):
        message += "The first name is incorrect: Only Letters\n"
    if not re.fullmatch(PATTERN_NAME, last_name):
        message += "The last name is incorrect: Only Letters\n"
    if not re.fullmatch(PATTERN_TEL, tel_number):
        message += "The telephone is incorrect: 111-111-1111\n"
    if not re.fullmatch(PATTERN_EMAIL, email):
        message += MSG_EMAIL
    if not re.fullmatch(PATTERN_PASSWORD, password):
        message += MSG_PASSWORD
    if not customer_address:
        message += "The address is required\n"
    if message:
        return fail(message)
    print(2)


    emailNormalized = normalizeEmail(email)
    if selectCustomerByEmail(emailNormalized):
        return fail("Customer already exists")
    print(3)

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    card_number = freshCardNumber()
    saved = saveCustomer(Customer(first_name=first_name, last_name=last_name, tel_number=tel_number,
                                  email=emailNormalized, customer_address=customer_address,
                                  password=hashed_password, card_number=card_number))
    print(4)
    if not saved:
        return fail("Could not create the account. Try again.", 500)
    return jsonify(ok=True, message=f"Account created. Your membership number is {card_number}."), 201