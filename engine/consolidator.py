"""
consolidator.py - Motor de Consolidación Departamental PAI Risaralda.
Toma los informes radicados y aprobados de los 14 municipios y genera
las 3 plantillas consolidadas oficiales para el Ministerio de Salud,
complementando la plantilla base departamental cargada por el Administrador
(con la información del Centro de Acopio Departamental / Depósito).
"""
import openpyxl
import os
import shutil
import re
from datetime import datetime, date

MESES_ORDEN = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

MAPA_FILAS_DEPARTAMENTAL_DOSIS = {
    "PEREIRA": 9,
    "APIA": 28,
    "BALBOA": 47,
    "BELEN": 66,
    "BELEN DE UMBRIA": 66,
    "DOSQUEBRADAS": 85,
    "GUATICA": 104,
    "LA CELIA": 123,
    "LA VIRGINIA": 142,
    "MARSELLA": 161,
    "MISTRATO": 180,
    "PUEBLO RICO": 199,
    "QUINCHIA": 218,
    "SANTA ROSA": 237,
    "SANTA ROSA DE CABAL": 237,
    "SANTUARIO": 256
}

MAPA_FILAS_CONSOLIDADO_REGIMEN = {
    "PEREIRA": 3,
    "APIA": 4,
    "BALBOA": 5,
    "BELEN": 6,
    "BELEN DE UMBRIA": 6,
    "DOSQUEBRADAS": 7,
    "GUATICA": 8,
    "LA CELIA": 9,
    "LA VIRGINIA": 10,
    "MARSELLA": 11,
    "MISTRATO": 12,
    "PUEBLO RICO": 13,
    "QUINCHIA": 14,
    "SANTA ROSA": 15,
    "SANTA ROSA DE CABAL": 15,
    "SANTUARIO": 16
}

MAPA_FILAS_EXTRANJEROS_MPIOS = {
    "PEREIRA": 9,
    "APIA": 18,
    "BALBOA": 27,
    "BELEN": 36,
    "BELEN DE UMBRIA": 36,
    "DOSQUEBRADAS": 45,
    "GUATICA": 54,
    "LA CELIA": 63,
    "LA VIRGINIA": 72,
    "MARSELLA": 81,
    "MISTRATO": 90,
    "PUEBLO RICO": 99,
    "QUINCHIA": 108,
    "SANTA ROSA": 117,
    "SANTA ROSA DE CABAL": 117,
    "SANTUARIO": 126
}

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
        return 0

def set_cell_safe(ws, r, c, val):
    """Escribe en una celda asegurando que no sea una MergedCell de solo lectura."""
    try:
        cell = ws.cell(row=r, column=c)
        if type(cell).__name__ != 'MergedCell':
            cell.value = val
    except Exception:
        pass

def obtener_plantilla_base_mes(tipo, mes, ano, templates_dir, custom_dir):
    """
    Busca si el Administrador cargó una plantilla base mensual personalizada
    con la información del Centro de Acopio o acumulados. Si no, usa la por defecto.
    tipo: 'movimiento', 'dosis', 'extranjeros'
    """
    tipo = tipo.lower()
    exts = [".xlsm", ".xlsx"] if tipo == "movimiento" else [".xlsx"]
    
    if os.path.exists(custom_dir):
        # 1. Buscar coincidencia exacta por prefijo
        prefijo = f"BASE_{tipo.upper()}_{mes}_{ano}"
        for f in os.listdir(custom_dir):
            if f.upper().startswith(prefijo) and any(f.endswith(e) for e in exts):
                return os.path.join(custom_dir, f), True
        
        # 2. Buscar por nombre genérico en la carpeta del mes
        for f in os.listdir(custom_dir):
            f_norm = f.upper()
            if tipo in f_norm.lower() and any(f.endswith(e) for e in exts):
                return os.path.join(custom_dir, f), True

    # Fallback a plantilla base por defecto
    default_names = {
        "movimiento": "Plantilla_Movimiento_Base.xlsm",
        "dosis": "Plantilla_Dosis_Base.xlsx",
        "extranjeros": "Plantilla_Extranjeros_Base.xlsx"
    }
    def_path = os.path.join(templates_dir, default_names[tipo])
    return def_path, False

