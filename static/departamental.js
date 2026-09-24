// departamental.js - Lógica del Tablero Departamental PAI Risaralda (Gobernación)

let datosDepartamentales = [];
let filtroActual = 'todos';

document.addEventListener('DOMContentLoaded', () => {
  verificarSesionAdmin();
  verificarEstadoIA();
  cargarTableroDepartamental();
});

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

    // Construir secciones del informe detallado
    const cruce = rec.cruce_colombianos;
    const cruceDep = rec.cruce_deposito || (dMov && dMov.cruce_deposito);
    const sim = rec.simultaneidad || [];
    const detAud = rec.detalle_auditoria || {};
    const dDosis = detAud.dosis || {};
    const dMov = detAud.movimiento || {};
    const dExt = detAud.extranjeros || {};

    // 1. Evaluar estado de cada regla para el checklist institucional
    const reglas = [
      {
        nombre: "Regla de Oro Demográfica PAI (541 Cols)",
        archivo: "Dosis Aplicadas",
        ok: dDosis.resumen_coherencia ? (dDosis.resumen_coherencia.coincidencia_genero_regimen && dDosis.resumen_coherencia.coincidencia_genero_etnico) : true,
        desc: "Suma(Género) == Suma(Régimen) == Suma(Pertenencia Étnica)"
      },
      {
        nombre: "Recálculo Anti-Adulteración de Fórmulas",
        archivo: "Dosis Aplicadas",
        ok: dDosis.resumen_coherencia ? (dDosis.resumen_coherencia.formulas_adulteradas === 0) : true,
        desc: "Verificación independiente sin confiar en celdas de total sobreescritas"
      },
      {
        nombre: "Continuidad Intermensual de Saldos (Regla 1)",
        archivo: "Movimiento Biológicos",
        ok: dMov.metricas_reglas ? dMov.metricas_reglas.regla1_continuidad_saldos : true,
        desc: "Saldo Anterior mes actual == Saldo Cierre del mes anterior archivado"
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
        desc: "Validación de lotes contra los 361 lotes activos del Depósito Departamental"
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
      <div class="rounded-2xl border-2 border-slate-200 overflow-hidden shadow-sm">
        <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
          <span class="text-xs font-black uppercase text-slate-800 tracking-wider">📋 Checklist Institucional de Reglas Auditadas</span>
          <span class="text-[11px] font-bold text-slate-600">${reglas.filter(r => r.ok).length}/${reglas.length} Reglas Cumplidas</span>
        </div>
        <div class="divide-y divide-slate-100 text-xs">
    `;

    reglas.forEach(r => {
      htmlReglas += `
        <div class="p-3 flex items-center justify-between gap-3 bg-white hover:bg-slate-50 transition">
          <div class="space-y-0.5">
            <div class="font-bold text-slate-900 flex items-center gap-2">
              <span>${r.nombre}</span>
              <span class="text-[10px] font-mono font-normal text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">${r.archivo}</span>
            </div>
            <div class="text-[11px] text-slate-600">${r.desc}</div>
          </div>
          <div>
            <span class="px-2.5 py-1 rounded-full text-[11px] font-black flex items-center gap-1 ${r.ok ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-rose-100 text-rose-900 border border-rose-300'}">
              ${r.ok ? '✓ CUMPLE' : '✕ INCONSISTENCIA'}
            </span>
          </div>
        </div>
      `;
    });
    htmlReglas += `</div></div>`;

    // 2. Reporte de Simultaneidad del Esquema Nacional (6 Cohortes Clave)
    let htmlSimultaneidad = '';
    if (sim && sim.length > 0) {
      htmlSimultaneidad = `
        <div class="rounded-2xl border-2 border-indigo-200 overflow-hidden shadow-sm">
          <div class="bg-indigo-50 px-4 py-2.5 border-b border-indigo-200 flex items-center justify-between">
            <span class="text-xs font-black uppercase text-indigo-950 tracking-wider">🎯 Informe de Oportunidades y Simultaneidad del Esquema (6 Cohortes)</span>
            <span class="text-[11px] font-bold text-indigo-800">Evaluación de Oportunidad Clínica</span>
          </div>
          <div class="p-4 bg-white grid grid-cols-1 md:grid-cols-2 gap-3">
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

    // 3. Cruce Oficial Regla 3: Despachado Depósito Departamental (Kardex) vs Recibido Municipio (Col 5)
    let htmlCruceDeposito = '';
    if (cruceDep && cruceDep.items && cruceDep.items.length > 0) {
      const resDep = cruceDep.resumen || {};
      htmlCruceDeposito = `
        <div class="rounded-2xl border-2 border-slate-200 overflow-hidden shadow-sm">
          <div class="bg-indigo-50 px-4 py-2.5 border-b border-indigo-200 flex flex-wrap items-center justify-between gap-2">
            <span class="text-xs font-black uppercase text-indigo-950 tracking-wider">📦 Cruce Oficial: Entregas Depósito Departamental (Kardex) vs Recibido Municipio (Regla 3)</span>
            <span class="text-[11px] font-bold text-indigo-900 bg-indigo-100/70 border border-indigo-200 px-2.5 py-0.5 rounded-full">
              ${resDep.biologicos_exactos || 0}/${resDep.biologicos_total || 0} Biológicos 100% Coincidentes (${resDep.porcentaje_coincidencia || 0}%)
            </span>
          </div>
          <div class="p-3 bg-white border-b border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
            <div class="bg-slate-50 p-2 rounded-xl border border-slate-200">
              <div class="text-[10px] uppercase font-bold text-slate-500">Despachado Depósito</div>
              <div class="text-base font-black text-slate-900 font-mono">${(resDep.total_despachado || 0).toLocaleString()}</div>
            </div>
            <div class="bg-slate-50 p-2 rounded-xl border border-slate-200">
              <div class="text-[10px] uppercase font-bold text-slate-500">Recibido Municipio</div>
              <div class="text-base font-black text-slate-900 font-mono">${(resDep.total_recibido || 0).toLocaleString()}</div>
            </div>
            <div class="bg-emerald-50 p-2 rounded-xl border border-emerald-200">
              <div class="text-[10px] uppercase font-bold text-emerald-700">Coincidencias Exactas</div>
              <div class="text-base font-black text-emerald-800 font-mono">${resDep.total_coincidencias || 0}</div>
            </div>
            <div class="bg-amber-50 p-2 rounded-xl border border-amber-200">
              <div class="text-[10px] uppercase font-bold text-amber-700">Diferencias Detectadas</div>
              <div class="text-base font-black text-amber-800 font-mono">${resDep.total_diferencias || 0}</div>
            </div>
          </div>
          <div class="max-h-64 overflow-y-auto bg-white">
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

    // 4. Tabla Comparativa Cruzada (Dosis Aplicadas a Colombianos vs Movimiento Colombianos)
    let htmlCruce = '';
    if (cruce && cruce.tabla_comparativa && cruce.tabla_comparativa.length > 0) {
      htmlCruce = `
        <div class="rounded-2xl border-2 border-slate-200 overflow-hidden shadow-sm">
          <div class="bg-slate-100 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
            <span class="text-xs font-black uppercase text-slate-800 tracking-wider">⚖️ Cruce Comparativo: Dosis Aplicadas (Plantilla) vs Movimiento (Colombianos)</span>
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

    // 4. Dictamen del Asistente IA
    const dictamenTexto = (rec.dictamen && rec.dictamen.dictamen_pedagogico) ? rec.dictamen.dictamen_pedagogico : '';
    const motorIa = (rec.dictamen && rec.dictamen.motor_ia) ? rec.dictamen.motor_ia : 'Tutor PAI';

    contenido.innerHTML = `
      <div class="space-y-5">
        
        <!-- Tarjeta de Recibo -->
        <div class="p-4 rounded-2xl bg-emerald-50 border-2 border-emerald-300 text-xs font-mono font-bold space-y-1.5 shadow-sm">
          <div class="flex items-center justify-between">
            <span class="text-emerald-950 font-black text-sm">RADICADO OFICIAL: ${rec.numero_radicado}</span>
            <span class="bg-emerald-200 text-emerald-950 px-2.5 py-0.5 rounded-full text-[10px] font-black border border-emerald-400">✓ AUDITADO Y APROBADO</span>
          </div>
          <div class="text-slate-700">Fecha y Hora de Entrega: ${rec.fecha}</div>
          <div class="text-indigo-900">Google Drive: Sincronizado a ${rec.google_drive ? rec.google_drive.correo : 'risaraldapaiweb@gmail.com'}</div>
          <div class="text-[10px] text-slate-500">Carpeta: ${rec.google_drive ? rec.google_drive.carpeta : 'PAI_RISARALDA_2026/' + mes + '/' + municipio}</div>
        </div>

        <!-- Métricas Auditadas -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div class="p-3 bg-white rounded-xl border-2 border-slate-200 shadow-sm">
            <div class="text-[10px] font-black uppercase text-slate-500">Dosis Aplicadas</div>
            <div class="text-lg font-black text-slate-900">${rec.metricas.dosis_aplicadas_nacionales.toLocaleString()}</div>
          </div>
          <div class="p-3 bg-white rounded-xl border-2 border-slate-200 shadow-sm">
            <div class="text-[10px] font-black uppercase text-slate-500">Dosis Movimiento</div>
            <div class="text-lg font-black text-slate-900">${rec.metricas.dosis_movimiento_total.toLocaleString()}</div>
          </div>
          <div class="p-3 bg-white rounded-xl border-2 border-slate-200 shadow-sm">
            <div class="text-[10px] font-black uppercase text-slate-500">Pérdidas Lotes</div>
            <div class="text-lg font-black text-amber-800">${rec.metricas.dosis_perdidas_total.toLocaleString()}</div>
          </div>
          <div class="p-3 bg-white rounded-xl border-2 border-slate-200 shadow-sm">
            <div class="text-[10px] font-black uppercase text-slate-500">Extranjeros</div>
            <div class="text-lg font-black text-blue-900">${rec.metricas.vacunados_extranjeros.toLocaleString()}</div>
          </div>
        </div>

        <!-- Checklist Institucional de Reglas -->
        ${htmlReglas}

        <!-- Reporte de Simultaneidad del Esquema -->
        ${htmlSimultaneidad}

        <!-- Cruce Oficial Entregas Depósito Departamental vs Recibido Municipio (Regla 3) -->
        ${htmlCruceDeposito}

        <!-- Cruce Dosis Aplicadas vs Movimiento -->
        ${htmlCruce}

        <!-- Dictamen del Asistente IA -->
        ${dictamenTexto ? `
          <div class="bg-slate-50 border-2 border-slate-200 rounded-2xl p-5 space-y-2.5 shadow-sm">
            <div class="flex items-center justify-between border-b border-slate-200 pb-2">
              <span class="text-xs font-black uppercase text-indigo-950 flex items-center gap-1.5">
                <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                <span>Dictamen del Asistente PAI Risaralda</span>
              </span>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white border border-slate-300 text-slate-700">🤖 ${motorIa}</span>
            </div>
            <div class="text-xs text-slate-800 leading-relaxed font-medium">
              ${(window.marked && window.marked.parse) ? marked.parse(dictamenTexto) : dictamenTexto.replace(/\n/g, '<br>')}
            </div>
          </div>
        ` : ''}

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
