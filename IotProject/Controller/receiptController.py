from flask import Blueprint, render_template, session, jsonify
from Model.receiptModel import getCustomerReceipt, getAllCustomerReceipts
from Receipts.receipt_email import send_receipt_email

receipt_bp = Blueprint('receipt_bp', __name__, template_folder='../View/html', static_folder='../View/css')


@receipt_bp.route('/receipt', methods=['GET'])
def receiptHistory():
    membership_number = session.get('membership_number')
    if membership_number is None:
        return jsonify({"error": "User not logged in"}), 401
    receipts = getAllCustomerReceipts(membership_number)
    return render_template('receipt_history.html', receipts=receipts)


@receipt_bp.route('/receipt/<int:receipt_id>/send', methods=['POST'])
def resendReceipt(receipt_id):
    membership_number = session.get('membership_number')
    if membership_number is None:
        return jsonify({"error": "User not logged in"}), 401
    receipt = getCustomerReceipt(membership_number, receipt_id)
    if receipt is None:
        return jsonify({"error": "Receipt not found"}), 404
    ok, message = send_receipt_email(receipt)
    if ok:
        return jsonify({"message": "Receipt sent successfully"}), 200
    return jsonify({"error": message}), 500