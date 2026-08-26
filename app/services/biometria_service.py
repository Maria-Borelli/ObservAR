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

def extract_template(data_url, backend="face_recognition"):
    img=decode_image(data_url); faces=detect_faces(img)
    if len(faces)!=1: raise BiometricError("É necessário exatamente um rosto na imagem.")
    if backend!="face_recognition": raise BiometricError("Backend biométrico real não disponível/configurado.")
    fr=_face_recognition()
    rgb=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    enc=fr.face_encodings(rgb)
    if len(enc)!=1: raise BiometricError("Não foi possível extrair a representação facial.")
    return np.asarray(enc[0], dtype=np.float64).tobytes()

def compare(data_url, stored, backend="face_recognition", tolerance=.50):
    candidate=np.frombuffer(extract_template(data_url, backend), dtype=np.float64)
    reference=np.frombuffer(stored, dtype=np.float64)
    if candidate.shape != reference.shape: return False
    return float(np.linalg.norm(candidate-reference)) <= tolerance
