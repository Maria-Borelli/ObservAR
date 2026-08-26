import pytest
from app import create_app
from app.models import db, Perfil, Usuario, BiometriaFacial
@pytest.fixture()
def app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"test"})
    with app.app_context():
        db.create_all()
        for n in (1,2,3): db.session.add(Perfil(nome=f"N{n}",nivel=n))
        db.session.commit()
        for n in (1,2,3):
            u=Usuario(nome=f"U{n}",login=f"u{n}",perfil=Perfil.query.filter_by(nivel=n).one());u.set_password("ok");db.session.add(u)
        db.session.commit()
    yield app
@pytest.fixture()
def client(app): return app.test_client()
def auth_session(client,uid):
    with client.session_transaction() as s:s["user_id"]=uid
