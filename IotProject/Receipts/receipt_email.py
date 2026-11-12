import os
import smtplib
from email.message import EmailMessage
from html import escape
#from dotenv import load_dotenv
from Database.db import db
from Model.customerModel import Customer
from Model.receiptModel import Receipt

#load_dotenv()
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "shon.ch05@gmail.com"#os.getenv("SENDER_EMAIL")
SENDER_PASSWORD =  ""#os.getenv("SENDER_PASSWORD")

def _build_bodies(customer, receipt, items):
    text = [
        f"Thank you for your purchase {customer.first_name} {customer.last_name}!", "",
        f"Receipt ID: {receipt.receipt_id}", "",
        f"{receipt.purchased_at}"
    ]
    table_rows = ""
    for name, quantity, price in items:
        table_rows += f"<tr><td>{escape(name)}</td><td>{quantity}</td><td>${price:.2f}</td></tr>"
    text += [
        "", 
        f"Total: ${receipt.total:.2f}", 
        f"Points Earned: {receipt.points_earned:.2f}", 
         f"Total Points: {customer.points}"
    ]
    html = f"""
    <h2>Thank you for your purchase, {escape(customer.first_name)}!</h2>
    <p>Receipt #{receipt.receipt_id} &mdash; {escape(str(receipt.purchased_at))}</p>
    <table cellpadding="6" cellspacing="0" border="1" style="border-collapse:collapse">
      <tr><th>Item</th><th>Qty</th><th>Price</th></tr>{table_rows}
    </table>
    <p><b>Total: ${receipt.total:.2f}</b><br>
    Points earned: {receipt.points_earned}<br>
    Total points: {customer.points}</p>"""
    return "\n".join(text), html
    
def send_receipt_email(receipt: Receipt):
    customer = db.session.get(Customer, receipt.membership_number)
    if not customer:
        return False, "Customer not found"
    items = [(item.name, item.quantity, item.unit_price) for item in receipt.lines]
    text_body, html_body = _build_bodies(customer, receipt, items)
    
    msg = EmailMessage()
    msg['Subject'] = f"Your Receipt #{receipt.receipt_id}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = customer.email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL,SENDER_PASSWORD)
            server.send_message(msg)
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)
