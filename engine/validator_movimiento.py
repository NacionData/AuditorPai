"""
validator_movimiento.py - Validador Avanzado para Movimiento de Biológicos PAI Risaralda.
Implementa las 5 Reglas de Auditoría Departamentales:
1. Continuidad intermensual contra archivo archivado oficial del mes anterior.
2. Flag oficial "VERDADERO": Cada biológico tiene exactamente 5 celdas para lotes (r a r+4)
   y en la fila r+5 se calcula la suma oficial y la celda de control VERDADERO/FALSO.
3. Cruce con entregas reales del Centro de Acopio Departamental (Google Sheets Kardex).
4. Catálogo maestro de lotes activos (Google Sheets Lotes) + Laboratorio y Vencimiento.
5. Racionalidad biológica de pérdidas (Vómito exclusivo oral, Factor Abierto exclusivo multidosis, sumatorias).
"""
import openpyxl
import os
import json
import re
from datetime import datetime, date

MESES_ORDEN = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

MESES_MAP = {
    "ENERO": ["ENERO", "ENE"],
    "FEBRERO": ["FEBRERO", "FEB"],
    "MARZO": ["MARZO", "MAR"],
    "ABRIL": ["ABRIL", "ABR"],
    "MAYO": ["MAYO", "MAY"],
    "JUNIO": ["JUNIO", "JUN"],
    "JULIO": ["JULIO", "JUL"],
    "AGOSTO": ["AGOSTO", "AGO"],
    "SEPTIEMBRE": ["SEPTIEMBRE", "SEP", "SET"],
    "OCTUBRE": ["OCTUBRE", "OCT"],
    "NOVIEMBRE": ["NOVIEMBRE", "NOV"],
    "DICIEMBRE": ["DICIEMBRE", "DIC"]
}

# Clasificación biológica para racionalidad de pérdidas
VACUNAS_ORALES = ["ROTAVIRUS", "POLIO ORAL", "BOPV", "OPV"]
VACUNAS_MULTIDOSIS = ["BCG", "FIEBRE AMARILLA", "TOXOIDE", "TD", "INFLUENZA MULTIDOSIS", "SARAMPION"]

def normalizar(texto):
    if not texto:
        return ""
    t = str(texto).upper().strip()
    for a, b in [("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ñ", "N")]:
        t = t.replace(a, b)
    return re.sub(r'[^A-Z0-9\s]', ' ', t).strip()

def safe_num(val):
    if val is None or val == "":
        return 0
    try:
        if isinstance(val, (int, float)):
            return int(round(val))
        v_str = str(val).strip().replace(",", ".")
        return int(round(float(v_str)))
    except (ValueError, TypeError):
        return None

def cargar_lotes_google_sheet():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fpath = os.path.join(base_dir, "storage", "catalogos", "deposito_risaralda.xlsx")
    lotes_dict = {}

    if not os.path.exists(fpath):
        return lotes_dict

    try:
        wb = openpyxl.load_workbook(fpath, data_only=True, read_only=True)
        if "Lotes" in wb.sheetnames:
            ws = wb["Lotes"]
            for row in ws.iter_rows(min_row=2, max_row=500, min_col=1, max_col=11, values_only=True):
                insumo = row[1]
                lote = row[7]   # Col 8
                fv = row[8]     # Col 9
                lab = row[9]    # Col 10
                if lote and str(lote).strip():
                    lote_clean = str(lote).strip().upper()
                    lotes_dict[lote_clean] = {
                        "insumo": str(insumo).strip() if insumo else "",
                        "vencimiento": str(fv)[:10] if fv else "",
                        "laboratorio": str(lab).strip() if lab else ""
                    }
        wb.close()
    except Exception as e:
        print(f"Error cargando lotes de Google Sheet: {e}")

    return lotes_dict

