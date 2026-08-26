from app.models import Usuario

def find_user(identifier):
    return Usuario.query.filter((Usuario.login==identifier)|(Usuario.email==identifier)).first()
