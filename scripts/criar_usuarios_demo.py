from app import create_app
from app.models import db, Perfil, Usuario

app = create_app()

USUARIOS_DESENVOLVIMENTO = [
    ("maria.clara", "Maria Clara", 3),
    ("lauan", "Lauan", 1),
    ("giovanni", "Giovanni", 2),
    ("miguel", "Miguel", 1),
]

with app.app_context():
    for login, nome, nivel in USUARIOS_DESENVOLVIMENTO:
        if not Usuario.query.filter_by(login=login).first():
            perfil = Perfil.query.filter_by(nivel=nivel).one()
            usuario = Usuario(login=login, nome=nome, perfil=perfil, ativo=True)
            usuario.set_password("senha1234")
            db.session.add(usuario)

    db.session.commit()
    print(
        "Usuários pessoais de desenvolvimento criados. "
        "Troque as senhas antes de demonstrar."
    )
