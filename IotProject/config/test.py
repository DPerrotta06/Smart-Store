import uuid
from sqlalchemy import select
from app import app                                   # adjust
from Database.db import db
from Model.customerModel import Customer, saveCustomer
from Model.receiptModel import (Receipt, saveCustomerReceipt,
                                getCustomerReceipt, getAllCustomerReceipts)
from Receipt.receipt_email import send_receipt_email

TEST_EMAIL = "your.own.address@gmail.com"

with app.app_context():
    # 1. customer
    customer = db.session.execute(
        select(Customer).filter_by(email=TEST_EMAIL)).scalar_one_or_none()
    if customer is None:
        customer = Customer(first_name="Test", last_name="User",
                            tel_number="514-555-0000", email=TEST_EMAIL,
                            customer_address="123 Test St",
                            customer_uuid=str(uuid.uuid4()),
                            points=0, password="not-a-real-hash")
        assert saveCustomer(customer), "could not save customer"
    mn = customer.membership_number
    print("customer membership_number:", mn)

    # 2. write
    receipt = Receipt(membership_number=mn, total=12.50, points_earned=12)
    assert saveCustomerReceipt(receipt), "could not save receipt"
    rid = receipt.receipt_id
    print("saved receipt:", rid)

    # 3. read
    assert getCustomerReceipt(mn, rid) is not None, "owner can't read own receipt"
    assert getCustomerReceipt(999999, rid) is None, "ownership check failed"
    assert len(getAllCustomerReceipts(mn)) >= 1
    print("read tests passed")

    # 4. email
    ok, msg = send_receipt_email(receipt)
    print("email:", ok, msg)

    # 5. routes
    client = app.test_client()
    assert client.post(f"/receipt/{rid}/send").status_code == 401   # not logged in

    with client.session_transaction() as s:
        s["membership_number"] = mn                                  # fake login

    r = client.post(f"/receipt/{rid}/send")
    print("resend route:", r.status_code, r.get_json())              # expect 200
    assert client.post("/receipt/999999/send").status_code == 404    # not found

    # r = client.get("/receipt")   # uncomment once receipt_history.html exists
    # assert r.status_code == 200