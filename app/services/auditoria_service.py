from flask import request
from app.models import db, LogAutenticacao, LogAcesso
def auth_log(user_id, identificador, etapa, sucesso, motivo=""):
    db.session.add(LogAutenticacao(usuario_id=user_id, identificador=identificador[:160], etapa=etapa, sucesso=sucesso, motivo=motivo[:180], ip=request.remote_addr))
    db.session.commit()
def access_log(user_id, permitido=True):
    db.session.add(LogAcesso(usuario_id=user_id, rota=request.path, metodo=request.method, permitido=permitido)); db.session.commit()
