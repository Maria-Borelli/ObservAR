from app.services.biometria_service import decode_image, BiometricError
def test_imagem_invalida():
    try: decode_image("x"); assert False
    except BiometricError: pass
