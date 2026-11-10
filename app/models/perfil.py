from app.models import db


class Perfil(db.Model):
    __tablename__ = "perfil"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nome = db.Column(
        db.String(80),
        nullable=False,
    )

    nivel = db.Column(
        db.Integer,
        unique=True,
        nullable=False,
    )
