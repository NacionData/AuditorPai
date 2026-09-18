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

    if api_key and (errores_totales or advertencias_totales):
        try:
            dictamen_ia = _consultar_gemini(api_key, municipio, mes, errores_totales, advertencias_totales)
        except Exception:
            dictamen_ia = None

    # Si no hay API key o falló la conexión remota, usamos el motor pedagógico local
    if not dictamen_ia:
        dictamen_ia = _generar_dictamen_local(municipio, mes, errores_totales, advertencias_totales, res_dosis, res_mov)

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

def _consultar_gemini(api_key, municipio, mes, errores, advertencias):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = f"""
Eres el auditor experto del Programa Ampliado de Inmunizaciones (PAI) de la Secretaría de Salud de Risaralda, Colombia.
El municipio de {municipio} cargó sus reportes mensuales de {mes}.
Se detectaron los siguientes errores técnicos y observaciones:

ERRORES CRÍTICOS:
{json.dumps(errores, indent=2, ensure_ascii=False)}

OBSERVACIONES / ADVERTENCIAS:
{json.dumps(advertencias[:6], indent=2, ensure_ascii=False)}

Escribe una respuesta corta, cordial, pedagógica y muy clara dirigida al coordinador/digitador de vacunación del municipio.
Explícale exactamente qué celdas o vacunas tienen problema y cómo corregirlas paso a paso antes de que su informe pueda ser radicado. Usa formato Markdown con viñetas claras.
"""
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        return res_json["candidates"][0]["content"]["parts"][0]["text"]
