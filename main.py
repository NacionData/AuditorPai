"""
main.py - Servidor Web API FastAPI para el Sistema PAI Risaralda.
"""
import os
import shutil
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from engine.detector import detectar_tipo_archivo
from engine.validator_dosis import validar_dosis
from engine.validator_movimiento import validar_movimiento
from engine.validator_extranjeros import validar_extranjeros
from engine.ai_auditor import generar_dictamen_auditoria, test_gemini_connection
from engine.consolidator import consolidar_departamento
from engine.auth import autenticar_usuario, verificar_token, cerrar_sesion
from engine.drive_sync import sincronizar_radicado_drive, sincronizar_consolidados_drive, obtener_estado_drive

app = FastAPI(title="Sistema PAI Risaralda", description="Plataforma de Auditoría y Consolidación de Vacunación")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
TEMP_DIR = os.path.join(BASE_DIR, "storage", "temp")
RADICADOS_DIR = os.path.join(BASE_DIR, "storage", "radicados")
CONSOLIDADOS_DIR = os.path.join(BASE_DIR, "storage", "consolidados")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates_base")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(RADICADOS_DIR, exist_ok=True)
os.makedirs(CONSOLIDADOS_DIR, exist_ok=True)

# Cargar catálogo de municipios
CAT_MUNICIPIOS_FILE = os.path.join(STORAGE_DIR, "catalogos", "municipios.json")
def obtener_municipios():
    if os.path.exists(CAT_MUNICIPIOS_FILE):
        with open(CAT_MUNICIPIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.get("/api/municipios")
def api_municipios():
    return obtener_municipios()

@app.post("/api/auth/login")
def api_login(usuario: str = Form(...), password: str = Form(...)):
    sesion = autenticar_usuario(usuario, password)
    if not sesion:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    return {
        "success": True,
        "token": sesion["token"],
        "usuario": sesion["usuario"],
        "nombre": sesion["nombre"],
        "rol": sesion["rol"],
        "municipio": sesion["municipio"],
        "dane": sesion["dane"]
    }

@app.get("/api/auth/me")
def api_me(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token no suministrado.")
    sesion = verificar_token(token)
    if not sesion:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    return sesion

@app.post("/api/auth/logout")
def api_logout(token: str = Form(None)):
    if token:
        cerrar_sesion(token)
    return {"success": True}

@app.get("/api/drive/estado")
def api_drive_estado():
    return obtener_estado_drive()

@app.get("/api/ia/estado")
def api_ia_estado():
    return test_gemini_connection()

@app.get("/api/estado/{mes}")
def api_estado(mes: str, ano: str = "2026"):
    mes = mes.upper()
    municipios = obtener_municipios()
    radicados_mes_dir = os.path.join(RADICADOS_DIR, ano, mes)

    estados = []
    for m in municipios:
        m_nombre = m["nombre"]
        m_dir = os.path.join(radicados_mes_dir, m_nombre)
        receipt_file = os.path.join(m_dir, "radicado.json")

        if os.path.exists(receipt_file):
            with open(receipt_file, "r", encoding="utf-8") as f:
                rec = json.load(f)
            estados.append({
                "municipio": m_nombre,
                "dane": m["dane"],
                "estado": "RADICADO",
                "fecha_radicacion": rec.get("fecha"),
                "numero_radicado": rec.get("numero_radicado"),
                "dosis_aplicadas": rec.get("metricas", {}).get("dosis_aplicadas_nacionales", 0),
                "extranjeros": rec.get("metricas", {}).get("vacunados_extranjeros", 0)
            })
        else:
            estados.append({
                "municipio": m_nombre,
                "dane": m["dane"],
                "estado": "PENDIENTE",
                "fecha_radicacion": None,
                "numero_radicado": None,
                "dosis_aplicadas": 0,
                "extranjeros": 0
            })

    total_radicados = sum(1 for e in estados if e["estado"] == "RADICADO")
    return {
        "mes": mes,
        "ano": ano,
        "total_municipios": len(municipios),
        "radicados": total_radicados,
        "pendientes": len(municipios) - total_radicados,
        "porcentaje_avance": round((total_radicados / len(municipios)) * 100, 1) if municipios else 0,
        "detalle": estados
    }

@app.post("/api/auditar")
async def api_auditar(
    municipio: str = Form(...),
    mes: str = Form(...),
    ano: str = Form("2026"),
    archivos: list[UploadFile] = File(...)
):
    municipio = municipio.upper()
    mes = mes.upper()
    session_id = str(uuid.uuid4())[:8]
    upload_tmp = os.path.join(TEMP_DIR, f"{municipio}_{mes}_{session_id}")
    os.makedirs(upload_tmp, exist_ok=True)

    archivos_clasificados = {
        "DOSIS": None,
        "MOVIMIENTO": None,
        "EXTRANJEROS": None,
        "ANEXOS": []
    }

    # 1. Guardar y detectar tipo de cada archivo subido
    for f in archivos:
        dest_path = os.path.join(upload_tmp, f.filename)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        det = detectar_tipo_archivo(dest_path)
        tipo = det["tipo"]
        if tipo == "DOSIS_APLICADAS" and not archivos_clasificados["DOSIS"]:
            archivos_clasificados["DOSIS"] = dest_path
        elif tipo == "MOVIMIENTO_BIOLOGICOS" and not archivos_clasificados["MOVIMIENTO"]:
            archivos_clasificados["MOVIMIENTO"] = dest_path
        elif tipo == "VACUNADOS_EXTRANJEROS" and not archivos_clasificados["EXTRANJEROS"]:
            archivos_clasificados["EXTRANJEROS"] = dest_path
        else:
            archivos_clasificados["ANEXOS"].append(dest_path)

    # 2. Ejecutar validaciones correspondientes
    res_dosis = None
    res_mov = None
    res_ext = None

    if archivos_clasificados["DOSIS"]:
        res_dosis = validar_dosis(archivos_clasificados["DOSIS"], mes_evaluar=mes, municipio_nombre=municipio)
    if archivos_clasificados["MOVIMIENTO"]:
        res_mov = validar_movimiento(archivos_clasificados["MOVIMIENTO"], mes_evaluar=mes, municipio_nombre=municipio)
    if archivos_clasificados["EXTRANJEROS"]:
        res_ext = validar_extranjeros(archivos_clasificados["EXTRANJEROS"], mes_evaluar=mes, municipio_nombre=municipio)

    # 3. Generar Dictamen y Retroalimentación con IA
    dictamen = generar_dictamen_auditoria(municipio, mes, res_dosis, res_mov, res_ext)

    # Almacenar referencia temporal para permitir radicación inmediata si pasa
    meta_session = {
        "session_id": session_id,
        "upload_tmp": upload_tmp,
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "archivos": archivos_clasificados,
        "dictamen": dictamen
    }
    with open(os.path.join(upload_tmp, "session_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_session, f, indent=2, ensure_ascii=False)

    return {
        "session_id": session_id,
        "municipio": municipio,
        "mes": mes,
        "archivos_detectados": {
            "dosis": bool(archivos_clasificados["DOSIS"]),
            "movimiento": bool(archivos_clasificados["MOVIMIENTO"]),
            "extranjeros": bool(archivos_clasificados["EXTRANJEROS"]),
            "anexos_count": len(archivos_clasificados["ANEXOS"])
        },
        "resumen_auditoria": dictamen,
        "detalle_dosis": res_dosis,
        "detalle_movimiento": res_mov,
        "detalle_extranjeros": res_ext,
        "puede_radicar": dictamen["aprobado"]
    }

@app.post("/api/radicar")
async def api_radicar(session_id: str = Form(...)):
    # Buscar sesión temporal
    matched_dir = None
    for folder in os.listdir(TEMP_DIR):
        if folder.endswith(session_id):
            matched_dir = os.path.join(TEMP_DIR, folder)
            break

    if not matched_dir or not os.path.exists(os.path.join(matched_dir, "session_meta.json")):
        raise HTTPException(status_code=400, detail="Sesión de radicación expirada o inválida.")

    with open(os.path.join(matched_dir, "session_meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)

    if not meta["dictamen"]["aprobado"]:
        raise HTTPException(status_code=400, detail="El informe contiene errores críticos y no puede radicarse.")

    municipio = meta["municipio"]
    mes = meta["mes"]
    ano = meta["ano"]
    num_radicado = f"RAD-RIS-{ano}-{mes[:3]}-{str(uuid.uuid4())[:6].upper()}"
    fecha_rad = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    os.makedirs(target_dir, exist_ok=True)

    # Copiar archivos a radicados definitivos
    archivos_radicados = {}
    for clave, p in meta["archivos"].items():
        if p and clave != "ANEXOS" and os.path.exists(p):
            fname = os.path.basename(p)
            dest = os.path.join(target_dir, f"{clave}_{fname}")
            shutil.copy2(p, dest)
            archivos_radicados[clave] = dest

    # Guardar recibo
    recibo = {
        "numero_radicado": num_radicado,
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "fecha": fecha_rad,
        "archivos": archivos_radicados,
        "metricas": meta["dictamen"]["metricas"]
    }

    # Sincronización automática a Google Drive (risaraldapaiweb@gmail.com)
    info_drive = sincronizar_radicado_drive(municipio, mes, ano, archivos_radicados, recibo)
    recibo["google_drive"] = {
        "correo": info_drive["correo"],
        "carpeta": info_drive["carpeta_nube"],
        "total_archivos": info_drive["total_archivos"],
        "fecha": info_drive["fecha_sincronizacion"]
    }

    with open(os.path.join(target_dir, "radicado.json"), "w", encoding="utf-8") as f:
        json.dump(recibo, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "mensaje": f"¡Informe radicado y sincronizado con el Drive de Risaralda exitosamente!",
        "recibo": recibo,
        "drive": info_drive
    }

@app.post("/api/consolidar/{mes}")
def api_consolidar(mes: str, ano: str = "2026"):
    mes = mes.upper()
    municipios = obtener_municipios()
    radicados_mes_dir = os.path.join(RADICADOS_DIR, ano, mes)

    fuentes = {}
    # 1. Buscar en radicados oficiales
    if os.path.exists(radicados_mes_dir):
        for m in municipios:
            m_nom = m["nombre"]
            m_dir = os.path.join(radicados_mes_dir, m_nom)
            if os.path.exists(m_dir):
                f_dosis, f_mov, f_ext = None, None, None
                for file_name in os.listdir(m_dir):
                    fpath = os.path.join(m_dir, file_name)
                    if file_name.startswith("DOSIS_"):
                        f_dosis = fpath
                    elif file_name.startswith("MOVIMIENTO_"):
                        f_mov = fpath
                    elif file_name.startswith("EXTRANJEROS_"):
                        f_ext = fpath
                if f_dosis or f_mov or f_ext:
                    fuentes[m_nom] = {"DOSIS": f_dosis, "MOVIMIENTO": f_mov, "EXTRANJEROS": f_ext}

    # 2. Si es agosto y no hay suficientes radicados por web aún, usar las fuentes de NACIONALES como respaldo
    if len(fuentes) < 5 and mes == "AGOSTO":
        nac_dir = os.path.join(os.path.dirname(BASE_DIR), "AGOSTO_2026_MUNICIPALES", "AGOSTO_2026", "NACIONALES")
        if os.path.exists(nac_dir):
            for f in os.listdir(nac_dir):
                if f.endswith(".xlsx"):
                    m_nom = os.path.splitext(f)[0]
                    if m_nom not in fuentes:
                        fuentes[m_nom] = {"DOSIS": os.path.join(nac_dir, f)}

    if not fuentes:
        raise HTTPException(status_code=400, detail=f"No hay informes radicados para consolidar en {mes} {ano}.")

    resultado = consolidar_departamento(mes=mes, ano=ano, fuentes_municipios=fuentes)

    # Sincronizar los 3 consolidados a Google Drive
    archivos_gen = {
        "dosis": os.path.join(CONSOLIDADOS_DIR, ano, mes, f"RISARALDA_Plantilla_Dosis_Aplicadas_{mes}_{ano}_MINSALUD.xlsx"),
        "movimiento": os.path.join(CONSOLIDADOS_DIR, ano, mes, f"Movimiento_PAI_{mes}_{ano}_MINSALUD.xlsm"),
        "extranjeros": os.path.join(CONSOLIDADOS_DIR, ano, mes, f"Extranjeros_PAI_{mes}_{ano}_MINSALUD.xlsx")
    }
    info_drive_consolidados = sincronizar_consolidados_drive(mes, ano, archivos_gen)

    return {
        "success": True,
        "mes": mes,
        "ano": ano,
        "municipios_consolidados": resultado["municipios_incluidos"],
        "total_consolidados": len(resultado["municipios_incluidos"]),
        "descargas": {
            "dosis": f"/api/descargar/dosis/{mes}",
            "movimiento": f"/api/descargar/movimiento/{mes}",
            "extranjeros": f"/api/descargar/extranjeros/{mes}"
        },
        "drive_sync": info_drive_consolidados
    }

@app.get("/api/descargar/{tipo}/{mes}")
def api_descargar(tipo: str, mes: str, ano: str = "2026"):
    mes = mes.upper()
    out_dir = os.path.join(CONSOLIDADOS_DIR, ano, mes)
    if not os.path.exists(out_dir):
        raise HTTPException(status_code=404, detail="No se encontró consolidado para este mes.")

    f_map = {
        "dosis": f"RISARALDA_Plantilla_Dosis_Aplicadas_{mes}_{ano}_MINSALUD.xlsx",
        "movimiento": f"Movimiento_PAI_{mes}_{ano}_MINSALUD.xlsm",
        "extranjeros": f"Extranjeros_PAI_{mes}_{ano}_MINSALUD.xlsx"
    }

    target_name = f_map.get(tipo.lower())
    if not target_name:
        raise HTTPException(status_code=400, detail="Tipo de archivo inválido.")

    fpath = os.path.join(out_dir, target_name)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"El archivo {target_name} aún no ha sido generado.")

    return FileResponse(fpath, filename=target_name)

# Endpoint público para que los municipios descarguen las plantillas oficiales 2026 en blanco
@app.get("/api/plantillas-base/{tipo}")
def api_descargar_plantilla_base(tipo: str):
    f_map = {
        "dosis": ("Plantilla_Dosis_Base.xlsx", "Plantilla_Dosis_Aplicadas_2026_OFICIAL_EN_BLANCO.xlsx"),
        "movimiento": ("Plantilla_Movimiento_Base.xlsm", "Movimiento_PAI_2026_OFICIAL_EN_BLANCO.xlsm"),
        "extranjeros": ("Plantilla_Extranjeros_Base.xlsx", "Extranjeros_PAI_2026_OFICIAL_EN_BLANCO.xlsx")
    }
    
    entry = f_map.get(tipo.lower())
    if not entry:
        raise HTTPException(status_code=400, detail="Tipo de plantilla inválido. Opciones: dosis, movimiento, extranjeros.")
        
    source_name, download_name = entry
    fpath = os.path.join(TEMPLATES_DIR, source_name)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Plantilla base no encontrada en el servidor.")
        
    return FileResponse(fpath, filename=download_name)

# Endpoints de Inspección y Descarga para el Administrador Departamental
@app.get("/api/admin/inspeccionar/{municipio}/{mes}")
def api_admin_inspeccionar(municipio: str, mes: str, ano: str = "2026"):
    municipio = municipio.upper()
    mes = mes.upper()
    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    receipt_file = os.path.join(target_dir, "radicado.json")

    if not os.path.exists(receipt_file):
        raise HTTPException(status_code=404, detail=f"El municipio {municipio} no registra radicado en {mes} {ano}.")

    with open(receipt_file, "r", encoding="utf-8") as f:
        recibo = json.load(f)

    # Identificar enlaces de descarga individuales de los archivos subidos por el municipio
    archivos_descargables = {}
    for clave, fpath in recibo.get("archivos", {}).items():
        if fpath and os.path.exists(fpath):
            archivos_descargables[clave] = f"/api/admin/descargar-archivo/{ano}/{mes}/{municipio}/{clave}"

    return {
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "recibo": recibo,
        "descargas_archivos": archivos_descargables
    }

@app.get("/api/admin/descargar-archivo/{ano}/{mes}/{municipio}/{clave}")
def api_admin_descargar_archivo(ano: str, mes: str, municipio: str, clave: str):
    municipio = municipio.upper()
    mes = mes.upper()
    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    receipt_file = os.path.join(target_dir, "radicado.json")

    if not os.path.exists(receipt_file):
        raise HTTPException(status_code=404, detail="Radicado no encontrado.")

    with open(receipt_file, "r", encoding="utf-8") as f:
        recibo = json.load(f)

    fpath = recibo.get("archivos", {}).get(clave)
    if not fpath or not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Archivo {clave} no encontrado.")

    return FileResponse(fpath, filename=os.path.basename(fpath))

# Rutas separadas para las interfaces Web
@app.get("/departamental")
@app.get("/admin")
def ruta_departamental():
    return FileResponse(os.path.join(STATIC_DIR, "departamental.html"))

# Montar archivos estáticos para la interfaz web (index.html servido en raíz)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
