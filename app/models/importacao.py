from datetime import datetime

from app.models import db


class HistoricoImportacao(db.Model):
    __tablename__ = "historico_importacao"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    nome_arquivo = db.Column(
        db.String(255),
        nullable=False,
    )

    hash_arquivo = db.Column(
        db.String(64),
        nullable=False,
        index=True,
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=True,
        index=True,
    )

    status = db.Column(
        db.String(40),
        nullable=False,
        index=True,
    )

    iniciada_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    concluida_em = db.Column(
        db.DateTime,
        nullable=True,
    )

    total_linhas = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    linhas_processadas = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    registros_importados = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    duplicados = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    conflitos = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    erros = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    lotes_processados = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    tempo_segundos = db.Column(
        db.Float,
        nullable=True,
    )

    mensagem = db.Column(
        db.Text,
        nullable=True,
    )

    cancelamento_solicitado = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    cancelamento_solicitado_em = db.Column(
        db.DateTime,
        nullable=True,
    )

    cancelado_em = db.Column(
        db.DateTime,
        nullable=True,
    )

    cancelado_por_usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=True,
        index=True,
    )

    registros_removidos = db.Column(
        db.Integer,
        default=0,
        nullable=False,
    )

    erro_cancelamento = db.Column(
        db.Text,
        nullable=True,
    )

    usuario = db.relationship(
        "Usuario",
        foreign_keys=[
            usuario_id
        ],
        backref="importacoes",
    )

    cancelado_por = db.relationship(
        "Usuario",
        foreign_keys=[
            cancelado_por_usuario_id
        ],
    )