def cargar_entregas_deposito(municipio, mes):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fpath = os.path.join(base_dir, "storage", "catalogos", "deposito_risaralda.xlsx")
    entregas = {}

    if not os.path.exists(fpath):
        return entregas

    try:
        wb = openpyxl.load_workbook(fpath, data_only=True, read_only=True)
        kardex_sheet = None
        for s in wb.sheetnames:
            if "Kardex" in s and ("2026" in s or "Septiembre" in s or "Agosto" in s):
                kardex_sheet = s
                break
        if not kardex_sheet and "Kardex 15 Septiembre 2026" in wb.sheetnames:
            kardex_sheet = "Kardex 15 Septiembre 2026"

        if kardex_sheet:
            ws = wb[kardex_sheet]
            mun_norm = normalizar(municipio)
            for row in ws.iter_rows(min_row=2, max_row=2000, min_col=1, max_col=10, values_only=True):
                tipo = row[0]
                m_row = row[3]
                vacuna = row[5]
                cant_sal = row[6]
                if tipo and str(tipo).strip().upper() in ["SALIDA", "DESPACHO", "ENTREGA"]:
                    if m_row and mun_norm in normalizar(m_row):
                        vac_norm = normalizar(vacuna)
                        c = safe_num(cant_sal) or 0
                        entregas[vac_norm] = entregas.get(vac_norm, 0) + c
        wb.close()
    except Exception as e:
        print(f"Error cargando entregas depósito: {e}")

    return entregas

def buscar_archivo_municipal_mes_anterior(municipio, mes_anterior, ano="2026"):
    mun_clean = normalizar(municipio).replace(" ", "")
    if "SANTAROSA" in mun_clean:
        mun_clean = "SANTAROSA"
    if "BELEN" in mun_clean:
        mun_clean = "BELEN"

    posibles_directorios = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "radicados", str(ano), mes_anterior, municipio),
        rf"C:\Users\alexi\OneDrive\Documents\Pai Permanente\Informes MSPS\Movimiento Biologico\{ano}\{mes_anterior.capitalize()}\MB Municipios",
        rf"C:\Users\alexi\OneDrive\Documents\Pai Permanente\Informes MSPS\Movimiento Biologico\{ano}\{mes_anterior.capitalize()}\Municipios",
        rf"C:\Users\alexi\OneDrive\Documents\Pai Permanente\Informes MSPS\Movimiento Biologico\{ano}\{mes_anterior.upper()}\MB Municipios",
        rf"C:\Users\alexi\OneDrive\Documents\Pai Permanente\Informes MSPS\Movimiento Biologico\{ano}\{mes_anterior.upper()}\Municipios",
        rf"C:\Users\alexi\OneDrive\Documents\YoRobot\Agente Informes Pai - Antigravity\AGOSTO_2026_MUNICIPALES"
    ]

    for d in posibles_directorios:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.startswith("~$") or not f.endswith((".xlsx", ".xlsm")):
                        continue
                    f_clean = normalizar(f).replace(" ", "")
                    if mun_clean in f_clean:
                        return os.path.join(root, f)
    return None

def obtener_saldos_mes_anterior_oficial(municipio, mes_evaluar, ano="2026", wb_actual=None):
    mes_idx = MESES_ORDEN.index(mes_evaluar) if mes_evaluar in MESES_ORDEN else -1
    if mes_idx <= 0:
        return {}

    mes_anterior = MESES_ORDEN[mes_idx - 1]
    prev_file = buscar_archivo_municipal_mes_anterior(municipio, mes_anterior, ano)

    saldos_previos = {}

    def extraer_saldos_de_hoja(ws):
        saldos = {}
        for row in ws.iter_rows(min_row=5, max_row=250, min_col=1, max_col=15, values_only=True):
            c1, c2, c13 = row[0], row[1], row[12]
            if c1 is not None and str(c1).strip().isdigit() and c2 and str(c2).strip():
                insumo = normalizar(c2)
                saldo_cierre = safe_num(c13)
                if saldo_cierre is not None:
                    saldos[insumo] = saldo_cierre
        return saldos

    if prev_file and os.path.exists(prev_file):
        try:
            wb_prev = openpyxl.load_workbook(prev_file, data_only=True, read_only=True)
            prev_sheet = None
            for s in wb_prev.sheetnames:
                if normalizar(s) == mes_anterior or s.upper().startswith(mes_anterior[:3]):
                    prev_sheet = s
                    break
            if prev_sheet:
                saldos_previos = extraer_saldos_de_hoja(wb_prev[prev_sheet])
            wb_prev.close()
        except Exception as e:
            print(f"Error leyendo saldos del archivo previo {prev_file}: {e}")

    # Si no se encontró en archivo externo, verificar si el libro actual contiene la hoja del mes anterior
    if not saldos_previos and wb_actual:
        try:
            for s in wb_actual.sheetnames:
                if normalizar(s) == mes_anterior or s.upper().startswith(mes_anterior[:3]):
                    saldos_previos = extraer_saldos_de_hoja(wb_actual[s])
                    break
        except Exception as e:
            print(f"Error extrayendo hoja previa de libro actual: {e}")

    return saldos_previos

