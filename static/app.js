// app.js - Lógica del Portal Municipal PAI Risaralda (Claro Clínico Pro)

let archivosSeleccionados = [];
let sesionActual = null;
let usuarioSesion = null;

document.addEventListener('DOMContentLoaded', () => {
  verificarSesionInicial();
  configurarDropzone();
});

// 1. Verificación de Sesión y Autenticación
function verificarSesionInicial() {
  const token = sessionStorage.getItem('pai_token');
  const usuarioData = sessionStorage.getItem('pai_usuario_data');

  if (!token || !usuarioData) {
    mostrarModalLogin();
    return;
  }

  try {
    usuarioSesion = JSON.parse(usuarioData);
    if (usuarioSesion.rol === 'admin') {
      window.location.href = '/departamental';
      return;
    }
    inicializarVistaMunicipal();
  } catch (e) {
    mostrarModalLogin();
  }
}

function mostrarModalLogin() {
  document.getElementById('modal-login').classList.remove('hidden');
}

function autocompletarLogin(usuario, clave) {
  document.getElementById('login-usuario').value = usuario;
  document.getElementById('login-password').value = clave;
}

async function ejecutarLogin(e) {
  e.preventDefault();
  const u = document.getElementById('login-usuario').value.trim();
  const p = document.getElementById('login-password').value;
  const errDiv = document.getElementById('login-error');
  const btn = document.getElementById('btn-login');

  errDiv.classList.add('hidden');
  btn.disabled = true;
  btn.innerHTML = '<span>Verificando credenciales...</span>';

  try {
    const formData = new FormData();
    formData.append('usuario', u);
    formData.append('password', p);

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Credenciales incorrectas');
    }

    const data = await res.json();
    sessionStorage.setItem('pai_token', data.token);
    sessionStorage.setItem('pai_usuario_data', JSON.stringify(data));
    usuarioSesion = data;

    if (data.rol === 'admin') {
      window.location.href = '/departamental';
      return;
    }

    document.getElementById('modal-login').classList.add('hidden');
    inicializarVistaMunicipal();

  } catch (err) {
    errDiv.textContent = err.message;
    errDiv.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Ingresar a la Plataforma</span>';
  }
}

function inicializarVistaMunicipal() {
  if (!usuarioSesion) return;

  const mun = usuarioSesion.municipio || 'PEREIRA';
  const dane = usuarioSesion.dane || '66001';

  document.getElementById('label-municipio-activo').textContent = `${mun} (${dane})`;
  
  const selectMun = document.getElementById('select-municipio');
  selectMun.innerHTML = `<option value="${mun}" selected>${mun} (DANE: ${dane})</option>`;
  selectMun.disabled = true;

  document.getElementById('modal-login').classList.add('hidden');
  actualizarEstadoBotonAuditar();
}

function cerrarSesionUsuario() {
  const token = sessionStorage.getItem('pai_token');
  if (token) {
    const fd = new FormData();
    fd.append('token', token);
    fetch('/api/auth/logout', { method: 'POST', body: fd }).catch(() => {});
  }
  sessionStorage.clear();
  window.location.reload();
}

// 2. Drag & Drop y Carga de Archivos
function configurarDropzone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dropzone-dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dropzone-dragover');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    agregarArchivos(dt.files);
  });

  fileInput.addEventListener('change', (e) => {
    agregarArchivos(e.target.files);
  });
}

function agregarArchivos(files) {
  for (const f of files) {
    if (!archivosSeleccionados.some(x => x.name === f.name && x.size === f.size)) {
      archivosSeleccionados.push(f);
    }
  }
  renderizarListaArchivos();
  actualizarEstadoBotonAuditar();
}

function removerArchivo(index) {
  archivosSeleccionados.splice(index, 1);
  renderizarListaArchivos();
  actualizarEstadoBotonAuditar();
}

function renderizarListaArchivos() {
  const container = document.getElementById('file-list-container');
  const list = document.getElementById('file-list');
  list.innerHTML = '';

  if (archivosSeleccionados.length === 0) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');
  archivosSeleccionados.forEach((f, idx) => {
    const item = document.createElement('div');
    item.className = 'flex items-center justify-between p-3.5 rounded-2xl bg-white border-2 border-slate-200 shadow-sm text-xs';
    
    const sizeKb = (f.size / 1024).toFixed(0);
    const ext = f.name.split('.').pop().toLowerCase();
    const isXlsm = ext === 'xlsm';

    item.innerHTML = `
      <div class="flex items-center gap-3 overflow-hidden">
        <div class="w-8 h-8 rounded-lg ${isXlsm ? 'bg-blue-100 text-blue-800' : 'bg-emerald-100 text-emerald-800'} flex items-center justify-center font-bold text-xs flex-shrink-0">
          ${isXlsm ? 'MB' : 'XLS'}
        </div>
        <span class="font-extrabold text-slate-900 truncate max-w-[280px]" title="${f.name}">${f.name}</span>
        <span class="text-slate-500 font-mono text-[11px]">(${sizeKb} KB)</span>
      </div>
      <button onclick="removerArchivo(${idx})" class="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition" title="Quitar archivo">
        ✕
      </button>
    `;
    list.appendChild(item);
  });
}

