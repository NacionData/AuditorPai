"""
ai_auditor.py - Asistente de Auditoría PAI con Inteligencia Artificial.
Sintetiza las inconsistencias técnicas en un dictamen pedagógico y comprensible
para el personal de salud municipal.
"""
import os
import json
import urllib.request

def generar_dictamen_auditoria(municipio, mes, res_dosis, res_mov, res_ext=None):
    """
    Toma los resultados de validación de los 3 archivos y genera:
    1. Estado global (APROBADO_RADICABLE / RECHAZADO_CON_ERRORES / APROBADO_CON_ADVERTENCIAS)
    2. Dictamen pedagógico en lenguaje claro para el vacunador municipal.
    3. Lista consolidada de acciones prioritarias.
    """
    errores_totales = []
    advertencias_totales = []

    if res_dosis:
        errores_totales.extend([f"[Dosis] {e['mensaje']}" for e in res_dosis.get("errores", [])])
        advertencias_totales.extend([f"[Dosis] {a['mensaje']}" for a in res_dosis.get("advertencias", [])])

    if res_mov:
        errores_totales.extend([f"[Movimiento] {e['mensaje']}" for e in res_mov.get("errores", [])])
        advertencias_totales.extend([f"[Movimiento] {a['mensaje']}" for a in res_mov.get("advertencias", [])])

    if res_ext:
        errores_totales.extend([f"[Extranjeros] {e['mensaje']}" for e in res_ext.get("errores", [])])
        advertencias_totales.extend([f"[Extranjeros] {a['mensaje']}" for a in res_ext.get("advertencias", [])])

    es_aprobado = len(errores_totales) == 0
    estado = "APROBADO_RADICABLE" if es_aprobado and len(advertencias_totales) == 0 else (
        "APROBADO_CON_ADVERTENCIAS" if es_aprobado else "RECHAZADO_CON_ERRORES"
    )

    # Verificamos si hay clave de Gemini API configurada
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    dictamen_ia = None
    modelo_usado = None

    if api_key and (errores_totales or advertencias_totales):
        try:
            dictamen_ia, modelo_usado = _consultar_gemini(api_key, municipio, mes, errores_totales, advertencias_totales)
        except Exception as e:
            print(f"[AI Auditor] Error consultando Gemini: {e}")
            dictamen_ia = None
            modelo_usado = None

    # Si no hay API key o falló la conexión remota, usamos el motor pedagógico local
    if not dictamen_ia:
        dictamen_ia = _generar_dictamen_local(municipio, mes, errores_totales, advertencias_totales, res_dosis, res_mov)
        modelo_usado = "Motor Local Risaralda"

    return {
        "estado": estado,
        "aprobado": es_aprobado,
        "municipio": municipio,
        "mes": mes,
        "total_errores": len(errores_totales),
        "total_advertencias": len(advertencias_totales),
        "errores_detallados": errores_totales,
        "advertencias_detalladas": advertencias_totales,
        "dictamen_pedagogico": dictamen_ia,
        "motor_ia": modelo_usado,
        "usando_gemini": bool(modelo_usado and "gemini" in modelo_usado.lower()),
        "metricas": {
            "dosis_aplicadas_nacionales": res_dosis.get("total_dosis_mes", 0) if res_dosis else 0,
            "dosis_movimiento_total": res_mov.get("total_dosis_aplicadas", 0) if res_mov else 0,
            "dosis_perdidas_total": res_mov.get("total_dosis_perdidas", 0) if res_mov else 0,
            "vacunados_extranjeros": res_ext.get("total_extranjeros_vacunados", 0) if res_ext else 0
        }
    }

