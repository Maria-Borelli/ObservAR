from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


db = SQLAlchemy()


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