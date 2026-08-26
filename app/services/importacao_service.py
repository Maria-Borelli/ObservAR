import csv
import hashlib
import os

import pandas as pd
from sqlalchemy import insert

from app.models import (
    EstacaoMonitoramento,
    MedicaoQualidadeAr,
    Municipio,
    ParametroMonitorado,
    db,
)


REQUIRED = {
    "no_fonte_dados",
    "dh_medicao",
    "no_item_monitorado",
    "id_estacao",
    "no_estacao",
    "id_municipio",
    "no_municipio",
}


OPTIONAL = {
    "nu_iqar",
    "nu_concentracao",
    "st_situacao",
    "cd_flag",
    "ds_flag",
    "st_situacao_iqar",
    "cd_normalizado",
    "cod_estacao",
    "nu_latitude",
    "nu_longitude",
    "st_estacao",
}


DEFAULT_CHUNK_SIZE = 1000


class ImportacaoCancelada(Exception):
    def __init__(self, resultado):
        super().__init__(
            "Importação cancelada."
        )

        self.resultado = resultado


def clean(value):
    """
    Converte valores vazios, NaN e NaT do pandas
    para None antes de enviar ao banco.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        if value.lower() in {
            "none",
            "nan",
            "nat",
            "null",
        }:
            return None

    return value


def _valor_comparavel(value):
    """
    Normaliza valores usados apenas para verificar
    se existe conflito entre duas medições.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()

    return value


def calcular_hash_arquivo(
    path,
    block_size=1024 * 1024,
):
    """
    Calcula o SHA-256 do arquivo inteiro sem
    carregar todo o conteúdo na memória.
    """

    digest = hashlib.sha256()

    with open(path, "rb") as arquivo:
        while True:
            bloco = arquivo.read(
                block_size
            )

            if not bloco:
                break

            digest.update(
                bloco
            )

    return digest.hexdigest()


def detectar_formato_csv(path):
    """
    Tenta identificar codificação e delimitador
    do CSV.
    """

    with open(path, "rb") as arquivo:
        amostra_bytes = arquivo.read(
            64 * 1024
        )

    if not amostra_bytes:
        raise ValueError(
            "O arquivo CSV está vazio."
        )

    texto = None
    encoding_escolhido = None

    for encoding in (
        "utf-8-sig",
        "utf-8",
        "latin-1",
    ):
        try:
            texto = amostra_bytes.decode(
                encoding
            )

            encoding_escolhido = (
                encoding
            )

            break

        except UnicodeDecodeError:
            continue

    if texto is None:
        raise ValueError(
            "Não foi possível identificar "
            "a codificação do arquivo."
        )

    try:
        dialect = csv.Sniffer().sniff(
            texto,
            delimiters=",;\t|",
        )

        sep = dialect.delimiter

    except csv.Error:
        sep = ","

    return (
        sep,
        encoding_escolhido,
    )