def _generar_dictamen_local(municipio, mes, errores, advertencias, res_dosis, res_mov):
    """Generador pedagógico nativo en español para salud pública."""
    lineas = []
    lineas.append(f"### 📋 Dictamen de Auditoría PAI — {municipio} ({mes})")
    
    if not errores and not advertencias:
        lineas.append("\n✅ **¡Felicitaciones! Todos los informes están completamente coherentes y auditados.**")
        lineas.append("- Las sumatorias de género, régimen y grupos étnicos coinciden al 100%.")
        lineas.append("- La ecuación de inventarios y los saldos por lotes están perfectamente cuadrados.")
        lineas.append("- **El informe se encuentra listo para radicación oficial ante la Secretaría de Salud de Risaralda.**")
        return "\n".join(lineas)

    if errores:
        lineas.append(f"\n⚠️ **Se detectaron {len(errores)} inconsistencias críticas que deben corregirse antes de radicar:**\n")
        for idx, err in enumerate(errores, 1):
            lineas.append(f"{idx}. {err}")
        lineas.append("\n💡 **Instrucciones para corregir:**")
        lineas.append("• En la plantilla de Dosis Aplicadas, asegúrate de que la cantidad total de dosis por género coincida exactamente con la suma por régimen (contributivo, subsidiado, etc.) y pertenencia étnica.")
        lineas.append("• En Movimiento de Biológicos, verifica que el Saldo que inicia el mes siguiente sea exactamente igual a: *Saldo Anterior + Entradas - Salidas - Pérdidas*, y que la suma de lotes coincida con ese saldo.")

    if advertencias:
        lineas.append(f"\nℹ️ **Observaciones preventivas ({len(advertencias)}):**\n")
        for idx, adv in enumerate(advertencias[:8], 1):
            lineas.append(f"• {adv}")
        if len(advertencias) > 8:
            lineas.append(f"• ... y {len(advertencias) - 8} observaciones adicionales de lotes o fechas.")

    return "\n".join(lineas)

def _obtener_candidatos_modelos():
    """Genera lista ordenada de modelos compatibles según la API activa."""
    candidatos = []
    env_model = os.environ.get("GEMINI_MODEL")
    if env_model:
        candidatos.append(env_model.strip())
    
    # Modelos recomendados y activos en orden de prioridad
    defaults = [
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    for d in defaults:
        if d not in candidatos:
            candidatos.append(d)
    return candidatos

def test_gemini_connection():
    """Prueba rápida de conectividad con la API de Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"activo": False, "mensaje": "Clave GEMINI_API_KEY no configurada", "modelo": None}

    candidatos = _obtener_candidatos_modelos()
    ultimo_error = None

    for modelo in candidatos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        data = json.dumps({
            "contents": [{"parts": [{"text": "Ping institucional PAI Risaralda. Responde solo OK."}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 20,
                "thinkingConfig": {"thinkingBudget": 0}
            }
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return {
                        "activo": True,
                        "mensaje": "Conexión exitosa con Google Gemini",
                        "modelo": modelo
                    }
        except Exception as e:
            ultimo_error = str(e)
            continue

    return {"activo": False, "mensaje": f"Error conectando con modelos: {ultimo_error}", "modelo": None}

def _consultar_gemini(api_key, municipio, mes, errores, advertencias):
    prompt = f"""
Eres el Coordinador Médico de Auditoría del Programa Ampliado de Inmunizaciones (PAI) de la Secretaría de Salud Departamental de Risaralda, Colombia.

El municipio de {municipio} ha cargado sus 3 informes oficiales de vacunación correspondientes a {mes} 2026 (Dosis Aplicadas, Movimiento de Biológicos y Extranjeros).
El motor de validación matemática estricta ha detectado las siguientes inconsistencias frente a la normatividad PAI (Ley 2406 de 2024 y Lineamientos Oficiales MinSalud 2026):

INCONSISTENCIAS CRÍTICAS ENCONTRADAS:
{json.dumps(errores, indent=2, ensure_ascii=False)}

OBSERVACIONES DE TRAZABILIDAD Y LOTES:
{json.dumps(advertencias[:8], indent=2, ensure_ascii=False)}

Instrucciones para tu dictamen:
1. Redacta un dictamen oficial, empático, altamente pedagógico y constructivo dirigido al personal de salud y coordinadores de vacunación de {municipio}.
2. Explica con absoluta claridad la causa de cada descuadre (ej: diferencia entre sumas de género y régimen, descuadre de saldos frente al cierre del mes anterior en Kardex, o causas de pérdida inválidas).
3. Brinda una guía paso a paso con viñetas indicando exactamente qué celdas o columnas deben ajustar en sus archivos de Excel para que su informe quede 100% aprobado y puedan radicar.
4. Mantén un tono institucional, cordial, motivador y profesional en formato Markdown limpio.
"""
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }).encode("utf-8")

    candidatos = _obtener_candidatos_modelos()
    ultimo_error = None

    for modelo in candidatos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                texto = res_json["candidates"][0]["content"]["parts"][0]["text"]
                return texto, modelo
        except Exception as e:
            ultimo_error = e
            print(f"[AI Auditor] Modelo {modelo} falló: {e}. Probando siguiente candidato...")
            continue

    raise RuntimeError(f"No fue posible consultar ningún modelo de Gemini. Último error: {ultimo_error}")
