"""
engine/kardex_sync.py - Conector y Sincronizador Automático de Kardex con Google Drive / Sheets.
Secretaría de Salud Departamental de Risaralda

Permite conectar automáticamente el sistema con el archivo de Google Sheets o Google Drive
donde el Centro de Acopio Departamental (Depósito de Vacunación) registra el Kardex oficial.
Se actualiza automáticamente el último día de cada mes (y en cualquier momento a demanda)
para garantizar que los cruces de la Regla 3 y el catálogo de 361 lotes estén 100% al día.
"""

import os
import re
import json
import shutil
import zipfile
import calendar
import threading
import time
import datetime
import urllib.request
import urllib.error
import io

from engine.timezone_co import ahora_colombia, ahora_colombia_str
from engine.cruce_deposito import limpiar_cache_kardex, obtener_info_kardex_actual
from engine.validator_movimiento import cargar_lotes_google_sheet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
CATALOGOS_DIR = os.path.join(STORAGE_DIR, "catalogos")
CONFIG_FILE = os.path.join(CATALOGOS_DIR, "kardex_drive_config.json")
KARDEX_FILE = os.path.join(CATALOGOS_DIR, "deposito_risaralda.xlsx")
KARDEX_BACKUP = os.path.join(CATALOGOS_DIR, "deposito_risaralda_backup.xlsx")
CREDENTIALS_FILE = os.path.join(STORAGE_DIR, "google_drive_credentials.json")

os.makedirs(CATALOGOS_DIR, exist_ok=True)

def calcular_proximo_ultimo_dia(fecha=None):
    """Calcula la fecha y hora del próximo último día de mes para la programación (Hora Legal Colombia UTC-5)."""
    if fecha is None:
        fecha = ahora_colombia()
    
    ano = fecha.year
    mes = fecha.month
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    fecha_cierre_actual = fecha.replace(day=ultimo_dia_mes, hour=23, minute=30, second=0, microsecond=0)
    
    if fecha > fecha_cierre_actual:
        # Ya pasó el cierre de este mes, calcular para el siguiente mes
        if mes == 12:
            sig_ano = ano + 1
            sig_mes = 1
        else:
            sig_ano = ano
            sig_mes = mes + 1
        ultimo_dia_sig = calendar.monthrange(sig_ano, sig_mes)[1]
        return fecha.replace(year=sig_ano, month=sig_mes, day=ultimo_dia_sig, hour=23, minute=30, second=0, microsecond=0)
    
    return fecha_cierre_actual

def obtener_config_kardex_drive():
    """Obtiene la configuración actual de conexión con Google Drive / Sheets."""
    config_default = {
        "url_origen": "",
        "auto_sync": True,
        "frecuencia": "ULTIMO_DIA_MES",
        "hora_programada": "23:30",
        "ultima_sincronizacion": None,
        "ultimo_resultado": "PENDIENTE_CONFIGURACION",
        "ultimo_mensaje": "Ingrese el enlace o ID de Google Sheets / Drive para activar la sincronización automática.",
        "tamano_kb": 0,
        "lotes_activos": 0,
        "proxima_sincronizacion": calcular_proximo_ultimo_dia().strftime("%Y-%m-%d %H:%M:%S")
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_default, f, indent=2, ensure_ascii=False)
        return config_default

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Asegurar que todas las llaves existan
            for k, v in config_default.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error leyendo configuración de Kardex Drive: {e}")
        return config_default

def guardar_config_kardex_drive(nueva_config: dict):
    """Actualiza y guarda la configuración de sincronización con Google Drive."""
    actual = obtener_config_kardex_drive()
    actual.update(nueva_config)
    
    # Recalcular próxima fecha si auto_sync está activo
    if actual.get("auto_sync"):
        actual["proxima_sincronizacion"] = calcular_proximo_ultimo_dia().strftime("%Y-%m-%d %H:%M:%S")
    else:
        actual["proxima_sincronizacion"] = "DESACTIVADA"

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(actual, f, indent=2, ensure_ascii=False)

    return actual

