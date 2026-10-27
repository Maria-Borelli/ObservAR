from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


from .perfil import Perfil
from .usuario import Usuario
from .biometria import BiometriaFacial
from .municipio import Municipio
from .estacao import EstacaoMonitoramento
from .parametro import ParametroMonitorado
from .medicao import MedicaoQualidadeAr
from .analise import AnaliseInterna
from .auditoria import LogAutenticacao, LogAcesso
from .importacao import HistoricoImportacao


__all__ = [
    "db",
    "Perfil",
    "Usuario",
    "BiometriaFacial",
    "Municipio",
    "EstacaoMonitoramento",
    "ParametroMonitorado",
    "MedicaoQualidadeAr",
    "AnaliseInterna",
    "LogAutenticacao",
    "LogAcesso",
    "HistoricoImportacao",
]
