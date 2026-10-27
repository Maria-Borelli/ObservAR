from datetime import datetime

from app.models import db


class AnaliseInterna(db.Model):
    __tablename__ = "analise_interna"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    medicao_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "medicao_qualidade_ar.id"
        ),
    )

    prioridade = db.Column(
        db.String(30),
    )

    parecer = db.Column(
        db.Text,
    )

    recomendacao = db.Column(
        db.Text,
    )

    criada_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
    )

    autor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
    )

    medicao = db.relationship(
        "MedicaoQualidadeAr",
        foreign_keys=[medicao_id],
        backref="analises_internas",
    )

    autor = db.relationship(
        "Usuario",
        foreign_keys=[autor_id],
        backref="analises_internas",
    )