def extraer_id_google(texto: str):
    """
    Extrae de forma robusta el ID del recurso de Google Sheets o Google Drive
    a partir de una URL compartida, enlace de edición o ID directo.
    """
    if not texto:
        return None, None
    t = str(texto).strip()

    # Formato 1: URL de Google Sheets (/spreadsheets/d/ID/...)
    m_sheets = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', t)
    if m_sheets:
        return m_sheets.group(1), "sheets"

    # Formato 2: URL de archivo en Google Drive (/file/d/ID/...)
    m_drive = re.search(r'/file/d/([a-zA-Z0-9_-]+)', t)
    if m_drive:
        return m_drive.group(1), "drive"

    # Formato 3: Parámetro id= en URL (drive.google.com/open?id=ID)
    m_id = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', t)
    if m_id:
        return m_id.group(1), "drive"

    # Formato 4: ID alfanumérico directo de Google (entre 25 y 65 caracteres)
    if re.match(r'^[a-zA-Z0-9_-]{25,65}$', t):
        return t, "sheets"

    return None, None

def descargar_kardex_google(url_o_id: str = None):
    """
    Descarga el archivo Excel oficial del Kardex desde Google Sheets o Google Drive.
    Valida su integridad como libro Excel, actualiza el archivo en el servidor,
    invalida cachés y recarga el catálogo de lotes activos.
    """
    cfg = obtener_config_kardex_drive()
    enlace = url_o_id or cfg.get("url_origen")

    if not enlace or not str(enlace).strip():
        return {
            "success": False,
            "error": "No se ha configurado la URL o ID del Google Sheets/Drive del Kardex."
        }

    gid, tipo = extraer_id_google(enlace)
    if not gid:
        return {
            "success": False,
            "error": "El enlace proporcionado no es una URL válida de Google Sheets o Google Drive."
        }

    # Construir URLs de descarga directa
    urls_intento = []
    if tipo == "sheets":
        # Google Sheets export format XLSX directo
        urls_intento.append(f"https://docs.google.com/spreadsheets/d/{gid}/export?format=xlsx")
        urls_intento.append(f"https://drive.google.com/uc?export=download&id={gid}")
    else:
        # Google Drive file download directo
        urls_intento.append(f"https://drive.google.com/uc?export=download&id={gid}&confirm=t")
        urls_intento.append(f"https://docs.google.com/spreadsheets/d/{gid}/export?format=xlsx")

    contenido_bytes = None
    ultimo_error = None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    for u in urls_intento:
        try:
            req = urllib.request.Request(u, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
                # Verificar que sea contenido binario suficiente
                if len(data) > 5000:
                    # Validar si es un archivo ZIP válido (formato base de .xlsx)
                    try:
                        with zipfile.ZipFile(io.BytesIO(data)) as zf:
                            if "xl/workbook.xml" in zf.namelist():
                                contenido_bytes = data
                                break
                    except Exception:
                        pass
        except Exception as e:
            ultimo_error = str(e)

    if not contenido_bytes:
        msg_err = f"No se pudo descargar el archivo Excel desde Google. Verifique que el archivo tenga permisos de acceso 'Cualquier persona con el enlace puede ver' o esté compartido con risaraldapaiweb@gmail.com. Detalle: {ultimo_error or 'Respuesta no válida'}"
        guardar_config_kardex_drive({
            "ultimo_resultado": "ERROR_DESCARGA",
            "ultimo_mensaje": msg_err
        })
        return {
            "success": False,
            "error": msg_err
        }

    # Crear backup del Kardex anterior si existe
    if os.path.exists(KARDEX_FILE):
        try:
            shutil.copy2(KARDEX_FILE, KARDEX_BACKUP)
        except Exception:
            pass

    # Guardar nuevo archivo
    with open(KARDEX_FILE, "wb") as f:
        f.write(contenido_bytes)

    # Invalida caché en memoria de cruce depósito
    limpiar_cache_kardex()

    # Sincronizar dinámicamente el catálogo maestro de lotes desde el libro recién descargado
    total_lotes = 0
    try:
        from engine.validator_movimiento import sincronizar_catalogo_lotes_maestros
        lotes_actualizados = sincronizar_catalogo_lotes_maestros(KARDEX_FILE)
        total_lotes = len(lotes_actualizados)
    except Exception as e:
        print(f"Error sincronizando catálogo dinámico de lotes tras sync Drive: {e}")

    # Obtener metadatos actualizados del archivo
    info_kardex = obtener_info_kardex_actual()
    info_kardex["total_lotes"] = total_lotes
    now_str = ahora_colombia_str()

    tamano_kb = round(len(contenido_bytes) / 1024, 1)
    msg_ok = f"Kardex oficial y Catálogo Maestro de Lotes sincronizados exitosamente desde Google Sheets ({tamano_kb} KB, {total_lotes} lotes activos catalogados)."

    guardar_config_kardex_drive({
        "url_origen": enlace,
        "ultima_sincronizacion": now_str,
        "ultimo_resultado": "SINCRONIZADO_OK",
        "ultimo_mensaje": msg_ok,
        "tamano_kb": tamano_kb,
        "lotes_activos": total_lotes,
        "proxima_sincronizacion": calcular_proximo_ultimo_dia().strftime("%Y-%m-%d %H:%M:%S")
    })

    return {
        "success": True,
        "mensaje": msg_ok,
        "fecha": now_str,
        "tamano_kb": tamano_kb,
        "total_lotes": total_lotes,
        "info": info_kardex
    }

def verificar_y_ejecutar_sync_programada():
    """
    Evalúa si corresponde ejecutar la sincronización automática del Kardex y Lotes (Hora Legal Colombia):
    - Se ejecuta el último día de cada mes (y el día 1 como puesta al día si estuvo apagado).
    - Ejecuta actualización periódica durante el mes si han pasado más de 6 horas en horario hábil.
    """
    cfg = obtener_config_kardex_drive()
    if not cfg.get("auto_sync") or not cfg.get("url_origen"):
        return False

    ahora = ahora_colombia()
    hoy = ahora.date()
    ultimo_dia_mes = calendar.monthrange(hoy.year, hoy.month)[1]
    
    es_ultimo_dia = (hoy.day == ultimo_dia_mes)
    es_dia_primero = (hoy.day == 1)

    ultima_sync = cfg.get("ultima_sincronizacion")
    ya_sincronizado_hoy = False
    horas_transcurridas = 999.0
    if ultima_sync:
        try:
            f_ult = datetime.datetime.strptime(ultima_sync.split(" ")[0], "%Y-%m-%d").date()
            if f_ult == hoy:
                ya_sincronizado_hoy = True
            dt_ult = datetime.datetime.strptime(ultima_sync, "%Y-%m-%d %H:%M:%S")
            horas_transcurridas = (ahora - dt_ult).total_seconds() / 3600.0
        except Exception:
            pass

    # Criterio 1: Cierre mensual obligatorio
    es_cierre_mensual = (es_ultimo_dia or es_dia_primero) and not ya_sincronizado_hoy
    
    # Criterio 2: Actualización dinámica periódica de lotes nuevos durante el día hábil (cada 6 horas)
    es_actualizacion_periodica = horas_transcurridas >= 6.0 and (7 <= ahora.hour <= 20)

    if es_cierre_mensual or es_actualizacion_periodica:
        motivo = "cierre mensual" if es_cierre_mensual else "actualización dinámica periódica de lotes y entregas"
        print(f"[Kardex Auto-Sync] Ejecutando sincronización automática ({motivo}) a las {ahora.strftime('%Y-%m-%d %H:%M:%S')}...")
        res = descargar_kardex_google(cfg.get("url_origen"))
        print(f"[Kardex Auto-Sync] Resultado: {res.get('mensaje') or res.get('error')}")
        return True

    return False

# Hilo demonio de sincronización periódica en segundo plano
_DEMONIO_INICIADO = False

def _bucle_demonio_sync():
    """Bucle que vigila cada 30 minutos si corresponde ejecutar el auto-sync mensual."""
    while True:
        try:
            verificar_y_ejecutar_sync_programada()
        except Exception as e:
            print(f"[Kardex Auto-Sync Daemon] Error en verificación: {e}")
        # Esperar 30 minutos (1800 segundos)
        time.sleep(1800)

def iniciar_demonio_kardex_sync():
    """Inicia el hilo en segundo plano que vigila el calendario mensual."""
    global _DEMONIO_INICIADO
    if _DEMONIO_INICIADO:
        return
    _DEMONIO_INICIADO = True
    t = threading.Thread(target=_bucle_demonio_sync, daemon=True, name="KardexAutoSyncDaemon")
    t.start()
    print("[Kardex Auto-Sync] Demonio de sincronización mensual iniciado correctamente.")
