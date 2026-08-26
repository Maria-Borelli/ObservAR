from time import perf_counter

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
)

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    AnaliseInterna,
    BiometriaFacial,
    EstacaoMonitoramento,
    LogAcesso,
    LogAutenticacao,
    MedicaoQualidadeAr,
    Usuario,
    db,
)

from app.services.autorizacao_service import current_user, require_level
from app.services.biometria_service import BiometricError, extract_template
from app.services.auditoria_service import auth_log
from app.services.monitorar_service import (
    medicoes_por_estacao,
    medicoes_recentes,
    resumo_dashboard,
)

bp = Blueprint("main", __name__)

PER_PAGE_ALLOWED = (25, 50, 100)


def _positive_page(name="page"):
    value = request.args.get(name, "1")
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def _per_page(name="per_page"):
    value = request.args.get(name, "25")
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 25
    return value if value in PER_PAGE_ALLOWED else 25


def _paginate(query, page_name="page", per_page_name="per_page"):
    """Paginação no banco; página acima do total é ajustada para a última."""
    page = _positive_page(page_name)
    per_page = _per_page(per_page_name)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    if pagination.pages and page > pagination.pages:
        pagination = query.paginate(
            page=pagination.pages,
            per_page=per_page,
            error_out=False,
        )
    return pagination, per_page


@bp.route("/")
@require_level(1)
def dashboard():
    started = perf_counter()
    usuario = current_user()
    stats = {"estacoes": 0, "municipios": 0, "medicoes": 0}
    recent = []
    chart_data = []
    banco_ok = True

    query_started = perf_counter()
    try:
        stats = resumo_dashboard()
        if stats["medicoes"] > 0:
            recent = medicoes_recentes(limite=8)
            chart_data = medicoes_por_estacao(limite=8)
    except SQLAlchemyError:
        db.session.rollback()
        banco_ok = False
    query_ms = (perf_counter() - query_started) * 1000

    acesso_texto = {
        1: "Acesso às informações gerais e aos indicadores ambientais.",
        2: "Acesso às medições detalhadas e às análises técnicas.",
        3: "Acesso completo aos dados, análises e configurações do sistema.",
    }.get(usuario.perfil.nivel, "Acesso definido pelo perfil do usuário.")

    render_started = perf_counter()
    response = render_template(
        "dashboard/index.html",
        u=usuario,
        stats=stats,
        recent=recent,
        chart_data=chart_data,
        banco_ok=banco_ok,
        acesso_texto=acesso_texto,
    )
    render_ms = (perf_counter() - render_started) * 1000

    if current_app.debug:
        current_app.logger.debug(
            "performance dashboard consultas_ms=%.1f renderizacao_ms=%.1f total_ms=%.1f",
            query_ms,
            render_ms,
            (perf_counter() - started) * 1000,
        )
    return response


@bp.route("/medicoes")
@require_level(1)
def medicoes():
    usuario = current_user()
    query = MedicaoQualidadeAr.query.options(
        joinedload(MedicaoQualidadeAr.estacao).joinedload(
            EstacaoMonitoramento.municipio
        ),
        joinedload(MedicaoQualidadeAr.parametro),
    )

    termo = request.args.get("q", "").strip()
    estacao_id = request.args.get("estacao_id", type=int)

    if termo:
        query = query.join(EstacaoMonitoramento).filter(
            EstacaoMonitoramento.nome.ilike(f"%{termo}%")
        )
    if estacao_id:
        query = query.filter(MedicaoQualidadeAr.estacao_id == estacao_id)

    query = query.order_by(
        MedicaoQualidadeAr.data_hora.desc(),
        MedicaoQualidadeAr.id.desc(),
    )
    pagination, per_page = _paginate(query)
    return render_template(
        "medicoes/index.html",
        u=usuario,
        items=pagination.items,
        pagination=pagination,
        per_page=per_page,
    )


