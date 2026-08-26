import secrets
from urllib.parse import urlencode

from flask import (
    Flask,
    abort,
    render_template,
    request,
    session,
)

from config import Config
from app.models import db



def formatar_numero_br(valor):
    """
    Formata números inteiros no padrão brasileiro.

    Exemplo:
    4926747 -> 4.926.747
    """
    if valor is None:
        return "0"

    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return str(valor)

    return f"{numero:,}".replace(",", ".")


def formatar_decimal_br(valor):
    """
    Formata números decimais usando vírgula.

    Exemplos:
    35.0   -> 35,0
    12.073 -> 12,073
    """
    if valor is None:
        return "—"

    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    texto = str(numero)

    if "." not in texto:
        texto += ".0"

    return texto.replace(".", ",")


def formatar_data_hora_br(valor):
    """
    Formata data e hora para apresentação.

    Exemplo:
    2025-12-31 23:30:00
    -> 31/12/2025 23:30
    """
    if valor is None:
        return "—"

    try:
        return valor.strftime(
            "%d/%m/%Y %H:%M"
        )
    except AttributeError:
        return str(valor)

# Paginação

def pagination_url(page, **changes):
    """
    Cria uma URL para outra página preservando
    os filtros já existentes na URL atual.

    Exemplo:

    /medicoes?q=centro&per_page=25&page=2

    ao avançar:

    /medicoes?q=centro&per_page=25&page=3
    """

    args = request.args.to_dict(
        flat=True
    )

    for key, value in changes.items():

        if value is None:
            args.pop(
                key,
                None,
            )

        else:
            args[key] = value

    args["page"] = page

    query_string = urlencode(
        args
    )

    if query_string:
        return (
            f"{request.path}"
            f"?{query_string}"
        )

    return request.path



def create_app(test_config=None):
    app = Flask(__name__)

    app.json.ensure_ascii = False

    app.config.from_object(
        Config
    )

    if test_config:
        app.config.update(
            test_config
        )

    db.init_app(app)

   
    app.jinja_env.filters[
        "numero_br"
    ] = formatar_numero_br

    app.jinja_env.filters[
        "decimal_br"
    ] = formatar_decimal_br

    app.jinja_env.filters[
        "data_hora_br"
    ] = formatar_data_hora_br

   
    app.jinja_env.globals[
        "pagination_url"
    ] = pagination_url

 
    from app.routes.auth import bp as auth
    from app.routes.main import bp as main
    from app.routes.importacao import bp as importacao

    app.register_blueprint(
        auth
    )

    app.register_blueprint(
        main
    )

    app.register_blueprint(
        importacao
    )

   
    @app.before_request
    def csrf_setup():

        session.setdefault(
            "_csrf",
            secrets.token_urlsafe(24),
        )

        if (
            request.method
            in {
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
            }
            and not app.config.get(
                "TESTING"
            )
        ):

            token_form = request.form.get(
                "_csrf"
            )

            token_header = request.headers.get(
                "X-CSRF-Token"
            )

            token_session = session.get(
                "_csrf"
            )

            if (
                token_form != token_session
                and
                token_header != token_session
            ):
                abort(400)

  
    @app.context_processor
    def inject():

        return {
            "csrf_token": (
                lambda:
                session.get(
                    "_csrf",
                    "",
                )
            )
        }

   
    @app.errorhandler(403)
    def e403(error):

        return (
            render_template(
                "errors/403.html"
            ),
            403,
        )

   
    @app.errorhandler(404)
    def e404(error):

        return (
            render_template(
                "errors/404.html"
            ),
            404,
        )

    
    @app.errorhandler(500)
    def e500(error):

        return (
            render_template(
                "errors/500.html"
            ),
            500,
        )

    return app