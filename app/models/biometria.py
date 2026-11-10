from datetime import datetime

from app.models import db


class BiometriaFacial(db.Model):
    __tablename__ = "biometria_facial"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False,
    )

    backend = db.Column(
        db.String(40),
        nullable=False,
    )

    template = db.Column(
        db.LargeBinary,
        nullable=False,
    )

    criada_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    ativa = db.Column(
        db.Boolean,
        default=True,
    )
