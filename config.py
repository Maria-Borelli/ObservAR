import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root@127.0.0.1:3306/monitorar_aps")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_MINUTES", "30")))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    BIOMETRIC_BACKEND = os.getenv("BIOMETRIC_BACKEND", "face_recognition")
    BIOMETRIC_TOLERANCE = float(os.getenv("BIOMETRIC_TOLERANCE", "0.50"))
    DEMO_BIOMETRIC_MODE = os.getenv("DEMO_BIOMETRIC_MODE", "0") == "1"

    IMPORT_CHUNK_SIZE = int(os.getenv("IMPORT_CHUNK_SIZE", "1000"))
    IMPORT_MAX_FILE_MB = int(os.getenv("IMPORT_MAX_FILE_MB", "1024"))
    MAX_CONTENT_LENGTH = IMPORT_MAX_FILE_MB * 1024 * 1024
