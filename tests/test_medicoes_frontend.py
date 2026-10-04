from datetime import datetime
from urllib.parse import parse_qs, urlparse
import re
import pytest
from app.models import db, EstacaoMonitoramento, MedicaoQualidadeAr
from conftest import auth_session


@pytest.mark.parametrize('level', [1, 2, 3])
def test_medicoes_preserva_busca_paginacao_e_colunas(client, app, level):
    with app.app_context():
        station = EstacaoMonitoramento(id_oficial='centro', nome='Centro')
        db.session.add(station)
        db.session.flush()
        for index in range(60):
            db.session.add(MedicaoQualidadeAr(
                chave_importacao=f'test-{index}', estacao_id=station.id, data_hora=datetime(2026, 1, 1),
                iqar=25, concentracao=12.5,
            ))
        db.session.commit()
        station_id = station.id
    auth_session(client, level)
    response = client.get(f'/medicoes?q=Centro&estacao_id={station_id}&per_page=25&page=2')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('<main ') == 1
    assert 'method="get"' in html
    assert 'name="q"' in html and 'value="Centro"' in html
    assert 'name="per_page"' in html and 'value="25"' in html
    assert html.count('<tr>') == 26
    assert '<th scope="col" class="column-iqar">' in html
    assert html.count('<td class="column-iqar">') == 25
    assert ('<th scope="col" class="column-concentracao">' in html) == (level >= 2)
    assert ('<td class="column-concentracao">' in html) == (level >= 2)
    assert 'aria-current="page"' in html
    assert 'class="measurements-spinner" hidden' in html
    assert 'm15 18-6-6 6-6' in html and 'm9 18 6-6-6-6' in html
    hrefs = re.findall(r'href="([^"]+)"', html)
    paging = [href.replace('&amp;', '&') for href in hrefs if '/medicoes?' in href]
    assert paging
    for href in paging:
        query = parse_qs(urlparse(href).query)
        assert query['q'] == ['Centro']
        assert query['estacao_id'] == [str(station_id)]
        assert query['per_page'] == ['25']


def test_medicoes_vazia_mantem_formulario(client):
    auth_session(client, 1)
    response = client.get('/medicoes?q=ausente&per_page=50')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="ausente"' in html and 'value="50"' in html
    assert 'class="empty"' in html
    assert '<table>' not in html

