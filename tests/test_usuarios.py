from unittest.mock import patch

from app import create_app
from app.models import BiometriaFacial, Perfil, Usuario, db
from conftest import auth_session


def _criar(client, nome, login, nivel):
    return client.post(
        "/usuarios/novo",
        data={
            "nome": nome,
            "login": login,
            "senha": "senha1234",
            "perfil_id": str(nivel),
            "ativo": "on",
        },
    )


def test_admin_cria_usuarios_com_niveis_diferentes(app, client):
    auth_session(client, 3)
    assert _criar(client, "Maria Clara", "maria", 1).status_code == 302
    assert _criar(client, "Lauan", "lauan", 2).status_code == 302
    with app.app_context():
        assert Usuario.query.filter_by(login="maria").one().perfil.nivel == 1
        assert Usuario.query.filter_by(login="lauan").one().perfil.nivel == 2


def test_admin_altera_nivel_de_permissao(app, client):
    auth_session(client, 3)
    response = client.post(
        "/usuarios/1/editar",
        data={
            "nome": "U1",
            "login": "u1",
            "perfil_id": "2",
            "ativo": "on",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Usuario, 1).perfil.nivel == 2


def test_usuario_comum_nao_gerencia_usuarios(client):
    auth_session(client, 1)
    assert _criar(client, "Teste", "teste", 1).status_code == 403
    assert client.post("/usuarios/2/status").status_code == 403
    assert client.post("/usuarios/2/excluir").status_code == 403


def test_nao_rebaixa_ultimo_admin_ativo(app, client):
    auth_session(client, 3)
    response = client.post(
        "/usuarios/3/editar",
        data={
            "nome": "U3",
            "login": "u3",
            "perfil_id": "2",
            "ativo": "on",
        },
    )
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(Usuario, 3).perfil.nivel == 3


def test_nao_desativa_ultimo_admin_ativo(app, client):
    auth_session(client, 3)
    response = client.post("/usuarios/3/status")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Usuario, 3).ativo is True


def test_biometria_autentica_usuario_especifico_e_carrega_permissao(app, client):
    with app.app_context():
        usuario = Usuario.query.filter_by(login="u2").one()
        db.session.add(
            BiometriaFacial(
                usuario_id=usuario.id,
                backend="face_recognition",
                template=b"face-u2",
                ativa=True,
            )
        )
        db.session.commit()

    assert client.post(
        "/login", data={"identifier": "u2", "password": "ok"}
    ).status_code == 302

    with patch("app.routes.auth.compare", return_value=True):
        response = client.post("/api/biometria/verificar", data={"image": "x"})

    assert response.status_code == 200
    with client.session_transaction() as sessao:
        assert sessao["user_id"] == 2

    assert client.get("/analises").status_code == 200
    assert client.get("/usuarios").status_code == 403


def test_usuario_e_perfil_persistem_apos_reabrir_aplicacao(tmp_path):
    banco = tmp_path / "persistencia.db"
    uri = f"sqlite:///{banco}"

    app1 = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": uri,
        "SECRET_KEY": "teste-persistencia",
    })
    with app1.app_context():
        db.create_all()
        perfil = Perfil(nome="Administrador", nivel=3)
        db.session.add(perfil)
        db.session.commit()
        usuario = Usuario(
            nome="Maria Clara",
            login="maria.persistente",
            perfil_id=perfil.id,
            ativo=True,
        )
        usuario.set_password("senha1234")
        db.session.add(usuario)
        db.session.commit()

    app2 = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": uri,
        "SECRET_KEY": "teste-persistencia",
    })
    with app2.app_context():
        usuario = Usuario.query.filter_by(login="maria.persistente").one()
        assert usuario.nome == "Maria Clara"
        assert usuario.perfil.nivel == 3
        assert usuario.ativo is True
