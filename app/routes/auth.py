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
    Perfil,
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

    
        auth_log(
            usuario.id,
            usuario.login,
            "senha",
            True,
            "Senha validada",
        )

        # Usuário sem biometria ativa é encaminhado para cadastrá-la
        # antes de concluir a autenticação.
        tem_biometria = (
            BiometriaFacial.query
            .filter_by(
                usuario_id=usuario.id,
                ativa=True,
            )
            .first()
        )

        if not tem_biometria:
            session["enroll_user_id"] = usuario.id

            return redirect(
                url_for("auth.cadastrar_biometria")
            )

        # Modo demonstração: pula a etapa de biometria e autentica direto.
        if current_app.config.get("DEMO_BIOMETRIC_MODE"):
            session["user_id"] = usuario.id
            session.permanent = True

            auth_log(
                usuario.id,
                usuario.login,
                "biometria",
                True,
                "Etapa de biometria ignorada (modo demonstração)",
            )

            return redirect(
                url_for(
                    "main.dashboard"
                )
            )

        session[
            "pending_user_id"
        ] = usuario.id

        return redirect(
            url_for(
                "auth.biometria"
            )
        )

    return render_template(
        "auth/login.html"
    )


# Cadastro aberto de usuário
#
# Qualquer pessoa pode criar uma conta a qualquer momento. A conta é criada
# com nível 1 (leitor). Após a criação, o usuário é encaminhado para
# cadastrar a biometria facial.

@bp.route(
    "/registro",
    methods=["GET", "POST"],
)
def registro():

    if request.method == "POST":

        nome = request.form.get(
            "nome",
            "",
        ).strip()

        login = request.form.get(
            "login",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        confirmar = request.form.get(
            "confirmar",
            "",
        )

        erro = None

        if not nome or not login or not password:
            erro = (
                "Preencha nome, usuário e senha."
            )

        elif len(password) < 8:
            erro = (
                "A senha deve ter ao menos "
                "8 caracteres."
            )

        elif password != confirmar:
            erro = (
                "As senhas não conferem."
            )

        elif (
            Usuario.query
            .filter_by(login=login)
            .first()
        ):
            erro = (
                "Este usuário já está em uso."
            )

        elif email and (
            Usuario.query
            .filter_by(email=email)
            .first()
        ):
            erro = (
                "Este e-mail já está em uso."
            )

        if erro:
            return render_template(
                "auth/registro.html",
                error=erro,
                nome=nome,
                login=login,
                email=email,
            ), 400

        # Conta aberta: criada com nível 1 (leitor).
        perfil = (
            Perfil.query
            .filter_by(nivel=1)
            .first()
        )

        if not perfil:
            perfil = Perfil(
                nivel=1,
                nome="Usuário geral",
            )
            db.session.add(perfil)
            db.session.flush()

        usuario = Usuario(
            nome=nome,
            login=login,
            email=email or None,
            perfil=perfil,
            ativo=True,
        )

        usuario.set_password(password)

        db.session.add(usuario)
        db.session.commit()

        auth_log(
            usuario.id,
            usuario.login,
            "registro",
            True,
            "Usuário cadastrado (nível 1)",
        )

        # Autentica parcialmente e encaminha para o cadastro da facial.
        session.clear()

        session["_csrf"] = (
            secrets.token_urlsafe(24)
        )

        session[
            "enroll_user_id"
        ] = usuario.id

        return redirect(
            url_for("auth.cadastrar_biometria")
        )

    return render_template(
        "auth/registro.html"
    )


# Cadastro de biometria facial para o próprio usuário
#
# Fluxo de onboarding usado quando:
#  - o usuário acabou de se cadastrar; ou
#  - o usuário fez login com senha válida mas ainda não tem facial.
# A sessão guarda `enroll_user_id`.

@bp.route(
    "/cadastrar-biometria"
)
def cadastrar_biometria():

    uid = session.get(
        "enroll_user_id"
    )

    if not uid:
        return redirect(
            url_for("auth.login")
        )

    usuario = Usuario.query.get(uid)

    if not usuario:
        session.clear()
        return redirect(
            url_for("auth.login")
        )

    # Se já tem biometria ativa, não precisa cadastrar de novo.
    ja_tem = (
        BiometriaFacial.query
        .filter_by(
            usuario_id=usuario.id,
            ativa=True,
        )
        .first()
    )

    if ja_tem:
        session.pop("enroll_user_id", None)
        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "auth/cadastrar_biometria.html",
        usuario=usuario,
    )


# API de cadastro de biometria do próprio usuário

@bp.post(
    "/api/cadastrar-biometria"
)
def cadastrar_biometria_salvar():

    uid = session.get(
        "enroll_user_id"
    )

    if not uid:
        return jsonify(
            ok=False,
            error=(
                "Sessão de cadastro "
                "biométrico expirada."
            ),
        ), 401

    usuario = Usuario.query.get(uid)

    if not usuario:
        session.clear()
        return jsonify(
            ok=False,
            error="Usuário não encontrado.",
        ), 404

    if not usuario.ativo:
        session.clear()
        return jsonify(
            ok=False,
            error="Conta de usuário inativa.",
        ), 403

    ja_tem = (
        BiometriaFacial.query
        .filter_by(
            usuario_id=usuario.id,
            ativa=True,
        )
        .first()
    )

    if ja_tem:
        return jsonify(
            ok=False,
            error="Biometria já cadastrada.",
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
            "cadastro_biometria",
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

    db.session.add(biometria)
    db.session.commit()

    auth_log(
        usuario.id,
        usuario.login,
        "cadastro_biometria",
        True,
        "Biometria cadastrada pelo usuário",
    )

    # Conclui a autenticação: biometria recém-cadastrada vale como 2ª etapa.
    session.pop("enroll_user_id", None)
    session["user_id"] = usuario.id
    session.permanent = True

    return jsonify(
        ok=True,
        redirect=url_for("main.dashboard"),
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

    if not usuario.ativo:
        session.clear()
        auth_log(
            usuario.id,
            usuario.login,
            "biometria",
            False,
            "Conta inativa",
        )
        return jsonify(
            ok=False,
            error="Conta de usuário inativa.",
        ), 403

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