from datetime import datetime

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app.models import db


class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nome = db.Column(
        db.String(120),
        nullable=False,
    )

    login = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True,
    )

    email = db.Column(
        db.String(160),
        unique=True,
    )

    senha_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    ativo = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )

    perfil_id = db.Column(
        db.Integer,
        db.ForeignKey("perfil.id"),
        nullable=False,
    )

    criado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    perfil = db.relationship(
        "Perfil",
        backref="usuarios",
    )

    biometrias = db.relationship(
        "BiometriaFacial",
        backref="usuario",
        cascade="all, delete-orphan",
    )

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(
            senha
        )

    def check_password(self, senha):
        return check_password_hash(
            self.senha_hash,
            senha,
        )
