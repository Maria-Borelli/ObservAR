from sqlalchemy import inspect, text

from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    colunas = {coluna["name"] for coluna in inspector.get_columns("usuario")}
    dialecto = db.engine.dialect.name

    comandos = []

    if "criado_em" not in colunas:
        if dialecto == "mysql":
            comandos.append(
                "ALTER TABLE usuario ADD COLUMN criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )
        else:
            comandos.append(
                "ALTER TABLE usuario ADD COLUMN criado_em DATETIME"
            )

    if "atualizado_em" not in colunas:
        if dialecto == "mysql":
            comandos.append(
                "ALTER TABLE usuario ADD COLUMN atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )
        else:
            comandos.append(
                "ALTER TABLE usuario ADD COLUMN atualizado_em DATETIME"
            )

    for comando in comandos:
        db.session.execute(text(comando))

    if dialecto != "mysql":
        db.session.execute(text(
            "UPDATE usuario SET criado_em = CURRENT_TIMESTAMP WHERE criado_em IS NULL"
        ))
        db.session.execute(text(
            "UPDATE usuario SET atualizado_em = CURRENT_TIMESTAMP WHERE atualizado_em IS NULL"
        ))

    db.session.commit()
    print("Estrutura de usuários atualizada sem remover contas existentes.")
