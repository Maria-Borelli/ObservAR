from app.models import db


class ParametroMonitorado(db.Model):
    __tablename__ = "parametro_monitorado"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nome = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
    )

    codigo_normalizado = db.Column(
        db.String(80),
    )

    criado_por_importacao_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "historico_importacao.id"
        ),
        nullable=True,
        index=True,
    )
