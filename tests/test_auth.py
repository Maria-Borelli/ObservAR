from unittest.mock import patch
from app.models import Usuario, BiometriaFacial, db
def test_senha_incorreta(client): assert client.post("/login",data={"identifier":"u1","password":"bad"}).status_code==401
def test_senha_valida_vai_biometria(client): assert client.post("/login",data={"identifier":"u1","password":"ok"}).status_code==302
def test_sem_biometria(client):
    client.post("/login",data={"identifier":"u1","password":"ok"})
    assert client.post("/api/biometria/verificar",data={"image":"x"}).status_code==409
def test_biometria_correta(app,client):
    with app.app_context():
        u=Usuario.query.filter_by(login="u1").one();db.session.add(BiometriaFacial(usuario_id=u.id,backend="face_recognition",template=b"x"));db.session.commit()
    client.post("/login",data={"identifier":"u1","password":"ok"})
    with patch("app.routes.auth.compare",return_value=True):
        r=client.post("/api/biometria/verificar",data={"image":"x"});assert r.status_code==200 and r.json["ok"]
def test_biometria_divergente(app,client):
    with app.app_context():
        u=Usuario.query.filter_by(login="u1").one();db.session.add(BiometriaFacial(usuario_id=u.id,backend="face_recognition",template=b"x"));db.session.commit()
    client.post("/login",data={"identifier":"u1","password":"ok"})
    with patch("app.routes.auth.compare",return_value=False): assert client.post("/api/biometria/verificar",data={"image":"x"}).status_code==403
