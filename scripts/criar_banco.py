from app import create_app
from app.models import db, Perfil
app=create_app()
with app.app_context():
    db.create_all()
    for n,nome in [(1,"Usuário geral"),(2,"Responsável técnico"),(3,"Autoridade administrativa")]:
        if not Perfil.query.filter_by(nivel=n).first(): db.session.add(Perfil(nivel=n,nome=nome))
    db.session.commit(); print("Banco e perfis criados.")
