from app import create_app
from app.models import db, Perfil, Usuario
app=create_app()
with app.app_context():
    for login,nome,nivel in [("consulta","Usuário Consulta",1),("tecnico","Responsável Técnico",2),("admin","Administrador",3)]:
        if not Usuario.query.filter_by(login=login).first():
            u=Usuario(login=login,nome=nome,perfil=Perfil.query.filter_by(nivel=nivel).one()); u.set_password("senha1234"); db.session.add(u)
    db.session.commit(); print("Usuários de desenvolvimento criados. Troque as senhas antes de demonstrar.")
