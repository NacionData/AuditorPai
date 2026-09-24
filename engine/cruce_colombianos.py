"""
cruce_colombianos.py - Auditoría Cruzada de Dosis Aplicadas a Colombianos.
Compara las dosis aplicadas reportadas en la Plantilla de Dosis (Colombianos)
contra las dosis aplicadas a colombianos reportadas en Movimiento de Biológicos (Col 6).

Genera un informe detallado con las diferencias biológico por biológico.
Por directriz institucional, es de carácter INFORMATIVO (con alerta visual para el municipio
y el departamento, sin bloquear la radicación).
"""
import re

def normalizar_cadena(t):
    if not t:
        return ""
    s = str(t).upper().strip()
    for a, b in [("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ñ", "N")]:
        s = s.replace(a, b)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def auditar_cruce_colombianos(res_dosis, res_mov):
    """
    Compara las dosis aplicadas en la Plantilla de Dosis vs Columna 6 de Movimiento.
    Retorna la tabla comparativa, totales y observaciones pedagógicas.
    """
    if not res_dosis or not res_mov:
        return None

    dosis_map = res_dosis.get("dosis_agrupadas_vacuna", {})
    mov_map = res_mov.get("dosis_colombianos_por_vacuna", {})

    # Definición de categorías estándar de biológicos para el cruce con discriminación exacta
    definiciones = [
        {
            "id": "BCG",
            "nombre": "BCG",
            "matcher_dosis": lambda k: "BCG" in k,
            "matcher_mov": lambda k: "BCG" in k
        },
        {
            "id": "HEPATITIS_B_PED",
            "nombre": "Hepatitis B Pediátrica / Recién Nacido",
            "matcher_dosis": lambda k: "HEPATITIS B" in k and "0459" not in k and "ADULTO" not in k and "PENTA" not in k,
            "matcher_mov": lambda k: "HEPATITIS B" in k and "PEDIATRICA" in k and "PENTA" not in k and "DIFTERIA" not in k and "DTWP" not in k
        },
        {
            "id": "HEPATITIS_B_ADULTO",
            "nombre": "Hepatitis B Adultos",
            "matcher_dosis": lambda k: "0459" in k or ("HEPATITIS B" in k and "ADULTO" in k),
            "matcher_mov": lambda k: "HEPATITIS B" in k and "ADULTO" in k
        },
        {
            "id": "ANTIPOLIO_VIP",
            "nombre": "Antipolio Inactivada (VIP)",
            "matcher_dosis": lambda k: "ANTIPOLIO" in k or "VIP" in k,
            "matcher_mov": lambda k: "POLIOVIRUS" in k or "IPV" in k
        },
        {
            "id": "PENTAVALENTE",
            "nombre": "Pentavalente (DPT-HB-Hib)",
            "matcher_dosis": lambda k: "PENTAVALENTE" in k,
            "matcher_mov": lambda k: "PENTAVALENTE" in k or ("DIFTERIA - TOS FERINA" in k and "CELULA COMPLETA" in k)
        },
        {
            "id": "HEXAVALENTE",
            "nombre": "Hexavalente",
            "matcher_dosis": lambda k: "HEXAVALENTE" in k,
            "matcher_mov": lambda k: "HEXAVALENTE" in k
        },
        {
            "id": "ROTAVIRUS",
            "nombre": "Rotavirus",
            "matcher_dosis": lambda k: "ROTAVIRUS" in k,
            "matcher_mov": lambda k: "ROTAVIRUS" in k
        },
        {
            "id": "NEUMOCOCO",
            "nombre": "Neumococo Conjugada",
            "matcher_dosis": lambda k: "NEUMOCOCO" in k,
            "matcher_mov": lambda k: "NEUMOCOCO" in k or "ANTINEUMOCOCICA" in k
        },
        {
            "id": "SRP",
            "nombre": "Triple Viral (SRP)",
            "matcher_dosis": lambda k: "SRP" in k or "TRIPLE VIRAL" in k,
            "matcher_mov": lambda k: ("SRP" in k or "TRIPLE VIRAL" in k or "PAPERAS" in k) and "DILUYENTE" not in k
        },
        {
            "id": "SR",
            "nombre": "Doble Viral (SR)",
            "matcher_dosis": lambda k: "SR" in k and "SRP" not in k and "VSR" not in k and "VIRUS SINCITIAL" not in k,
            "matcher_mov": lambda k: "SARAMPION RUBEOLA (SR)" in k or ("DOBLE VIRAL" in k and "PAPERAS" not in k)
        },
        {
            "id": "FIEBRE_AMARILLA",
            "nombre": "Fiebre Amarilla",
            "matcher_dosis": lambda k: "FIEBRE AMARILLA" in k,
            "matcher_mov": lambda k: "FIEBRE AMARILLA" in k or "ANTIAMARILICA" in k
        },
        {
            "id": "HEPATITIS_A",
            "nombre": "Hepatitis A Pediátrica",
            "matcher_dosis": lambda k: "HEPATITIS A" in k,
            "matcher_mov": lambda k: "HEPATITIS A" in k
        },
        {
            "id": "VARICELA",
            "nombre": "Varicela",
            "matcher_dosis": lambda k: "VARICELA" in k,
            "matcher_mov": lambda k: "VARICELA" in k
        },
        {
            "id": "DPT",
            "nombre": "DPT (Refuerzo 18m y 5a)",
            "matcher_dosis": lambda k: k.strip() == "DPT" or ("DPT" in k and "PENTA" not in k and "HB" not in k and "HIB" not in k),
            "matcher_mov": lambda k: "DIFTERIA, TETANO Y TOSFERINA (DPT)" in k
        },
        {
            "id": "TDAP_PEDIATRICA",
            "nombre": "TDaP Pediátrica Acelular",
            "matcher_dosis": lambda k: "TDAP" in k and "PEDIATRICA" in k,
            "matcher_mov": lambda k: "DTAP" in k and ("PEDIATRICA" in k or "INFANTIL" in k)
        },
        {
            "id": "TD_ADULTO",
            "nombre": "Toxoide Tetánico-Diftérico (Td) Adulto",
            "matcher_dosis": lambda k: "TOXOIDE TETANICO" in k or (k.strip() == "TD"),
            "matcher_mov": lambda k: "TETANOS Y DIFTERIA (TD) ADULTO" in k
        },
        {
            "id": "TDAP_GESTANTE",
            "nombre": "Tdap Gestantes / Acelular",
            "matcher_dosis": lambda k: "TDAP ACELULAR" in k and "PEDIATRICA" not in k,
            "matcher_mov": lambda k: "DTAP" in k and ("GESTA" in k or "ADOLESCENTE" in k or "ADULTO" in k) and "INFANTIL" not in k
        },
        {
            "id": "INFLUENZA",
            "nombre": "Influenza Estacional (Pediátrica + Adultos)",
            "matcher_dosis": lambda k: "INFLUENZA" in k and "HAEMOPHILUS" not in k and "HIB" not in k,
            "matcher_mov": lambda k: "INFLUENZA" in k and "HAEMOPHILUS" not in k and "HIB" not in k and "PENTA" not in k
        },
        {
            "id": "VSR",
            "nombre": "Virus Sincitial Respiratorio (VSR)",
            "matcher_dosis": lambda k: "VIRUS SINCITIAL" in k or "VSR" in k,
            "matcher_mov": lambda k: "VIRUS SINCITIAL" in k or "VRS" in k
        },
        {
            "id": "VPH",
            "nombre": "Virus del Papiloma Humano (VPH)",
            "matcher_dosis": lambda k: "VPH" in k.replace(" ", "") or "PAPILOMA" in k,
            "matcher_mov": lambda k: "PAPILOMA" in k or "VPH" in k
        },
        {
            "id": "ANTIRRABICA",
            "nombre": "Antirrábica Humana",
            "matcher_dosis": lambda k: "ANTIRRABICA" in k,
            "matcher_mov": lambda k: "ANTIRRABICA" in k and "INMUNOGLOBULINA" not in k
        },
        {
            "id": "COVID19",
            "nombre": "COVID-19",
            "matcher_dosis": lambda k: "COVID" in k or "469" in k,
            "matcher_mov": lambda k: "COVID" in k
        },
        {
            "id": "DENGUE",
            "nombre": "Dengue",
            "matcher_dosis": lambda k: "DENGUE" in k,
            "matcher_mov": lambda k: "DENGUE" in k
        },
        {
            "id": "MENINGOCOCO",
            "nombre": "Meningococo",
            "matcher_dosis": lambda k: "MENINGOCOCO" in k,
            "matcher_mov": lambda k: "MENINGOCOCO" in k
        }
    ]

    tabla_comparativa = []
    tot_plantilla = 0
    tot_movimiento = 0
    coincidencias = 0
    discrepancias = 0
    alertas_cruce = []

    for def_item in definiciones:
        nombre_bio = def_item["nombre"]
        fn_d = def_item["matcher_dosis"]
        fn_m = def_item["matcher_mov"]

        # Calcular dosis en Plantilla de Dosis
        val_dosis = 0
        for k_d, v_d in dosis_map.items():
            k_norm = normalizar_cadena(k_d)
            if fn_d(k_norm):
                val_dosis += v_d

        # Calcular dosis en Movimiento (Col 6: Colombianos)
        val_mov = 0
        for k_m, v_m in mov_map.items():
            k_norm = normalizar_cadena(k_m)
            if fn_m(k_norm):
                val_mov += v_m

        if val_dosis > 0 or val_mov > 0:
            tot_plantilla += val_dosis
            tot_movimiento += val_mov
            dif = val_dosis - val_mov

            if dif == 0:
                coincidencias += 1
                estado = "COINCIDENCIA_EXACTA"
                observacion = "Coincidencia 100% exacta."
            else:
                discrepancias += 1
                estado = "DIFERENCIA_OBSERVADA"
                if dif > 0:
                    observacion = f"Plantilla reporta +{dif} dosis más que Movimiento Colombianos."
                else:
                    observacion = f"Movimiento Colombianos reporta +{abs(dif)} dosis más que Plantilla."

                alerta_msg = f"[Cruce Dosis vs Movimiento] En '{nombre_bio}': Plantilla de Dosis reporta {val_dosis} dosis vs Movimiento (Colombianos) que reporta {val_mov} dosis (Diferencia: {dif:+d} dosis)."
                alertas_cruce.append({
                    "biologico": nombre_bio,
                    "dosis_plantilla": val_dosis,
                    "dosis_movimiento": val_mov,
                    "diferencia": dif,
                    "mensaje": alerta_msg
                })

            tabla_comparativa.append({
                "biologico": nombre_bio,
                "dosis_plantilla": val_dosis,
                "dosis_movimiento": val_mov,
                "diferencia": dif,
                "estado": estado,
                "observacion": observacion
            })

    total_evaluados = coincidencias + discrepancias
    pct_coincidencia = round((coincidencias / total_evaluados * 100), 1) if total_evaluados > 0 else 100.0

    return {
        "tipo": "CRUCE_DOSIS_VS_MOVIMIENTO_COLOMBIANOS",
        "total_dosis_plantilla": tot_plantilla,
        "total_dosis_movimiento_colombianos": tot_movimiento,
        "diferencia_total": tot_plantilla - tot_movimiento,
        "coincidencias_exactas": coincidencias,
        "discrepancias_observadas": discrepancias,
        "porcentaje_coincidencia": pct_coincidencia,
        "bloquea_radicacion": False,
        "tabla_comparativa": tabla_comparativa,
        "alertas": alertas_cruce
    }
