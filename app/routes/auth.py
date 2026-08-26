import secrets
from time import perf_counter

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.models import (
    BiometriaFacial,
    Usuario,
    db,
)

from app.services.autenticacao_service import find_user
from app.services.auditoria_service import auth_log
from app.services.biometria_service import (
    BiometricError,
    compare,
    extract_template,
)


bp = Blueprint(
    "auth",
    __name__,
)


@bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    if request.method == "POST":

        ident = request.form.get(
            "identifier",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        usuario = find_user(
            ident
        )

        if (
            not usuario
            or not usuario.ativo
            or not usuario.check_password(password)
        ):

            auth_log(
                usuario.id if usuario else None,
                ident,
                "senha",
                False,
                "Credenciais inválidas",
            )

            return render_template(
                "auth/login.html",
                error="Usuário ou senha inválidos.",
            ), 401

        # Limpa qualquer sessão antiga
        session.clear()

        # Gera novo token CSRF
        session["_csrf"] = (
            secrets.token_urlsafe(24)
        )

    
        session[
            "pending_user_id"
        ] = usuario.id

        auth_log(
            usuario.id,
            usuario.login,
            "senha",
            True,
            "Senha validada",
        )

        return redirect(
            url_for(
                "auth.biometria"
            )
        )

    return render_template(
        "auth/login.html"
    )

#Tela de autenticação facial

@bp.route(
    "/biometria"
)
def biometria():

    uid = session.get(
        "pending_user_id"
    )

    if not uid:
        return redirect(
            url_for(
                "auth.login"
            )
        )

    usuario = Usuario.query.get(
        uid
    )

    if not usuario:
        session.clear()

        return redirect(
            url_for(
                "auth.login"
            )
        )

    return render_template(
        "auth/biometria.html",
        usuario=usuario,
    )

#API de verificação biométrica

@bp.post(
    "/api/biometria/verificar"
)
def verificar():
    request_started = perf_counter()

    uid = session.get(
        "pending_user_id"
    )

    if not uid:
        return jsonify(
            ok=False,
            error=(
                "Sessão de autenticação "
                "expirada."
            ),
        ), 401

    usuario = Usuario.query.get(
        uid
    )

    if not usuario:
        session.clear()

        return jsonify(
            ok=False,
            error="Usuário não encontrado.",
        ), 404

    biometria = (
        BiometriaFacial.query
        .filter_by(
            usuario_id=usuario.id,
            ativa=True,
        )
        .first()
    )

    if not biometria:

        auth_log(
            usuario.id,
            usuario.login,
            "biometria",
            False,
            "Sem biometria cadastrada",
        )

        return jsonify(
            ok=False,
            error=(
                "Usuário sem biometria "
                "cadastrada."
            ),
        ), 409

    image = request.form.get(
        "image",
        "",
    )

    try:
        biometric_started = perf_counter()

        resultado = compare(
            image,
            biometria.template,
            biometria.backend,
            current_app.config[
                "BIOMETRIC_TOLERANCE"
            ],
        )
        biometric_ms = (perf_counter() - biometric_started) * 1000

    except BiometricError as erro:

        auth_log(
            usuario.id,
            usuario.login,
            "biometria",
            False,
            str(erro),
        )

        return jsonify(
            ok=False,
            error=str(erro),
        ), 422

    if not resultado:

        auth_log(
            usuario.id,
            usuario.login,
            "biometria",
            False,
            "Biometria divergente",
        )

        return jsonify(
            ok=False,
            error=(
                "Biometria não corresponde "
                "ao usuário."
            ),
        ), 403

 
    session_started = perf_counter()
    session.pop(
        "pending_user_id",
        None,
    )

    session[
        "user_id"
    ] = usuario.id

    session.permanent = True
    session_ms = (perf_counter() - session_started) * 1000

    log_started = perf_counter()
    auth_log(
        usuario.id,
        usuario.login,
        "biometria",
        True,
        "Correspondência facial",
    )
    log_ms = (perf_counter() - log_started) * 1000

    if current_app.debug:
        current_app.logger.debug(
            "performance biometria comparacao_total_ms=%.1f sessao_ms=%.1f log_ms=%.1f total_ms=%.1f",
            biometric_ms,
            session_ms,
            log_ms,
            (perf_counter() - request_started) * 1000,
        )

    return jsonify(
        ok=True,
        redirect=url_for(
            "main.dashboard"
        ),
    )



@bp.post(
    "/logout"
)
def logout():

    session.clear()

    return redirect(
        url_for(
            "auth.login"
        )
    )



@bp.route(
    "/setup-biometria",
    methods=["GET", "POST"],
)
def setup_biometria():

    if request.method == "POST":

        ident = request.form.get(
            "identifier",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        usuario = find_user(
            ident
        )

        if (
            not usuario
            or not usuario.ativo
            or not usuario.check_password(password)
        ):

            auth_log(
                usuario.id if usuario else None,
                ident,
                "setup_biometria_senha",
                False,
                "Credenciais inválidas",
            )

            return render_template(
                "auth/setup_biometria.html",
                error=(
                    "Usuário ou senha "
                    "inválidos."
                ),
            ), 401

        # Só nível 3 pode usar o bootstrap biométrico

        if usuario.perfil.nivel != 3:

            auth_log(
                usuario.id,
                usuario.login,
                "setup_biometria_senha",
                False,
                (
                    "Usuário não possui "
                    "nível administrativo"
                ),
            )

            return render_template(
                "auth/setup_biometria.html",
                error=(
                    "Somente usuário de "
                    "nível 3 pode realizar "
                    "o cadastro inicial."
                ),
            ), 403

        biometria_existente = (
            BiometriaFacial.query
            .filter_by(
                usuario_id=usuario.id,
                ativa=True,
            )
            .first()
        )

   
        if biometria_existente:

            return render_template(
                "auth/setup_biometria.html",
                error=(
                    "Este administrador já "
                    "possui biometria "
                    "cadastrada."
                ),
            ), 409

        session.clear()

        session["_csrf"] = (
            secrets.token_urlsafe(24)
        )

        session[
            "setup_biometria_user_id"
        ] = usuario.id

        auth_log(
            usuario.id,
            usuario.login,
            "setup_biometria_senha",
            True,
            (
                "Credenciais administrativas "
                "validadas"
            ),
        )

        return redirect(
            url_for(
                "auth.setup_biometria_camera"
            )
        )

    return render_template(
        "auth/setup_biometria.html"
    )


@bp.route(
    "/setup-biometria/camera"
)
def setup_biometria_camera():

    uid = session.get(
        "setup_biometria_user_id"
    )

    if not uid:

        return redirect(
            url_for(
                "auth.setup_biometria"
            )
        )

    usuario = Usuario.query.get(
        uid
    )

    if not usuario:

        session.pop(
            "setup_biometria_user_id",
            None,
        )

        return redirect(
            url_for(
                "auth.setup_biometria"
            )
        )

    if usuario.perfil.nivel != 3:

        session.pop(
            "setup_biometria_user_id",
            None,
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    biometria_existente = (
        BiometriaFacial.query
        .filter_by(
            usuario_id=usuario.id,
            ativa=True,
        )
        .first()
    )

    if biometria_existente:

        session.pop(
            "setup_biometria_user_id",
            None,
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    return render_template(
        "auth/setup_biometria_camera.html",
        usuario=usuario,
    )


#API de cadastro biométrico inicial

@bp.post(
    "/api/setup-biometria/cadastrar"
)
def setup_biometria_cadastrar():

    uid = session.get(
        "setup_biometria_user_id"
    )

    if not uid:

        return jsonify(
            ok=False,
            error=(
                "Sessão de cadastro "
                "biométrico expirada."
            ),
        ), 401

    usuario = Usuario.query.get(
        uid
    )

    if not usuario:

        session.pop(
            "setup_biometria_user_id",
            None,
        )

        return jsonify(
            ok=False,
            error="Usuário não encontrado.",
        ), 404

    if usuario.perfil.nivel != 3:

        session.pop(
            "setup_biometria_user_id",
            None,
        )

        return jsonify(
            ok=False,
            error="Operação não autorizada.",
        ), 403

    biometria_existente = (
        BiometriaFacial.query
        .filter_by(
            usuario_id=usuario.id,
            ativa=True,
        )
        .first()
    )

    if biometria_existente:

        return jsonify(
            ok=False,
            error=(
                "Biometria já cadastrada."
            ),
        ), 409

    image = request.form.get(
        "image",
        "",
    )

    if not image:

        return jsonify(
            ok=False,
            error=(
                "Nenhuma imagem facial "
                "foi enviada."
            ),
        ), 400

    try:

        template = extract_template(
            image,
            current_app.config[
                "BIOMETRIC_BACKEND"
            ],
        )

    except BiometricError as erro:

        auth_log(
            usuario.id,
            usuario.login,
            "setup_biometria",
            False,
            str(erro),
        )

        return jsonify(
            ok=False,
            error=str(erro),
        ), 422

    biometria = BiometriaFacial(
        usuario_id=usuario.id,

        backend=current_app.config[
            "BIOMETRIC_BACKEND"
        ],

        template=template,

        ativa=True,
    )

    db.session.add(
        biometria
    )

    db.session.commit()

    auth_log(
        usuario.id,
        usuario.login,
        "setup_biometria",
        True,
        (
            "Biometria administrativa "
            "inicial cadastrada"
        ),
    )

    session.pop(
        "setup_biometria_user_id",
        None,
    )

    return jsonify(
        ok=True,
        redirect=url_for(
            "auth.login"
        ),
    )