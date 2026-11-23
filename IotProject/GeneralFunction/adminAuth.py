"""Admin access without a session.

Who is an admin is decided by the Admin table (listed = admin). An admin logs in with their normal
customer account; the login returns a signed token that the admin page keeps in memory and sends back
in the Authorization header. Every admin request checks the table again, so removing someone
from the table works immediately."""
from functools import wraps

from flask import current_app, jsonify, request
from itsdangerous import URLSafeTimedSerializer, BadSignature

from Model.adminModel import isAdmin

MAX_AGE_SECONDS = 3600


def _serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="admin-login")


def issueAdminToken(membership_number):
    return _serializer().dumps(membership_number)


def readAdminToken(token):
    """The membership number inside a valid, unexpired admin token, or None."""
    try:
        return _serializer().loads(token, max_age=MAX_AGE_SECONDS)
    except BadSignature:  # also covers expired tokens
        return None


def requireAdmin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        number = readAdminToken(header[7:]) if header.startswith("Bearer ") else None
        if number is None or not isAdmin(number):
            return jsonify(error="Admin login required."), 401
        return view(*args, **kwargs)
    return wrapper