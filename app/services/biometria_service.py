import base64, io, os
import numpy as np
import cv2

class BiometricError(Exception): pass

def decode_image(data_url):
    try:
        raw=data_url.split(",",1)[-1]
        arr=np.frombuffer(base64.b64decode(raw), np.uint8)
        img=cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None: raise ValueError
        return img
    except Exception as e: raise BiometricError("Imagem inválida.") from e

def detect_faces(img):
    gray=cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    return cascade.detectMultiScale(gray, 1.1, 5, minSize=(80,80))

def _face_recognition():
    try: import face_recognition as fr; return fr
    except ImportError as e:
        raise BiometricError("Backend face_recognition não instalado. Instale a dependência opcional ou configure outro backend.") from e


# ---------------------------------------------------------------------------
# Backend OpenCV (sem dlib): extrai um descritor da face usando apenas OpenCV.
#
# A face é recortada, convertida para tons de cinza, redimensionada para um
# tamanho fixo e equalizada. Em seguida é extraído um descritor LBP
# (Local Binary Patterns) em histograma por células, que captura a textura
# da face e distingue pessoas muito melhor que os pixels crus. A comparação
# é feita por interseção de histograma.
# Não é tão robusto quanto o face_recognition, mas funciona em qualquer
# máquina sem dependências de compilação.
# ---------------------------------------------------------------------------

# A face é normalizada para 50x50 antes de extrair o LBP.
_OPENCV_FACE_SIZE = (50, 50)


def _maior_face(faces):
    # Retorna a face de maior área (x, y, w, h).
    return max(faces, key=lambda f: f[2] * f[3])


# Grade de células para o histograma LBP. A face 50x50 é dividida em 5x5
# células de 10x10 px; cada célula gera um histograma LBP de 256 posições.
_LBP_GRID = (5, 5)
_LBP_BINS = 256


def _lbp(gray):
    # Local Binary Pattern 3x3 clássico (sem uniform), implementado com numpy.
    centro = gray[1:-1, 1:-1]
    codigo = np.zeros(centro.shape, dtype=np.uint8)
    vizinhos = [
        (gray[0:-2, 0:-2], 1),   (gray[0:-2, 1:-1], 2),   (gray[0:-2, 2:], 4),
        (gray[1:-1, 2:], 8),     (gray[2:, 2:], 16),      (gray[2:, 1:-1], 32),
        (gray[2:, 0:-2], 64),    (gray[1:-1, 0:-2], 128),
    ]
    for vizinho, peso in vizinhos:
        codigo = codigo + (vizinho >= centro).astype(np.uint8) * peso
    return codigo


def _descritor_opencv(img):
    faces = detect_faces(img)
    if len(faces) == 0:
        raise BiometricError("Nenhum rosto detectado na imagem.")
    if len(faces) > 1:
        raise BiometricError("É necessário exatamente um rosto na imagem.")

    x, y, w, h = _maior_face(faces)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face = gray[y:y + h, x:x + w]

    if face.size == 0:
        raise BiometricError("Não foi possível recortar o rosto.")

    face = cv2.resize(face, _OPENCV_FACE_SIZE, interpolation=cv2.INTER_AREA)
    face = cv2.equalizeHist(face)

    # LBP capta textura/micropadrões da face, separando pessoas muito melhor
    # que os pixels crus. O descritor é a concatenação dos histogramas LBP
    # de cada célula da grade, cada histograma normalizado (soma = 1).
    lbp = _lbp(face)

    gx, gy = _LBP_GRID
    alt, larg = lbp.shape
    passo_y = alt // gy
    passo_x = larg // gx

    histogramas = []
    for i in range(gy):
        for j in range(gx):
            celula = lbp[
                i * passo_y:(i + 1) * passo_y,
                j * passo_x:(j + 1) * passo_x,
            ]
            hist, _ = np.histogram(
                celula.ravel(),
                bins=_LBP_BINS,
                range=(0, 256),
            )
            soma = hist.sum()
            if soma > 0:
                hist = hist / soma
            histogramas.append(hist)

    vetor = np.concatenate(histogramas).astype(np.float32)
    return vetor


def _extrair_face_recognition(img):
    faces = detect_faces(img)
    if len(faces) != 1:
        raise BiometricError("É necessário exatamente um rosto na imagem.")
    fr = _face_recognition()
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    enc = fr.face_encodings(rgb)
    if len(enc) != 1:
        raise BiometricError("Não foi possível extrair a representação facial.")
    return np.asarray(enc[0], dtype=np.float64)


def extract_template(data_url, backend="opencv"):
    img = decode_image(data_url)

    if backend == "opencv":
        return _descritor_opencv(img).tobytes()

    if backend == "face_recognition":
        return _extrair_face_recognition(img).tobytes()

    raise BiometricError("Backend biométrico não disponível/configurado.")


def compare(data_url, stored, backend="opencv", tolerance=.50):
    # Cada backend usa um dtype diferente no template armazenado.
    dtype = np.float32 if backend == "opencv" else np.float64

    candidate = np.frombuffer(extract_template(data_url, backend), dtype=dtype)
    reference = np.frombuffer(stored, dtype=dtype)

    if candidate.shape != reference.shape:
        return False

    if backend == "opencv":
        return _similaridade_lbp(candidate, reference) >= (1.0 - tolerance)

    # face_recognition: distância euclidiana <= tolerância.
    return float(np.linalg.norm(candidate - reference)) <= tolerance


def _similaridade_lbp(a, b):
    # Interseção de histograma: soma dos mínimos célula a célula.
    # Como cada histograma de célula soma 1 e há N células, o máximo é N;
    # normalizamos pelo nº de células para obter um valor em [0, 1].
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    intersecao = float(np.minimum(a, b).sum())
    n_celulas = _LBP_GRID[0] * _LBP_GRID[1]
    return intersecao / n_celulas
