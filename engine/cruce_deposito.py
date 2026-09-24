"""
Módulo de Auditoría: Cruce de Entregas del Depósito Departamental vs Movimiento Municipal (Regla 3 PAI)
Secretaría de Salud Departamental de Risaralda

Compara las dosis e insumos oficialmente despachados por el Centro de Acopio Departamental
(Kardex oficial en storage/catalogos/deposito_risaralda.xlsx) contra las dosis recibidas
reportadas por el municipio en la Columna 5 ("Dosis Recibidas del Centro de Acopio")
del archivo Movimiento Mensual de Biológicos e Insumos.
"""

import os
import re
import datetime
import unicodedata
import openpyxl

MESES_NUM = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
    "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
    "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12
}

def normalizar_cadena(t):
    if not t:
        return ""
    s = unicodedata.normalize("NFD", str(t))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9]", "", s.upper())

def normalizar_municipio_clave(mun):
    m = normalizar_cadena(mun)
    if "VIRGINIA" in m: return "LAVIRGINIA"
    if "SANTAROSA" in m: return "SANTAROSA"
    if "BELEN" in m: return "BELENDEUMBRIA"
    if "PUEBLO" in m: return "PUEBLORICO"
    if "CELIA" in m: return "LACELIA"
    return m

# Definición maestro de mapeo canónico
# (Clave, Nombre Visible, Grupo, Opciones Kardex [lista de tokens obligatorios], Opciones Movimiento [lista de tokens obligatorios])
REGLAS_MAPEO = [
    # Biológicos
    ("BIO_BCG", "BCG (Tuberculosis)", "Biológico", [["BCG"]], [["BCG"]]),
    ("BIO_HEP_B_PED", "Hepatitis B Pediátrica", "Biológico", [["HEPATITISB", "PEDIATRICA"]], [["HEPATITISB", "PEDIATRICA"]]),
    ("BIO_HEP_B_ADU", "Hepatitis B Adultos", "Biológico", [["HEPATITISB", "ADULTO"]], [["HEPATITISB", "ADULTO"]]),
    ("BIO_POLIO_VIP", "Polio Inactiva (VIP)", "Biológico", [["POLIO"]], [["POLIO"]]),
    ("BIO_PENTAVALENTE", "Pentavalente PAI", "Biológico", [["PENTAVALENTE"]], [["PENTAVALENTE"]]),
    ("BIO_HEXAVALENTE", "Hexavalente", "Biológico", [["HEXAVALENTE"]], [["HEXAVALENTE"]]),
    ("BIO_DTAP_PED", "DTaP Pediátrica (Acelular)", "Biológico", [["DPTA"], ["DTAP", "PEDIATR"]], [["DTAP", "PEDIATR"]]),
    ("BIO_DPT", "DPT Pediátrica", "Biológico", [["DPT"]], [["DPT"]]),
    ("BIO_ROTAVIRUS", "Rotavirus Oral", "Biológico", [["ROTAVIRUS"]], [["ROTAVIRUS"]]),
    ("BIO_NEUMOCOCO", "Neumococo (PCV13)", "Biológico", [["NEUMOC"]], [["NEUMOC"]]),
    ("BIO_SRP", "Triple Viral (SRP)", "Biológico", [["TRIPLEVIRAL"]], [["TRIPLEVIRAL"], ["PAPERAS"]]),
    ("BIO_SR", "Doble Viral (SR)", "Biológico", [["SARAMPIONRUBEOLA"]], [["DOBLEVIRAL"], ["SARAMPIONRUBEOLA"]]),
    ("BIO_FA", "Fiebre Amarilla", "Biológico", [["ANTIAMARILICA"], ["FIEBREAMARILLA"]], [["FIEBREAMARILLA"], ["ANTIAMARILICA"]]),
    ("BIO_HEP_A", "Hepatitis A Pediátrica", "Biológico", [["HEPATITISA"]], [["HEPATITISA"]]),
    ("BIO_VARICELA", "Varicela", "Biológico", [["VARICELA"]], [["VARICELA"]]),
    ("BIO_TD_ADU", "Td Adulto", "Biológico", [["TDADULTO"]], [["TDADULTO"]]),
    ("BIO_TDAP_GES", "TdaP Gestante", "Biológico", [["TDAP"], ["DTAP", "GESTA"]], [["TDAP"], ["DTAP", "GESTA"]]),
    ("BIO_FLU_PED", "Influenza Pediátrica", "Biológico", [["INFLUENZA", "PEDIATRICA"]], [["INFLUENZA", "PEDIATRICA"]]),
    ("BIO_FLU_ADU", "Influenza Adultos", "Biológico", [["INFLUENZA"]], [["INFLUENZA", "ADULTO"]]),
    ("BIO_VRS", "Virus Sincitial Respiratorio (VRS)", "Biológico", [["SINCITIAL"], ["VRS"]], [["SINCITIAL"], ["VRS"]]),
    ("BIO_VPH", "Virus Papiloma Humano (VPH)", "Biológico", [["VPH"], ["PAPILOMA"]], [["VPH"], ["PAPILOMA"]]),
    ("BIO_ANTIRRABICA", "Antirrábica Humana", "Biológico", [["ANTIRRABICA"]], [["ANTIRRABICA"]]),
    ("BIO_IG_ANTIRRABICA", "Inmunoglobulina Antirrábica", "Biológico", [["INMUNOGLOBULINA", "ANTIRRABICA"]], [["INMUNOGLOBULINA", "ANTIRRABICA"]]),
    ("BIO_IG_HEP_B", "Inmunoglobulina Antihepatitis B", "Biológico", [["INMUNOGLOBULINA", "HEPATITISB"]], [["INMUNOGLOBULINA", "HEPATITISB"]]),
    ("BIO_IG_TETANICA", "Inmunoglobulina Antitetánica", "Biológico", [["INMUNOGLOBULINA", "TETANICA"]], [["INMUNOGLOBULINA", "TETANICA"]]),
    # Diluyentes
    ("DIL_BCG", "Diluyente BCG", "Diluyente", [["BCG"]], [["BCG"]]),
    ("DIL_SRP", "Diluyente Triple Viral (SRP)", "Diluyente", [["TRIPLEVIRAL"]], [["TRIPLEVIRAL"], ["PAPERAS"]]),
    ("DIL_SR", "Diluyente Doble Viral (SR)", "Diluyente", [["SARAMPIONRUBEOLA"]], [["DOBLEVIRAL"], ["SARAMPIONRUBEOLA"]]),
    ("DIL_FA", "Diluyente Fiebre Amarilla", "Diluyente", [["FIEBREAMARILLA"], ["ANTIAMARILICA"]], [["FIEBREAMARILLA"], ["ANTIAMARILICA"]]),
    ("DIL_VARICELA", "Diluyente Varicela", "Diluyente", [["VARICELA"]], [["VARICELA"]]),
    ("DIL_ANTIRRABICA", "Diluyente Antirrábica", "Diluyente", [["ANTIRRABICA"]], [["ANTIRRABICA"]]),
    ("DIL_VRS", "Diluyente VRS", "Diluyente", [["SINCITIAL"], ["VRS"]], [["SINCITIAL"], ["VRS"]]),
    # Insumos y Jeringas
    ("INS_JERINGA_22G", "Jeringa 22G", "Insumo", [["22G"]], [["22G"]]),
    ("INS_JERINGA_23G", "Jeringa 23G", "Insumo", [["23G"]], [["23G"]]),
    ("INS_JERINGA_25G", "Jeringa 25G", "Insumo", [["25G"]], [["25G"]]),
    ("INS_CARNE_FA", "Carné Internacional FA", "Insumo", [["CARNE", "INTERNACIONAL"]], [["CARNE", "INTERNACIONAL"]]),
]

