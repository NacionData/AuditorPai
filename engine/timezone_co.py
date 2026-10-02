"""
engine/timezone_co.py - Manejo centralizado de Hora Legal de la República de Colombia (UTC-5 / America/Bogota).
Garantiza que toda la plataforma (servidor, validadores, radicados, auditorías y sincronizaciones)
opere estrictamente con la zona horaria colombiana, sin importar el sistema operativo o si se despliega en la nube (Docker/Railway/AWS).
"""
import calendar
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

try:
    TZ_COLOMBIA = ZoneInfo("America/Bogota")
except Exception:
    TZ_COLOMBIA = timezone(timedelta(hours=-5), name="America/Bogota")

MESES_ORDENADOS = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

MESES_NOMBRES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def ahora_colombia() -> datetime:
    """Retorna el objeto datetime actual en la zona horaria oficial de Colombia (UTC-5)."""
    return datetime.now(TZ_COLOMBIA)

def ahora_colombia_str(formato: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Retorna la fecha y hora colombiana formateada como string."""
    return ahora_colombia().strftime(formato)

def mes_ha_finalizado(mes: str, ano: int = 2026) -> tuple[bool, str]:
    """
    Valida si el mes a reportar ya ha finalizado según la hora legal colombiana.
    Regla PAI Departamental: Los municipios no pueden radicar un mes en curso ni meses futuros;
    solo se permite radicar una vez ha culminado el mes (a partir del primer día del mes siguiente).
    Ejemplo: El informe de Septiembre solo se puede radicar a partir del 1 de Octubre.
    """
    mes_up = (mes or "").strip().upper()
    if mes_up not in MESES_ORDENADOS:
        return False, f"El mes '{mes}' no es un mes oficial del calendario."

    mes_num = MESES_ORDENADOS.index(mes_up) + 1
    now = ahora_colombia()

    # Inicio permitido para radicar: 00:00:00 del primer día del mes siguiente
    if mes_num == 12:
        inicio_permitido = datetime(ano + 1, 1, 1, 0, 0, 0, tzinfo=TZ_COLOMBIA)
        nombre_mes_sig = f"Enero de {ano + 1}"
    else:
        inicio_permitido = datetime(ano, mes_num + 1, 1, 0, 0, 0, tzinfo=TZ_COLOMBIA)
        nombre_mes_sig = f"{MESES_NOMBRES[mes_num + 1]} de {ano}"

    if now < inicio_permitido:
        return False, (
            f"El informe mensual de {MESES_NOMBRES[mes_num]} {ano} no puede radicarse todavía porque el mes aún no ha finalizado. "
            f"Conforme a los lineamientos del PAI, la radicación oficial solo se habilita una vez terminado el mes (a partir del 1 de {nombre_mes_sig})."
        )

    return True, ""

def obtener_info_tiempo_colombia() -> dict:
    """Retorna información detallada sobre la hora colombiana y los meses habilitados para radicar."""
    now = ahora_colombia()
    mes_actual_idx = now.month  # 1..12
    meses_habilitados = []
    meses_bloqueados = []

    for idx, m_nombre in enumerate(MESES_ORDENADOS, start=1):
        finalizado, motivo = mes_ha_finalizado(m_nombre, now.year)
        if finalizado:
            meses_habilitados.append({
                "mes": m_nombre,
                "nombre": MESES_NOMBRES[idx],
                "habilitado": True
            })
        else:
            meses_bloqueados.append({
                "mes": m_nombre,
                "nombre": MESES_NOMBRES[idx],
                "habilitado": False,
                "motivo": motivo
            })

    return {
        "zona_horaria": "America/Bogota (UTC-5)",
        "hora_colombiana_iso": now.isoformat(),
        "fecha_hora_texto": now.strftime("%Y-%m-%d %I:%M:%S %p"),
        "fecha": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M:%S"),
        "ano": now.year,
        "mes_actual_nombre": MESES_NOMBRES[mes_actual_idx],
        "mes_actual_clave": MESES_ORDENADOS[mes_actual_idx - 1],
        "meses_habilitados": meses_habilitados,
        "meses_bloqueados": meses_bloqueados
    }
