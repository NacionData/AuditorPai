"""
validator_extranjeros.py - Validador para la plantilla de Vacunados Extranjeros.
Audita las 6 hojas de países fronterizos y su coherencia de reporte mensual.
"""
import openpyxl
import re

HOJAS_PAISES = [
    "1_BRASIL", "2_ECUADOR", "3_PANAMA", "4_PERU", "5_OTROS", "6_VENEZOLANOS"
]

MESES_ORDEN = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

def normalizar(texto):
    if not texto:
        return ""
    t = str(texto).upper().strip()
    for a, b in [("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ñ", "N")]:
        t = t.replace(a, b)
    return t

def safe_num(val):
    if val is None or val == "":
        return 0
    try:
        if isinstance(val, (int, float)):
            return int(round(val))
        return int(round(float(str(val).strip().replace(",", "."))))
    except (ValueError, TypeError):
        return None

def validar_extranjeros(filepath, mes_evaluar="AGOSTO", municipio_nombre=None):
    mes_evaluar = normalizar(mes_evaluar)
    resultado = {
        "valido": True,
        "tipo": "VACUNADOS_EXTRANJEROS",
        "mes": mes_evaluar,
        "municipio": municipio_nombre or "DESCONOCIDO",
        "total_extranjeros_vacunados": 0,
        "hojas_evaluadas": [],
        "errores": [],
        "advertencias": []
    }

    try:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        hojas_disponibles = [h for h in wb.sheetnames]
        hojas_norm = [normalizar(h) for h in hojas_disponibles]

        # Verificar presencia de hojas de países
        hojas_a_revisar = []
        for p in HOJAS_PAISES:
            p_norm = normalizar(p)
            for idx, h in enumerate(hojas_norm):
                if p_norm in h or p_norm.split("_")[-1] in h:
                    hojas_a_revisar.append(hojas_disponibles[idx])
                    break

        if not hojas_a_revisar:
            resultado["valido"] = False
            resultado["errores"].append({
                "tipo": "HOJAS_PAISES_FALTANTES",
                "mensaje": "El archivo no contiene las hojas requeridas de países fronterizos (Venezuela, Brasil, etc.)."
            })
            wb.close()
            return resultado

        # Evaluar cada hoja de país
        mes_idx = MESES_ORDEN.index(mes_evaluar) if mes_evaluar in MESES_ORDEN else 7
        fila_teorica = 9 + (mes_idx * 9)

        total_dosis_ext = 0
        total_acumulado_ano = 0
        desglose_mensual = {m: 0 for m in MESES_ORDEN}

        for h_name in hojas_a_revisar:
            ws = wb[h_name]
            resultado["hojas_evaluadas"].append(h_name)

            # Cargar slice en memoria con todas las 480 columnas de biológicos
            grid = []
            for row in ws.iter_rows(min_row=1, max_row=260, min_col=1, max_col=480, values_only=True):
                grid.append(row)

            def get_val(r, c):
                if 1 <= r <= len(grid):
                    row = grid[r - 1]
                    if 1 <= c <= len(row):
                        return row[c - 1]
                return None

            start_row = fila_teorica
            # Comprobar si fila coincide con el mes a evaluar en columna 3 (o col 2/4)
            val_c3 = get_val(fila_teorica, 3)
            if not (val_c3 and mes_evaluar in normalizar(val_c3)):
                for r in range(8, min(len(grid) + 1, 130)):
                    c3 = get_val(r, 3) or get_val(r, 2)
                    if c3 and mes_evaluar in normalizar(c3):
                        start_row = r
                        break

            row_tot_gen = start_row + 3
            row_tot_reg = start_row + 8

            # Escaneo completo de las columnas de biológicos (Col 5 hasta 475)
            for c in range(5, 476):
                tot_gen = safe_num(get_val(row_tot_gen, c)) or 0
                tot_reg = safe_num(get_val(row_tot_reg, c)) or 0

                if tot_gen == 0 and tot_reg == 0:
                    continue

                total_dosis_ext += tot_gen

                if tot_gen != tot_reg:
                    col_let = openpyxl.utils.get_column_letter(c)
                    resultado["errores"].append({
                        "tipo": "DESCUADRE_EXTRANJEROS",
                        "hoja": h_name,
                        "columna": col_let,
                        "mensaje": f"En hoja '{h_name}' (Col {col_let}): Total Género ({tot_gen}) != Total Régimen ({tot_reg})."
                    })
                    resultado["valido"] = False

            # Calcular además el desglose histórico acumulado de todos los meses
            for m_i, m_nom in enumerate(MESES_ORDEN):
                m_start_r = 9 + (m_i * 9)
                m_tot_gen_r = m_start_r + 3
                if m_tot_gen_r <= len(grid):
                    row_vals = grid[m_tot_gen_r - 1]
                    sum_m = sum(safe_num(v) or 0 for c_idx, v in enumerate(row_vals[4:475], start=5) if v is not None)
                    desglose_mensual[m_nom] += sum_m
                    total_acumulado_ano += sum_m

        resultado["total_extranjeros_vacunados"] = total_dosis_ext
        resultado["total_acumulado_ano"] = total_acumulado_ano
        resultado["desglose_mensual"] = {k: v for k, v in desglose_mensual.items() if v > 0}

        if total_dosis_ext == 0 and total_acumulado_ano > 0:
            detalles_prev = ", ".join([f"{k}: {v}" for k, v in resultado["desglose_mensual"].items()])
            resultado["advertencias"].append({
                "tipo": "INFORME_SIN_DOSIS_DEL_MES_CON_HISTORICO",
                "mensaje": f"El informe registra 0 dosis aplicadas para {mes_evaluar}, pero contiene un acumulado de {total_acumulado_ano} dosis en meses previos ({detalles_prev})."
            })

        wb.close()

    except Exception as e:
        resultado["valido"] = False
        resultado["errores"].append({
            "tipo": "ERROR_LECTURA",
            "mensaje": f"Fallo al procesar archivo de Extranjeros: {str(e)}"
        })

    return resultado
