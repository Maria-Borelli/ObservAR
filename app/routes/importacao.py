import os
import tempfile
import threading

from datetime import datetime
from time import perf_counter

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
)

from werkzeug.utils import secure_filename

from app.models import (
    HistoricoImportacao,
    db,
)

from app.services.autorizacao_service import (
    current_user,
    require_level,
)

from app.services.importacao_service import (
    ImportacaoCancelada,
    calcular_hash_arquivo,
    import_csv,
    limpar_importacao,
    validar_csv,
)


bp = Blueprint(
    "importacao",
    __name__,
    url_prefix="/importacao",
)


STATUS_ATIVOS = (
    "Aguardando",
    "Processando",
    "Cancelamento solicitado",
    "Removendo dados importados",
)


STATUS_CANCELAVEIS = (
    "Aguardando",
    "Processando",
)


STATUS_SUCESSO = (
    "Concluída",
    "Concluída com ressalvas",
)


_import_lock = threading.Lock()


def _historico_payload(item):
    return {
        "id":
            item.id,

        "nome_arquivo":
            item.nome_arquivo,

        "status":
            item.status,

        "total_linhas":
            item.total_linhas or 0,

        "linhas_processadas":
            item.linhas_processadas or 0,

        "registros_importados":
            item.registros_importados or 0,

        "duplicados":
            item.duplicados or 0,

        "conflitos":
            item.conflitos or 0,

        "erros":
            item.erros or 0,

        "lotes_processados":
            item.lotes_processados or 0,

        "registros_removidos":
            item.registros_removidos or 0,

        "tempo_segundos":
            item.tempo_segundos,

        "mensagem":
            item.mensagem,

        "cancelamento_solicitado":
            bool(
                item.cancelamento_solicitado
            ),

        "cancelavel":
            item.status
            in STATUS_CANCELAVEIS,

        "iniciada_em": (
            item.iniciada_em.isoformat()
            if item.iniciada_em
            else None
        ),

        "concluida_em": (
            item.concluida_em.isoformat()
            if item.concluida_em
            else None
        ),

        "cancelado_em": (
            item.cancelado_em.isoformat()
            if item.cancelado_em
            else None
        ),

        "concluida":
            item.status
            not in STATUS_ATIVOS,
    }


def _cancelamento_solicitado(
    importacao_id,
):
    solicitado = (
        db.session.query(
            HistoricoImportacao
            .cancelamento_solicitado
        )
        .filter(
            HistoricoImportacao.id
            == importacao_id
        )
        .scalar()
    )

    return bool(
        solicitado
    )


def _atualizar_progresso(
    importacao_id,
    dados,
):
    item = db.session.get(
        HistoricoImportacao,
        importacao_id,
    )

    if not item:
        return

    if item.cancelamento_solicitado:
        if item.status not in (
            "Removendo dados importados",
            "Cancelada",
        ):
            item.status = (
                "Cancelamento solicitado"
            )

            item.mensagem = (
                "Cancelamento solicitado. "
                "Interrompendo a importação..."
            )

        db.session.commit()

        return

    item.status = "Processando"

    item.total_linhas = (
        dados.get(
            "total",
            item.total_linhas or 0,
        )
        or 0
    )

    item.linhas_processadas = (
        dados.get(
            "lidos",
            0,
        )
    )

    item.registros_importados = (
        dados.get(
            "inseridos",
            0,
        )
    )

    item.duplicados = (
        dados.get(
            "duplicados",
            0,
        )
    )

    item.conflitos = (
        dados.get(
            "conflitos",
            0,
        )
    )

    item.erros = (
        dados.get(
            "erros",
            0,
        )
    )

    item.lotes_processados = (
        dados.get(
            "lote",
            0,
        )
    )

    item.mensagem = (
        f"Processando lote "
        f"{item.lotes_processados}..."
    )

    db.session.commit()


