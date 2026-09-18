// departamental.js - Lógica del Tablero Departamental PAI Risaralda (Gobernación)

let datosDepartamentales = [];
let filtroActual = 'todos';

document.addEventListener('DOMContentLoaded', () => {
  verificarSesionAdmin();
  cargarTableroDepartamental();
});

function verificarSesionAdmin() {
  const token = sessionStorage.getItem('pai_token');
  const usuarioData = sessionStorage.getItem('pai_usuario_data');

  if (!token || !usuarioData) {
    window.location.href = '/';
    return;
  }

  try {
    const user = JSON.parse(usuarioData);
    if (user.rol !== 'admin') {
      alert("Acceso restringido: Esta vista es exclusiva para el Administrador Departamental.");
      window.location.href = '/';
      return;
    }
  } catch (e) {
    window.location.href = '/';
  }
}

function cerrarSesionAdmin() {
  const token = sessionStorage.getItem('pai_token');
  if (token) {
    const fd = new FormData();
    fd.append('token', token);
    fetch('/api/auth/logout', { method: 'POST', body: fd }).catch(() => {});
  }
  sessionStorage.clear();
  window.location.href = '/';
}

// 1. Cargar Estado Departamental
async function cargarTableroDepartamental() {
  const mes = document.getElementById('select-mes-admin').value || 'AGOSTO';
  
  try {
    const res = await fetch(`/api/estado/${mes}`);
    if (!res.ok) throw new Error("Error consultando estado departamental");
    
    const data = await res.json();
    datosDepartamentales = data.detalle || [];

    document.getElementById('metric-radicados').textContent = data.radicados;
    document.getElementById('metric-radicados-sub').textContent = `${data.porcentaje_avance}% del departamento`;
    document.getElementById('metric-pendientes').textContent = data.pendientes;

    renderizarGrillaAdmin();
  } catch (err) {
    console.error("Error cargando tablero departamental:", err);
  }
}

function filtrarMunicipios(tipo) {
  filtroActual = tipo;
  
  const btnT = document.getElementById('btn-f-todos');
  const btnR = document.getElementById('btn-f-radicados');
  const btnP = document.getElementById('btn-f-pendientes');

  [btnT, btnR, btnP].forEach(b => {
    b.className = "px-3.5 py-1.5 rounded-xl text-slate-700 hover:bg-white transition";
  });

  if (tipo === 'todos') {
    btnT.className = "px-3.5 py-1.5 rounded-xl bg-white text-slate-950 shadow-sm border border-slate-300 font-black";
  } else if (tipo === 'radicados') {
    btnR.className = "px-3.5 py-1.5 rounded-xl bg-white text-emerald-900 shadow-sm border border-emerald-300 font-black";
  } else {
    btnP.className = "px-3.5 py-1.5 rounded-xl bg-white text-rose-900 shadow-sm border border-rose-300 font-black";
  }

  renderizarGrillaAdmin();
}

