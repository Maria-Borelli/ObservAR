import io

import pandas as pd

from app.models import (
    HistoricoImportacao,
    MedicaoQualidadeAr,
    db,
)

from app.services.importacao_service import (
    DEFAULT_CHUNK_SIZE,
    limpar_importacao,
)

from conftest import auth_session


COLUNAS = {
    "no_fonte_dados": ["MMA"],
    "dh_medicao": [
        "2024-01-01 10:00"
    ],
    "no_item_monitorado": [
        "MP2.5"
    ],
    "id_estacao": ["1"],
    "no_estacao": ["E1"],
    "id_municipio": ["2"],
    "no_municipio": ["Cidade"],
}


def csv_bytes(
    dados=None,
):
    frame = pd.DataFrame(
        dados or COLUNAS
    )

    return (
        frame
        .to_csv(
            index=False
        )
        .encode(
            "utf-8"
        )
    )


def test_importacao_admin_pagina(
    client,
):
    auth_session(
        client,
        3,
    )

    response = client.get(
        "/importacao"
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        "Importação de dados"
        .encode("utf-8")
        in response.data
    )


def test_importacao_bloqueia_usuario_sem_nivel(
    client,
):
    auth_session(
        client,
        1,
    )

    response = client.get(
        "/importacao"
    )

    assert (
        response.status_code
        == 403
    )


def test_importacao_web_csv_valido_e_mesmo_arquivo(
    client,
    app,
):
    auth_session(
        client,
        3,
    )

    response = client.post(
        "/importacao/iniciar",
        data={
            "arquivo": (
                io.BytesIO(
                    csv_bytes()
                ),
                "monitorar_2024.csv",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
    )

    assert (
        response.status_code
        == 202
    )

    payload = (
        response.get_json()
    )

    assert (
        payload["ok"]
        is True
    )

    with app.app_context():
        assert (
            MedicaoQualidadeAr
            .query
            .count()
            == 1
        )

        item = (
            db.session.get(
                HistoricoImportacao,
                payload["id"],
            )
        )

        assert (
            item.status
            == "Concluída"
        )

        assert (
            item.registros_importados
            == 1
        )

    response2 = client.post(
        "/importacao/iniciar",
        data={
            "arquivo": (
                io.BytesIO(
                    csv_bytes()
                ),
                "outro_nome.csv",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
    )

    assert (
        response2.status_code
        == 409
    )

    payload2 = (
        response2.get_json()
    )

    assert (
        payload2[
            "duplicate_file"
        ]
        is True
    )

    with app.app_context():
        assert (
            MedicaoQualidadeAr
            .query
            .count()
            == 1
        )


def test_importacao_rejeita_arquivo_sem_colunas(
    client,
):
    auth_session(
        client,
        3,
    )

    response = client.post(
        "/importacao/iniciar",
        data={
            "arquivo": (
                io.BytesIO(
                    b"x\n1\n"
                ),
                "invalido.csv",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
    )

    assert (
        response.status_code
        == 400
    )

    assert (
        "Colunas obrigatórias ausentes"
        .encode("utf-8")
        in response.data
    )


def test_lote_padrao_e_1000():
    assert (
        DEFAULT_CHUNK_SIZE
        == 1000
    )


def test_cancelamento_exige_admin(
    client,
):
    auth_session(
        client,
        1,
    )

    response = client.post(
        "/importacao/1/cancelar"
    )

    assert (
        response.status_code
        == 403
    )


def test_cancelamento_importacao_inexistente(
    client,
):
    auth_session(
        client,
        3,
    )

    response = client.post(
        "/importacao/999999/cancelar"
    )

    assert (
        response.status_code
        == 404
    )


def test_nao_cancela_importacao_concluida(
    client,
    app,
):
    auth_session(
        client,
        3,
    )

    response = client.post(
        "/importacao/iniciar",
        data={
            "arquivo": (
                io.BytesIO(
                    csv_bytes()
                ),
                "teste.csv",
            )
        },
        content_type=(
            "multipart/form-data"
        ),
    )

    payload = (
        response.get_json()
    )

    resposta_cancelamento = (
        client.post(
            f"/importacao/"
            f"{payload['id']}/cancelar"
        )
    )

    assert (
        resposta_cancelamento
        .status_code
        == 409
    )


def test_limpeza_remove_somente_medicoes_da_importacao(
    app,
):
    with app.app_context():
        historico = (
            HistoricoImportacao(
                nome_arquivo=(
                    "teste.csv"
                ),
                hash_arquivo=(
                    "a" * 64
                ),
                status=(
                    "Processando"
                ),
            )
        )

        db.session.add(
            historico
        )

        db.session.commit()

        medicao_importacao = (
            MedicaoQualidadeAr(
                chave_importacao=(
                    "b" * 64
                ),
                importacao_id=(
                    historico.id
                ),
            )
        )

        medicao_antiga = (
            MedicaoQualidadeAr(
                chave_importacao=(
                    "c" * 64
                ),
                importacao_id=None,
            )
        )

        db.session.add_all(
            [
                medicao_importacao,
                medicao_antiga,
            ]
        )

        db.session.commit()

        removidos = (
            limpar_importacao(
                historico.id
            )
        )

        assert removidos == 1

        assert (
            MedicaoQualidadeAr
            .query
            .filter_by(
                chave_importacao=(
                    "b" * 64
                )
            )
            .first()
            is None
        )

        assert (
            MedicaoQualidadeAr
            .query
            .filter_by(
                chave_importacao=(
                    "c" * 64
                )
            )
            .first()
            is not None
        )