def _finalizar_cancelamento(
    importacao_id,
    resultado,
    started,
):
    item = db.session.get(
        HistoricoImportacao,
        importacao_id,
    )

    if not item:
        return

    item.status = (
        "Removendo dados importados"
    )

    item.mensagem = (
        "Removendo os registros "
        "adicionados por esta importação..."
    )

    db.session.commit()

    try:
        removidos = limpar_importacao(
            importacao_id
        )

        item = db.session.get(
            HistoricoImportacao,
            importacao_id,
        )

        item.status = "Cancelada"

        item.linhas_processadas = (
            resultado.get(
                "lidos",
                item.linhas_processadas or 0,
            )
        )

        item.registros_importados = (
            resultado.get(
                "inseridos",
                item.registros_importados or 0,
            )
        )

        item.duplicados = (
            resultado.get(
                "duplicados",
                item.duplicados or 0,
            )
        )

        item.conflitos = (
            resultado.get(
                "conflitos",
                item.conflitos or 0,
            )
        )

        item.erros = (
            resultado.get(
                "erros",
                item.erros or 0,
            )
        )

        item.lotes_processados = (
            resultado.get(
                "lotes",
                item.lotes_processados or 0,
            )
        )

        item.registros_removidos = (
            removidos
        )

        item.cancelado_em = (
            datetime.utcnow()
        )

        item.concluida_em = (
            item.cancelado_em
        )

        item.tempo_segundos = (
            perf_counter()
            - started
        )

        item.mensagem = (
            "Importação cancelada. "
            f"Foram removidos "
            f"{removidos} registros "
            "adicionados por este envio."
        )

        db.session.commit()

    except Exception as erro:
        db.session.rollback()

        current_app.logger.exception(
            "Falha ao limpar importação %s",
            importacao_id,
        )

        item = db.session.get(
            HistoricoImportacao,
            importacao_id,
        )

        if item:
            item.status = (
                "Erro durante o cancelamento"
            )

            item.erro_cancelamento = (
                str(erro)[:1000]
            )

            item.mensagem = (
                "O cancelamento foi solicitado, "
                "mas não foi possível remover "
                "todos os registros."
            )

            item.tempo_segundos = (
                perf_counter()
                - started
            )

            db.session.commit()


def _executar_importacao(
    app,
    importacao_id,
    temp_path,
    sep,
    encoding,
):
    started = perf_counter()

    with app.app_context():
        try:
            item = db.session.get(
                HistoricoImportacao,
                importacao_id,
            )

            if not item:
                return

            if item.cancelamento_solicitado:
                raise ImportacaoCancelada(
                    {
                        "lidos": 0,
                        "inseridos": 0,
                        "duplicados": 0,
                        "conflitos": 0,
                        "erros": 0,
                        "lotes": 0,
                    }
                )

            item.status = "Processando"

            item.mensagem = (
                "Importando registros "
                "para o banco de dados..."
            )

            db.session.commit()

            resultado = import_csv(
                path=temp_path,
                sep=sep,
                encoding=encoding,
                chunk_size=current_app.config.get(
                    "IMPORT_CHUNK_SIZE",
                    1000,
                ),
                mostrar_progresso=False,
                progress_callback=(
                    lambda dados:
                    _atualizar_progresso(
                        importacao_id,
                        dados,
                    )
                ),
                importacao_id=importacao_id,
                cancel_check=(
                    lambda:
                    _cancelamento_solicitado(
                        importacao_id
                    )
                ),
            )

            item = db.session.get(
                HistoricoImportacao,
                importacao_id,
            )

            if item.cancelamento_solicitado:
                raise ImportacaoCancelada(
                    resultado
                )

            item.total_linhas = (
                resultado["total_arquivo"]
            )

            item.linhas_processadas = (
                resultado["lidos"]
            )

            item.registros_importados = (
                resultado["inseridos"]
            )

            item.duplicados = (
                resultado["duplicados"]
            )

            item.conflitos = (
                resultado["conflitos"]
            )

            item.erros = (
                resultado["erros"]
            )

            item.lotes_processados = (
                resultado["lotes"]
            )

            item.tempo_segundos = (
                perf_counter()
                - started
            )

            item.concluida_em = (
                datetime.utcnow()
            )

            if (
                resultado["conflitos"]
                or resultado["erros"]
            ):
                item.status = (
                    "Concluída com ressalvas"
                )

                item.mensagem = (
                    "Importação concluída. "
                    "Registros conflitantes "
                    "foram preservados no banco."
                )

            elif (
                resultado["inseridos"] == 0
                and resultado["duplicados"] > 0
            ):
                item.status = "Concluída"

                item.mensagem = (
                    "Os registros deste arquivo "
                    "já existem no banco de dados. "
                    "Nenhuma informação foi duplicada."
                )

            else:
                item.status = "Concluída"

                item.mensagem = (
                    "Importação concluída "
                    "sem duplicação de dados."
                )

            db.session.commit()

        except ImportacaoCancelada as cancelada:
            db.session.rollback()

            _finalizar_cancelamento(
                importacao_id,
                cancelada.resultado,
                started,
            )

        except ValueError as erro:
            db.session.rollback()

            item = db.session.get(
                HistoricoImportacao,
                importacao_id,
            )

            if item:
                item.status = "Erro"

                item.concluida_em = (
                    datetime.utcnow()
                )

                item.tempo_segundos = (
                    perf_counter()
                    - started
                )

                item.mensagem = (
                    str(erro)[:1000]
                )

                db.session.commit()

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Falha durante processamento "
                "da importação %s",
                importacao_id,
            )

            item = db.session.get(
                HistoricoImportacao,
                importacao_id,
            )

            if item:
                item.status = "Erro"

                item.concluida_em = (
                    datetime.utcnow()
                )

                item.tempo_segundos = (
                    perf_counter()
                    - started
                )

                item.mensagem = (
                    "Não foi possível concluir "
                    "a importação. Consulte o log "
                    "do servidor."
                )

                db.session.commit()

        finally:
            db.session.remove()

            try:
                if os.path.exists(
                    temp_path
                ):
                    os.remove(
                        temp_path
                    )

            except OSError:
                current_app.logger.warning(
                    "Não foi possível remover "
                    "arquivo temporário "
                    "de importação."
                )


