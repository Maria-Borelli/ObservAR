from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.models import (
    EstacaoMonitoramento,
    MedicaoQualidadeAr,
    Municipio,
    db,
)


def total_estacoes():
    """Retorna a quantidade de estações cadastradas."""
    return (
        db.session.query(
            func.count(EstacaoMonitoramento.id)
        )
        .scalar()
        or 0
    )


def total_municipios():
    """Retorna a quantidade de municípios cadastrados."""
    return (
        db.session.query(
            func.count(Municipio.id)
        )
        .scalar()
        or 0
    )


def total_medicoes():
    """Retorna a quantidade de medições importadas."""
    return (
        db.session.query(
            func.count(MedicaoQualidadeAr.id)
        )
        .scalar()
        or 0
    )


def resumo_dashboard():
    """Retorna os totais utilizados nos cards do dashboard."""
    return {
        "estacoes": total_estacoes(),
        "municipios": total_municipios(),
        "medicoes": total_medicoes(),
    }


def medicoes_recentes(limite=8):
    """Retorna as medições mais recentes."""

    return (
        MedicaoQualidadeAr.query
        .options(
            joinedload(
                MedicaoQualidadeAr.estacao
            ).joinedload(
                EstacaoMonitoramento.municipio
            ),
            joinedload(
                MedicaoQualidadeAr.parametro
            ),
        )
        .order_by(
            MedicaoQualidadeAr.data_hora.desc()
        )
        .limit(limite)
        .all()
    )


def medicoes_por_estacao(limite=8):
    """Retorna as estações com maior quantidade de medições."""

    resultados = (
        db.session.query(
            EstacaoMonitoramento.nome,
            func.count(
                MedicaoQualidadeAr.id
            ).label("total"),
        )
        .join(
            MedicaoQualidadeAr,
            MedicaoQualidadeAr.estacao_id
            == EstacaoMonitoramento.id,
        )
        .group_by(
            EstacaoMonitoramento.id,
            EstacaoMonitoramento.nome,
        )
        .order_by(
            func.count(
                MedicaoQualidadeAr.id
            ).desc()
        )
        .limit(limite)
        .all()
    )

    return [
        {
            "label": nome,
            "total": int(total),
        }
        for nome, total in resultados
    ]