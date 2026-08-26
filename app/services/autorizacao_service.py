from functools import wraps
from flask import session, redirect, url_for, abort
from app.models import Usuario
from .auditoria_service import access_log
def current_user():
    uid=session.get("user_id")
    return Usuario.query.get(uid) if uid else None
def login_required(fn):
    @wraps(fn)
    def inner(*a,**k):
        u=current_user()
        if not u: return redirect(url_for("auth.login"))
        return fn(*a,**k)
    return inner
def require_level(level):
    def deco(fn):
        @wraps(fn)
        def inner(*a,**k):
            u=current_user()
            if not u: return redirect(url_for("auth.login"))
            if not u.ativo or u.perfil.nivel < level:
                access_log(u.id, False); abort(403)
            access_log(u.id, True)
            return fn(*a,**k)
        return inner
    return deco
