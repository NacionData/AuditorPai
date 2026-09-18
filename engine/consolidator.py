"""
consolidator.py - Motor de Consolidación Departamental PAI Risaralda.
Toma los informes radicados y aprobados de los 14 municipios y genera
las 3 plantillas consolidadas oficiales para el Ministerio de Salud.
"""
import openpyxl
import os
import shutil
import re

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

def normalizar(texto):
    if not texto:
        return ""
    t = str(texto).upper().strip()
    for a, b in [("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ñ", "N")]:
        t = t.replace(a, b)
    return t

def consolidar_departamento(mes="AGOSTO", ano="2026", fuentes_municipios=None):
    """
    Consolida los archivos de los municipios en las plantillas oficiales MinSalud.
    fuentes_municipios: dict { "NOMBRE_MUNICIPIO": { "DOSIS": path, "MOVIMIENTO": path, "EXTRANJEROS": path } }
    Retorna un diccionario con las rutas de los 3 archivos consolidados generados.
    """
    mes = normalizar(mes)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates_base")
    output_dir = os.path.join(base_dir, "storage", "consolidados", str(ano), mes)
    os.makedirs(output_dir, exist_ok=True)

    archivos_generados = {
        "dosis": None,
        "movimiento": None,
        "extranjeros": None,
        "municipios_incluidos": []
    }

    if not fuentes_municipios:
        return archivos_generados

    # -------------------------------------------------------------
    # 1. CONSOLIDAR DOSIS APLICADAS
    # -------------------------------------------------------------
    base_dosis = os.path.join(templates_dir, "Plantilla_Dosis_Base.xlsx")
    out_dosis = os.path.join(output_dir, f"RISARALDA_Plantilla_Dosis_Aplicadas_{mes}_{ano}_MINSALUD.xlsx")
    shutil.copy2(base_dosis, out_dosis)

    wb_out_dosis = openpyxl.load_workbook(out_dosis)
    ws_dosis = wb_out_dosis["1_PLANTILLA_MENSUAL"]
    ws_regimen = wb_out_dosis["3_CONSOLIDADO REGIMEN"] if "3_CONSOLIDADO REGIMEN" in wb_out_dosis.sheetnames else None

    # Actualizar mes en cabecera
    ws_dosis["D5"] = mes
    ws_dosis["D4"] = int(ano) if ano.isdigit() else ano

    mes_idx = MESES_ORDEN.index(mes) if mes in MESES_ORDEN else 7
    src_row_start_teorica = 9 + (mes_idx * 19)

    max_c = 150

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
                
                # Extraer en bloque
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

                # Copiar las 19 filas del bloque
                for r_offset in range(19):
                    src_r = src_start + r_offset
                    dst_r = target_row_start + r_offset
                    if src_r <= len(grid_src):
                        row_vals = grid_src[src_r - 1]
                        for c_i in range(5, max_c + 1):
                            v = row_vals[c_i - 1] if c_i <= len(row_vals) else None
                            if v is not None and isinstance(v, (int, float)) and v != 0:
                                ws_dosis.cell(dst_r, c_i).value = v

                # Copiar a 3_CONSOLIDADO REGIMEN si existe
                if ws_regimen:
                    reg_row = None
                    for k, r_idx in MAPA_FILAS_CONSOLIDADO_REGIMEN.items():
                        if k == mun_norm or mun_norm in k or k in mun_norm:
                            reg_row = r_idx
                            break
                    if reg_row:
                        tot_gen_r = src_start + 3
                        if tot_gen_r <= len(grid_src):
                            gen_vals = grid_src[tot_gen_r - 1]
                            for c_i in range(4, min(max_c + 1, ws_regimen.max_column + 1)):
                                v = gen_vals[c_i] if c_i < len(gen_vals) else None
                                if v is not None and isinstance(v, (int, float)):
                                    ws_regimen.cell(reg_row, c_i).value = v

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
    base_mov = os.path.join(templates_dir, "Plantilla_Movimiento_Base.xlsm")
    out_mov = os.path.join(output_dir, f"Movimiento_PAI_{mes}_{ano}_MINSALUD.xlsm")
    shutil.copy2(base_mov, out_mov)

    # Actualizar hoja del mes en el libro departamental
    try:
        wb_out_mov = openpyxl.load_workbook(out_mov, keep_vba=True)
        # Actualizar celda de mes
        target_sname = None
        for s in wb_out_mov.sheetnames:
            if s.upper() == mes:
                target_sname = s
                break

        if target_sname:
            ws_m_out = wb_out_mov[target_sname]
            ws_m_out["E6"] = mes
            ws_m_out["I6"] = int(ano) if ano.isdigit() else ano

        wb_out_mov.save(out_mov)
        wb_out_mov.close()
        archivos_generados["movimiento"] = out_mov
    except Exception as e:
        print(f"Error guardando movimiento: {e}")
        archivos_generados["movimiento"] = out_mov

    # -------------------------------------------------------------
    # 3. CONSOLIDAR EXTRANJEROS
    # -------------------------------------------------------------
    base_ext = os.path.join(templates_dir, "Plantilla_Extranjeros_Base.xlsx")
    out_ext = os.path.join(output_dir, f"Extranjeros_PAI_{mes}_{ano}_MINSALUD.xlsx")
    shutil.copy2(base_ext, out_ext)
    archivos_generados["extranjeros"] = out_ext

    return archivos_generados