function actualizarEstadoBotonAuditar() {
  const btn = document.getElementById('btn-auditar');
  btn.disabled = !(archivosSeleccionados.length > 0);
}

// 3. Ejecutar Auditoría
async function ejecutarAuditoria() {
  if (archivosSeleccionados.length === 0 || !usuarioSesion) return;

  const mun = usuarioSesion.municipio || document.getElementById('select-municipio').value;
  const mes = document.getElementById('select-mes').value;
  const ano = document.getElementById('input-ano').value;

  const btn = document.getElementById('btn-auditar');
  const spinner = document.getElementById('audit-loading');
  const resultsDiv = document.getElementById('audit-results');

  btn.disabled = true;
  spinner.classList.remove('hidden');
  resultsDiv.classList.add('hidden');
  resultsDiv.innerHTML = '';

  const formData = new FormData();
  formData.append('municipio', mun);
  formData.append('mes', mes);
  formData.append('ano', ano);
  archivosSeleccionados.forEach(f => {
    formData.append('archivos', f);
  });

  try {
    const res = await fetch('/api/auditar', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Error durante la auditoría');
    }

    const data = await res.json();
    sesionActual = data.session_id;
    renderizarResultadosAuditoria(data);
  } catch (err) {
    alert("Error al auditar: " + err.message);
  } finally {
    spinner.classList.add('hidden');
    btn.disabled = false;
  }
}

