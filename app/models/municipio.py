from app.models import db


class Municipio(db.Model):
    __tablename__ = "municipio"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    id_oficial = db.Column(
        db.String(40),
        unique=True,
    )

    nome = db.Column(
        db.String(160),
        nullable=False,
        index=True,
    )

    criado_por_importacao_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "historico_importacao.id"
        ),
        nullable=True,
        index=True,
    )
