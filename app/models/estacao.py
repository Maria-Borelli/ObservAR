from app.models import db


class EstacaoMonitoramento(db.Model):
    __tablename__ = "estacao_monitoramento"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    id_oficial = db.Column(
        db.String(80),
        unique=True,
    )

    codigo = db.Column(
        db.String(80),
    )

    nome = db.Column(
        db.String(180),
        nullable=False,
    )

    latitude = db.Column(
        db.Float,
    )

    longitude = db.Column(
        db.Float,
    )

    situacao = db.Column(
        db.String(60),
    )

    municipio_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "municipio.id"
        ),
    )

    criado_por_importacao_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "historico_importacao.id"
        ),
        nullable=True,
        index=True,
    )

    municipio = db.relationship(
        "Municipio",
        backref="estacoes",
    )