@bp.route("/estacoes")
@require_level(1)
def estacoes():
    usuario = current_user()
    query = EstacaoMonitoramento.query.options(
        joinedload(EstacaoMonitoramento.municipio)
    ).order_by(EstacaoMonitoramento.nome.asc(), EstacaoMonitoramento.id.asc())
    pagination, per_page = _paginate(query)
    return render_template(
        "estacoes/index.html",
        u=usuario,
        items=pagination.items,
        pagination=pagination,
        per_page=per_page,
    )


@bp.route("/mapa")
@require_level(1)
def mapa():
    usuario = current_user()
    # O mapa precisa do conjunto geográfico; selecionamos apenas estações com
    # coordenadas e o município, sem carregar medições relacionadas.
    stations = (
        EstacaoMonitoramento.query
        .options(joinedload(EstacaoMonitoramento.municipio))
        .filter(
            EstacaoMonitoramento.latitude.between(-90, 90),
            EstacaoMonitoramento.longitude.between(-180, 180),
        )
        .all()
    )
    return render_template("mapa/index.html", u=usuario, stations=stations)


@bp.route("/analises")
@require_level(2)
def analises():
    query = AnaliseInterna.query.order_by(
        AnaliseInterna.criada_em.desc(),
        AnaliseInterna.id.desc(),
    )
    pagination, per_page = _paginate(query)
    return render_template(
        "analises/index.html",
        u=current_user(),
        items=pagination.items,
        pagination=pagination,
        per_page=per_page,
    )


@bp.route("/usuarios")
@require_level(3)
def usuarios():
    query = (
        Usuario.query
        .options(
            joinedload(Usuario.perfil),
            selectinload(Usuario.biometrias),
        )
        .order_by(Usuario.nome.asc(), Usuario.id.asc())
    )
    pagination, per_page = _paginate(query)
    return render_template(
        "usuarios/index.html",
        u=current_user(),
        items=pagination.items,
        pagination=pagination,
        per_page=per_page,
    )


@bp.route("/auditoria")
@require_level(3)
def auditoria():
    auth_query = LogAutenticacao.query.order_by(
        LogAutenticacao.criado_em.desc(),
        LogAutenticacao.id.desc(),
    )
    access_query = LogAcesso.query.order_by(
        LogAcesso.criado_em.desc(),
        LogAcesso.id.desc(),
    )
    auth_pagination, auth_per_page = _paginate(
        auth_query, "auth_page", "auth_per_page"
    )
    access_pagination, access_per_page = _paginate(
        access_query, "access_page", "access_per_page"
    )
    return render_template(
        "auditoria/index.html",
        u=current_user(),
        auth=auth_pagination.items,
        access=access_pagination.items,
        auth_pagination=auth_pagination,
        access_pagination=access_pagination,
        auth_per_page=auth_per_page,
        access_per_page=access_per_page,
    )


@bp.route("/usuarios/<int:uid>/biometria")
@require_level(3)
def cadastro_bio(uid):
    return render_template(
        "usuarios/biometria.html",
        u=current_user(),
        target=Usuario.query.get_or_404(uid),
    )


@bp.post("/api/usuarios/<int:uid>/biometria")
@require_level(3)
def save_bio(uid):
    target = Usuario.query.get_or_404(uid)
    image = request.form.get("image", "")
    if not image:
        return jsonify(ok=False, error="Nenhuma imagem facial foi enviada."), 400
    try:
        template = extract_template(
            image, current_app.config["BIOMETRIC_BACKEND"]
        )
    except BiometricError as erro:
        return jsonify(ok=False, error=str(erro)), 422

    try:
        BiometriaFacial.query.filter_by(
            usuario_id=uid, ativa=True
        ).update({"ativa": False})
        db.session.add(
            BiometriaFacial(
                usuario_id=uid,
                backend=current_app.config["BIOMETRIC_BACKEND"],
                template=template,
                ativa=True,
            )
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(ok=False, error="Não foi possível salvar a biometria."), 500

    auth_log(
        uid, target.login, "cadastro_biometrico", True,
        "Referência biométrica cadastrada"
    )
    return jsonify(ok=True)
