"""
Valida que o face_recognition foi instalado corretamente e consegue
carregar os modelos do dlib. Usado pelo instalar_face_recognition.ps1.

Sai com código 0 em sucesso, 1 em falha.
"""

import sys
import warnings

# O face_recognition_models ainda usa pkg_resources (depreciado); silencia
# o aviso para não poluir a saída da validação.
warnings.filterwarnings("ignore", category=UserWarning)


def main():
    try:
        import numpy as np
        import face_recognition as fr
    except Exception as erro:  # noqa: BLE001
        print(f"[ERRO] Falha ao importar face_recognition: {erro}")
        return 1

    try:
        # Imagem sintética só para exercitar o pipeline e carregar os modelos.
        img = (np.random.rand(100, 100, 3) * 255).astype("uint8")
        encodings = fr.face_encodings(img)
    except Exception as erro:  # noqa: BLE001
        print(f"[ERRO] face_recognition importou, mas falhou ao processar: {erro}")
        return 1

    print(
        "[OK] face_recognition funcionando. "
        f"(encodings numa imagem aleatoria: {len(encodings)}, esperado 0)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