def validar_csv(
    path,
    sep=None,
    encoding=None,
):
    """
    Valida o CSV antes do início da importação.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Arquivo não encontrado: {path}"
        )

    if sep is None or encoding is None:
        (
            detected_sep,
            detected_encoding,
        ) = detectar_formato_csv(
            path
        )

        sep = (
            sep
            or detected_sep
        )

        encoding = (
            encoding
            or detected_encoding
        )

    try:
        cabecalho = pd.read_csv(
            path,
            sep=sep,
            encoding=encoding,
            nrows=0,
        )

    except (
        UnicodeDecodeError,
        pd.errors.ParserError,
    ) as erro:
        raise ValueError(
            "O arquivo enviado não possui "
            "o formato esperado."
        ) from erro

    missing = sorted(
        REQUIRED
        - set(
            cabecalho.columns
        )
    )

    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(
                missing
            )
        )

    return {
        "sep": sep,
        "encoding": encoding,
        "colunas": list(
            cabecalho.columns
        ),
    }


def contar_linhas(
    path,
    encoding="utf-8",
):
    """
    Conta as linhas do CSV sem carregar
    o arquivo inteiro na memória.
    """

    try:
        with open(
            path,
            "r",
            encoding=encoding,
            errors="ignore",
        ) as arquivo:
            quantidade = sum(
                1
                for _ in arquivo
            )

        return max(
            quantidade - 1,
            0,
        )

    except Exception:
        return 0


def separar_linhas_invalidas(
    chunk,
):
    """
    Remove linhas sem os campos mínimos necessários
    para criar município, estação, parâmetro
    e medição.

    Retorna:
        dataframe_valido
        quantidade_de_erros
    """

    obrigatorios_linha = [
        "no_fonte_dados",
        "dh_medicao",
        "no_item_monitorado",
        "id_estacao",
        "no_estacao",
        "id_municipio",
        "no_municipio",
    ]

    mascara_invalida = pd.Series(
        False,
        index=chunk.index,
    )

    for coluna in obrigatorios_linha:
        valores = chunk[
            coluna
        ]

        vazio = (
            valores.isna()
            | valores
            .astype(str)
            .str.strip()
            .eq("")
            | valores
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(
                {
                    "none",
                    "nan",
                    "nat",
                    "null",
                }
            )
        )

        mascara_invalida = (
            mascara_invalida
            | vazio
        )

    quantidade_erros = int(
        mascara_invalida.sum()
    )

    chunk_valido = (
        chunk.loc[
            ~mascara_invalida
        ]
        .copy()
    )

    return (
        chunk_valido,
        quantidade_erros,
    )


def preparar_chunk(
    chunk,
):
    """
    Trata data/hora e campos numéricos do lote.

    Se existir qualquer valor inválido em dh_medicao,
    a importação é interrompida.
    """

    chunk = chunk.copy()

    chunk[
        "dh_medicao"
    ] = pd.to_datetime(
        chunk[
            "dh_medicao"
        ],
        errors="coerce",
    )

    if (
        chunk[
            "dh_medicao"
        ]
        .isna()
        .any()
    ):
        raise ValueError(
            "Há valores inválidos em dh_medicao."
        )

    for coluna in (
        "nu_iqar",
        "nu_concentracao",
        "nu_latitude",
        "nu_longitude",
    ):
        if coluna in chunk.columns:
            chunk[
                coluna
            ] = pd.to_numeric(
                chunk[
                    coluna
                ]
                .astype(str)
                .str.replace(
                    ",",
                    ".",
                    regex=False,
                ),
                errors="coerce",
            )

    return chunk


def _carregar_referencias_chunk(
    chunk,
    importacao_id=None,
):
    """
    Busca referências já existentes e cria somente
    municípios, estações e parâmetros ausentes.

    Os registros criados recebem o identificador da
    importação para permitir limpeza em caso de
    cancelamento.
    """

    municipio_ids = {
        str(
            clean(v)
        )
        for v in chunk[
            "id_municipio"
        ].tolist()
        if clean(v) is not None
    }

    estacao_ids = {
        str(
            clean(v)
        )
        for v in chunk[
            "id_estacao"
        ].tolist()
        if clean(v) is not None
    }

    parametro_nomes = {
        str(
            clean(v)
        )
        for v in chunk[
            "no_item_monitorado"
        ].tolist()
        if clean(v) is not None
    }

    municipios = {}

    if municipio_ids:
        municipios = {
            str(
                item.id_oficial
            ): item
            for item in (
                Municipio.query
                .filter(
                    Municipio.id_oficial.in_(
                        municipio_ids
                    )
                )
                .all()
            )
        }

    estacoes = {}

    if estacao_ids:
        estacoes = {
            str(
                item.id_oficial
            ): item
            for item in (
                EstacaoMonitoramento.query
                .filter(
                    EstacaoMonitoramento
                    .id_oficial
                    .in_(
                        estacao_ids
                    )
                )
                .all()
            )
        }

    parametros = {}

    if parametro_nomes:
        parametros = {
            item.nome: item
            for item in (
                ParametroMonitorado.query
                .filter(
                    ParametroMonitorado
                    .nome
                    .in_(
                        parametro_nomes
                    )
                )
                .all()
            )
        }

 

    for _, r in (
        chunk
        .drop_duplicates(
            subset=[
                "id_municipio"
            ]
        )
        .iterrows()
    ):
        valor_id = clean(
            r.get(
                "id_municipio"
            )
        )

        nome = clean(
            r.get(
                "no_municipio"
            )
        )

        if (
            valor_id is None
            or nome is None
        ):
            continue

        key = str(
            valor_id
        )

        if key in municipios:
            continue

        obj = Municipio(
            id_oficial=key,
            nome=str(
                nome
            ),
            criado_por_importacao_id=(
                importacao_id
            ),
        )

        db.session.add(
            obj
        )

        municipios[
            key
        ] = obj

    db.session.flush()

 
    for _, r in (
        chunk
        .drop_duplicates(
            subset=[
                "id_estacao"
            ]
        )
        .iterrows()
    ):
        valor_id = clean(
            r.get(
                "id_estacao"
            )
        )

        nome_estacao = clean(
            r.get(
                "no_estacao"
            )
        )

        municipio_id = clean(
            r.get(
                "id_municipio"
            )
        )

        if (
            valor_id is None
            or nome_estacao is None
            or municipio_id is None
        ):
            continue

        key = str(
            valor_id
        )

        if key in estacoes:
            continue

        mun = municipios.get(
            str(
                municipio_id
            )
        )

        if mun is None:
            continue

        obj = EstacaoMonitoramento(
            id_oficial=key,
            codigo=clean(
                r.get(
                    "cod_estacao"
                )
            ),
            nome=str(
                nome_estacao
            ),
            latitude=clean(
                r.get(
                    "nu_latitude"
                )
            ),
            longitude=clean(
                r.get(
                    "nu_longitude"
                )
            ),
            situacao=clean(
                r.get(
                    "st_estacao"
                )
            ),
            municipio_id=(
                mun.id
            ),
            criado_por_importacao_id=(
                importacao_id
            ),
        )

        db.session.add(
            obj
        )

        estacoes[
            key
        ] = obj

    db.session.flush()

 
    for _, r in (
        chunk
        .drop_duplicates(
            subset=[
                "no_item_monitorado"
            ]
        )
        .iterrows()
    ):
        key = clean(
            r.get(
                "no_item_monitorado"
            )
        )

        if key is None:
            continue

        key = str(
            key
        )

        if key in parametros:
            continue

        obj = ParametroMonitorado(
            nome=key,
            codigo_normalizado=clean(
                r.get(
                    "cd_normalizado"
                )
            ),
            criado_por_importacao_id=(
                importacao_id
            ),
        )

        db.session.add(
            obj
        )

        parametros[
            key
        ] = obj

    db.session.flush()

    return (
        municipios,
        estacoes,
        parametros,
    )


def _chave_medicao(
    r,
):
    """
    Cria a chave única lógica da medição.
    """

    estacao_id = str(
        clean(
            r.get(
                "id_estacao"
            )
        )
    )

    parametro_nome = str(
        clean(
            r.get(
                "no_item_monitorado"
            )
        )
    )

    fonte = clean(
        r.get(
            "no_fonte_dados"
        )
    )

    data_hora = r[
        "dh_medicao"
    ]

    raw = (
        f"{estacao_id}|"
        f"{parametro_nome}|"
        f"{data_hora.isoformat()}|"
        f"{fonte}"
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


def _payload_medicao(
    r,
    key,
    estacao_obj,
    parametro_obj,
    importacao_id=None,
):
    """
    Monta os dados da medição que serão enviados
    para o banco.
    """

    return {
        "chave_importacao":
            key,

        "fonte":
            clean(
                r.get(
                    "no_fonte_dados"
                )
            ),

        "data_hora":
            r[
                "dh_medicao"
            ],

        "iqar":
            clean(
                r.get(
                    "nu_iqar"
                )
            ),

        "concentracao":
            clean(
                r.get(
                    "nu_concentracao"
                )
            ),

        "situacao":
            clean(
                r.get(
                    "st_situacao"
                )
            ),

        "codigo_flag":
            clean(
                r.get(
                    "cd_flag"
                )
            ),

        "descricao_flag":
            clean(
                r.get(
                    "ds_flag"
                )
            ),

        "situacao_iqar":
            clean(
                r.get(
                    "st_situacao_iqar"
                )
            ),

        "estacao_id":
            estacao_obj.id,

        "parametro_id":
            parametro_obj.id,

        "importacao_id":
            importacao_id,
    }


def limpar_importacao(
    importacao_id,
):
    """
    Remove somente os registros criados pela
    importação informada.

    A ordem é:
    1. medições;
    2. parâmetros sem uso;
    3. estações sem uso;
    4. municípios sem estações.
    """

    removidas = (
        MedicaoQualidadeAr.query
        .filter_by(
            importacao_id=(
                importacao_id
            )
        )
        .delete(
            synchronize_session=False
        )
    )

    db.session.flush()

 
    parametros = (
        ParametroMonitorado.query
        .filter_by(
            criado_por_importacao_id=(
                importacao_id
            )
        )
        .all()
    )

    for parametro in parametros:
        possui_medicoes = (
            MedicaoQualidadeAr.query
            .filter_by(
                parametro_id=(
                    parametro.id
                )
            )
            .first()
        )

        if not possui_medicoes:
            db.session.delete(
                parametro
            )

    db.session.flush()

 
    estacoes = (
        EstacaoMonitoramento.query
        .filter_by(
            criado_por_importacao_id=(
                importacao_id
            )
        )
        .all()
    )

    for estacao in estacoes:
        possui_medicoes = (
            MedicaoQualidadeAr.query
            .filter_by(
                estacao_id=(
                    estacao.id
                )
            )
            .first()
        )

        if not possui_medicoes:
            db.session.delete(
                estacao
            )

    db.session.flush()

 
    municipios = (
        Municipio.query
        .filter_by(
            criado_por_importacao_id=(
                importacao_id
            )
        )
        .all()
    )

    for municipio in municipios:
        possui_estacoes = (
            EstacaoMonitoramento.query
            .filter_by(
                municipio_id=(
                    municipio.id
                )
            )
            .first()
        )

        if not possui_estacoes:
            db.session.delete(
                municipio
            )

    db.session.commit()

    return int(
        removidas
        or 0
    )


def _ha_conflito(
    existing,
    novo,
):
    """
    Verifica se a mesma chave representa
    conteúdo diferente.
    """

    campos = (
        "fonte",
        "data_hora",
        "iqar",
        "concentracao",
        "situacao",
        "codigo_flag",
        "descricao_flag",
        "situacao_iqar",
        "estacao_id",
        "parametro_id",
    )

    for campo in campos:
        antigo = _valor_comparavel(
            getattr(
                existing,
                campo,
            )
        )

        atual = _valor_comparavel(
            novo[
                campo
            ]
        )

        if antigo != atual:
            return True

    return False


def _inserir_em_lote(
    rows,
):
    """
    Insere novas medições com proteção adicional
    de unicidade.

    MySQL:
        INSERT IGNORE

    SQLite:
        OR IGNORE
    """

    if not rows:
        return 0

    dialect = (
        db.session
        .get_bind()
        .dialect
        .name
    )

    stmt = insert(
        MedicaoQualidadeAr
    ).values(
        rows
    )

    if dialect == "mysql":
        stmt = stmt.prefix_with(
            "IGNORE"
        )

    elif dialect == "sqlite":
        stmt = stmt.prefix_with(
            "OR IGNORE"
        )

    resultado = db.session.execute(
        stmt
    )

    db.session.commit()

    if (
        resultado.rowcount is None
        or resultado.rowcount < 0
    ):
        return len(
            rows
        )

    return int(
        resultado.rowcount
    )


def _resultado_cancelamento(
    lidos,
    considerados,
    inserted,
    duplicates,
    conflicts,
    errors,
    numero_lote,
    chunk_size,
    total_arquivo,
):
    """
    Cria o resumo usado quando a importação
    é interrompida pelo cancelamento.
    """

    return {
        "lidos":
            lidos,

        "considerados":
            considerados,

        "inseridos":
            inserted,

        "duplicados":
            duplicates,

        "conflitos":
            conflicts,

        "erros":
            errors,

        "lotes":
            numero_lote,

        "tamanho_lote":
            chunk_size,

        "total_arquivo":
            total_arquivo,
    }


def import_csv(
    path,
    sep=None,
    encoding=None,
    municipio=None,
    estacao=None,
    inicio=None,
    fim=None,
    chunk_size=DEFAULT_CHUNK_SIZE,
    mostrar_progresso=True,
    progress_callback=None,
    importacao_id=None,
    cancel_check=None,
):
    """
    Importa dados MonitorAr em lotes de 1.000.

    A cada lote:
    - verifica cancelamento;
    - valida linhas;
    - trata dados;
    - aplica filtros;
    - consulta referências em bloco;
    - detecta duplicados;
    - detecta conflitos;
    - verifica cancelamento novamente;
    - insere somente os registros novos;
    - realiza commit;
    - atualiza o progresso;
    - verifica cancelamento novamente.
    """

    validacao = validar_csv(
        path,
        sep=sep,
        encoding=encoding,
    )

    sep = validacao[
        "sep"
    ]

    encoding = validacao[
        "encoding"
    ]

    if chunk_size <= 0:
        raise ValueError(
            "O tamanho do lote deve "
            "ser maior que zero."
        )

    total_arquivo = contar_linhas(
        path,
        encoding,
    )

    lidos = 0
    considerados = 0
    inserted = 0
    duplicates = 0
    conflicts = 0
    errors = 0
    numero_lote = 0

 
    if mostrar_progresso:
        print()
        print(
            "=" * 60
        )

        print(
            "IMPORTAÇÃO MONITORAR"
        )

        print(
            "=" * 60
        )

        if total_arquivo:
            print(
                (
                    "Registros no arquivo: "
                    f"{total_arquivo:,}"
                ).replace(
                    ",",
                    ".",
                )
            )

        print(
            (
                "Tamanho do lote: "
                f"{chunk_size:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            "-" * 60
        )

    reader = pd.read_csv(
        path,
        sep=sep,
        encoding=encoding,
        dtype=str,
        chunksize=chunk_size,
    )

    try:
        for chunk in reader:
            numero_lote += 1


            if (
                cancel_check
                and cancel_check()
            ):
                raise ImportacaoCancelada(
                    _resultado_cancelamento(
                        lidos=(
                            lidos
                        ),
                        considerados=(
                            considerados
                        ),
                        inserted=(
                            inserted
                        ),
                        duplicates=(
                            duplicates
                        ),
                        conflicts=(
                            conflicts
                        ),
                        errors=(
                            errors
                        ),
                        numero_lote=(
                            numero_lote
                            - 1
                        ),
                        chunk_size=(
                            chunk_size
                        ),
                        total_arquivo=(
                            total_arquivo
                        ),
                    )
                )

            lidos += len(
                chunk
            )


            (
                chunk,
                erros_obrigatorios,
            ) = separar_linhas_invalidas(
                chunk
            )

            errors += (
                erros_obrigatorios
            )

            if chunk.empty:
                status = {
                    "lote":
                        numero_lote,

                    "lidos":
                        lidos,

                    "considerados":
                        considerados,

                    "inseridos":
                        inserted,

                    "duplicados":
                        duplicates,

                    "conflitos":
                        conflicts,

                    "erros":
                        errors,

                    "total":
                        total_arquivo,
                }

                if progress_callback:
                    progress_callback(
                        status
                    )

                continue

        
            chunk = preparar_chunk(
                chunk
            )


            if municipio:
                chunk = chunk[
                    chunk[
                        "no_municipio"
                    ]
                    == municipio
                ]

            if estacao:
                chunk = chunk[
                    chunk[
                        "id_estacao"
                    ]
                    == str(
                        estacao
                    )
                ]

            if inicio:
                chunk = chunk[
                    chunk[
                        "dh_medicao"
                    ]
                    >= pd.Timestamp(
                        inicio
                    )
                ]

            if fim:
                chunk = chunk[
                    chunk[
                        "dh_medicao"
                    ]
                    <= pd.Timestamp(
                        fim
                    )
                ]

            considerados += len(
                chunk
            )

            if chunk.empty:
                status = {
                    "lote":
                        numero_lote,

                    "lidos":
                        lidos,

                    "considerados":
                        considerados,

                    "inseridos":
                        inserted,

                    "duplicados":
                        duplicates,

                    "conflitos":
                        conflicts,

                    "erros":
                        errors,

                    "total":
                        total_arquivo,
                }

                if progress_callback:
                    progress_callback(
                        status
                    )

                continue


            (
                _,
                estacoes_cache,
                parametros_cache,
            ) = _carregar_referencias_chunk(
                chunk,
                importacao_id=(
                    importacao_id
                ),
            )

            candidatos = []
            chaves_lote = []
            chaves_vistas = {}

            duplicados_mesmo_lote = 0
            conflitos_mesmo_lote = 0


            for _, r in (
                chunk.iterrows()
            ):
                key = _chave_medicao(
                    r
                )

                estacao_valor = clean(
                    r.get(
                        "id_estacao"
                    )
                )

                parametro_valor = clean(
                    r.get(
                        "no_item_monitorado"
                    )
                )

                if (
                    estacao_valor
                    is None
                    or parametro_valor
                    is None
                ):
                    errors += 1

                    continue

                estacao_key = str(
                    estacao_valor
                )

                parametro_key = str(
                    parametro_valor
                )

                estacao_obj = (
                    estacoes_cache
                    .get(
                        estacao_key
                    )
                )

                parametro_obj = (
                    parametros_cache
                    .get(
                        parametro_key
                    )
                )

                if (
                    estacao_obj
                    is None
                    or parametro_obj
                    is None
                ):
                    errors += 1

                    continue

                payload = (
                    _payload_medicao(
                        r,
                        key,
                        estacao_obj,
                        parametro_obj,
                        importacao_id=(
                            importacao_id
                        ),
                    )
                )

                if key in chaves_vistas:
                    if (
                        chaves_vistas[
                            key
                        ]
                        == payload
                    ):
                        (
                            duplicados_mesmo_lote
                        ) += 1

                    else:
                        (
                            conflitos_mesmo_lote
                        ) += 1

                    continue

                chaves_vistas[
                    key
                ] = payload

                candidatos.append(
                    payload
                )

                chaves_lote.append(
                    key
                )

           
            existentes = {}

            if chaves_lote:
                resultados = (
                    MedicaoQualidadeAr
                    .query
                    .filter(
                        MedicaoQualidadeAr
                        .chave_importacao
                        .in_(
                            chaves_lote
                        )
                    )
                    .all()
                )

                for obj in resultados:
                    existentes[
                        obj.chave_importacao
                    ] = obj

            novos = []

            for candidato in candidatos:
                chave = candidato[
                    "chave_importacao"
                ]

                existente = (
                    existentes.get(
                        chave
                    )
                )

                if existente is None:
                    novos.append(
                        candidato
                    )

                elif _ha_conflito(
                    existente,
                    candidato,
                ):
                    conflicts += 1

                else:
                    duplicates += 1

            duplicates += (
                duplicados_mesmo_lote
            )

            conflicts += (
                conflitos_mesmo_lote
            )

          
            if (
                cancel_check
                and cancel_check()
            ):
          
                db.session.rollback()

                raise ImportacaoCancelada(
                    _resultado_cancelamento(
                        lidos=(
                            lidos
                        ),
                        considerados=(
                            considerados
                        ),
                        inserted=(
                            inserted
                        ),
                        duplicates=(
                            duplicates
                        ),
                        conflicts=(
                            conflicts
                        ),
                        errors=(
                            errors
                        ),
                        numero_lote=(
                            numero_lote
                            - 1
                        ),
                        chunk_size=(
                            chunk_size
                        ),
                        total_arquivo=(
                            total_arquivo
                        ),
                    )
                )

          
            inseridos_lote = (
                _inserir_em_lote(
                    novos
                )
            )

            duplicates += max(
                len(
                    novos
                )
                - inseridos_lote,
                0,
            )

            inserted += (
                inseridos_lote
            )

            status = {
                "lote":
                    numero_lote,

                "lidos":
                    lidos,

                "considerados":
                    considerados,

                "inseridos":
                    inserted,

                "duplicados":
                    duplicates,

                "conflitos":
                    conflicts,

                "erros":
                    errors,

                "total":
                    total_arquivo,
            }

            if progress_callback:
                progress_callback(
                    status
                )

           
            if (
                cancel_check
                and cancel_check()
            ):
                raise ImportacaoCancelada(
                    _resultado_cancelamento(
                        lidos=(
                            lidos
                        ),
                        considerados=(
                            considerados
                        ),
                        inserted=(
                            inserted
                        ),
                        duplicates=(
                            duplicates
                        ),
                        conflicts=(
                            conflicts
                        ),
                        errors=(
                            errors
                        ),
                        numero_lote=(
                            numero_lote
                        ),
                        chunk_size=(
                            chunk_size
                        ),
                        total_arquivo=(
                            total_arquivo
                        ),
                    )
                )

         
            if mostrar_progresso:
                if total_arquivo:
                    percentual = min(
                        (
                            lidos
                            / total_arquivo
                        )
                        * 100,
                        100,
                    )

                    texto = (
                        f"Lote {numero_lote:>4} | "
                        f"{lidos:,} / "
                        f"{total_arquivo:,} "
                        f"({percentual:6.2f}%) | "
                        f"Inseridos: "
                        f"{inserted:,} | "
                        f"Duplicados: "
                        f"{duplicates:,} | "
                        f"Conflitos: "
                        f"{conflicts:,} | "
                        f"Erros: "
                        f"{errors:,}"
                    )

                    print(
                        texto.replace(
                            ",",
                            ".",
                        )
                    )

                else:
                    texto = (
                        f"Lote {numero_lote:>4} | "
                        f"Lidos: "
                        f"{lidos:,} | "
                        f"Inseridos: "
                        f"{inserted:,} | "
                        f"Duplicados: "
                        f"{duplicates:,} | "
                        f"Conflitos: "
                        f"{conflicts:,} | "
                        f"Erros: "
                        f"{errors:,}"
                    )

                    print(
                        texto.replace(
                            ",",
                            ".",
                        )
                    )

    except ImportacaoCancelada:
        db.session.rollback()

        raise

    except Exception:
        db.session.rollback()

        raise

    finally:
        reader.close()
 

    if mostrar_progresso:
        print(
            "-" * 60
        )

        print(
            "IMPORTAÇÃO CONCLUÍDA"
        )

        print(
            "-" * 60
        )

        print(
            (
                f"Linhas lidas: "
                f"{lidos:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            (
                "Linhas consideradas: "
                f"{considerados:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            (
                "Registros inseridos: "
                f"{inserted:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            (
                "Duplicados ignorados: "
                f"{duplicates:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            (
                "Conflitos preservados: "
                f"{conflicts:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            (
                "Registros com erro: "
                f"{errors:,}"
            ).replace(
                ",",
                ".",
            )
        )

        print(
            "=" * 60
        )

        print()

    return {
        "lidos":
            lidos,

        "considerados":
            considerados,

        "inseridos":
            inserted,

        "duplicados":
            duplicates,

        "conflitos":
            conflicts,

        "erros":
            errors,

        "lotes":
            numero_lote,

        "tamanho_lote":
            chunk_size,

        "total_arquivo":
            total_arquivo,
    }