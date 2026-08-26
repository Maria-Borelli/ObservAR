from app import create_app
from app.models import HistoricoImportacao, db


app = create_app()


with app.app_context():
    HistoricoImportacao.__table__.create(
        bind=db.engine,
        checkfirst=True,
    )

    print(
        "Tabela historico_importacao verificada/criada com segurança."
    )
