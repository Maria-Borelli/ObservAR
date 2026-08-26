from app import create_app
from app.models import db, Usuario


app = create_app()


with app.app_context():

    usuarios = [
        "admin",
        "tecnico",
        "consulta",
    ]

    nova_senha = "senha1234"

    for login in usuarios:

        usuario = Usuario.query.filter_by(
            login=login
        ).first()

        if usuario:
            usuario.set_password(nova_senha)

            print(
                f"Senha de {login} alterada."
            )

        else:
            print(
                f"Usuário {login} não encontrado."
            )

    db.session.commit()

    print("Senhas atualizadas com sucesso.")