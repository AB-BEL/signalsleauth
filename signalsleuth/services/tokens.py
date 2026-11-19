"""Signed bearer tokens for the mobile/SPA client."""
from flask import current_app, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .. import db

TOKEN_MAX_AGE = 60 * 60 * 24 * 14  # 14 days


def serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="signalsleuth-mobile")


def issue_token(user_id):
    return serializer().dumps({"uid": int(user_id)})


def user_from_token():
    """Resolve student from Bearer token or existing session."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            data = serializer().loads(token, max_age=TOKEN_MAX_AGE)
            return db.get_user(data["uid"])
        except (BadSignature, SignatureExpired, KeyError, TypeError):
            return None
    uid = session.get("user_id")
    if uid and session.get("role") != "admin":
        return db.get_user(uid)
    return None
