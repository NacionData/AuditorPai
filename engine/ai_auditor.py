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

    if api_key:
        try:
            dictamen_ia, modelo_usado = _consultar_gemini(api_key, municipio, mes, errores_totales, advertencias_totales)
        except Exception as e:
            print(f"[AI Auditor] Consulta a Gemini no disponible ({e}). Activando motor pedagógico local oficial.")
            dictamen_ia = None
            modelo_usado = None

    # Si no hay API key, falló la conexión remota o la respuesta fue incompleta, usamos el motor pedagógico local garantizado
    if not dictamen_ia:
        dictamen_ia = _generar_dictamen_local(municipio, mes, errores_totales, advertencias_totales, res_dosis, res_mov)
        modelo_usado = "Motor Pedagógico Departamental Risaralda"

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
    """
    Generador pedagógico nativo en español para salud pública de Risaralda.
    Garantiza estructura completa, formal, empática y 100% cerrada sin cortes.
    """
    es_aprobado = len(errores) == 0
    lineas = []

    # Encabezado Institucional Departamental
    lineas.append("# DICTAMEN OFICIAL DE AUDITORÍA MÉDICA PAI")
    lineas.append("**Programa Ampliado de Inmunizaciones (PAI) — Secretaría de Salud Departamental de Risaralda**\n")
    lineas.append(f"• **Para:** Coordinación de Vacunación, IPS y Equipo PAI – Municipio de {municipio}")
    lineas.append("• **De:** Coordinador Médico de Auditoría PAI Risaralda")
    lineas.append(f"• **Periodo Evaluado:** {mes} de 2026")
    lineas.append("• **Informes Evaluados:** Dosis Aplicadas, Movimiento de Biológicos y Población Extranjera")
    if es_aprobado and not advertencias:
        lineas.append("• **Estado de Radicación:** **APROBADO PARA RADICACIÓN OFICIAL (100% CONFORME)**\n")
    elif es_aprobado:
        lineas.append("• **Estado de Radicación:** **APROBADO PARA RADICACIÓN OFICIAL (CON OBSERVACIONES INFORMATIVAS)**\n")
    else:
        lineas.append("• **Estado de Radicación:** **INCONSISTENCIAS CRÍTICAS DETECTADAS (REQUIERE CORRECCIÓN O JUSTIFICACIÓN)**\n")

    lineas.append("---\n")
    lineas.append("### 1. Concepto General de Auditoría Médica")
    lineas.append(f"Estimado equipo de salud del municipio de {municipio}:\n")

    if es_aprobado:
        lineas.append("Tras procesar la información reportada a través del motor de validación de datos y coherencia biológica con base en los lineamientos del Ministerio de Salud y Protección Social (Actualización Julio 2026), nos complace informarles que **no se identificaron inconsistencias críticas que bloqueen la radicación**.")
        lineas.append(f"Sus tres informes oficiales correspondientes al mes de {mes} de 2026 son **válidos, consistentes y se encuentran plenamente autorizados para su radicación oficial** ante la Secretaría de Salud Departamental de Risaralda.\n")
    else:
        lineas.append(f"Tras la auditoría exhaustiva de sus informes oficiales correspondientes al mes de {mes} de 2026, el sistema identificó **{len(errores)} inconsistencia(s) crítica(s)** que deben ser atendidas para asegurar la integridad de los datos epidemiológicos del departamento.\n")

    if errores:
        lineas.append("### 2. Inconsistencias Críticas que Requieren Atención")
        lineas.append("*(Estas observaciones son de carácter bloqueante y deben subsanarse en las plantillas o mediante justificación técnica autorizada)*\n")
        for idx, err in enumerate(errores, 1):
            lineas.append(f"{idx}. {err}")

        lineas.append("\n💡 **Instrucciones Oficiales para la Corrección:**")
        lineas.append("• **Plantilla de Dosis Aplicadas:** Verifique que el recálculo independiente de datos brutos coincida exactamente: la sumatoria por Género debe ser idéntica a la sumatoria por Régimen y a la sumatoria por Pertenencia Étnica.")
        lineas.append("• **Plantilla de Movimiento de Biológicos:** Recuerde que las fórmulas de las plantillas oficiales MinSalud están estandarizadas y no deben modificarse bajo ninguna circunstancia. Verifique el inventario físico en termos/neveras de la IPS y las actas de entrega/remisión oficial emitidas por la cadena de frío departamental.")
        lineas.append("• **Conciliación con Depósito Departamental:** Si tras la verificación física persiste alguna discrepancia frente al Kardex del Depósito, comuníquese con el Referente Departamental o registre la novedad a través del botón de justificación oficial.")

    if advertencias:
        simul_adv = [a for a in advertencias if "Simultaneidad" in a]
        otras_adv = [a for a in advertencias if "Simultaneidad" not in a]

        num_sec = "3" if errores else "2"
        lineas.append(f"\n### {num_sec}. Oportunidades de Vacunación y Seguimiento Clínico (Informativo)")
        lineas.append("*(Las siguientes observaciones son pedagógicas y preventivas para fortalecer el esquema en campo; **NO impiden ni bloquean la radicación**)*\n")

        if simul_adv:
            lineas.append("**Análisis de Oportunidades y Simultaneidad de Esquema:**")
            for sa in simul_adv:
                lineas.append(f"• {sa}")
            lineas.append("")

        if otras_adv:
            lineas.append("**Trazabilidad Preventiva de Lotes y Diluyentes:**")
            for adv in otras_adv:
                lineas.append(f"• {adv}")

    # Cierre y Firma Institucional
    lineas.append("\n---\n")
    lineas.append("### 3. Recomendaciones Institucionales Permanentes" if not (errores and advertencias) else "\n### 4. Recomendaciones Institucionales Permanentes")
    lineas.append("1. **Búsqueda Activa Comunitaria:** Priorizar el rastreo de susceptibles en cohortes con coberturas diferidas.")
    lineas.append("2. **Cadena de Frío:** Mantener el registro continuo de temperatura y verificar lotes vigentes autorizados.")
    lineas.append("3. **Radicación Oportuna:** Una vez verificado el dictamen, proceda con la radicación oficial para el consolidado departamental ante MinSalud.\n")
    lineas.append("Atentamente,\n")
    lineas.append("**COORDINACIÓN MÉDICA DE AUDITORÍA PAI**  ")
    lineas.append("*Programa Ampliado de Inmunizaciones (PAI)*  ")
    lineas.append("*Secretaría de Salud Departamental de Risaralda*")

    return "\n".join(lineas)

