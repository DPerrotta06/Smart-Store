import smtplib
import imaplib
import email
from email.message import EmailMessage
from email.header import decode_header

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "" #REMOVE AFTER
SENDER_PASSWORD = "" #FILL IN LATER
RECEIVER_EMAIL = ""


def send_email(fridge, temp):
    payload = EmailMessage()
    payload["Subject"] = "Tempearture Inquiry"
    payload["FROM"] = SENDER_EMAIL
    payload["TO"] = RECEIVER_EMAIL
    payload.set_content(f"The temperature of {fridge} is {temp}°C.\nWould you like to turn on the fan? (YES or NO)") 
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls() #Encryption channel for emails
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(payload)
    print("Email sent to recipient!")
   

def read_latest_email():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(SENDER_EMAIL, SENDER_PASSWORD)
    mail.select("inbox")
    status, messages = mail.search(None, "ALL")
    latest_id = messages[0].split()[-1]
    status, msg_data = mail.fetch(latest_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8")
    from_ = msg.get("From")
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
    print("-------------------------")
    print(f"From:    {from_}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print("-------------------------")
    mail.logout()

def is_yes():
    print()


def wait_for_reply():
    print()

try:
    send_email()
    read_latest_email()
except Exception as e:
    print(f"Error: {e}")