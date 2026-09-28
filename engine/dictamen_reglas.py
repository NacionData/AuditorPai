"""
dictamen_reglas.py - Generador de Dictamen Técnico por Regla para Administración Departamental.
Secretaría de Salud Departamental de Risaralda.

Evalúa exhaustivamente el cumplimiento de cada una de las reglas técnicas y biológicas
auditadas sobre los informes radicados por los 14 municipios de Risaralda:
1. Regla de Oro Demográfica PAI (541 Columnas)
2. Recálculo Anti-Adulteración de Fórmulas Matemáticas
3. Continuidad Intermensual de Saldos (Regla 1)
4. Coherencia de Lotes vs Saldo Siguiente y Control VERDADERO (Regla 2)
5. Cruce Entregas Depósito Departamental vs Recibido (Regla 3)
6. Catálogo Maestro de 361 Lotes Oficiales (Regla 4)
7. Racionalidad de 11 Causas de Pérdida (Regla 5)
8. Diluyentes en Vacunas Liofilizadas (Regla 6)
9. Coherencia Matricial en Vacunados Extranjeros
10. Cruce Comparativo Dosis Nacionales vs Movimiento Biológico
11. Auditoría Clínica de Simultaneidad del Esquema Nacional (6 Cohortes)
"""

def generar_dictamen_reglas_detallado(municipio, mes, ano, r_dosis, r_mov, r_ext, cruce_colombianos=None, cruce_deposito=None):
    """
    Construye un dictamen institucional regla por regla con métricas exactas,
    estado de aprobación técnica y hallazgos detallados.
    """
    reglas = []

    # =========================================================================
    # REGLA 1: REGLA DE ORO DEMOGRÁFICA PAI (Dosis Aplicadas)
    # =========================================================================
    res_dosis_coh = (r_dosis or {}).get("resumen_coherencia", {})
    tot_dosis = (r_dosis or {}).get("total_dosis_mes", 0)
    gen_ok = res_dosis_coh.get("coincidencia_genero_regimen", True)
    etn_ok = res_dosis_coh.get("coincidencia_genero_etnico", True)
    oro_cumple = gen_ok and etn_ok and not any(e.get("tipo") == "REGLA_DE_ORO" for e in (r_dosis or {}).get("errores", []))

    desfases_oro = [e["mensaje"] for e in (r_dosis or {}).get("errores", []) if e.get("tipo") == "REGLA_DE_ORO"]
    reglas.append({
        "id": "regla_oro",
        "codigo": "REG-01",
        "nombre": "Regla de Oro Demográfica PAI (541 Columnas)",
        "archivo": "Dosis Aplicadas",
        "cumple": oro_cumple,
        "estado": "CUMPLE" if oro_cumple else "INCONSISTENCIA",
        "resumen": "Suma(Género) == Suma(Régimen) == Suma(Pertenencia Étnica)",
        "metricas": {
            "total_dosis_aplicadas": tot_dosis,
            "genero_vs_regimen": "Coincide (100%)" if gen_ok else "Descuadre detectado",
            "genero_vs_etnia": "Coincide (100%)" if etn_ok else "Descuadre detectado"
        },
        "hallazgos": desfases_oro if not oro_cumple else ["Coherencia demográfica del 100% verificada en todas las celdas."]
    })

    # =========================================================================
    # REGLA 2: RECÁLCULO ANTI-ADULTERACIÓN DE FÓRMULAS
    # =========================================================================
    forms_adulteradas = res_dosis_coh.get("formulas_adulteradas", 0)
    anti_cumple = (forms_adulteradas == 0) and not any(e.get("tipo") == "FORMULA_ADULTERADA" for e in (r_dosis or {}).get("errores", []))
    err_anti = [e["mensaje"] for e in (r_dosis or {}).get("errores", []) if e.get("tipo") == "FORMULA_ADULTERADA"]
    reglas.append({
        "id": "anti_adulteracion",
        "codigo": "REG-02",
        "nombre": "Recálculo Anti-Adulteración de Fórmulas",
        "archivo": "Dosis Aplicadas",
        "cumple": anti_cumple,
        "estado": "CUMPLE" if anti_cumple else "FÓRMULA ALTERADA",
        "resumen": "Verificación independiente sin confiar en celdas de total sobreescritas",
        "metricas": {
            "formulas_adulteradas": forms_adulteradas,
            "integridad_formulas": "100% Íntegras" if anti_cumple else f"{forms_adulteradas} sobreescritas"
        },
        "hallazgos": err_anti if not anti_cumple else ["Todas las fórmulas oficiales de sumatoria se mantienen sin adulteración."]
    })

    # =========================================================================
    # REGLA 3: CONTINUIDAD INTERMENSUAL DE SALDOS (Regla 1 Movimiento)
    # =========================================================================
    m_reglas = (r_mov or {}).get("metricas_reglas", {})
    reg1_cumple = m_reglas.get("regla1_continuidad_saldos", True) and not any(e.get("regla") == "REGLA_1_CONTINUIDAD_SALDOS" for e in (r_mov or {}).get("errores", []))
    err_reg1 = [e["mensaje"] for e in (r_mov or {}).get("errores", []) if e.get("regla") == "REGLA_1_CONTINUIDAD_SALDOS"]
    reglas.append({
        "id": "regla_1_continuidad",
        "codigo": "REG-03",
        "nombre": "Continuidad Intermensual de Saldos (Regla 1)",
        "archivo": "Movimiento de Biológicos",
        "cumple": reg1_cumple,
        "estado": "CUMPLE" if reg1_cumple else "INCONSISTENCIA",
        "resumen": "Saldo Anterior mes actual == Saldo Siguiente mes anterior oficial",
        "metricas": {
            "continuidad": "100% Cuadrada" if reg1_cumple else "Desfase detectado",
            "biologicos_con_error": len(err_reg1)
        },
        "hallazgos": err_reg1 if not reg1_cumple else ["El saldo inicial de cada biológico coincide con el cierre oficial previo archivado."]
    })

    # =========================================================================
    # REGLA 4: COHERENCIA DE 5 LOTES VS SALDO SIGUIENTE (Regla 2 Movimiento)
    # =========================================================================
    reg2_cumple = m_reglas.get("regla2_flag_verdadero", True) and not any(e.get("regla") == "REGLA_2_COHERENCIA_LOTES" for e in (r_mov or {}).get("errores", []))
    err_reg2 = [e["mensaje"] for e in (r_mov or {}).get("errores", []) if e.get("regla") == "REGLA_2_COHERENCIA_LOTES"]
    adv_reg2 = [a["mensaje"] for a in (r_mov or {}).get("advertencias", []) if a.get("regla") == "REGLA_2_COHERENCIA_LOTES"]
    reglas.append({
        "id": "regla_2_lotes_vs_saldo",
        "codigo": "REG-04",
        "nombre": "Coherencia de 5 Lotes vs Saldo Siguiente (Regla 2)",
        "archivo": "Movimiento de Biológicos",
        "cumple": reg2_cumple,
        "estado": "CUMPLE" if reg2_cumple else "INCONSISTENCIA",
        "resumen": "Suma de 5 celdas de lotes == Saldo Siguiente y Celda de Control VERDADERO",
        "metricas": {
            "coherencia_lotes": "100% Cuadrada" if reg2_cumple else "Descuadre en celdas",
            "inconsistencias": len(err_reg2)
        },
        "hallazgos": err_reg2 if not reg2_cumple else (adv_reg2 if adv_reg2 else ["La suma de lotes coincide exactamente con el saldo disponible al cierre."])
    })

    # =========================================================================
    # REGLA 5: CRUCE DE ENTREGAS DEPÓSITO DEPARTAMENTAL (Regla 3 Kardex)
    # =========================================================================
    cdep = cruce_deposito or (r_mov or {}).get("cruce_deposito", {})
    res_cdep = cdep.get("resumen", {})
    tot_desp = res_cdep.get("total_despachado", 0)
    tot_rec = res_cdep.get("total_recibido", 0)
    bio_ex = res_cdep.get("biologicos_exactos", 0)
    bio_tot = res_cdep.get("biologicos_total", 0)
    reg3_cumple = (bio_ex == bio_tot) if bio_tot > 0 else True
    alertas_reg3 = cdep.get("alertas", [])
    reglas.append({
        "id": "regla_3_cruce_deposito",
        "codigo": "REG-05",
        "nombre": "Cruce Entregas Depósito Departamental (Regla 3)",
        "archivo": "Movimiento vs Kardex",
        "cumple": reg3_cumple,
        "estado": "CUMPLE" if reg3_cumple else "DIFERENCIA DETECTADA",
        "resumen": "Dosis recibidas (Columna 5) vs Kardex de despachos del Depósito Departamental",
        "metricas": {
            "total_despachado_kardex": tot_desp,
            "total_recibido_municipio": tot_rec,
            "biologicos_exactos": f"{bio_ex}/{bio_tot} ({res_cdep.get('porcentaje_coincidencia', 100)}%)",
            "diferencias_detectadas": res_cdep.get("total_diferencias", 0)
        },
        "hallazgos": [a["mensaje"] for a in alertas_reg3] if alertas_reg3 else ["Conciliación del 100% con los despachos oficiales del Depósito Departamental."]
    })

    # =========================================================================
    # REGLA 6: CATÁLOGO MAESTRO DE 361 LOTES OFICIALES (Regla 4)
    # =========================================================================
    reg4_cumple = m_reglas.get("regla4_lotes_oficiales", True) and not any("REGLA_4" in e.get("regla", "") for e in (r_mov or {}).get("errores", []))
    err_reg4 = [e["mensaje"] for e in (r_mov or {}).get("errores", []) if "REGLA_4" in e.get("regla", "")]
    reglas.append({
        "id": "regla_4_catalogo_lotes",
        "codigo": "REG-06",
        "nombre": "Catálogo Maestro de Lotes Oficiales (Regla 4)",
        "archivo": "Movimiento de Biológicos",
        "cumple": reg4_cumple,
        "estado": "CUMPLE" if reg4_cumple else "LOTES NO AUTORIZADOS",
        "resumen": "Validación de lotes reportados contra los 361 lotes activos del Depósito",
        "metricas": {
            "lotes_autorizados": "100% Verificados" if reg4_cumple else "Lotes no autorizados detectados",
            "lotes_invalidos_o_blancos": len(err_reg4)
        },
        "hallazgos": err_reg4 if not reg4_cumple else ["Todos los lotes digitados figuran en el catálogo maestro departamental."]
    })

    # =========================================================================
    # REGLA 7: RACIONALIDAD DE 11 CAUSAS DE PÉRDIDA (Regla 5)
    # =========================================================================
    reg5_cumple = m_reglas.get("regla5_racionalidad_perdidas", True) and not any(e.get("regla") == "REGLA_5_RACIONALIDAD_PERDIDAS" for e in (r_mov or {}).get("errores", []))
    err_reg5 = [e["mensaje"] for e in (r_mov or {}).get("errores", []) if e.get("regla") == "REGLA_5_RACIONALIDAD_PERDIDAS"]
    tot_perdidas = (r_mov or {}).get("total_dosis_perdidas", 0)
    reglas.append({
        "id": "regla_5_causas_perdida",
        "codigo": "REG-07",
        "nombre": "Racionalidad de 11 Causas de Pérdida (Regla 5)",
        "archivo": "Movimiento de Biológicos",
        "cumple": reg5_cumple,
        "estado": "CUMPLE" if reg5_cumple else "INCONSISTENCIA",
        "resumen": "Suma de 11 causas == Total Pérdidas reportadas (Vómito Franco solo en vacunas orales)",
        "metricas": {
            "total_dosis_perdidas": tot_perdidas,
            "coherencia_causas": "100% Coherente" if reg5_cumple else "Descuadre en causas"
        },
        "hallazgos": err_reg5 if not reg5_cumple else ["Distribución matemática y epidemiológica de pérdidas cuadradas al 100%."]
    })

    # =========================================================================
    # REGLA 8: DILUYENTES EN VACUNAS LIOFILIZADAS (Regla 6)
    # =========================================================================
    err_reg6 = [e["mensaje"] for e in (r_mov or {}).get("errores", []) if e.get("regla") == "REGLA_6_DILUYENTES_INSUFICIENTES"]
    adv_reg6 = [a["mensaje"] for a in (r_mov or {}).get("advertencias", []) if "DILUYENTE" in a.get("regla", "")]
    reg6_cumple = len(err_reg6) == 0
    reglas.append({
        "id": "regla_6_diluyentes",
        "codigo": "REG-08",
        "nombre": "Diluyentes en Vacunas Liofilizadas (Regla 6)",
        "archivo": "Movimiento de Biológicos",
        "cumple": reg6_cumple,
        "estado": "CUMPLE" if reg6_cumple else "DILUYENTES INSUFICIENTES",
        "resumen": "Diluyentes utilizados >= Vacunas reconstituidas utilizadas (Excluye VRS que no requiere diluyente)",
        "metricas": {
            "balance_diluyentes": "Suficiente y Trazable" if reg6_cumple else "Déficit detectado",
            "observaciones": len(adv_reg6)
        },
        "hallazgos": err_reg6 if not reg6_cumple else (adv_reg6 if adv_reg6 else ["Consumo de diluyentes compatible con los biológicos reconstituidos."])
    })

    # =========================================================================
    # REGLA 9: COHERENCIA MATRICIAL EN VACUNADOS EXTRANJEROS
    # =========================================================================
    err_ext = [e["mensaje"] for e in (r_ext or {}).get("errores", [])]
    ext_cumple = len(err_ext) == 0
    tot_ext = (r_ext or {}).get("total_extranjeros_vacunados", 0)
    reglas.append({
        "id": "extranjeros_matricial",
        "codigo": "REG-09",
        "nombre": "Coherencia Matricial en Vacunados Extranjeros",
        "archivo": "Vacunados Extranjeros",
        "cumple": ext_cumple,
        "estado": "CUMPLE" if ext_cumple else "INCONSISTENCIA",
        "resumen": "Total Género == Total Régimen en las 6 hojas de países migrantes",
        "metricas": {
            "total_extranjeros_vacunados": tot_ext,
            "coherencia_hojas_paises": "100% Coincidente" if ext_cumple else "Descuadre en hojas"
        },
        "hallazgos": err_ext if not ext_cumple else ["Cruce demográfico y por nacionalidad validado en las 6 hojas de países."]
    })

    # =========================================================================
    # REGLA 10: CRUCE DOSIS A COLOMBIANOS (Dosis vs Movimiento)
    # =========================================================================
    c_col = cruce_colombianos or {}
    difs_col = c_col.get("diferencias", [])
    tot_dosis_col = c_col.get("total_dosis_plantilla", 0)
    tot_mov_col = c_col.get("total_movimiento_colombianos", 0)
    col_cumple = len(difs_col) == 0
    reglas.append({
        "id": "cruce_dosis_vs_movimiento",
        "codigo": "REG-10",
        "nombre": "Cruce Comparativo Dosis Nacionales vs Movimiento",
        "archivo": "Dosis vs Movimiento",
        "cumple": col_cumple,
        "estado": "COINCIDENCIA EXACTA" if col_cumple else "DIFERENCIA DETECTADA",
        "resumen": "Dosis aplicadas a colombianos en plantilla Dosis vs dosis colombianas en Movimiento",
        "metricas": {
            "total_dosis_plantilla": tot_dosis_col,
            "total_movimiento_colombianos": tot_mov_col,
            "biologicos_con_diferencia": len(difs_col)
        },
        "hallazgos": [d["mensaje"] for d in difs_col] if difs_col else ["Coincidencia plena entre dosis aplicadas a colombianos y el movimiento de biológicos."]
    })

    # =========================================================================
    # REGLA 11: ANÁLISIS DE SIMULTANEIDAD DEL ESQUEMA NACIONAL (6 Cohortes)
    # =========================================================================
    sim_cohortes = res_dosis_coh.get("informe_simultaneidad", [])
    optimas = sum(1 for c in sim_cohortes if c.get("estado") == "OPTIMO")
    total_coh = len(sim_cohortes)
    sim_cumple = (optimas == total_coh) if total_coh > 0 else True
    reglas.append({
        "id": "simultaneidad_esquema",
        "codigo": "REG-11",
        "nombre": "Auditoría Clínica de Simultaneidad del Esquema Nacional",
        "archivo": "Dosis Aplicadas",
        "cumple": sim_cumple,
        "estado": "ÓPTIMA (100%)" if sim_cumple else "DESFASE OBSERVADO",
        "resumen": "Evaluación de oportunidad clínica simultánea en las 6 cohortes (2m, 4m, 6m, 12m, 18m, 5a)",
        "metricas": {
            "cohortes_optimas": f"{optimas}/{total_coh}",
            "oportunidad_clinica": "100% Óptima" if sim_cumple else f"{total_coh - optimas} cohortes con desfase"
        },
        "hallazgos": [f"{c['cohorte']}: {c['resumen']}" for c in sim_cohortes if c.get("estado") != "OPTIMO"] if not sim_cumple else ["Simultaneidad clínica óptima en las 6 cohortes del esquema."]
    })

    total_cumplidas = sum(1 for r in reglas if r["cumple"])

    return {
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "total_reglas": len(reglas),
        "reglas_cumplidas": total_cumplidas,
        "porcentaje_cumplimiento": round((total_cumplidas / len(reglas)) * 100, 1),
        "reglas": reglas
    }