def _obtener_candidatos_modelos():
    """Genera lista ordenada de modelos compatibles según la API activa."""
    candidatos = []
    env_model = os.environ.get("GEMINI_MODEL")
    if env_model:
        candidatos.append(env_model.strip())

    defaults = [
        "gemini-flash-latest",
        "gemini-3.6-flash",
        "gemini-3.1-flash-lite",
        "gemini-pro-latest",
        "gemini-2.5-flash"
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
        target = modelo if modelo.startswith("models/") else f"models/{modelo}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{target}:generateContent?key={api_key}"
        data = json.dumps({
            "contents": [{"parts": [{"text": "Ping institucional PAI Risaralda. Responde solo OK."}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 20
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

def _es_dictamen_completo(texto: str, finish_reason: str) -> bool:
    """Verifica con rigor que el texto del dictamen esté 100% completo y no cortado."""
    if not texto or len(texto.strip()) < 350:
        return False
    if finish_reason in ["MAX_TOKENS", "LENGTH"]:
        return False

    t_strip = texto.rstrip()
    
    # Patrones de truncamiento sintáctico abrupto
    palabras_corte = [
        " y", " de", " con", " que", " la", " el", " en", " para", 
        " por", " su", " sus", "**", "##", "*", "_", " son", " es", " del",
        " a", " al", " un", " una", " los", " las"
    ]
    for corte in palabras_corte:
        if t_strip.endswith(corte):
            return False

    # Debe poseer un cierre institucional o formal
    terminaciones_validas = [
        ".", "!", "?", ")", "]", "Risaralda", "PAI", "Salud", 
        "Departamental", "Atentamente", "cordialmente", "Oficial", "AUDITORÍA", "auditoría"
    ]
    if any(t_strip.endswith(tv) for tv in terminaciones_validas):
        return True

    # Puntuación en los últimos caracteres
    if any(c in t_strip[-10:] for c in [".", "!", ")", "]"]):
        return True

    return False

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
6. CONCISIÓN Y COMPLETITUD TOTAL: Sé conciso, directo y estructurado. Es indispensable que el dictamen incluya Concepto General, Desarrollo, Recomendaciones y Firma Oficial de Cierre, entregándose 100% completo sin cortes.
"""
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192
        }
    }).encode("utf-8")

    candidatos = _obtener_candidatos_modelos()
    ultimo_error = None

    for modelo in candidatos:
        target = modelo if modelo.startswith("models/") else f"models/{modelo}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{target}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    cand = candidates[0]
                    finish_reason = cand.get("finishReason", "")
                    partes = cand.get("content", {}).get("parts", [])
                    # Extraer y concatenar TODAS las partes de texto devueltas
                    texto = "".join([p.get("text", "") for p in partes if p.get("text")]).strip()
                    
                    if _es_dictamen_completo(texto, finish_reason):
                        return texto, modelo
                    else:
                        print(f"[AI Auditor] Modelo {modelo} devolvió texto incompleto (longitud {len(texto)}, finishReason={finish_reason}). Probando siguiente...")
                        ultimo_error = "Respuesta incompleta o truncada"
                        continue
        except Exception as e:
            ultimo_error = e
            print(f"[AI Auditor] Modelo {modelo} falló: {e}. Probando siguiente candidato...")
            continue

    raise RuntimeError(f"No fue posible obtener un dictamen completo de Gemini. Último error: {ultimo_error}")