def clasificar_item(texto, origen="kardex"):
    t_norm = normalizar_cadena(texto)
    es_dil = "DILUYENTE" in t_norm
    es_carne = "CARNE" in t_norm or "TARJETA" in t_norm
    es_jeringa = "JERINGA" in t_norm

    for clave, nombre_vis, grupo, opts_k, opts_m in REGLAS_MAPEO:
        if grupo == "Biológico" and (es_dil or es_carne or es_jeringa):
            continue
        if grupo == "Diluyente" and not es_dil:
            continue
        if grupo == "Insumo" and not (es_carne or es_jeringa):
            continue

        opts = opts_k if origen == "kardex" else opts_m

        # Exclusiones específicas
        if "HEP_B" in clave and "PENTAVALENTE" in t_norm: continue
        if clave == "BIO_DPT" and ("ACELULAR" in t_norm or "DTAP" in t_norm or "DPTA" in t_norm): continue
        if clave == "BIO_FLU_ADU" and "PEDIATRICA" in t_norm: continue
        if clave == "BIO_ANTIRRABICA" and "INMUNOGLOBULINA" in t_norm: continue
        if clave == "BIO_SR" and ("PAPERAS" in t_norm or "TRIPLE" in t_norm): continue
        if clave == "DIL_SR" and ("PAPERAS" in t_norm or "TRIPLE" in t_norm): continue

        for req_words in opts:
            if all(w in t_norm for w in req_words):
                return clave, nombre_vis, grupo

    return None, texto, "Otros"

