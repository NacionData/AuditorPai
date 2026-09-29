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
        lineas.append("\n💡 **Instrucciones oficiales para corregir:**")
        lineas.append("• En la plantilla de Dosis Aplicadas, asegúrate de que la cantidad total de dosis por género coincida exactamente con la suma por régimen (contributivo, subsidiado, etc.) y pertenencia étnica.")
        lineas.append("• En Movimiento de Biológicos, verifique el inventario físico en sus equipos de frío y las actas de entrega/remisiones del Depósito Departamental. Recuerde que las fórmulas de las plantillas oficiales MinSalud están protegidas y no deben ser modificadas ni sobreescritas bajo ninguna circunstancia. Si tras verificar los conteos físicos persiste una diferencia frente al Kardex oficial del Depósito Departamental, comuníquese inmediatamente con el Referente Departamental de Vacunación del PAI Risaralda para realizar la respectiva conciliación administrativa.")

    if advertencias:
        simul_adv = [a for a in advertencias if "Simultaneidad" in a]
        otras_adv = [a for a in advertencias if "Simultaneidad" not in a]

        if simul_adv:
            lineas.append("\n📊 **Análisis Pedagógico de Simultaneidad del Esquema (Oportunidades de Vacunación):**")
            lineas.append("*(Estas observaciones son informativas para el seguimiento en campo y no bloquean la radicación)*\n")
            for sa in simul_adv:
                lineas.append(f"• {sa}")

        if otras_adv:
            lineas.append(f"\nℹ️ **Observaciones preventivas de lotes y diluyentes ({len(otras_adv)}):**\n")
            for idx, adv in enumerate(otras_adv, 1):
                lineas.append(f"• {adv}")

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
El motor de validación matemática y de coherencia biológica ha analizado los datos frente a los Lineamientos Oficiales del Esquema Nacional de Vacunación (Actualización MinSalud Julio 2026):

INCONSISTENCIAS CRÍTICAS ENCONTRADAS (Bloquean radicación):
{json.dumps(errores, indent=2, ensure_ascii=False)}

OBSERVACIONES DE SIMULTANEIDAD DEL ESQUEMA, LOTES Y DILUYENTES (Informativas, NO impiden la radicación):
{json.dumps(advertencias[:12], indent=2, ensure_ascii=False)}

DIRECTRICES OBLIGATORIAS PARA TU DICTAMEN INSTITUCIONAL:
1. REDACCIÓN Y FORMATO: Redacta un dictamen oficial, empático, altamente pedagógico, técnico y constructivo dirigido al personal de salud y coordinadores de vacunación de {municipio}. Usa Markdown estructurado con viñetas limpias y concisas. NUNCA uses sintaxis LaTeX (está estrictamente prohibido usar $$ o $).
2. POLÍTICA ESTRICTA SOBRE FÓRMULAS DE EXCEL: Queda terminantemente PROHIBIDO invitar, sugerir o instruir al usuario a modificar, alterar o recalcular fórmulas de Excel (como la ecuación de saldo final, sumas de lotes o celdas de control). Las fórmulas de las plantillas oficiales MinSalud son estandarizadas y no se tocan.
3. CONCILIACIÓN FÍSICA Y KARDEX (REGLA 3): Ante inconsistencias en biológicos recibidos versus el Kardex del Depósito Departamental, o diferencias en saldos y lotes, indica expresamente:
   - Verificar detalladamente el inventario físico en los termos/neveras de la IPS y las actas físicas de entrega/remisión oficial emitidas por la cadena de frío departamental.
   - Si tras verificar el inventario físico se corrobora que el conteo municipal es exacto y la discrepancia con el Kardex oficial persiste, instruye al vacunador a comunicarse inmediatamente con el Referente Departamental de Vacunación del PAI Risaralda para la respectiva conciliación administrativa.
4. LOTES Y TRAZABILIDAD: Si un lote no figura en el catálogo maestro departamental o está faltante, instruye al municipio a verificar la etiqueta biológica y registrar el lote oficial correspondiente. No se pueden radicar informes con lotes inexistentes o erróneos.
5. SIMULTANEIDAD Y COHORTES (INFORMATIVO): Si el informe está aprobado o presenta observaciones de simultaneidad clínica (2m, 4m, 6m, 12m, 18m, 5a) o diluyentes, destaca con claridad que el informe ES VÁLIDO y PUEDE SER RADICADO, y orienta al equipo con recomendaciones pedagógicas de búsqueda activa de susceptibles para completar esquemas.
6. CONCISIÓN Y COMPLETITUD: Sé conciso, directo y estructurado para asegurar que el dictamen se entregue completo sin cortes.
"""
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }).encode("utf-8")

    candidatos = _obtener_candidatos_modelos()
    ultimo_error = None

    for modelo in candidatos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    cand = candidates[0]
                    finish_reason = cand.get("finishReason", "")
                    partes = cand.get("content", {}).get("parts", [])
                    texto = partes[0].get("text", "") if partes else ""
                    if finish_reason == "MAX_TOKENS":
                        texto += "\n\n*(Nota institucional: Dictamen extenso sintetizado por límite de extensión).* "
                    return texto, modelo
        except Exception as e:
            ultimo_error = e
            print(f"[AI Auditor] Modelo {modelo} falló: {e}. Probando siguiente candidato...")
            continue

    raise RuntimeError(f"No fue posible consultar ningún modelo de Gemini. Último error: {ultimo_error}")