function renderizarGrillaAdmin() {
  const grid = document.getElementById('grid-municipios-admin');
  grid.innerHTML = '';

  const listaFiltrada = datosDepartamentales.filter(m => {
    if (filtroActual === 'radicados') return m.estado === 'RADICADO';
    if (filtroActual === 'pendientes') return m.estado !== 'RADICADO';
    return true;
  });

  listaFiltrada.forEach(m => {
    const card = document.createElement('div');
    const isRad = m.estado === 'RADICADO';

    card.className = `p-5 rounded-3xl border-2 ${isRad ? 'bg-white border-emerald-300 hover:border-emerald-600' : 'bg-slate-50 border-slate-300'} space-y-3 shadow-sm transition flex flex-col justify-between`;

    card.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-mono font-black text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-300">
            DANE: ${m.dane}
          </span>
          <span class="text-[10px] px-3 py-1 rounded-full font-black ${isRad ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-rose-100 text-rose-900 border border-rose-300'}">
            ${isRad ? '✓ RADICADO' : '⏳ PENDIENTE'}
          </span>
        </div>

        <div>
          <h4 class="text-base font-black text-slate-900">${m.municipio}</h4>
          ${isRad ? `
            <div class="text-xs font-mono font-bold text-emerald-800 mt-1">${m.numero_radicado}</div>
            <div class="text-[11px] font-bold text-slate-500">${m.fecha_radicacion}</div>
          ` : `
            <div class="text-xs font-bold text-rose-700 mt-1">Sin radicación oficial</div>
            <div class="text-[11px] font-bold text-slate-500">Pendiente de cargue</div>
          `}
        </div>

        <div class="pt-2 border-t-2 border-slate-100 flex items-center justify-between text-xs font-mono">
          <span class="text-slate-600 font-bold">Dosis:</span>
          <span class="font-black ${isRad ? 'text-emerald-900' : 'text-slate-400'} text-sm">${isRad ? m.dosis_aplicadas.toLocaleString() : '0'}</span>
        </div>
      </div>

      ${isRad ? `
        <button onclick="inspeccionarMunicipio('${m.municipio}')" class="w-full mt-3 py-2 px-3 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-900 border border-indigo-200 text-xs font-black transition flex items-center justify-center gap-1.5">
          <svg class="w-4 h-4 text-indigo-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
          <span>Inspeccionar y Descargar</span>
        </button>
      ` : `
        <div class="w-full mt-3 py-2 text-center text-[11px] font-bold text-slate-400 bg-slate-100 rounded-xl border border-slate-200">
          Esperando reporte
        </div>
      `}
    `;

    grid.appendChild(card);
  });
}

// 2. Inspección de Informes de un Municipio
async function inspeccionarMunicipio(municipio) {
  const mes = document.getElementById('select-mes-admin').value || 'AGOSTO';
  const modal = document.getElementById('modal-inspeccion');
  const titulo = document.getElementById('modal-insp-titulo');
  const contenido = document.getElementById('modal-insp-contenido');

  titulo.textContent = `${municipio} — ${mes} 2026`;
  contenido.innerHTML = '<div class="text-center py-6 font-bold text-slate-500">Cargando detalles del informe...</div>';
  modal.classList.remove('hidden');

  try {
    const res = await fetch(`/api/admin/inspeccionar/${municipio}/${mes}`);
    if (!res.ok) throw new Error("No se pudo cargar la información del radicado");
    
    const data = await res.json();
    const rec = data.recibo;
    const desc = data.descargas_archivos;

    contenido.innerHTML = `
      <div class="space-y-4">
        
        <!-- Tarjeta de Recibo -->
        <div class="p-4 rounded-2xl bg-emerald-50 border-2 border-emerald-300 text-xs font-mono font-bold space-y-1.5">
          <div class="text-emerald-950 font-black text-sm">RADICADO OFICIAL: ${rec.numero_radicado}</div>
          <div class="text-slate-700">Fecha y Hora de Entrega: ${rec.fecha}</div>
          <div class="text-indigo-900">Google Drive: Sincronizado a ${rec.google_drive ? rec.google_drive.correo : 'risaraldapaiweb@gmail.com'}</div>
          <div class="text-[10px] text-slate-500">Carpeta: ${rec.google_drive ? rec.google_drive.carpeta : 'PAI_RISARALDA_2026/' + mes + '/' + municipio}</div>
        </div>

        <!-- Métricas Auditadas -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div class="text-[10px] font-black uppercase text-slate-500">Dosis Aplicadas</div>
            <div class="text-lg font-black text-slate-900">${rec.metricas.dosis_aplicadas_nacionales.toLocaleString()}</div>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div class="text-[10px] font-black uppercase text-slate-500">Dosis Movimiento</div>
            <div class="text-lg font-black text-slate-900">${rec.metricas.dosis_movimiento_total.toLocaleString()}</div>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div class="text-[10px] font-black uppercase text-slate-500">Pérdidas Lotes</div>
            <div class="text-lg font-black text-amber-800">${rec.metricas.dosis_perdidas_total.toLocaleString()}</div>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <div class="text-[10px] font-black uppercase text-slate-500">Extranjeros</div>
            <div class="text-lg font-black text-blue-900">${rec.metricas.vacunados_extranjeros.toLocaleString()}</div>
          </div>
        </div>

        <!-- Descargas de Archivos Originales Subidos por el Municipio -->
        <div class="space-y-2 pt-2 border-t-2 border-slate-100">
          <h4 class="text-xs font-black uppercase text-slate-800 tracking-wider">Descargar Archivos Originales del Municipio:</h4>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            ${desc.DOSIS ? `
              <a href="${desc.DOSIS}" class="p-3 rounded-xl bg-white border-2 border-slate-200 hover:border-emerald-600 text-xs font-black flex items-center justify-between shadow-sm transition">
                <span>💉 Dosis Aplicadas</span>
                <span>⬇️</span>
              </a>
            ` : ''}
            ${desc.MOVIMIENTO ? `
              <a href="${desc.MOVIMIENTO}" class="p-3 rounded-xl bg-white border-2 border-slate-200 hover:border-blue-600 text-xs font-black flex items-center justify-between shadow-sm transition">
                <span>🧬 Movimiento PAI</span>
                <span>⬇️</span>
              </a>
            ` : ''}
            ${desc.EXTRANJEROS ? `
              <a href="${desc.EXTRANJEROS}" class="p-3 rounded-xl bg-white border-2 border-slate-200 hover:border-amber-600 text-xs font-black flex items-center justify-between shadow-sm transition">
                <span>🌍 Extranjeros</span>
                <span>⬇️</span>
              </a>
            ` : ''}
          </div>
        </div>

      </div>
    `;

  } catch (err) {
    contenido.innerHTML = `<div class="p-4 rounded-xl bg-rose-100 text-rose-900 font-bold text-xs">${err.message}</div>`;
  }
}

function cerrarModalInspeccion() {
  document.getElementById('modal-inspeccion').classList.add('hidden');
}

// 3. Ejecutar Consolidación Departamental MinSalud en 1 Clic
async function ejecutarConsolidacionDepartamental() {
  const mes = document.getElementById('select-mes-admin').value || 'AGOSTO';
  const btn = document.getElementById('btn-consolidar');
  const boxDescargas = document.getElementById('box-descargas');

  btn.disabled = true;
  btn.innerHTML = '<span>⏳ Consolidando 14 municipios...</span>';

  try {
    const res = await fetch(`/api/consolidar/${mes}`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error en la consolidación");
    }

    const data = await res.json();

    document.getElementById('btn-dl-dosis').href = data.descargas.dosis;
    document.getElementById('btn-dl-mov').href = data.descargas.movimiento;
    document.getElementById('btn-dl-ext').href = data.descargas.extranjeros;

    boxDescargas.classList.remove('hidden');
    boxDescargas.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert("Error al consolidar: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Consolidar Risaralda en 1 Clic</span>';
  }
}