_MEMORIA_KARDEX = {}

def cargar_despachos_kardex_oficial(municipio, mes, ano=2026):
    """
    Carga todos los despachos registrados en el Kardex oficial del Depósito Departamental
    para el municipio y mes/año indicados. Utiliza caché en memoria según mtime del archivo.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fpath = os.path.join(base_dir, "storage", "catalogos", "deposito_risaralda.xlsx")
    despachos = {}

    if not os.path.exists(fpath):
        return despachos

    mes_clean = str(mes).strip().upper()
    mes_target = MESES_NUM.get(mes_clean, None)
    try:
        ano_target = int(ano)
    except:
        ano_target = 2026

    mun_key = normalizar_municipio_clave(municipio)
    mtime = os.path.getmtime(fpath)
    cache_key = f"{mun_key}_{mes_clean}_{ano_target}_{mtime}"
    if cache_key in _MEMORIA_KARDEX:
        return _MEMORIA_KARDEX[cache_key]

    try:
        wb = openpyxl.load_workbook(fpath, data_only=True, read_only=True)
        # Buscar en todas las hojas de Kardex que tengan datos relevantes
        kardex_sheets = [s for s in wb.sheetnames if "KARDEX" in s.upper()]
        kardex_sheets.sort(key=lambda s: ("2025" in s or "2026" in s), reverse=True)

        for sname in kardex_sheets:
            ws = wb[sname]
            for r, row in enumerate(ws.iter_rows(values_only=True)):
                if r == 0 or len(row) < 7:
                    continue
                f_val = row[2]
                tipo_val = str(row[0] or "").strip().upper()
                mun_row = str(row[3] or "").strip().upper()
                vac_row = str(row[5] or "").strip()
                sal_val = row[6]
                lote_row = str(row[8] or "").strip() if len(row) > 8 and row[8] else ""

                if not vac_row or not sal_val:
                    continue

                try:
                    c_sal = float(sal_val)
                    if c_sal <= 0:
                        continue
                except:
                    continue

                # Filtrar municipio
                m_row_key = normalizar_municipio_clave(mun_row)
                if mun_key not in m_row_key and m_row_key not in mun_key:
                    continue

                # Filtrar fecha (mes y año)
                coincide_fecha = False
                if isinstance(f_val, (datetime.datetime, datetime.date)):
                    if f_val.year == ano_target and (mes_target is None or f_val.month == mes_target):
                        coincide_fecha = True
                elif f_val and str(ano_target) in str(f_val):
                    f_str = str(f_val).upper()
                    if mes_clean in f_str:
                        coincide_fecha = True
                    elif mes_target and f"{mes_target:02d}" in f_str:
                        coincide_fecha = True

                if not coincide_fecha:
                    continue

                clave, nombre_vis, grupo = clasificar_item(vac_row, "kardex")
                if not clave:
                    clave = normalizar_cadena(vac_row)
                    nombre_vis = vac_row
                    grupo = "Otros"

                if clave not in despachos:
                    despachos[clave] = {
                        "clave": clave,
                        "nombre": nombre_vis,
                        "grupo": grupo,
                        "total_despachado": 0.0,
                        "lotes": set(),
                        "movimientos": []
                    }

                despachos[clave]["total_despachado"] += c_sal
                if lote_row:
                    despachos[clave]["lotes"].add(lote_row)
                despachos[clave]["movimientos"].append({
                    "fecha": f_val.strftime("%Y-%m-%d") if isinstance(f_val, (datetime.datetime, datetime.date)) else str(f_val),
                    "cantidad": c_sal,
                    "lote": lote_row
                })

        wb.close()
        _MEMORIA_KARDEX[cache_key] = despachos
    except Exception as e:
        print(f"Error cargando despachos Kardex: {e}")

    return despachos

def auditar_cruce_deposito(municipio, mes, ano, items_recibidos_municipio):
    """
    Realiza la auditoría de cruce entre lo despachado por el Depósito Departamental
    y lo reportado como recibido en Columna 5 de Movimiento de Biológicos por el Municipio.

    items_recibidos_municipio: diccionario {clave_o_insumo: float(dosis_recibidas)} o lista de tuples.
    """
    despachos_kardex = cargar_despachos_kardex_oficial(municipio, mes, ano)

    # Clasificar lo reportado por el municipio
    recibidos_dict = {}
    if isinstance(items_recibidos_municipio, dict):
        for raw_name, cant in items_recibidos_municipio.items():
            try:
                c = float(cant or 0)
                if c > 0:
                    clave, nom, grp = clasificar_item(raw_name, "movimiento")
                    if not clave:
                        clave = normalizar_cadena(raw_name)
                        nom = raw_name
                        grp = "Otros"
                    if clave not in recibidos_dict:
                        recibidos_dict[clave] = {"nombre": nom, "grupo": grp, "total_recibido": 0.0}
                    recibidos_dict[clave]["total_recibido"] += c
            except:
                pass

    todas_claves = sorted(set(list(despachos_kardex.keys()) + list(recibidos_dict.keys())))

    items_resultado = []
    total_desp = 0.0
    total_rec = 0.0
    total_coincidencias = 0
    total_diferencias = 0
    bio_exactos = 0
    bio_total = 0
    alertas_regla3 = []

    # Ordenar priorizando la lista oficial REGLAS_MAPEO
    claves_ordenadas = []
    for clave, _, _, _, _ in REGLAS_MAPEO:
        if clave in todas_claves:
            claves_ordenadas.append(clave)
    for c in todas_claves:
        if c not in claves_ordenadas:
            claves_ordenadas.append(c)

    for clave in claves_ordenadas:
        k_info = despachos_kardex.get(clave, None)
        m_info = recibidos_dict.get(clave, None)

        desp = k_info["total_despachado"] if k_info else 0.0
        rec = m_info["total_recibido"] if m_info else 0.0
        nombre = k_info["nombre"] if k_info else (m_info["nombre"] if m_info else clave)
        grupo = k_info["grupo"] if k_info else (m_info["grupo"] if m_info else "Biológico")
        lotes_k = sorted(list(k_info["lotes"])) if k_info else []

        dif = rec - desp
        total_desp += desp
        total_rec += rec

        es_coincidente = abs(dif) < 0.001
        if es_coincidente:
            total_coincidencias += 1
            estado = "COINCIDE_EXACTO"
            estado_texto = "Coincide exacto (100%)"
        else:
            total_diferencias += 1
            estado = "DIFERENCIA_DETECTADA"
            signo = "+" if dif > 0 else ""
            estado_texto = f"Diferencia: {signo}{dif:.0f} dosis"

        if grupo == "Biológico":
            bio_total += 1
            if es_coincidente:
                bio_exactos += 1
            else:
                alertas_regla3.append({
                    "regla": "REGLA_3_CRUCE_DEPOSITO",
                    "insumo": nombre,
                    "grupo": grupo,
                    "despachado_deposito": desp,
                    "recibido_municipio": rec,
                    "diferencia": dif,
                    "lotes_despachados": lotes_k,
                    "mensaje": f"[Regla 3] En '{nombre}': El Centro de Acopio Departamental despachó {desp:.0f} dosis (Lotes: {', '.join(lotes_k) or 'N/A'}), pero el municipio reportó haber recibido {rec:.0f} dosis en Columna 5. Diferencia: {dif:+.0f} dosis."
                })

        items_resultado.append({
            "clave": clave,
            "insumo": nombre,
            "grupo": grupo,
            "despachado_deposito": desp,
            "recibido_municipio": rec,
            "diferencia": dif,
            "lotes_despachados": lotes_k,
            "estado": estado,
            "estado_texto": estado_texto
        })

    porcentaje = round((total_coincidencias / len(todas_claves) * 100), 1) if todas_claves else 100.0

    return {
        "disponible": len(despachos_kardex) > 0,
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "resumen": {
            "total_items": len(todas_claves),
            "total_coincidencias": total_coincidencias,
            "total_diferencias": total_diferencias,
            "total_despachado": total_desp,
            "total_recibido": total_rec,
            "porcentaje_coincidencia": porcentaje,
            "biologicos_exactos": bio_exactos,
            "biologicos_total": bio_total
        },
        "items": items_resultado,
        "alertas": alertas_regla3
    }