// 4. Renderizar Resultados en Claro Clínico Pro
function renderizarResultadosAuditoria(data) {
  const resultsDiv = document.getElementById('audit-results');
  resultsDiv.classList.remove('hidden');

  const resAud = data.resumen_auditoria;
  const aprobado = data.puede_radicar;

  let html = `
    <div class="rounded-3xl border-2 p-6 md:p-8 space-y-6 shadow-sm ${aprobado ? 'bg-emerald-50/90 border-emerald-400' : 'bg-rose-50/90 border-rose-400'}">
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
        <div class="flex items-center gap-4">
          <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-white text-2xl font-black shadow-md flex-shrink-0 ${aprobado ? 'bg-emerald-700' : 'bg-rose-700'}">
            ${aprobado ? '✓' : '✕'}
          </div>
          <div>
            <span class="text-xs font-black uppercase tracking-wider px-3 py-0.5 rounded-full ${aprobado ? 'bg-emerald-200 border border-emerald-400 text-emerald-950' : 'bg-rose-200 border border-rose-400 text-rose-950'}">
              ${aprobado ? 'Dictamen: Aprobado' : 'Inconsistencias Detectadas'}
            </span>
            <h3 class="text-xl font-black text-slate-950 mt-1">
              ${aprobado ? '¡INFORME 100% AUDITADO Y LISTO PARA RADICAR!' : 'INFORME REQUIERE CORRECCIONES'}
            </h3>
            <p class="text-xs font-bold text-slate-700 mt-0.5">
              ${data.municipio} • Reporte Oficial de ${data.mes} ${data.ano || '2026'}
            </p>
          </div>
        </div>

        ${aprobado ? `
          <button onclick="radicarInforme()" class="py-3.5 px-6 rounded-2xl bg-emerald-700 hover:bg-emerald-800 text-white font-black text-xs shadow-lg shadow-emerald-700/25 transition flex items-center justify-center gap-2 transform hover:scale-105">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <span>Radicar Informe Oficial</span>
          </button>
        ` : `
          <div class="px-4 py-2.5 rounded-xl bg-rose-200 border-2 border-rose-400 text-rose-950 text-xs font-black flex items-center gap-2">
            <span>🔒 Bloqueado para Radicación</span>
          </div>
        `}
      </div>

      <!-- Métricas Clave en Tarjetas Blancas -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t-2 ${aprobado ? 'border-emerald-300' : 'border-rose-300'}">
        <div class="bg-white p-4 rounded-2xl border-2 border-slate-200 shadow-sm">
          <div class="text-xs font-black uppercase text-slate-700">Dosis Aplicadas</div>
          <div class="text-2xl font-black text-slate-950 mt-1">${resAud.metricas.dosis_aplicadas_nacionales.toLocaleString()}</div>
          <div class="text-xs text-emerald-800 font-extrabold mt-0.5">✓ Matriz Demográfica</div>
        </div>
        <div class="bg-white p-4 rounded-2xl border-2 border-slate-200 shadow-sm">
          <div class="text-xs font-black uppercase text-slate-700">Dosis Movimiento</div>
          <div class="text-2xl font-black text-slate-950 mt-1">${resAud.metricas.dosis_movimiento_total.toLocaleString()}</div>
          <div class="text-xs text-emerald-800 font-extrabold mt-0.5">✓ Inventario Lotes</div>
        </div>
        <div class="bg-white p-4 rounded-2xl border-2 border-slate-200 shadow-sm">
          <div class="text-xs font-black uppercase text-slate-700">Dosis Pérdidas</div>
          <div class="text-2xl font-black text-amber-800 mt-1">${resAud.metricas.dosis_perdidas_total.toLocaleString()}</div>
          <div class="text-xs text-amber-800 font-extrabold mt-0.5">11 Causas Evaluadas</div>
        </div>
        <div class="bg-white p-4 rounded-2xl border-2 border-slate-200 shadow-sm">
          <div class="text-xs font-black uppercase text-slate-700">Extranjeros</div>
          <div class="text-2xl font-black text-blue-900 mt-1">${resAud.metricas.vacunados_extranjeros.toLocaleString()}</div>
          <div class="text-xs text-blue-800 font-extrabold mt-0.5">6 Países Validados</div>
        </div>
      </div>

      <!-- Dictamen Pedagógico de IA -->
      <div class="bg-white border-2 ${aprobado ? 'border-emerald-300' : 'border-rose-300'} rounded-2xl p-6 space-y-3 shadow-sm">
        <div class="flex items-center gap-2 text-xs font-black uppercase tracking-wider ${aprobado ? 'text-emerald-900' : 'text-rose-900'}">
          <svg class="w-5 h-5 text-indigo-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          <span>Dictamen del Asistente PAI Risaralda (IA)</span>
        </div>
        <div class="text-sm font-bold text-slate-800 leading-relaxed space-y-2 whitespace-pre-line bg-slate-50 p-4 rounded-xl border border-slate-200">
          ${resAud.dictamen_pedagogico}
        </div>
      </div>

    </div>
  `;

  resultsDiv.innerHTML = html;
  resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

// 5. Radicación Oficial y Sincronización a Google Drive
async function radicarInforme() {
  if (!sesionActual) return;

  try {
    const formData = new FormData();
    formData.append('session_id', sesionActual);

    const res = await fetch('/api/radicar', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Fallo en la radicación");
    }

    const data = await res.json();
    mostrarModalRadicado(data.recibo);
    
    // Limpiar formulario tras radicar
    archivosSeleccionados = [];
    renderizarListaArchivos();
    actualizarEstadoBotonAuditar();
    document.getElementById('audit-results').classList.add('hidden');

  } catch (err) {
    alert("Error al radicar: " + err.message);
  }
}

function mostrarModalRadicado(recibo) {
  const modal = document.getElementById('modal-radicado');
  const detalle = document.getElementById('recibo-detalle');

  detalle.innerHTML = `
    <div><strong>N° DE RADICADO:</strong> <span class="text-emerald-800 font-black text-sm">${recibo.numero_radicado}</span></div>
    <div><strong>MUNICIPIO:</strong> ${recibo.municipio}</div>
    <div><strong>MES DE REPORTE:</strong> ${recibo.mes} ${recibo.ano}</div>
    <div><strong>FECHA / HORA:</strong> ${recibo.fecha}</div>
    <div class="text-emerald-800 font-black">ESTADO: RADICADO Y 100% AUDITADO</div>
    <div class="pt-2 border-t-2 border-slate-200"><strong>DOSIS NACIONALES:</strong> ${recibo.metricas.dosis_aplicadas_nacionales.toLocaleString()}</div>
    <div><strong>DOSIS MOVIMIENTO:</strong> ${recibo.metricas.dosis_movimiento_total.toLocaleString()}</div>
    <div><strong>EXTRANJEROS:</strong> ${recibo.metricas.vacunados_extranjeros.toLocaleString()}</div>
    <div class="pt-2 border-t-2 border-slate-200 text-indigo-900 font-black">
      ☁️ GOOGLE DRIVE: Sincronizado a ${recibo.google_drive ? recibo.google_drive.correo : 'risaraldapaiweb@gmail.com'}
    </div>
    <div class="text-[10px] text-slate-500 font-mono">Carpeta: ${recibo.google_drive ? recibo.google_drive.carpeta : 'PAI_RISARALDA_2026/AGOSTO/' + recibo.municipio}</div>
  `;

  modal.classList.remove('hidden');
}

function cerrarModalRadicado() {
  document.getElementById('modal-radicado').classList.add('hidden');
}
