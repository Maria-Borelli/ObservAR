import argparse

from app import create_app
from app.services.importacao_service import import_csv


parser = argparse.ArgumentParser(
    description=(
        "Importador de dados MonitorAr "
        "para MySQL."
    )
)

parser.add_argument(
    "csv",
    help="Caminho para o arquivo CSV.",
)

parser.add_argument(
    "--sep",
    default=",",
    help="Separador do CSV. Padrão: vírgula.",
)

parser.add_argument(
    "--encoding",
    default="utf-8",
    help="Codificação. Padrão: utf-8.",
)

parser.add_argument(
    "--municipio",
)

parser.add_argument(
    "--estacao",
)

parser.add_argument(
    "--inicio",
)

parser.add_argument(
    "--fim",
)

parser.add_argument(
    "--chunk-size",
    type=int,
    default=1000,
    help=(
        "Quantidade de registros "
        "processados por lote. "
        "Padrão: 1000."
    ),
)

args = parser.parse_args()


app = create_app()


with app.app_context():

    try:

        resultado = import_csv(
            path=args.csv,
            sep=args.sep,
            encoding=args.encoding,
            municipio=args.municipio,
            estacao=args.estacao,
            inicio=args.inicio,
            fim=args.fim,
            chunk_size=args.chunk_size,
            mostrar_progresso=True,
        )

        print("Resumo retornado:")
        print(resultado)

    except KeyboardInterrupt:

        print()
        print(
            "Importação interrompida "
            "pelo usuário."
        )

    except Exception as erro:

        raise SystemExit(
            f"Importação cancelada: {erro}"
        )