def consolidar_departamento(mes="AGOSTO", ano="2026", fuentes_municipios=None):
    """
    Consolida los archivos de los municipios en las plantillas oficiales MinSalud.
    fuentes_municipios: dict { "NOMBRE_MUNICIPIO": { "DOSIS": path, "MOVIMIENTO": path, "EXTRANJEROS": path } }
    Retorna un diccionario con las rutas de los 3 archivos consolidados generados y metadatos.
    """
    mes = normalizar(mes)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates_base")
    custom_templates_dir = os.path.join(base_dir, "storage", "templates_mes", str(ano), mes)
    output_dir = os.path.join(base_dir, "storage", "consolidados", str(ano), mes)
    os.makedirs(output_dir, exist_ok=True)

    archivos_generados = {
        "dosis": None,
        "movimiento": None,
        "extranjeros": None,
        "municipios_incluidos": [],
        "bases_utilizadas": {}
    }

    if not fuentes_municipios:
        return archivos_generados

    # -------------------------------------------------------------
    # 1. CONSOLIDAR DOSIS APLICADAS
    # -------------------------------------------------------------
    base_dosis, es_custom_dosis = obtener_plantilla_base_mes("dosis", mes, ano, templates_dir, custom_templates_dir)
    out_dosis = os.path.join(output_dir, f"RISARALDA_Plantilla_Dosis_Aplicadas_{mes}_{ano}_MINSALUD.xlsx")
    shutil.copy2(base_dosis, out_dosis)
    archivos_generados["bases_utilizadas"]["dosis"] = "PERSONALIZADA_DEPOSITO" if es_custom_dosis else "DEFECTO"

    wb_out_dosis = openpyxl.load_workbook(out_dosis)
    ws_dosis = wb_out_dosis["1_PLANTILLA_MENSUAL"]
    ws_regimen = wb_out_dosis["3_CONSOLIDADO REGIMEN"] if "3_CONSOLIDADO REGIMEN" in wb_out_dosis.sheetnames else None

    # Actualizar mes en cabecera
    ws_dosis["D5"] = mes
    ws_dosis["D4"] = int(ano) if ano.isdigit() else ano

    mes_idx = MESES_ORDEN.index(mes) if mes in MESES_ORDEN else 7
    src_row_start_teorica = 9 + (mes_idx * 19)
    max_c = 541

    for mun_nombre, f_dict in fuentes_municipios.items():
        mun_norm = normalizar(mun_nombre)
        target_row_start = None
        for k, row_idx in MAPA_FILAS_DEPARTAMENTAL_DOSIS.items():
            if k == mun_norm or mun_norm in k or k in mun_norm:
                target_row_start = row_idx
                break

        if not target_row_start or "DOSIS" not in f_dict or not f_dict["DOSIS"]:
            continue

        dosis_path = f_dict["DOSIS"]
        if not os.path.exists(dosis_path):
            continue

        try:
            wb_src = openpyxl.load_workbook(dosis_path, data_only=True, read_only=True)
            if "1_PLANTILLA_MENSUAL" in wb_src.sheetnames:
                ws_src = wb_src["1_PLANTILLA_MENSUAL"]
                grid_src = list(ws_src.iter_rows(min_row=1, max_row=260, min_col=1, max_col=max_c, values_only=True))
                
                # Buscar fila inicial en origen
                src_start = src_row_start_teorica
                val_c3 = grid_src[src_start - 1][2] if src_start <= len(grid_src) else None
                if not (val_c3 and mes in normalizar(val_c3)):
                    for r_i in range(8, len(grid_src) + 1):
                        cell_v = grid_src[r_i - 1][2]
                        if cell_v and mes in normalizar(cell_v):
                            src_start = r_i
                            break

                # Copiar solo las filas de datos primarios (omitiendo filas de fórmulas de totales: 3, 8, 15)
                filas_totales_offset = {3, 8, 15}
                for r_offset in range(19):
                    if r_offset in filas_totales_offset:
                        continue
                    src_r = src_start + r_offset
                    dst_r = target_row_start + r_offset
                    if src_r <= len(grid_src):
                        row_vals = grid_src[src_r - 1]
                        for c_i in range(5, max_c + 1):
                            # Omitir columnas de fórmulas de resumen y metadatos (474 a 521 y 524)
                            if (474 <= c_i <= 521) or c_i == 524:
                                continue
                            v = row_vals[c_i - 1] if c_i <= len(row_vals) else None
                            if v is not None and isinstance(v, (int, float)) and v != 0:
                                ws_dosis.cell(dst_r, c_i).value = v

                if mun_nombre not in archivos_generados["municipios_incluidos"]:
                    archivos_generados["municipios_incluidos"].append(mun_nombre)
            wb_src.close()
        except Exception as e:
            print(f"Error consolidando dosis de {mun_nombre}: {e}")

    wb_out_dosis.save(out_dosis)
    wb_out_dosis.close()
    archivos_generados["dosis"] = out_dosis

    # -------------------------------------------------------------
    # 2. CONSOLIDAR MOVIMIENTO DE BIOLÓGICOS (.xlsm)
    # -------------------------------------------------------------
    # La plantilla departamental oficial contiene:
    # - Parte 1: Centro de Acopio Departamental (CA) (Filas 8 a 410) -> SE PRESERVA INTACTA como la subió el Administrador.
    # - Parte 2: Consolidado Municipios (Filas 411 a 860) -> SE COMPLEMENTA sumando los 14 municipios.
    # -------------------------------------------------------------
    base_mov, es_custom_mov = obtener_plantilla_base_mes("movimiento", mes, ano, templates_dir, custom_templates_dir)
    out_mov = os.path.join(output_dir, f"Movimiento_PAI_{mes}_{ano}_MINSALUD.xlsm")
    shutil.copy2(base_mov, out_mov)
    archivos_generados["bases_utilizadas"]["movimiento"] = "PERSONALIZADA_DEPOSITO" if es_custom_mov else "DEFECTO"

    try:
        # 2.1 Cargar y agregar los datos de Movimiento de los municipios
        # Estructura de agregación por ítem:
        # { insumo_norm: { 'dosis_col': 0, 'dosis_ext': 0, 'perdidas': { 'causa_key': total }, 'lotes': { 'lote': { 'dosis': N, 'lab': S, 'fv': S } } } }
        datos_consolidados_items = {}

        # Mapeo de columnas de pérdidas en el archivo MUNICIPAL
        # Col 28: Pol. Frasco Abierto Inst -> Dept Col 26 (Z)
        # Col 29: Pol. Frasco Abierto Ext  -> Dept Col 27 (AA)
        # Col 31: Cadena frío              -> Dept Col 29 (AC)
        # Col 32: Contaminación            -> Dept Col 30 (AD)
        # Col 33: Vial roto                -> Dept Col 31 (AE)
        # Col 34: Manipulación             -> Dept Col 32 (AF)
        # Col 35: Vencimiento              -> Dept Col 33 (AG)
        # Col 36: Farmacovigilancia        -> Dept Col 34 (AH)
        # Col 37: Vómito franco            -> Dept Col 35 (AI)
        # Col 38: Fuera de edad            -> Dept Col 36 (AJ)
        # Col 39: Decisión paciente        -> Dept Col 37 (AK)
        # Col 40: Robo / hurto             -> Dept Col 38 (AL)
        MAPA_COLS_PERDIDAS_MUN_TO_DEPT = {
            28: 26, # Inst
            29: 27, # Ext
            31: 29, # Cadena frío
            32: 30, # Contaminación
            33: 31, # Vial roto
            34: 32, # Manipulación
            35: 33, # Vencimiento
            36: 34, # Farmaco
            37: 35, # Vómito franco
            38: 36, # Fuera de edad
            39: 37, # Decisión paciente
            40: 38  # Siniestro o robo
        }

        for mun_nombre, f_dict in fuentes_municipios.items():
            if "MOVIMIENTO" not in f_dict or not f_dict["MOVIMIENTO"]:
                continue
            mov_path = f_dict["MOVIMIENTO"]
            if not os.path.exists(mov_path):
                continue

            try:
                wb_m_src = openpyxl.load_workbook(mov_path, data_only=True, read_only=True)
                # Buscar hoja del mes
                target_sheet_m = None
                for s in wb_m_src.sheetnames:
                    if mes in normalizar(s) or normalizar(s).startswith(mes[:3]):
                        target_sheet_m = s
                        break
                if not target_sheet_m:
                    wb_m_src.close()
                    continue

                ws_m_src = wb_m_src[target_sheet_m]
                grid_m = list(ws_m_src.iter_rows(min_row=1, max_row=400, min_col=1, max_col=45, values_only=True))
                wb_m_src.close()

                r = 1
                while r <= len(grid_m):
                    row = grid_m[r - 1]
                    c1 = row[0] if len(row) > 0 else None
                    c2 = row[1] if len(row) > 1 else None

                    es_item = False
                    try:
                        if c1 is not None and int(c1) > 0 and c2 and str(c2).strip():
                            es_item = True
                    except (ValueError, TypeError):
                        es_item = False

                    if not es_item:
                        r += 1
                        continue

                    insumo_raw = str(c2).strip()
                    insumo_norm = normalizar(insumo_raw)

                    if insumo_norm not in datos_consolidados_items:
                        datos_consolidados_items[insumo_norm] = {
                            "insumo_raw": insumo_raw,
                            "dosis_col": 0,
                            "dosis_ext": 0,
                            "perdidas_cols": {dept_c: 0 for dept_c in MAPA_COLS_PERDIDAS_MUN_TO_DEPT.values()},
                            "lotes": {}
                        }

                    item_acc = datos_consolidados_items[insumo_norm]

                    # Dosis aplicadas
                    d_col = safe_num(row[5]) if len(row) > 5 else 0 # Col F (6)
                    d_ext = safe_num(row[6]) if len(row) > 6 else 0 # Col G (7)
                    item_acc["dosis_col"] += d_col
                    item_acc["dosis_ext"] += d_ext

                    # Causas de pérdidas
                    for mun_c, dept_c in MAPA_COLS_PERDIDAS_MUN_TO_DEPT.items():
                        val_p = safe_num(row[mun_c - 1]) if len(row) >= mun_c else 0
                        item_acc["perdidas_cols"][dept_c] += val_p

                    # Extraer lotes (slots de r a r+4)
                    for slot in range(5):
                        slot_r = r + slot
                        if slot_r <= len(grid_m):
                            r_slot = grid_m[slot_r - 1]
                            d_lote = safe_num(r_slot[13]) if len(r_slot) > 13 else 0 # Col 14 (N)
                            n_lote = str(r_slot[14]).strip().upper() if len(r_slot) > 14 and r_slot[14] else "" # Col 15 (O)
                            lab_lote = str(r_slot[15]).strip() if len(r_slot) > 15 and r_slot[15] else "" # Col 16 (P)
                            fv_lote = r_slot[16] if len(r_slot) > 16 else None # Col 17 (Q)

                            if n_lote and n_lote.endswith(".0"):
                                n_lote = n_lote[:-2]

                            if d_lote > 0 and n_lote:
                                if n_lote not in item_acc["lotes"]:
                                    item_acc["lotes"][n_lote] = {
                                        "dosis": 0,
                                        "lab": lab_lote,
                                        "fv": fv_lote
                                    }
                                item_acc["lotes"][n_lote]["dosis"] += d_lote
                                if lab_lote and not item_acc["lotes"][n_lote]["lab"]:
                                    item_acc["lotes"][n_lote]["lab"] = lab_lote
                                if fv_lote and not item_acc["lotes"][n_lote]["fv"]:
                                    item_acc["lotes"][n_lote]["fv"] = fv_lote

                    r += 6
            except Exception as e:
                print(f"Error procesando movimiento de {mun_nombre}: {e}")

        # 2.2 Inyectar la información consolidada en la sección 'CONSOLIDADO MUNICIPIOS' del libro departamental
        wb_out_mov = openpyxl.load_workbook(out_mov, keep_vba=True)
        target_sname = None
        for s in wb_out_mov.sheetnames:
            if normalizar(s) == mes or s.upper().startswith(mes[:3]):
                target_sname = s
                break

        if target_sname:
            ws_m_out = wb_out_mov[target_sname]
            ws_m_out["E6"] = mes
            ws_m_out["I6"] = int(ano) if ano.isdigit() else ano

            # Identificar ítems en la sección CONSOLIDADO MUNICIPIOS (Filas 411 en adelante)
            for r_dept in range(411, min(ws_m_out.max_row + 1, 880)):
                c1 = ws_m_out.cell(row=r_dept, column=1).value
                c2 = ws_m_out.cell(row=r_dept, column=2).value

                es_item_dept = False
                try:
                    if c1 is not None and str(c1).strip().isdigit() and int(c1) > 0 and c2 and str(c2).strip():
                        es_item_dept = True
                except (ValueError, TypeError):
                    es_item_dept = False

                if not es_item_dept:
                    continue

                item_dept_norm = normalizar(c2)

                # Buscar coincidencia en los datos consolidados de los municipios
                acc_data = None
                if item_dept_norm in datos_consolidados_items:
                    acc_data = datos_consolidados_items[item_dept_norm]
                else:
                    # Búsqueda por subcadena / difusa
                    for k, v in datos_consolidados_items.items():
                        if k in item_dept_norm or item_dept_norm in k:
                            acc_data = v
                            break

                if acc_data:
                    # 1. Dosis Aplicadas Colombianos y Extranjeros
                    set_cell_safe(ws_m_out, r_dept, 6, acc_data["dosis_col"])
                    set_cell_safe(ws_m_out, r_dept, 7, acc_data["dosis_ext"])

                    # Asegurar fórmulas nativas de MinSalud
                    set_cell_safe(ws_m_out, r_dept, 8, f"=+F{r_dept}+G{r_dept}")
                    set_cell_safe(ws_m_out, r_dept, 9, f"=+AM{r_dept}")
                    set_cell_safe(ws_m_out, r_dept, 10, f"=+H{r_dept}+I{r_dept}")
                    set_cell_safe(ws_m_out, r_dept, 11, f"=+(D{r_dept}+E{r_dept})-(J{r_dept})")

                    # 2. Pérdidas por causas
                    for col_idx, suma_causa in acc_data["perdidas_cols"].items():
                        set_cell_safe(ws_m_out, r_dept, col_idx, suma_causa)

                    set_cell_safe(ws_m_out, r_dept, 28, f"=+Z{r_dept}+AA{r_dept}")
                    set_cell_safe(ws_m_out, r_dept, 39, f"=SUM(AB{r_dept}:AL{r_dept+4})")

                    # 3. Lotes agregados (Top 5 lotes sumados) para biológicos y diluyentes (r_dept < 706)
                    if r_dept < 706:
                        lotes_ordenados = sorted(
                            acc_data["lotes"].items(),
                            key=lambda x: x[1]["dosis"],
                            reverse=True
                        )

                        for slot in range(5):
                            slot_r = r_dept + slot
                            if slot < len(lotes_ordenados):
                                l_cod, l_info = lotes_ordenados[slot]
                                set_cell_safe(ws_m_out, slot_r, 12, l_info["dosis"]) # Dosis lote
                                set_cell_safe(ws_m_out, slot_r, 13, l_cod) # No. Lote
                                if l_info["lab"]:
                                    set_cell_safe(ws_m_out, slot_r, 14, l_info["lab"]) # Lab
                                if l_info["fv"]:
                                    set_cell_safe(ws_m_out, slot_r, 15, l_info["fv"]) # Vencimiento
                            else:
                                # Limpiar slots vacíos
                                set_cell_safe(ws_m_out, slot_r, 12, None)
                                set_cell_safe(ws_m_out, slot_r, 13, None)

                        # Fila de control en r_dept + 5
                        chk_r = r_dept + 5
                        set_cell_safe(ws_m_out, chk_r, 11, f"=K{r_dept}=L{chk_r}")
                        set_cell_safe(ws_m_out, chk_r, 12, f"=SUM(L{r_dept}:L{r_dept+4})")

        wb_out_mov.save(out_mov)
        wb_out_mov.close()
        archivos_generados["movimiento"] = out_mov
    except Exception as e:
        print(f"Error consolidando movimiento departamental: {e}")
        archivos_generados["movimiento"] = out_mov

    # -------------------------------------------------------------
    # 3. CONSOLIDAR EXTRANJEROS (.xlsx)
    # -------------------------------------------------------------
    base_ext, es_custom_ext = obtener_plantilla_base_mes("extranjeros", mes, ano, templates_dir, custom_templates_dir)
    out_ext = os.path.join(output_dir, f"Extranjeros_PAI_{mes}_{ano}_MINSALUD.xlsx")
    shutil.copy2(base_ext, out_ext)
    archivos_generados["bases_utilizadas"]["extranjeros"] = "PERSONALIZADA" if es_custom_ext else "DEFECTO"

    try:
        wb_out_ext = openpyxl.load_workbook(out_ext)
        hojas_paises = ["1_BRASIL", "2_ECUADOR", "3_PANAMA", "4_PERU", "5_OTROS", "6_VENEZOLANOS"]

        for mun_nombre, f_dict in fuentes_municipios.items():
            if "EXTRANJEROS" not in f_dict or not f_dict["EXTRANJEROS"]:
                continue
            ext_path = f_dict["EXTRANJEROS"]
            if not os.path.exists(ext_path):
                continue

            mun_norm = normalizar(mun_nombre)
            target_r_ext = None
            for k, r_idx in MAPA_FILAS_EXTRANJEROS_MPIOS.items():
                if k == mun_norm or mun_norm in k or k in mun_norm:
                    target_r_ext = r_idx
                    break

            if not target_r_ext:
                continue

            try:
                wb_ext_src = openpyxl.load_workbook(ext_path, data_only=True, read_only=True)
                for h_nombre in hojas_paises:
                    if h_nombre in wb_ext_src.sheetnames and h_nombre in wb_out_ext.sheetnames:
                        ws_src = wb_ext_src[h_nombre]
                        ws_dst = wb_out_ext[h_nombre]
                        grid_e = list(ws_src.iter_rows(min_row=1, max_row=150, min_col=1, max_col=480, values_only=True))

                        # Buscar bloque del municipio o usar bloque inicial
                        src_r_start = 9
                        for row_idx, r_vals in enumerate(grid_e[:40]):
                            c3_val = r_vals[2] if len(r_vals) > 2 else None
                            if c3_val and mun_norm in normalizar(c3_val):
                                src_r_start = row_idx + 1
                                break

                        # Copiar 9 filas del municipio (omitiendo filas de totales 3 y 8)
                        for r_offset in range(9):
                            if r_offset in {2, 7}: # Total género y total régimen
                                continue
                            s_row_i = src_r_start + r_offset
                            d_row_i = target_r_ext + r_offset
                            if s_row_i <= len(grid_e):
                                row_vals = grid_e[s_row_i - 1]
                                for c_idx in range(5, min(len(row_vals) + 1, 475)):
                                    v = row_vals[c_idx - 1]
                                    if v is not None and isinstance(v, (int, float)) and v != 0:
                                        ws_dst.cell(row=d_row_i, column=c_idx).value = v

                wb_ext_src.close()
            except Exception as e_mun:
                print(f"Error consolidando extranjeros de {mun_nombre}: {e_mun}")

        wb_out_ext.save(out_ext)
        wb_out_ext.close()
        archivos_generados["extranjeros"] = out_ext
    except Exception as e:
        print(f"Error consolidando extranjeros: {e}")
        archivos_generados["extranjeros"] = out_ext

    return archivos_generados
