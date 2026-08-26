from app.models import db, EstacaoMonitoramento, Municipio
from conftest import auth_session


def _seed_stations(app, total=60):
    with app.app_context():
        municipio = Municipio(id_oficial="m1", nome="Município")
        db.session.add(municipio)
        db.session.flush()
        for i in range(total):
            db.session.add(
                EstacaoMonitoramento(
                    id_oficial=f"e{i}",
                    nome=f"Estação {i:03d}",
                    municipio=municipio,
                )
            )
        db.session.commit()


def test_estacoes_primeira_pagina_e_limite(client, app):
    _seed_stations(app)
    auth_session(client, 1)
    response = client.get("/estacoes?per_page=25")
    assert response.status_code == 200
    assert response.data.count(b"<tr>") == 26  # cabeçalho + 25 registros
    assert b"P\xc3\xa1gina 1 de 3" in response.data


def test_estacoes_pagina_invalida_volta_para_primeira(client, app):
    _seed_stations(app)
    auth_session(client, 1)
    response = client.get("/estacoes?page=texto&per_page=999")
    assert response.status_code == 200
    assert b"P\xc3\xa1gina 1 de 3" in response.data


def test_estacoes_pagina_acima_total_ajusta_ultima(client, app):
    _seed_stations(app)
    auth_session(client, 1)
    response = client.get("/estacoes?page=999&per_page=25")
    assert response.status_code == 200
    assert b"P\xc3\xa1gina 3 de 3" in response.data
    assert b'aria-disabled="true"' in response.data
