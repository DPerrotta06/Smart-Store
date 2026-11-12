from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature

MAX_AGE_SECONDS = 600

def normalizeEmail(email: str):
    usernamePart,domainPart=email.split('@',1)
    if "." in usernamePart:
        usernamePartClean=usernamePart.replace(".","")
        cleanEmail=f"{usernamePartClean}@{domainPart}"
        return cleanEmail.lower()
    return email.lower()



def _serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="member-login")


def issueToken(membership_number):
    return _serializer().dumps(membership_number)


def readToken(token):
    """The membership number inside a valid, unexpired token, or None."""
    try:
        return _serializer().loads(token, max_age=MAX_AGE_SECONDS)
    except BadSignature:  # also covers expired tokens
        return None

        
    