@bp.get("")
@require_level(3)
def index():
    historico = (
        HistoricoImportacao.query
        .order_by(
            HistoricoImportacao
            .iniciada_em
            .desc(),

            HistoricoImportacao
            .id
            .desc(),
        )
        .limit(20)
        .all()
    )

    return render_template(
        "importacao/index.html",
        u=current_user(),
        historico=historico,
        max_mb=current_app.config.get(
            "IMPORT_MAX_FILE_MB",
            1024,
        ),
        chunk_size=current_app.config.get(
            "IMPORT_CHUNK_SIZE",
            1000,
        ),
    )


@bp.post("/iniciar")
@require_level(3)
def iniciar():
    arquivo = request.files.get(
        "arquivo"
    )

    if (
        not arquivo
        or not arquivo.filename
    ):
        return jsonify(
            ok=False,
            error=(
                "Selecione um arquivo CSV "
                "para continuar."
            ),
        ), 400

    nome_original = os.path.basename(
        arquivo.filename
    ).strip()

    if not nome_original.lower().endswith(
        ".csv"
    ):
        return jsonify(
            ok=False,
            error=(
                "O arquivo enviado não possui "
                "o formato esperado."
            ),
        ), 400

    nome_seguro = secure_filename(
        nome_original
    )

    if not nome_seguro:
        return jsonify(
            ok=False,
            error=(
                "O nome do arquivo enviado "
                "é inválido."
            ),
        ), 400

    limite_mb = current_app.config.get(
        "IMPORT_MAX_FILE_MB",
        1024,
    )

    limite_bytes = (
        limite_mb
        * 1024
        * 1024
    )

    temp_dir = current_app.config.get(
        "IMPORT_TEMP_DIR"
    )

    if not temp_dir:
        temp_dir = os.path.join(
            current_app.instance_path,
            "imports",
        )

    os.makedirs(
        temp_dir,
        exist_ok=True,
    )

    fd, temp_path = tempfile.mkstemp(
        prefix="observar_",
        suffix=".csv",
        dir=temp_dir,
    )

    os.close(fd)

    try:
        arquivo.save(
            temp_path
        )

        tamanho = os.path.getsize(
            temp_path
        )

        if tamanho == 0:
            raise ValueError(
                "O arquivo CSV está vazio."
            )

        if tamanho > limite_bytes:
            raise ValueError(
                "O arquivo excede o tamanho "
                f"máximo permitido de "
                f"{limite_mb} MB."
            )

        validacao = validar_csv(
            temp_path
        )

        hash_arquivo = (
            calcular_hash_arquivo(
                temp_path
            )
        )

        anterior = (
            HistoricoImportacao.query
            .filter(
                HistoricoImportacao
                .hash_arquivo
                == hash_arquivo,

                HistoricoImportacao
                .status
                .in_(STATUS_SUCESSO),
            )
            .order_by(
                HistoricoImportacao
                .concluida_em
                .desc()
            )
            .first()
        )

        usuario = current_user()

        if anterior:
            tentativa = (
                HistoricoImportacao(
                    nome_arquivo=(
                        nome_original[:255]
                    ),
                    hash_arquivo=(
                        hash_arquivo
                    ),
                    usuario_id=(
                        usuario.id
                    ),
                    status=(
                        "Arquivo já importado"
                    ),
                    iniciada_em=(
                        datetime.utcnow()
                    ),
                    concluida_em=(
                        datetime.utcnow()
                    ),
                    total_linhas=(
                        anterior.total_linhas
                        or 0
                    ),
                    mensagem=(
                        "Este arquivo já foi "
                        "importado anteriormente. "
                        "Nenhum registro foi "
                        "adicionado."
                    ),
                )
            )

            db.session.add(
                tentativa
            )

            db.session.commit()

            return jsonify(
                ok=False,
                duplicate_file=True,
                error=tentativa.mensagem,
            ), 409

        with _import_lock:
            ativa = (
                HistoricoImportacao.query
                .filter(
                    HistoricoImportacao
                    .status
                    .in_(STATUS_ATIVOS)
                )
                .first()
            )

            if ativa:
                return jsonify(
                    ok=False,
                    error=(
                        "Já existe uma importação "
                        "em andamento."
                    ),
                ), 409

            item = HistoricoImportacao(
                nome_arquivo=(
                    nome_original[:255]
                ),
                hash_arquivo=hash_arquivo,
                usuario_id=usuario.id,
                status="Aguardando",
                iniciada_em=(
                    datetime.utcnow()
                ),
                mensagem=(
                    "Preparando importação..."
                ),
            )

            db.session.add(item)
            db.session.commit()

            importacao_id = item.id

        app = (
            current_app
            ._get_current_object()
        )

        if current_app.config.get(
            "TESTING"
        ):
            _executar_importacao(
                app,
                importacao_id,
                temp_path,
                validacao["sep"],
                validacao["encoding"],
            )

        else:
            thread = threading.Thread(
                target=_executar_importacao,
                args=(
                    app,
                    importacao_id,
                    temp_path,
                    validacao["sep"],
                    validacao["encoding"],
                ),
                daemon=True,
                name=(
                    f"importacao-"
                    f"{importacao_id}"
                ),
            )

            thread.start()

        return jsonify(
            ok=True,
            id=importacao_id,
            status_url=(
                f"/importacao/"
                f"{importacao_id}/status"
            ),
            cancel_url=(
                f"/importacao/"
                f"{importacao_id}/cancelar"
            ),
            message=(
                "Verificando registros "
                "existentes no banco de dados..."
            ),
        ), 202

    except ValueError as erro:
        try:
            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )
        except OSError:
            pass

        return jsonify(
            ok=False,
            error=str(erro),
        ), 400

    except Exception:
        try:
            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )
        except OSError:
            pass

        current_app.logger.exception(
            "Falha ao preparar importação"
        )

        return jsonify(
            ok=False,
            error=(
                "Não foi possível preparar "
                "a importação."
            ),
        ), 500


