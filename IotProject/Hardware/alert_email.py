import os
import time
import smtplib
import imaplib
import email
from email.utils import parsedate_to_datetime
from email.message import EmailMessage
from email.header import decode_header
from dotenv import load_dotenv


load_dotenv() #used personal email and don't want to expose myself to the internet on github
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")


#Function sends an email to the admin using the smtplib library.
#Admin must answer with YES (case insensitive) to return true. Anything else returns false.
#The email is sent securely via TLS encryption.
# @param fridge
# @param temp
def send_email(fridge, temp, question="Would you like to turn on the fan? (YES or NO)"):
    payload = EmailMessage()
    payload["Subject"] = f"Temperature Inquiry ({fridge})"
    payload["FROM"] = SENDER_EMAIL
    payload["TO"] = RECEIVER_EMAIL
    payload.set_content(f"The temperature of {fridge} is {temp}°C.\n{question}") 
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls() #Encryption channel for emails
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(payload)
    print("Email sent to recipient!")


#This function handles the receiving the content of the email.
# @param msg
def receive_email(msg):
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
    return ""


# Checks if the admin replied with a YES
# Anything else returns false
# @param fridge
# @param since
def is_yes(fridge, since):
    email_recipient = imaplib.IMAP4_SSL("imap.gmail.com") # read the email from admin inbox
    try:
        email_recipient.login(SENDER_EMAIL, SENDER_PASSWORD)
        email_recipient.select("inbox")
        _, found = email_recipient.search(None, f'(UNSEEN FROM "{RECEIVER_EMAIL}" SUBJECT "Temperature Inquiry ({fridge})")') #ignore the status and sends a search request for the email that was recently sent
        ids = found[0].split()
        if not ids:
            return None
        _, data = email_recipient.fetch(ids[-1], "(RFC822)") #downloads the email that the serach found using the standard email format RFC822
        msg = email.message_from_bytes(data[0][1]) #convert the message of the email sent into bytes so we can determine the response
        sent = parsedate_to_datetime(msg["Date"]).timestamp()
        if sent < since:
            return None
        response = receive_email(msg).strip().split()
        return bool(response) and response[0].strip(".,!").upper() == "YES" # case-insensitive
    finally:
        email_recipient.logout() #cut the session


# Waits for the admin to reply given a set amount of seconds
# If no replywas given then it will return false by default
# @param fridge
# @param timeout
# @param interval
def wait_for_reply(fridge, timeout = 300, interval = 10):
    start = time.time()
    end = start + timeout
    while time.time() < end:
        answer = is_yes(fridge, start)
        if answer is not None:
            return answer
        time.sleep(interval)
    return False

