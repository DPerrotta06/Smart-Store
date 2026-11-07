import os
import time
import smtplib
import imaplib
import email
from email.utils import parsedate_to_datetime
from email.message import EmailMessage
from email.header import decode_header
from dotenv import load_dotenv

