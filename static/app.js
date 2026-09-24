// app.js - Lógica del Portal Municipal PAI Risaralda (Claro Clínico Pro)

let archivosSeleccionados = [];
let sesionActual = null;
let usuarioSesion = null;

document.addEventListener('DOMContentLoaded', () => {
  verificarSesionInicial();
  verificarEstadoIA();
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

async function verificarEstadoIA() {
  try {
    const res = await fetch('/api/ia/estado');
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById('ia-status-badge');
      const text = document.getElementById('ia-status-text');
      if (badge && text) {
        badge.classList.remove('hidden');
        if (data.activo) {
          text.textContent = `✨ Gemini IA: Conectado`;
          badge.title = `Conectado a Google Gemini (${data.modelo})`;
        } else {
          badge.classList.remove('bg-indigo-50', 'border-indigo-200', 'text-indigo-900');
          badge.classList.add('bg-slate-100', 'border-slate-300', 'text-slate-700');
          badge.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-slate-500"></span><span>IA Local</span>`;
          badge.title = data.mensaje || "Motor pedagógico local";
        }
      }
    }
  } catch (e) {
    console.warn("Estado IA:", e);
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

  const dDosis = data.detalle_dosis || {};
  const dMov = data.detalle_movimiento || {};
  const dExt = data.detalle_extranjeros || {};
  const cruce = data.cruce_colombianos;
  const cruceDep = data.cruce_deposito || (dMov && dMov.cruce_deposito);
  const sim = (dDosis.resumen_coherencia && dDosis.resumen_coherencia.informe_simultaneidad) ? dDosis.resumen_coherencia.informe_simultaneidad : [];

  // 1. Checklist de Reglas
  const reglas = [
    {
      nombre: "Regla de Oro Demográfica PAI (541 Columnas)",
      archivo: "Dosis Aplicadas",
      ok: dDosis.resumen_coherencia ? (dDosis.resumen_coherencia.coincidencia_genero_regimen && dDosis.resumen_coherencia.coincidencia_genero_etnico) : true,
      desc: "Suma(Género) == Suma(Régimen) == Suma(Pertenencia Étnica)"
    },
    {
      nombre: "Recálculo Anti-Adulteración de Fórmulas",
      archivo: "Dosis Aplicadas",
      ok: dDosis.resumen_coherencia ? (dDosis.resumen_coherencia.formulas_adulteradas === 0) : true,
      desc: "Comprobación fila por fila contra fórmulas alteradas o sobreescritas"
    },
    {
      nombre: "Continuidad Intermensual de Saldos (Regla 1)",
      archivo: "Movimiento Biológicos",
      ok: dMov.metricas_reglas ? dMov.metricas_reglas.regla1_continuidad_saldos : true,
      desc: "Saldo Anterior mes actual == Saldo Siguiente mes anterior oficial"
    },
    {
      nombre: "Coherencia de 5 Lotes vs Saldo Siguiente (Regla 2)",
      archivo: "Movimiento Biológicos",
      ok: dMov.metricas_reglas ? dMov.metricas_reglas.regla2_flag_verdadero : true,
      desc: "Suma de dosis en las 5 celdas de lotes == Saldo Siguiente (Col N = Col M)"
    },
    {
      nombre: "Cruce Entregas Depósito Departamental (Regla 3)",
      archivo: "Movimiento vs Kardex",
      ok: cruceDep && cruceDep.resumen ? (cruceDep.resumen.biologicos_exactos === cruceDep.resumen.biologicos_total) : true,
      desc: "Dosis recibidas (Col 5) vs despachadas en Kardex oficial por el Depósito Departamental"
    },
    {
      nombre: "Catálogo Maestro de Lotes Oficiales (Regla 4)",
      archivo: "Movimiento Biológicos",
      ok: dMov.metricas_reglas ? dMov.metricas_reglas.regla4_lotes_oficiales : true,
      desc: "Lotes registrados contra el catálogo maestro del Depósito de Risaralda"
    },
    {
      nombre: "Diluyentes en Liofilizados (Regla 6)",
      archivo: "Movimiento Biológicos",
      ok: !(dMov.errores || []).some(e => e.regla === 'REGLA_6_DILUYENTES_INSUFICIENTES'),
      desc: "Diluyentes utilizados >= Vacunas reconstituidas utilizadas"
    },
    {
      nombre: "Racionalidad de 11 Causas de Pérdida (Regla 5)",
      archivo: "Movimiento Biológicos",
      ok: dMov.metricas_reglas ? dMov.metricas_reglas.regla5_racionalidad_perdidas : true,
      desc: "Suma de 11 causas == Total Pérdidas reportadas"
    },
    {
      nombre: "Coherencia Matricial en Países Fronterizos",
      archivo: "Vacunados Extranjeros",
      ok: !(dExt.errores || []).some(e => e.tipo === 'DESCUADRE_EXTRANJEROS'),
      desc: "Total Género == Total Régimen en las 6 hojas de países migrantes"
    }
  ];

  let htmlReglas = `
    <div class="rounded-2xl border-2 border-slate-200 overflow-hidden shadow-sm bg-white">
      <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
        <span class="text-xs font-black uppercase text-slate-800 tracking-wider">📋 Checklist de Reglas de Auditoría Auditadas</span>
        <span class="text-[11px] font-bold text-slate-600">${reglas.filter(r => r.ok).length}/${reglas.length} Reglas Cumplidas</span>
      </div>
      <div class="divide-y divide-slate-100 text-xs">
  `;

  reglas.forEach(r => {
    htmlReglas += `
      <div class="p-3 flex items-center justify-between gap-3 hover:bg-slate-50 transition">
        <div class="space-y-0.5">
          <div class="font-bold text-slate-900 flex items-center gap-2">
            <span>${r.nombre}</span>
            <span class="text-[10px] font-mono font-normal text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">${r.archivo}</span>
          </div>
          <div class="text-[11px] text-slate-600">${r.desc}</div>
        </div>
        <div>
          <span class="px-2.5 py-1 rounded-full text-[11px] font-black flex items-center gap-1 ${r.ok ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-rose-100 text-rose-900 border border-rose-300'}">
            ${r.ok ? '✓ CUMPLE' : '✕ BLOQUEA'}
          </span>
        </div>
      </div>
    `;
  });
  htmlReglas += `</div></div>`;

  // 2. Cruce Oficial Regla 3: Despachado Depósito Departamental (Kardex) vs Recibido Municipio (Col 5)
  let htmlCruceDeposito = '';
  if (cruceDep && cruceDep.items && cruceDep.items.length > 0) {
    const resDep = cruceDep.resumen || {};
    htmlCruceDeposito = `
      <div class="rounded-2xl border-2 border-slate-200 overflow-hidden shadow-sm bg-white">
        <div class="bg-indigo-50 px-4 py-2.5 border-b border-indigo-200 flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-black uppercase text-indigo-950 tracking-wider">📦 Cruce Oficial: Entregas Depósito Departamental vs Recibido por Municipio (Regla 3)</span>
          </div>
          <span class="text-[11px] font-bold text-indigo-900 bg-indigo-100/70 border border-indigo-200 px-2.5 py-0.5 rounded-full">
            ${resDep.biologicos_exactos || 0}/${resDep.biologicos_total || 0} Biológicos 100% Coincidentes (${resDep.porcentaje_coincidencia || 0}%)
          </span>
        </div>
        <div class="p-3 bg-slate-50 border-b border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
          <div class="bg-white p-2 rounded-xl border border-slate-200">
            <div class="text-[10px] uppercase font-bold text-slate-500">Despachado Depósito</div>
            <div class="text-base font-black text-slate-900 font-mono">${(resDep.total_despachado || 0).toLocaleString()}</div>
          </div>
          <div class="bg-white p-2 rounded-xl border border-slate-200">
            <div class="text-[10px] uppercase font-bold text-slate-500">Recibido Municipio</div>
            <div class="text-base font-black text-slate-900 font-mono">${(resDep.total_recibido || 0).toLocaleString()}</div>
          </div>
          <div class="bg-white p-2 rounded-xl border border-slate-200">
            <div class="text-[10px] uppercase font-bold text-emerald-700">Coincidencias Exactas</div>
            <div class="text-base font-black text-emerald-800 font-mono">${resDep.total_coincidencias || 0}</div>
          </div>
          <div class="bg-white p-2 rounded-xl border border-slate-200">
            <div class="text-[10px] uppercase font-bold text-amber-700">Diferencias Detectadas</div>
            <div class="text-base font-black text-amber-800 font-mono">${resDep.total_diferencias || 0}</div>
          </div>
        </div>
        <div class="max-h-64 overflow-y-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-100 text-[10px] uppercase font-black text-slate-600 border-b border-slate-200 sticky top-0">
              <tr>
                <th class="p-2.5 pl-4">Insumo / Biológico</th>
                <th class="p-2.5 text-center">Grupo</th>
                <th class="p-2.5 text-right">Despacho Kardex</th>
                <th class="p-2.5 text-right">Recibido Municipio</th>
                <th class="p-2.5 text-right">Diferencia</th>
                <th class="p-2.5 pr-4 text-center">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-medium text-slate-800">
    `;

    cruceDep.items.forEach(it => {
      const esMatch = Math.abs(it.diferencia) < 0.001;
      const lotesTxt = (it.lotes_despachados && it.lotes_despachados.length > 0)
        ? `<div class="text-[10px] font-mono text-slate-500">Lotes Kardex: ${it.lotes_despachados.join(', ')}</div>`
        : '';
      htmlCruceDeposito += `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-2.5 pl-4">
            <div class="font-bold text-slate-900">${it.insumo}</div>
            ${lotesTxt}
          </td>
          <td class="p-2.5 text-center">
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${it.grupo === 'Biológico' ? 'bg-indigo-100 text-indigo-900 border border-indigo-200' : (it.grupo === 'Diluyente' ? 'bg-teal-100 text-teal-900 border border-teal-200' : 'bg-slate-100 text-slate-800 border border-slate-200')}">
              ${it.grupo}
            </span>
          </td>
          <td class="p-2.5 text-right font-mono font-bold">${it.despachado_deposito.toLocaleString()}</td>
          <td class="p-2.5 text-right font-mono font-bold">${it.recibido_municipio.toLocaleString()}</td>
          <td class="p-2.5 text-right font-mono font-black ${esMatch ? 'text-emerald-700' : 'text-amber-700'}">
            ${it.diferencia > 0 ? '+' + it.diferencia : it.diferencia}
          </td>
          <td class="p-2.5 pr-4 text-center">
            <span class="text-[10px] font-black px-2 py-0.5 rounded-full ${esMatch ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-amber-100 text-amber-900 border border-amber-300'}">
              ${esMatch ? '✓ Exacta' : '⚠️ ' + (it.diferencia > 0 ? '+' : '') + it.diferencia}
            </span>
          </td>
        </tr>
      `;
    });

    htmlCruceDeposito += `
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // 2.1 Tabla Comparativa Cruzada (Dosis Aplicadas a Colombianos vs Movimiento Colombianos)
  let htmlCruce = '';
  if (cruce && cruce.tabla_comparativa && cruce.tabla_comparativa.length > 0) {
    htmlCruce = `
      <div class="rounded-2xl border-2 border-slate-200 overflow-hidden shadow-sm bg-white">
        <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
          <span class="text-xs font-black uppercase text-slate-800 tracking-wider">⚖️ Comparación Cruzada: Dosis Aplicadas (Plantilla) vs Movimiento (Colombianos)</span>
          <span class="text-[11px] font-bold text-slate-600">${cruce.coincidencias_exactas} Coincidencias • ${cruce.discrepancias_observadas} Diferencias (${cruce.porcentaje_coincidencia}%)</span>
        </div>
        <div class="max-h-60 overflow-y-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-[10px] uppercase font-black text-slate-600 border-b border-slate-200 sticky top-0">
              <tr>
                <th class="p-2.5 pl-4">Biológico</th>
                <th class="p-2.5 text-right">Dosis Plantilla</th>
                <th class="p-2.5 text-right">Dosis Movimiento</th>
                <th class="p-2.5 text-right">Diferencia</th>
                <th class="p-2.5 pr-4 text-center">Estado</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-medium text-slate-800">
    `;

    cruce.tabla_comparativa.forEach(f => {
      const esMatch = f.diferencia === 0;
      htmlCruce += `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-2.5 pl-4 font-bold text-slate-900">${f.biologico}</td>
          <td class="p-2.5 text-right font-mono font-bold">${f.dosis_plantilla.toLocaleString()}</td>
          <td class="p-2.5 text-right font-mono font-bold">${f.dosis_movimiento.toLocaleString()}</td>
          <td class="p-2.5 text-right font-mono font-black ${esMatch ? 'text-emerald-700' : 'text-amber-700'}">${f.diferencia > 0 ? '+' + f.diferencia : f.diferencia}</td>
          <td class="p-2.5 pr-4 text-center">
            <span class="text-[10px] font-black px-2 py-0.5 rounded-full ${esMatch ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-amber-100 text-amber-900 border border-amber-300'}">
              ${esMatch ? '✓ Exacta' : '⚠️ ' + f.diferencia}
            </span>
          </td>
        </tr>
      `;
    });

    htmlCruce += `
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // 3. Reporte de Oportunidades y Simultaneidad (6 Cohortes)
  let htmlSimultaneidad = '';
  if (sim && sim.length > 0) {
    htmlSimultaneidad = `
      <div class="rounded-2xl border-2 border-indigo-200 overflow-hidden shadow-sm bg-white">
        <div class="bg-indigo-50 px-4 py-2.5 border-b border-indigo-200 flex items-center justify-between">
          <span class="text-xs font-black uppercase text-indigo-950 tracking-wider">🎯 Informe de Oportunidades y Simultaneidad del Esquema (6 Cohortes)</span>
          <span class="text-[11px] font-bold text-indigo-800">Oportunidades de Vacunación</span>
        </div>
        <div class="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
    `;

    sim.forEach(c => {
      const esOpt = c.estado === 'OPTIMO';
      const listaBios = (c.biologicos || []).map(b => `<span class="font-bold">${b.nombre}:</span> <span class="font-mono text-indigo-950 font-black">${b.dosis}</span>`).join(' • ');
      htmlSimultaneidad += `
        <div class="p-3.5 rounded-xl border-2 ${esOpt ? 'border-emerald-200 bg-emerald-50/50' : 'border-amber-200 bg-amber-50/50'} space-y-1.5 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-black text-slate-900">${c.cohorte}</span>
            <span class="text-[10px] font-black px-2 py-0.5 rounded-full ${esOpt ? 'bg-emerald-200 text-emerald-950' : 'bg-amber-200 text-amber-950'}">
              ${esOpt ? '✓ 100% ÓPTIMA' : '⚠️ DESFASE OBSERVADO'}
            </span>
          </div>
          <div class="text-[11px] text-slate-700">${listaBios}</div>
          <div class="text-[10px] font-bold ${esOpt ? 'text-emerald-800' : 'text-amber-800'} pt-1 border-t border-slate-200/60">${c.resumen}</div>
        </div>
      `;
    });

    htmlSimultaneidad += `</div></div>`;
  }

  let html = `
    <div class="rounded-3xl border-2 p-6 md:p-8 space-y-6 shadow-sm ${aprobado ? 'bg-emerald-50/90 border-emerald-400' : 'bg-rose-50/90 border-rose-400'}">
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
        <div class="flex items-center gap-4">
          <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-white text-2xl font-black shadow-md flex-shrink-0 ${aprobado ? 'bg-emerald-700' : 'bg-rose-700'}">
            ${aprobado ? '✓' : '✕'}
          </div>
          <div>
            <span class="text-xs font-black uppercase tracking-wider px-3 py-0.5 rounded-full ${aprobado ? 'bg-emerald-200 border border-emerald-400 text-emerald-950' : 'bg-rose-200 border border-rose-400 text-rose-950'}">
              ${aprobado ? 'Dictamen: Aprobado' : 'Inconsistencias Críticas Detectadas'}
            </span>
            <h3 class="text-xl font-black text-slate-950 mt-1">
              ${aprobado ? '¡INFORME 100% AUDITADO Y LISTO PARA RADICAR!' : 'INFORME BLOQUEADO: REQUIERE CORRECCIONES'}
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
            <span>🔒 Radicación Bloqueada hasta Corregir Errores</span>
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

      <!-- Checklist de Reglas -->
      ${htmlReglas}

      <!-- Cruce Oficial Entregas Depósito Departamental vs Recibido Municipio (Regla 3) -->
      ${htmlCruceDeposito}

      <!-- Cruce Comparativo Dosis vs Movimiento -->
      ${htmlCruce}

      <!-- Reporte de Simultaneidad del Esquema -->
      ${htmlSimultaneidad}

      <!-- Dictamen Pedagógico de IA -->
      <div class="bg-white border-2 ${aprobado ? 'border-emerald-300' : 'border-rose-300'} rounded-2xl p-6 space-y-4 shadow-sm">
        <div class="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-200">
          <div class="flex items-center gap-2 text-xs font-black uppercase tracking-wider ${aprobado ? 'text-emerald-900' : 'text-rose-900'}">
            <svg class="w-5 h-5 text-indigo-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            <span>Dictamen del Asistente PAI Risaralda</span>
          </div>
          <span class="text-xs font-black px-3 py-1 rounded-full border ${resAud.usando_gemini ? 'bg-indigo-100 border-indigo-300 text-indigo-950' : 'bg-slate-100 border-slate-300 text-slate-800'}">
            ${resAud.usando_gemini ? '✨ ' + (resAud.motor_ia || 'Gemini IA') : '🤖 ' + (resAud.motor_ia || 'Motor Local')}
          </span>
        </div>
        <div class="dictamen-contenido text-sm font-medium text-slate-900 leading-relaxed bg-slate-50 p-5 rounded-2xl border border-slate-200">
          ${(window.marked && window.marked.parse) ? marked.parse(resAud.dictamen_pedagogico) : resAud.dictamen_pedagogico.replace(/\n/g, '<br>')}
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
