"""
engine/auth.py - Módulo de autenticación y control de acceso por roles para PAI Risaralda.
"""
import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USUARIOS_FILE = os.path.join(BASE_DIR, "storage", "usuarios.json")

# Almacenamiento en memoria de sesiones activas: {token: {"usuario": str, "rol": str, "municipio": str, "exp": datetime}}
SESIONES_ACTIVAS = {}
DURACION_SESION_HORAS = 24

def _cargar_usuarios() -> dict:
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def hash_password(password: str) -> str:
    """Genera hash SHA-256 de la contraseña."""
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()

def autenticar_usuario(usuario: str, password: str) -> dict | None:
    """Verifica credenciales y retorna los datos del usuario si es válido."""
    usuarios = _cargar_usuarios()
    usuario_key = usuario.strip().lower()
    
    # Buscar por clave exacta o insensible a mayúsculas
    user_data = None
    for k, v in usuarios.items():
        if k.lower() == usuario_key or v.get("usuario", "").lower() == usuario_key:
            user_data = v
            break
            
    if not user_data:
        return None
        
    # Verificar contraseña (soporta hash guardado o coincidencia con clave_inicial inicial)
    pwd_hash = hash_password(password)
    clave_directa = user_data.get("clave_inicial")
    
    if pwd_hash == user_data.get("password_hash") or (clave_directa and password.strip() == clave_directa):
        token = f"PAI-SEC-{str(uuid.uuid4()).replace('-', '')[:24]}"
        exp = datetime.now() + timedelta(hours=DURACION_SESION_HORAS)
        
        info_sesion = {
            "token": token,
            "usuario": user_data["usuario"],
            "nombre": user_data["nombre"],
            "rol": user_data["rol"],
            "municipio": user_data.get("municipio"),
            "dane": user_data.get("dane"),
            "exp": exp
        }
        SESIONES_ACTIVAS[token] = info_sesion
        return info_sesion
        
    return None

def verificar_token(token: str) -> dict | None:
    """Valida si un token de sesión está activo y vigente."""
    if not token:
        return None
    sesion = SESIONES_ACTIVAS.get(token)
    if not sesion:
        return None
    if datetime.now() > sesion["exp"]:
        del SESIONES_ACTIVAS[token]
        return None
    return sesion

def cerrar_sesion(token: str) -> bool:
    """Invalida un token de sesión."""
    if token in SESIONES_ACTIVAS:
        del SESIONES_ACTIVAS[token]
        return True
    return False

def obtener_perfil_municipio(municipio_nombre: str) -> dict | None:
    """Retorna información municipal a partir del nombre."""
    usuarios = _cargar_usuarios()
    for _, v in usuarios.items():
        if v.get("municipio") and v["municipio"].upper() == municipio_nombre.strip().upper():
            return v
    return None
