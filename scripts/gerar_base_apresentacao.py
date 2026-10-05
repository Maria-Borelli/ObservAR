from pathlib import Path

import pandas as pd


CHUNK_SIZE = 250_000

ARQUIVOS = {
    "2024": Path(
        r"C:\Users\borel\Downloads"
        r"\dados_monitorar_2024"
        r"\Dados_MonitorAr_2024.csv"
    ),
    "2025": Path(
        r"D:\Projetos\APS\dados"
        r"\Dados_MonitorAr_2025.csv"
    ),
}

PASTA_SAIDA = Path(
    r"D:\Projetos\APS\dados\apresentacao"
)

MES_INICIAL = 1
MES_FINAL = 6


def gerar_csv_reduzido(
    ano: str,
    origem: Path,
) -> None:
    destino = PASTA_SAIDA / (
        f"Dados_MonitorAr_{ano}_apresentacao.csv"
    )

    print()
    print("=" * 60)
    print(f"Processando {ano}")
    print(f"Origem : {origem}")
    print(f"Destino: {destino}")
    print("=" * 60)

    if not origem.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {origem}"
        )

    if destino.exists():
        destino.unlink()

    total_lido = 0
    total_mantido = 0
    primeiro_chunk = True

    for numero_chunk, df in enumerate(
        pd.read_csv(
            origem,
            chunksize=CHUNK_SIZE,
        ),
        start=1,
    ):
        total_lido += len(df)

        datas = pd.to_datetime(
            df["dh_medicao"],
            errors="coerce",
        )

        mascara = (
            datas.dt.month.between(
                MES_INICIAL,
                MES_FINAL,
            )
        )

        reduzido = df.loc[mascara]

        total_mantido += len(reduzido)

        if not reduzido.empty:
            reduzido.to_csv(
                destino,
                mode="w" if primeiro_chunk else "a",
                header=primeiro_chunk,
                index=False,
            )

            primeiro_chunk = False

        print(
            f"Chunk {numero_chunk:02d} | "
            f"Lidos: {total_lido:,} | "
            f"Mantidos: {total_mantido:,}"
        )

    percentual = (
        total_mantido / total_lido * 100
        if total_lido
        else 0
    )

    print()
    print(f"{ano} concluído.")
    print(f"Registros originais : {total_lido:,}")
    print(f"Registros mantidos  : {total_mantido:,}")
    print(f"Percentual mantido  : {percentual:.2f}%")
    print(f"Arquivo             : {destino}")


def main() -> None:
    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Gerando base reduzida para apresentação."
    )
    print(
        f"Período mantido: meses "
        f"{MES_INICIAL:02d} a {MES_FINAL:02d}."
    )

    for ano, origem in ARQUIVOS.items():
        gerar_csv_reduzido(
            ano,
            origem,
        )

    print()
    print("=" * 60)
    print("BASE DE APRESENTAÇÃO GERADA COM SUCESSO")
    print("=" * 60)


if __name__ == "__main__":
    main()