from sqlalchemy import inspect, text

from app import create_app
from app.models import db


def coluna_existe(
    inspector,
    tabela,
    coluna,
):
    return coluna in {
        item["name"]
        for item in inspector.get_columns(
            tabela
        )
    }


def adicionar_coluna(
    tabela,
    coluna,
    definicao,
):
    db.session.execute(
        text(
            f"""
            ALTER TABLE {tabela}
            ADD COLUMN {coluna} {definicao}
            """
        )
    )

    db.session.commit()


def main():
    app = create_app()

    with app.app_context():
        inspector = inspect(
            db.engine
        )

        alteracoes = [
            (
                "municipio",
                "criado_por_importacao_id",
                "INT NULL",
            ),
            (
                "estacao_monitoramento",
                "criado_por_importacao_id",
                "INT NULL",
            ),
            (
                "parametro_monitorado",
                "criado_por_importacao_id",
                "INT NULL",
            ),
            (
                "medicao_qualidade_ar",
                "importacao_id",
                "INT NULL",
            ),
            (
                "historico_importacao",
                "cancelamento_solicitado",
                "BOOLEAN NOT NULL DEFAULT FALSE",
            ),
            (
                "historico_importacao",
                "cancelamento_solicitado_em",
                "DATETIME NULL",
            ),
            (
                "historico_importacao",
                "cancelado_em",
                "DATETIME NULL",
            ),
            (
                "historico_importacao",
                "cancelado_por_usuario_id",
                "INT NULL",
            ),
            (
                "historico_importacao",
                "registros_removidos",
                "INT NOT NULL DEFAULT 0",
            ),
            (
                "historico_importacao",
                "erro_cancelamento",
                "TEXT NULL",
            ),
        ]

        for (
            tabela,
            coluna,
            definicao,
        ) in alteracoes:
            inspector = inspect(
                db.engine
            )

            if coluna_existe(
                inspector,
                tabela,
                coluna,
            ):
                print(
                    f"[OK] {tabela}.{coluna}"
                )
                continue

            adicionar_coluna(
                tabela,
                coluna,
                definicao,
            )

            print(
                f"[CRIADA] "
                f"{tabela}.{coluna}"
            )

        indices = [
            (
                "municipio",
                "idx_municipio_importacao",
                "criado_por_importacao_id",
            ),
            (
                "estacao_monitoramento",
                "idx_estacao_importacao",
                "criado_por_importacao_id",
            ),
            (
                "parametro_monitorado",
                "idx_parametro_importacao",
                "criado_por_importacao_id",
            ),
            (
                "medicao_qualidade_ar",
                "idx_medicao_importacao",
                "importacao_id",
            ),
        ]

        inspector = inspect(
            db.engine
        )

        for tabela, nome, coluna in indices:
            existentes = {
                item["name"]
                for item
                in inspector.get_indexes(
                    tabela
                )
            }

            if nome in existentes:
                continue

            db.session.execute(
                text(
                    f"""
                    CREATE INDEX {nome}
                    ON {tabela} ({coluna})
                    """
                )
            )

            db.session.commit()

            print(
                f"[ÍNDICE] {nome}"
            )

        print()
        print(
            "Atualização concluída."
        )


if __name__ == "__main__":
    main()