from conftest import auth_session
def test_n1_bloqueado_analises(client): auth_session(client,1); assert client.get("/analises").status_code==403
def test_n2_bloqueado_admin(client): auth_session(client,2); assert client.get("/usuarios").status_code==403
def test_admin_autorizado(client): auth_session(client,3); assert client.get("/usuarios").status_code==200
def test_url_protegida_sem_login(client): assert client.get("/medicoes").status_code==302
