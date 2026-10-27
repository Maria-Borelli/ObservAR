from app.models import db


class MedicaoQualidadeAr(db.Model):
    __tablename__ = "medicao_qualidade_ar"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    chave_importacao = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    fonte = db.Column(
        db.String(160),
    )

    data_hora = db.Column(
        db.DateTime,
        index=True,
    )

    iqar = db.Column(
        db.Float,
    )

    concentracao = db.Column(
        db.Float,
    )

    situacao = db.Column(
        db.String(80),
    )

    codigo_flag = db.Column(
        db.String(80),
    )

    descricao_flag = db.Column(
        db.Text,
    )

    situacao_iqar = db.Column(
        db.String(80),
    )

    estacao_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "estacao_monitoramento.id"
        ),
    )

    parametro_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "parametro_monitorado.id"
        ),
    )

    importacao_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "historico_importacao.id"
        ),
        nullable=True,
        index=True,
    )

    estacao = db.relationship(
        "EstacaoMonitoramento",
        backref="medicoes",
    )

    parametro = db.relationship(
        "ParametroMonitorado",
        backref="medicoes",
    )