def validar_movimiento(filepath, mes_evaluar="AGOSTO", municipio_nombre=None, ano="2026"):
    """
    Audita el archivo de Movimiento de Biológicos aplicando las 5 Reglas Departamentales.
    Estructura exacta: Cada biológico consta de 5 filas de lotes (r a r+4) y una fila de control (r+5).
    """
    mes_evaluar = normalizar(mes_evaluar)
    municipio_nombre = normalizar(municipio_nombre) if municipio_nombre else "DESCONOCIDO"

    lotes_maestros = cargar_lotes_google_sheet()
    entregas_deposito = cargar_entregas_deposito(municipio_nombre, mes_evaluar)

    resultado = {
        "valido": True,
        "tipo": "MOVIMIENTO_BIOLOGICOS",
        "mes": mes_evaluar,
        "municipio": municipio_nombre,
        "total_biologicos_evaluados": 0,
        "total_dosis_aplicadas": 0,
        "total_dosis_perdidas": 0,
        "errores": [],
        "advertencias": [],
        "metricas_reglas": {
            "regla1_continuidad_saldos": True,
            "regla2_flag_verdadero": True,
            "regla3_cruce_deposito": True,
            "regla4_lotes_oficiales": True,
            "regla5_racionalidad_perdidas": True
        }
    }

    try:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)

        target_sheet = None
        mes_aliases = MESES_MAP.get(mes_evaluar, [mes_evaluar])
        for sheet_name in wb.sheetnames:
            s_norm = normalizar(sheet_name)
            if any(alias == s_norm or s_norm.startswith(alias) for alias in mes_aliases):
                target_sheet = sheet_name
                break

        if not target_sheet:
            resultado["valido"] = False
            resultado["errores"].append({
                "tipo": "HOJA_MES_FALTANTE",
                "mensaje": f"No se encontró la hoja correspondiente al mes de {mes_evaluar}."
            })
            wb.close()
            return resultado

        # Cargar saldos oficiales del mes anterior
        saldos_previos_oficiales = obtener_saldos_mes_anterior_oficial(municipio_nombre, mes_evaluar, ano, wb_actual=wb)

        ws = wb[target_sheet]
        rows_data = list(ws.iter_rows(min_row=1, max_row=240, min_col=1, max_col=45, values_only=True))
        wb.close()

        def get_c(r, c):
            if 1 <= r <= len(rows_data):
                row = rows_data[r - 1]
                if 1 <= c <= len(row):
                    return row[c - 1]
            return None

        r = 1
        while r <= len(rows_data):
            c1 = get_c(r, 1)
            c2 = get_c(r, 2)

            es_item = False
            try:
                if c1 is not None and int(c1) > 0 and c2 and str(c2).strip():
                    es_item = True
            except (ValueError, TypeError):
                es_item = False

            if not es_item:
                r += 1
                continue

            num_item = int(c1)
            insumo_raw = str(c2).strip()
            insumo_norm = normalizar(insumo_raw)
            resultado["total_biologicos_evaluados"] += 1

            saldo_ant = safe_num(get_c(r, 4)) or 0
            ent_acopio = safe_num(get_c(r, 5)) or 0
            dosis_col = safe_num(get_c(r, 6)) or 0
            dosis_ext = safe_num(get_c(r, 7)) or 0
            ent_traslado = safe_num(get_c(r, 8)) or 0
            sal_traslado = safe_num(get_c(r, 9)) or 0
            tot_aplicadas = safe_num(get_c(r, 10)) or (dosis_col + dosis_ext)
            dosis_perdidas = safe_num(get_c(r, 11)) or 0
            saldo_sig = safe_num(get_c(r, 13))

            resultado["total_dosis_aplicadas"] += tot_aplicadas
            resultado["total_dosis_perdidas"] += dosis_perdidas

            # =================================================================
            # REGLA 1: CONTINUIDAD INTERMENSUAL (vs Archivo Oficial Previo)
            # =================================================================
            if saldos_previos_oficiales:
                saldo_cierre_previo = None
                if insumo_norm in saldos_previos_oficiales:
                    saldo_cierre_previo = saldos_previos_oficiales[insumo_norm]
                else:
                    # Búsqueda difusa si no coincide 100% exacto
                    for k, v in saldos_previos_oficiales.items():
                        if k in insumo_norm or insumo_norm in k:
                            saldo_cierre_previo = v
                            break

                if saldo_cierre_previo is not None and saldo_ant != saldo_cierre_previo:
                    dif = abs(saldo_ant - saldo_cierre_previo)
                    resultado["errores"].append({
                        "regla": "REGLA_1_CONTINUIDAD_SALDOS",
                        "insumo": insumo_raw,
                        "saldo_reportado": saldo_ant,
                        "saldo_oficial_previo": saldo_cierre_previo,
                        "diferencia": dif,
                        "mensaje": f"[Regla 1] En '{insumo_raw}': El Saldo Anterior en {mes_evaluar} ({saldo_ant}) NO coincide con el cierre oficial del mes anterior ({saldo_cierre_previo}). Descuadre: {dif} dosis alteradas."
                    })
                    resultado["valido"] = False
                    resultado["metricas_reglas"]["regla1_continuidad_saldos"] = False

            # =================================================================
            # REGLA 2: ESTRUCTURA DE 5 CELDAS DE LOTES + FILA DE CONTROL (VERDADERO)
            # =================================================================
            # Cada biológico tiene exactamente 5 celdas para lotes: filas r a r+4 (slots 0 a 4)
            dosis_lotes_manual = 0
            lotes_item_encontrados = []

            for slot in range(5):
                slot_r = r + slot
                if slot_r > len(rows_data):
                    break
                d_lote = safe_num(get_c(slot_r, 14))
                n_lote = get_c(slot_r, 15)
                lab_lote = get_c(slot_r, 16)
                fv_lote = get_c(slot_r, 17)

                if d_lote is not None and d_lote > 0:
                    dosis_lotes_manual += d_lote
                    lote_clean = str(n_lote).strip().upper() if n_lote else ""
                    # Enriquecer laboratorio y vencimiento desde catálogo maestro si el digitador no lo digitó
                    lab_enriquecido = str(lab_lote).strip() if lab_lote else ""
                    fv_enriquecido = fv_lote
                    if lote_clean in lotes_maestros:
                        if not lab_enriquecido:
                            lab_enriquecido = lotes_maestros[lote_clean].get("laboratorio", "")
                        if not fv_enriquecido:
                            fv_enriquecido = lotes_maestros[lote_clean].get("vencimiento", "")

                    lotes_item_encontrados.append({
                        "slot": slot + 1,
                        "fila": slot_r,
                        "dosis": d_lote,
                        "lote": lote_clean,
                        "lab": lab_enriquecido,
                        "fv": fv_enriquecido
                    })

            # La fila de control y verificación oficial está exactamente en r + 5
            chk_row = r + 5
            celda_control_val = get_c(chk_row, 13) # Col 13 (M): fórmula =M5=N10 (TRUE/FALSE)
            celda_suma_lotes = safe_num(get_c(chk_row, 14)) # Col 14 (N): fórmula =SUM(N5:N9)

            es_verdadero = False
            if celda_control_val is not None:
                val_str = str(celda_control_val).strip().upper()
                if val_str in ["TRUE", "VERDADERO", "1"]:
                    es_verdadero = True

            saldo_esperado = saldo_sig if saldo_sig is not None else 0

            # Validar coincidencia de la suma manual de los 5 slots contra el saldo siguiente
            # Y verificar que la celda de control oficial responda VERDADERO
            if dosis_lotes_manual != saldo_esperado or (saldo_esperado > 0 and not es_verdadero):
                dif = abs(dosis_lotes_manual - saldo_esperado)
                resultado["errores"].append({
                    "regla": "REGLA_2_COHERENCIA_LOTES",
                    "insumo": insumo_raw,
                    "fila": r,
                    "saldo_siguiente": saldo_esperado,
                    "suma_lotes_5_celdas": dosis_lotes_manual,
                    "celda_control_oficial": str(celda_control_val),
                    "diferencia": dif,
                    "mensaje": f"[Regla 2] En '{insumo_raw}': La suma de las 5 celdas de lotes ({dosis_lotes_manual}) no coincide con el Saldo que inicia el mes siguiente ({saldo_esperado}). La celda de validación arrojó '{celda_control_val}'. Descuadre: {dif} dosis."
                })
                resultado["valido"] = False
                resultado["metricas_reglas"]["regla2_flag_verdadero"] = False

            # =================================================================
            # REGLA 3: CRUCE CON ENTREGAS DEL CENTRO DE ACOPIO (Google Sheets)
            # =================================================================
            if entregas_deposito:
                despachado_deposito = None
                for vac_k, cant_dep in entregas_deposito.items():
                    if vac_k in insumo_norm or insumo_norm in vac_k:
                        despachado_deposito = cant_dep
                        break

                if despachado_deposito is not None and ent_acopio != despachado_deposito:
                    dif = abs(ent_acopio - despachado_deposito)
                    resultado["advertencias"].append({
                        "regla": "REGLA_3_CRUCE_DEPOSITO",
                        "insumo": insumo_raw,
                        "recibido_municipio": ent_acopio,
                        "despachado_deposito": despachado_deposito,
                        "diferencia": dif,
                        "mensaje": f"[Regla 3] En '{insumo_raw}': El municipio reportó haber recibido {ent_acopio} dosis del Centro de Acopio, pero en el Kardex oficial del Depósito Departamental figuran despachadas {despachado_deposito} dosis. Diferencia: {dif} dosis."
                    })

            # =================================================================
            # REGLA 4: VALIDACIÓN DE LOTES CONTRA HOJA 'LOTES' (Google Sheets)
            # =================================================================
            for lote_info in lotes_item_encontrados:
                lote_code = lote_info["lote"]
                lab_info = lote_info["lab"]
                fv_info = lote_info["fv"]
                slot_num = lote_info["slot"]
                f_slot = lote_info["fila"]

                if not lote_code:
                    resultado["errores"].append({
                        "regla": "REGLA_4_LOTE_FALTANTE",
                        "insumo": insumo_raw,
                        "mensaje": f"[Regla 4] En '{insumo_raw}' (Fila {f_slot}, Celda lote {slot_num}): Hay {lote_info['dosis']} dosis asignadas pero la celda de No. Lote está en blanco."
                    })
                    resultado["valido"] = False
                else:
                    if lotes_maestros and lote_code not in lotes_maestros:
                        resultado["advertencias"].append({
                            "regla": "REGLA_4_LOTE_NO_CATALOGADO",
                            "insumo": insumo_raw,
                            "lote": lote_code,
                            "mensaje": f"[Regla 4] En '{insumo_raw}': El lote '{lote_code}' no figura en el catálogo maestro oficial del Depósito de Risaralda. Por favor verificar."
                        })

            # =================================================================
            # REGLA 5: RACIONALIDAD BIOLÓGICA DE PÉRDIDAS
            # =================================================================
            p_fa_inst = safe_num(get_c(r, 28)) or 0
            p_fa_ext = safe_num(get_c(r, 29)) or 0
            p_fa_tot = safe_num(get_c(r, 30)) or (p_fa_inst + p_fa_ext)
            p_frio = safe_num(get_c(r, 31)) or 0
            p_contam = safe_num(get_c(r, 32)) or 0
            p_roto = safe_num(get_c(r, 33)) or 0
            p_manip = safe_num(get_c(r, 34)) or 0
            p_vencim = safe_num(get_c(r, 35)) or 0
            p_farmaco = safe_num(get_c(r, 36)) or 0
            p_vomito = safe_num(get_c(r, 37)) or 0
            p_edad = safe_num(get_c(r, 38)) or 0
            p_decision = safe_num(get_c(r, 39)) or 0
            p_robo = safe_num(get_c(r, 40)) or 0

            # 5.1: Vómito franco exclusivo para vacunas orales
            es_oral = any(v in insumo_norm for v in VACUNAS_ORALES)
            if p_vomito > 0 and not es_oral:
                resultado["errores"].append({
                    "regla": "REGLA_5_RACIONALIDAD_PERDIDAS",
                    "insumo": insumo_raw,
                    "causa": "Vómito Franco",
                    "dosis": p_vomito,
                    "mensaje": f"[Regla 5] En '{insumo_raw}': Se reportaron {p_vomito} dosis perdidas por 'Vómito Franco', pero este biológico se administra por vía inyectable. El vómito solo aplica para vacunas orales (Rotavirus / Polio oral)."
                })
                resultado["valido"] = False
                resultado["metricas_reglas"]["regla5_racionalidad_perdidas"] = False

            # 5.2: Factor abierto exclusivo para multidosis
            es_multidosis = any(v in insumo_norm for v in VACUNAS_MULTIDOSIS)
            if p_fa_tot > 0 and not es_multidosis and "JERINGA" not in insumo_norm and "DILUYENTE" not in insumo_norm:
                resultado["advertencias"].append({
                    "regla": "REGLA_5_RACIONALIDAD_PERDIDAS",
                    "insumo": insumo_raw,
                    "causa": "Factor Abierto",
                    "dosis": p_fa_tot,
                    "mensaje": f"[Regla 5] En '{insumo_raw}': Se registraron {p_fa_tot} dosis en 'Factor Abierto'. Verifica si la presentación utilizada en el municipio es monodosis o multidosis."
                })

            # 5.3: Suma de causas debe igualar a Total Pérdidas
            suma_causas = p_fa_tot + p_frio + p_contam + p_roto + p_manip + p_vencim + p_farmaco + p_vomito + p_edad + p_decision + p_robo
            if dosis_perdidas > 0:
                if suma_causas != dosis_perdidas:
                    dif = abs(suma_causas - dosis_perdidas)
                    resultado["errores"].append({
                        "regla": "REGLA_5_SUMA_PERDIDAS",
                        "insumo": insumo_raw,
                        "dosis_perdidas_resumen": dosis_perdidas,
                        "suma_causas": suma_causas,
                        "diferencia": dif,
                        "mensaje": f"[Regla 5] En '{insumo_raw}': El Total Dosis Perdidas reportado ({dosis_perdidas}) no coincide con la suma de las 11 causas clasificadas ({suma_causas}). Descuadre: {dif} dosis."
                    })
                    resultado["valido"] = False
                    resultado["metricas_reglas"]["regla5_racionalidad_perdidas"] = False

            # Avanzamos exactamente al siguiente ítem biológico (bloque de 6 filas: 5 slots + 1 fila check)
            r += 6

    except Exception as e:
        resultado["valido"] = False
        resultado["errores"].append({
            "tipo": "ERROR_LECTURA",
            "mensaje": f"Fallo al procesar archivo de Movimiento: {str(e)}"
        })

    return resultado