@bp.post(
    "/<int:importacao_id>/cancelar"
)
@require_level(3)
def cancelar(importacao_id):
    usuario = current_user()

    with _import_lock:
        item = db.session.get(
            HistoricoImportacao,
            importacao_id,
        )

        if not item:
            return jsonify(
                ok=False,
                error=(
                    "Importação não encontrada."
                ),
            ), 404

        if item.status not in (
            STATUS_CANCELAVEIS
        ):
            return jsonify(
                ok=False,
                error=(
                    "Esta importação já foi "
                    "concluída e não pode mais "
                    "ser cancelada."
                ),
            ), 409

        if item.cancelamento_solicitado:
            return jsonify(
                ok=True,
                already_requested=True,
                message=(
                    "O cancelamento desta "
                    "importação já foi solicitado."
                ),
            )

        item.cancelamento_solicitado = True

        item.cancelamento_solicitado_em = (
            datetime.utcnow()
        )

        item.cancelado_por_usuario_id = (
            usuario.id
        )

        item.status = (
            "Cancelamento solicitado"
        )

        item.mensagem = (
            "Cancelamento solicitado. "
            "Interrompendo a importação..."
        )

        db.session.commit()

    return jsonify(
        ok=True,
        message=(
            "Cancelamento solicitado. "
            "Interrompendo a importação..."
        ),
    )


@bp.get(
    "/<int:importacao_id>/status"
)
@require_level(3)
def status(importacao_id):
    item = db.session.get(
        HistoricoImportacao,
        importacao_id,
    )

    if not item:
        return jsonify(
            ok=False,
            error=(
                "Importação não encontrada."
            ),
        ), 404

    return jsonify(
        ok=True,
        importacao=_historico_payload(
            item
        ),
    )