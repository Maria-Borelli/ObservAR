from datetime import datetime

from app.models import db


class LogAutenticacao(db.Model):
    __tablename__ = "log_autenticacao"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
    )

    identificador = db.Column(
        db.String(160),
    )

    etapa = db.Column(
        db.String(40),
    )

    sucesso = db.Column(
        db.Boolean,
        nullable=False,
    )

    motivo = db.Column(
        db.String(180),
    )

    ip = db.Column(
        db.String(64),
    )

    criado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )


class LogAcesso(db.Model):
    __tablename__ = "log_acesso"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
    )

    rota = db.Column(
        db.String(180),
    )

    metodo = db.Column(
        db.String(12),
    )

    permitido = db.Column(
        db.Boolean,
        nullable=False,
    )

    criado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )
