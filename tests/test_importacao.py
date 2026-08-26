import os
import tempfile

import pandas as pd

from app.services.importacao_service import import_csv


BASE = {
    "no_fonte_dados": ["MMA"],
    "dh_medicao": ["2024-01-01 10:00"],
    "no_item_monitorado": ["MP2.5"],
    "id_estacao": ["1"],
    "no_estacao": ["E1"],
    "id_municipio": ["2"],
    "no_municipio": ["Cidade"],
}


def criar_csv_temporario(dados):
    fd, caminho = tempfile.mkstemp(suffix=".csv")

  
    os.close(fd)

    pd.DataFrame(dados).to_csv(
        caminho,
        index=False,
    )

    return caminho


def test_csv_valido_e_duplicidade(app):
    caminho = criar_csv_temporario(BASE)

    try:
        with app.app_context():

            resultado = import_csv(
                caminho,
                mostrar_progresso=False,
            )

            assert resultado["inseridos"] == 1

            resultado = import_csv(
                caminho,
                mostrar_progresso=False,
            )

            assert resultado["duplicados"] == 1

    finally:
        if os.path.exists(caminho):
            os.remove(caminho)


def test_coluna_faltante(app):
    caminho = criar_csv_temporario({
        "x": [1]
    })

    try:
        with app.app_context():

            try:
                import_csv(
                    caminho,
                    mostrar_progresso=False,
                )

                assert False

            except ValueError as erro:
                assert (
                    "Colunas obrigatórias ausentes"
                    in str(erro)
                )

    finally:
        if os.path.exists(caminho):
            os.remove(caminho)


def test_data_invalida(app):
    dados = dict(BASE)

    dados["dh_medicao"] = [
        "nao-data"
    ]

    caminho = criar_csv_temporario(
        dados
    )

    try:
        with app.app_context():

            try:
                import_csv(
                    caminho,
                    mostrar_progresso=False,
                )

                assert False

            except ValueError as erro:
                assert (
                    "dh_medicao"
                    in str(erro)
                )

    finally:
        if os.path.exists(caminho):
            os.remove(caminho)