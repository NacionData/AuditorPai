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
from engine.validator_movimiento import validar_movimiento, cargar_lotes_google_sheet
from engine.validator_extranjeros import validar_extranjeros
from engine.cruce_colombianos import auditar_cruce_colombianos
from engine.cruce_deposito import auditar_cruce_deposito, obtener_info_kardex_actual, limpiar_cache_kardex
from engine.ai_auditor import generar_dictamen_auditoria, test_gemini_connection
from engine.consolidator import consolidar_departamento
from engine.dictamen_reglas import generar_dictamen_reglas_detallado
from engine.auth import autenticar_usuario, verificar_token, cerrar_sesion
from engine.drive_sync import sincronizar_radicado_drive, sincronizar_consolidados_drive, obtener_estado_drive
from engine.kardex_sync import (
    obtener_config_kardex_drive,
    guardar_config_kardex_drive,
    descargar_kardex_google,
    iniciar_demonio_kardex_sync
)

app = FastAPI(title="Sistema PAI Risaralda", description="Plataforma de Auditoría y Consolidación de Vacunación")

@app.on_event("startup")
async def startup_event():
    iniciar_demonio_kardex_sync()

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
TEMPLATES_MES_DIR = os.path.join(BASE_DIR, "storage", "templates_mes")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(RADICADOS_DIR, exist_ok=True)
os.makedirs(CONSOLIDADOS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_MES_DIR, exist_ok=True)

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
        dev_file = os.path.join(m_dir, "estado_devolucion.json")

        if os.path.exists(receipt_file):
            with open(receipt_file, "r", encoding="utf-8") as f:
                rec = json.load(f)
            estado_rad = rec.get("estado", "RADICADO")
            estados.append({
                "municipio": m_nombre,
                "dane": m["dane"],
                "estado": estado_rad,
                "tiene_justificacion": rec.get("tiene_justificacion", False),
                "justificacion": rec.get("justificacion"),
                "aprobado_departamental": rec.get("aprobado_departamental"),
                "fecha_radicacion": rec.get("fecha"),
                "numero_radicado": rec.get("numero_radicado"),
                "dosis_aplicadas": rec.get("metricas", {}).get("dosis_aplicadas_nacionales", 0),
                "extranjeros": rec.get("metricas", {}).get("vacunados_extranjeros", 0)
            })
        elif os.path.exists(dev_file):
            with open(dev_file, "r", encoding="utf-8") as f:
                dev_info = json.load(f)
            estados.append({
                "municipio": m_nombre,
                "dane": m["dane"],
                "estado": "DEVUELTO",
                "motivo_devolucion": dev_info.get("motivo"),
                "fecha_devolucion": dev_info.get("fecha_devolucion"),
                "radicado_previo": dev_info.get("radicado_previo"),
                "fecha_radicacion": None,
                "numero_radicado": None,
                "dosis_aplicadas": 0,
                "extranjeros": 0
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

    total_radicados = sum(1 for e in estados if e["estado"] in ["RADICADO", "RADICADO_CON_JUSTIFICACION", "APROBADO_OFICIAL"])
    total_justificados = sum(1 for e in estados if e["estado"] == "RADICADO_CON_JUSTIFICACION")
    return {
        "mes": mes,
        "ano": ano,
        "total_municipios": len(municipios),
        "radicados": total_radicados,
        "justificados": total_justificados,
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

    # 2.5 Comparación Cruzada: Dosis Aplicadas a Colombianos vs Movimiento Colombianos
    cruce_colombianos = None
    if res_dosis and res_mov:
        cruce_colombianos = auditar_cruce_colombianos(res_dosis, res_mov)
        if cruce_colombianos and cruce_colombianos.get("alertas"):
            res_mov["advertencias"].extend(cruce_colombianos["alertas"])

    # 2.6 Cruce Oficial Regla 3: Despachado Depósito Departamental vs Recibido Municipio
    cruce_deposito = res_mov.get("cruce_deposito") if res_mov else None

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
        "dictamen": dictamen,
        "cruce_colombianos": cruce_colombianos,
        "cruce_deposito": cruce_deposito,
        "detalle_dosis": res_dosis,
        "detalle_movimiento": res_mov,
        "detalle_extranjeros": res_ext
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
        "cruce_colombianos": cruce_colombianos,
        "cruce_deposito": cruce_deposito,
        "puede_radicar": dictamen["aprobado"]
    }

@app.post("/api/radicar")
async def api_radicar(
    session_id: str = Form(...),
    justificacion: str = Form(None)
):
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

    justificacion_limpia = str(justificacion or "").strip()
    es_aprobado = meta.get("dictamen", {}).get("aprobado", False)

    if not es_aprobado:
        if not justificacion_limpia or len(justificacion_limpia) < 10:
            raise HTTPException(
                status_code=400, 
                detail="El informe contiene inconsistencias bloqueantes. Para radicar bajo excepción, debe ingresar una justificación técnica o administrativa detallada (mínimo 10 caracteres)."
            )

    municipio = meta["municipio"]
    mes = meta["mes"]
    ano = meta["ano"]
    num_radicado = f"RAD-RIS-{ano}-{mes[:3]}-{str(uuid.uuid4())[:6].upper()}"
    fecha_rad = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    os.makedirs(target_dir, exist_ok=True)
    dev_file = os.path.join(target_dir, "estado_devolucion.json")
    if os.path.exists(dev_file):
        try:
            os.remove(dev_file)
        except Exception:
            pass

    # Copiar archivos a radicados definitivos
    archivos_radicados = {}
    for clave, p in meta["archivos"].items():
        if p and clave != "ANEXOS" and os.path.exists(p):
            fname = os.path.basename(p)
            dest = os.path.join(target_dir, f"{clave}_{fname}")
            shutil.copy2(p, dest)
            archivos_radicados[clave] = dest

    tiene_justificacion = bool(not es_aprobado and justificacion_limpia)

    # Guardar recibo completo con auditoría detallada
    recibo = {
        "numero_radicado": num_radicado,
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "fecha": fecha_rad,
        "estado": "RADICADO_CON_JUSTIFICACION" if tiene_justificacion else "RADICADO",
        "tiene_justificacion": tiene_justificacion,
        "justificacion": justificacion_limpia if tiene_justificacion else None,
        "aprobado_departamental": None,
        "archivos": archivos_radicados,
        "metricas": meta["dictamen"]["metricas"],
        "dictamen": meta.get("dictamen"),
        "cruce_colombianos": meta.get("cruce_colombianos"),
        "cruce_deposito": meta.get("cruce_deposito"),
        "simultaneidad": (meta.get("detalle_dosis") or {}).get("resumen_coherencia", {}).get("informe_simultaneidad", []),
        "dictamen_reglas": generar_dictamen_reglas_detallado(
            municipio, mes, ano,
            meta.get("detalle_dosis"),
            meta.get("detalle_movimiento"),
            meta.get("detalle_extranjeros"),
            meta.get("cruce_colombianos"),
            meta.get("cruce_deposito")
        ),
        "detalle_auditoria": {
            "dosis": meta.get("detalle_dosis"),
            "movimiento": meta.get("detalle_movimiento"),
            "extranjeros": meta.get("detalle_extranjeros")
        }
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

@app.get("/api/admin/plantillas-base/{mes}")
def api_admin_plantillas_base(mes: str, ano: str = "2026"):
    mes = mes.upper()
    custom_dir = os.path.join(TEMPLATES_MES_DIR, ano, mes)

    res = {
        "mes": mes,
        "ano": ano,
        "movimiento": {"personalizada": False, "nombre_archivo": "Plantilla_Movimiento_Base.xlsm", "fecha": None, "tamano_kb": 0},
        "dosis": {"personalizada": False, "nombre_archivo": "Plantilla_Dosis_Base.xlsx", "fecha": None, "tamano_kb": 0},
        "extranjeros": {"personalizada": False, "nombre_archivo": "Plantilla_Extranjeros_Base.xlsx", "fecha": None, "tamano_kb": 0}
    }

    if os.path.exists(custom_dir):
        meta_file = os.path.join(custom_dir, "metadata.json")
        meta = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

        for tipo in ["movimiento", "dosis", "extranjeros"]:
            exts = [".xlsm", ".xlsx"] if tipo == "movimiento" else [".xlsx"]
            prefijo = f"BASE_{tipo.upper()}_{mes}_{ano}"
            for f in os.listdir(custom_dir):
                if f.upper().startswith(prefijo) and any(f.endswith(e) for e in exts):
                    fpath = os.path.join(custom_dir, f)
                    st = os.stat(fpath)
                    mod_dt = datetime.fromtimestamp(st.st_mtime).strftime("%d/%m/%Y %H:%M")
                    orig_name = meta.get(tipo, {}).get("nombre_original", f)
                    res[tipo] = {
                        "personalizada": True,
                        "nombre_archivo": orig_name,
                        "archivo_sistema": f,
                        "fecha": mod_dt,
                        "tamano_kb": round(st.st_size / 1024, 1)
                    }
                    break
    return res

@app.post("/api/admin/subir-plantilla-base/{tipo}/{mes}")
async def api_admin_subir_plantilla_base(tipo: str, mes: str, file: UploadFile = File(...), ano: str = "2026"):
    tipo = tipo.lower()
    if tipo not in ["movimiento", "dosis", "extranjeros"]:
        raise HTTPException(status_code=400, detail="Tipo de plantilla no válido. Debe ser: movimiento, dosis o extranjeros.")

    mes = mes.upper()
    fname = file.filename or ""
    ext = os.path.splitext(fname)[1].lower()

    if tipo == "movimiento" and ext not in [".xlsm", ".xlsx"]:
        raise HTTPException(status_code=400, detail="Para Movimiento de Biológicos se requiere archivo .xlsm o .xlsx.")
    if tipo != "movimiento" and ext != ".xlsx":
        raise HTTPException(status_code=400, detail="Para este informe se requiere archivo formato .xlsx.")

    custom_dir = os.path.join(TEMPLATES_MES_DIR, ano, mes)
    os.makedirs(custom_dir, exist_ok=True)

    dest_name = f"BASE_{tipo.upper()}_{mes}_{ano}{ext}"
    dest_path = os.path.join(custom_dir, dest_name)

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    # Guardar metadatos
    meta_file = os.path.join(custom_dir, "metadata.json")
    meta = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as jf:
                meta = json.load(jf)
        except Exception:
            meta = {}

    meta[tipo] = {
        "nombre_original": fname,
        "fecha_subida": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tamano_bytes": len(content)
    }
    with open(meta_file, "w", encoding="utf-8") as jf:
        json.dump(meta, jf, ensure_ascii=False, indent=2)

    return {
        "success": True,
        "mensaje": f"Plantilla base departamental de {tipo.capitalize()} cargada exitosamente para {mes} {ano}.",
        "tipo": tipo,
        "mes": mes,
        "nombre_original": fname
    }

@app.post("/api/admin/restablecer-plantilla-base/{tipo}/{mes}")
def api_admin_restablecer_plantilla_base(tipo: str, mes: str, ano: str = "2026"):
    tipo = tipo.lower()
    mes = mes.upper()
    custom_dir = os.path.join(TEMPLATES_MES_DIR, ano, mes)

    if os.path.exists(custom_dir):
        exts = [".xlsm", ".xlsx"] if tipo == "movimiento" else [".xlsx"]
        prefijo = f"BASE_{tipo.upper()}_{mes}_{ano}"
        for f in os.listdir(custom_dir):
            if f.upper().startswith(prefijo) and any(f.endswith(e) for e in exts):
                try:
                    os.remove(os.path.join(custom_dir, f))
                except Exception:
                    pass
        meta_file = os.path.join(custom_dir, "metadata.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as jf:
                    meta = json.load(jf)
                if tipo in meta:
                    del meta[tipo]
                with open(meta_file, "w", encoding="utf-8") as jf:
                    json.dump(meta, jf, ensure_ascii=False, indent=2)
            except Exception:
                pass

    return {
        "success": True,
        "mensaje": f"Plantilla de {tipo.capitalize()} restablecida a la oficial por defecto para {mes} {ano}."
    }

@app.get("/api/admin/info-kardex")
def api_admin_info_kardex():
    """Retorna información técnica y estado del archivo oficial de Kardex Departamental."""
    return obtener_info_kardex_actual()

@app.post("/api/admin/subir-kardex")
async def api_admin_subir_kardex(file: UploadFile = File(...)):
    """
    Permite a la administración departamental subir el archivo Excel actualizado
    del Kardex de entregas del Depósito Departamental (deposito_risaralda.xlsx).
    """
    fname = file.filename or ""
    ext = os.path.splitext(fname)[1].lower()
    if ext != ".xlsx":
        raise HTTPException(status_code=400, detail="El Kardex Departamental debe ser un archivo Excel (.xlsx).")

    catalogos_dir = os.path.join(STORAGE_DIR, "catalogos")
    os.makedirs(catalogos_dir, exist_ok=True)
    dest_path = os.path.join(catalogos_dir, "deposito_risaralda.xlsx")
    backup_path = os.path.join(catalogos_dir, "deposito_risaralda_backup.xlsx")

    content = await file.read()
    if len(content) < 1000:
        raise HTTPException(status_code=400, detail="El archivo está vacío o dañado.")

    tmp_path = os.path.join(catalogos_dir, f"tmp_{uuid.uuid4().hex[:8]}.xlsx")
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        import openpyxl
        wb = openpyxl.load_workbook(tmp_path, data_only=True, read_only=True)
        sheets = wb.sheetnames
        wb.close()
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"No se pudo procesar el archivo Excel: {str(e)}")

    if os.path.exists(dest_path):
        try:
            shutil.copy2(dest_path, backup_path)
        except Exception:
            pass

    shutil.move(tmp_path, dest_path)
    limpiar_cache_kardex()

    try:
        cargar_lotes_google_sheet()
    except Exception as e:
        print(f"Error recargando lotes: {e}")

    info = obtener_info_kardex_actual()

    return {
        "success": True,
        "mensaje": f"Kardex Oficial del Depósito Departamental actualizado exitosamente ({fname}).",
        "archivo": "deposito_risaralda.xlsx",
        "nombre_original": fname,
        "info": info
    }

@app.get("/api/admin/kardex-drive-config")
def api_admin_kardex_drive_config():
    """Retorna la configuración actual del conector de Google Drive/Sheets para el Kardex."""
    return obtener_config_kardex_drive()

@app.post("/api/admin/guardar-kardex-drive-config")
def api_admin_guardar_kardex_drive_config(
    url_origen: str = Form(...),
    auto_sync: bool = Form(True)
):
    """Guarda la URL o ID del Google Sheets/Drive del Kardex y estado de auto-sincronización mensual."""
    cfg = guardar_config_kardex_drive({
        "url_origen": url_origen.strip(),
        "auto_sync": auto_sync
    })
    return {
        "success": True,
        "mensaje": "Configuración de conexión automática del Kardex guardada exitosamente.",
        "config": cfg
    }

@app.post("/api/admin/sincronizar-kardex-drive")
def api_admin_sincronizar_kardex_drive(url_origen: str = Form(None)):
    """Ejecuta la sincronización inmediata del Kardex oficial desde Google Drive / Sheets."""
    res = descargar_kardex_google(url_origen)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Error al sincronizar con Google Drive/Sheets."))
    return res

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
        "bases_utilizadas": resultado.get("bases_utilizadas", {}),
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

    # Si el radicado es previo o no tiene el informe detallado, calcular en vivo
    if "cruce_colombianos" not in recibo and recibo.get("archivos", {}).get("DOSIS") and recibo.get("archivos", {}).get("MOVIMIENTO"):
        try:
            f_dos = recibo["archivos"]["DOSIS"]
            f_mov = recibo["archivos"]["MOVIMIENTO"]
            f_ext = recibo["archivos"].get("EXTRANJEROS")
            r_d = validar_dosis(f_dos, mes_evaluar=mes, municipio_nombre=municipio) if os.path.exists(f_dos) else None
            r_m = validar_movimiento(f_mov, mes_evaluar=mes, municipio_nombre=municipio) if os.path.exists(f_mov) else None
            r_e = validar_extranjeros(f_ext, mes_evaluar=mes, municipio_nombre=municipio) if f_ext and os.path.exists(f_ext) else None
            if r_d and r_m:
                recibo["cruce_colombianos"] = auditar_cruce_colombianos(r_d, r_m)
            if r_m and "cruce_deposito" in r_m:
                recibo["cruce_deposito"] = r_m["cruce_deposito"]
            if r_d:
                recibo["simultaneidad"] = r_d.get("resumen_coherencia", {}).get("informe_simultaneidad", [])
            recibo["dictamen"] = generar_dictamen_auditoria(municipio, mes, r_d, r_m, r_e)
            recibo["detalle_auditoria"] = {
                "dosis": r_d,
                "movimiento": r_m,
                "extranjeros": r_e
            }
        except Exception as e_insp:
            print(f"[Admin Inspeccionar] Fallo al enriquecer radicado en vivo: {e_insp}")

    if "cruce_deposito" not in recibo:
        mov_det = recibo.get("detalle_auditoria", {}).get("movimiento")
        if mov_det and "cruce_deposito" in mov_det:
            recibo["cruce_deposito"] = mov_det["cruce_deposito"]
        elif recibo.get("archivos", {}).get("MOVIMIENTO"):
            try:
                f_mov = recibo["archivos"]["MOVIMIENTO"]
                if os.path.exists(f_mov):
                    r_m = validar_movimiento(f_mov, mes_evaluar=mes, municipio_nombre=municipio, ano=ano)
                    if r_m and "cruce_deposito" in r_m:
                        recibo["cruce_deposito"] = r_m["cruce_deposito"]
            except Exception as e_cd:
                print(f"[Admin Inspeccionar] Fallo al extraer cruce_deposito: {e_cd}")

    if "dictamen_reglas" not in recibo or not recibo.get("dictamen_reglas"):
        try:
            recibo["dictamen_reglas"] = generar_dictamen_reglas_detallado(
                municipio, mes, ano,
                recibo.get("detalle_auditoria", {}).get("dosis"),
                recibo.get("detalle_auditoria", {}).get("movimiento"),
                recibo.get("detalle_auditoria", {}).get("extranjeros"),
                recibo.get("cruce_colombianos"),
                recibo.get("cruce_deposito")
            )
        except Exception as e_dr:
            print(f"[Admin Inspeccionar] Fallo generando dictamen_reglas: {e_dr}")

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

@app.post("/api/admin/devolver-radicado")
def api_admin_devolver_radicado(
    municipio: str = Form(...),
    mes: str = Form(...),
    ano: str = Form("2026"),
    motivo: str = Form(...)
):
    municipio = municipio.upper()
    mes = mes.upper()
    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    receipt_file = os.path.join(target_dir, "radicado.json")

    if not os.path.exists(receipt_file):
        raise HTTPException(status_code=404, detail=f"No se encontró radicado activo para {municipio} en {mes} {ano}.")

    with open(receipt_file, "r", encoding="utf-8") as f:
        recibo = json.load(f)

    # 1. Crear carpeta de histórico de devoluciones con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    num_rad = recibo.get("numero_radicado", "RAD")
    hist_dir = os.path.join(target_dir, "historico_devoluciones", f"{timestamp}_{num_rad}")
    os.makedirs(hist_dir, exist_ok=True)

    # 2. Mover archivos y recibo actual al histórico
    for file_name in os.listdir(target_dir):
        fpath = os.path.join(target_dir, file_name)
        if os.path.isfile(fpath) and file_name != "estado_devolucion.json":
            shutil.move(fpath, os.path.join(hist_dir, file_name))

    # 3. Guardar metadatos de la devolución
    info_dev = {
        "estado": "DEVUELTO",
        "municipio": municipio,
        "mes": mes,
        "ano": ano,
        "fecha_devolucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "motivo": motivo.strip(),
        "radicado_previo": num_rad
    }

    with open(os.path.join(hist_dir, "devolucion_meta.json"), "w", encoding="utf-8") as f:
        json.dump(info_dev, f, indent=2, ensure_ascii=False)

    with open(os.path.join(target_dir, "estado_devolucion.json"), "w", encoding="utf-8") as f:
        json.dump(info_dev, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "mensaje": f"El informe de {municipio} ({mes} {ano}) ha sido devuelto satisfactoriamente. Se habilitó la re-radicación para el municipio.",
        "detalle": info_dev
    }

@app.post("/api/admin/aprobar-justificacion")
def api_admin_aprobar_justificacion(
    municipio: str = Form(...),
    mes: str = Form(...),
    ano: str = Form("2026"),
    observacion: str = Form(None)
):
    municipio = municipio.upper()
    mes = mes.upper()
    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    receipt_file = os.path.join(target_dir, "radicado.json")

    if not os.path.exists(receipt_file):
        raise HTTPException(status_code=404, detail="No se encontró radicado oficial para este municipio y mes.")

    with open(receipt_file, "r", encoding="utf-8") as f:
        recibo = json.load(f)

    recibo["estado"] = "APROBADO_OFICIAL"
    recibo["aprobado_departamental"] = {
        "aprobado": True,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "observacion": (observacion or "Justificación de inconsistencias revisada y aceptada por la Referente Departamental.").strip()
    }

    with open(receipt_file, "w", encoding="utf-8") as f:
        json.dump(recibo, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "mensaje": f"La justificación del informe de {municipio} ({mes} {ano}) ha sido APROBADA satisfactoriamente.",
        "detalle": recibo["aprobado_departamental"]
    }

@app.get("/api/municipio/estado/{municipio}/{mes}")
def api_municipio_estado(municipio: str, mes: str, ano: str = "2026"):
    municipio = municipio.upper()
    mes = mes.upper()
    target_dir = os.path.join(RADICADOS_DIR, ano, mes, municipio)
    receipt_file = os.path.join(target_dir, "radicado.json")
    dev_file = os.path.join(target_dir, "estado_devolucion.json")

    if os.path.exists(receipt_file):
        with open(receipt_file, "r", encoding="utf-8") as f:
            rec = json.load(f)
        return {
            "estado": rec.get("estado", "RADICADO"),
            "tiene_justificacion": rec.get("tiene_justificacion", False),
            "justificacion": rec.get("justificacion"),
            "aprobado_departamental": rec.get("aprobado_departamental"),
            "numero_radicado": rec.get("numero_radicado"),
            "fecha": rec.get("fecha"),
            "municipio": municipio,
            "mes": mes,
            "ano": ano
        }
    elif os.path.exists(dev_file):
        with open(dev_file, "r", encoding="utf-8") as f:
            dev = json.load(f)
        return {
            "estado": "DEVUELTO",
            "motivo": dev.get("motivo"),
            "fecha_devolucion": dev.get("fecha_devolucion"),
            "radicado_previo": dev.get("radicado_previo"),
            "municipio": municipio,
            "mes": mes,
            "ano": ano
        }
    else:
        return {
            "estado": "PENDIENTE",
            "municipio": municipio,
            "mes": mes,
            "ano": ano
        }

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
