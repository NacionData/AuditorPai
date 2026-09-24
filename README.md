# Sistema PAI Risaralda — Reglas del Proyecto para Antigravity

Bienvenido al proyecto **Sistema de Auditoría y Consolidación PAI Risaralda** (Secretaría de Salud Departamental de Risaralda).

## 1. Propósito
Plataforma web con IA para recepción, auditoría matemática estricta y consolidación mensual de los informes de vacunación de los 14 municipios de Risaralda:
Pereira, Dosquebradas, Santa Rosa de Cabal, La Virginia, Belén de Umbría, Apía, Balboa, Guática, La Celia, Marsella, Mistrató, Pueblo Rico, Quinchía y Santuario.

## 2. Informes y Reglas de Negocio
1. Dosis Aplicadas (Plantilla PAI):
   - Regla de Oro: Suma(Género) == Suma(Régimen) == Suma(Pertenencia Étnica).
   - Recálculo independiente de celdas de datos brutos.
2. Movimiento de Biológicos:
   - Bloques de 6 filas por ítem (filas r a r+4 para 5 lotes; fila r+5 de control).
   - Regla 1: Saldo Anterior == Saldo Siguiente del mes previo oficial archivado en el servidor.
   - Regla 2: Suma de 5 celdas de lotes == Saldo Siguiente, y celda de control Col M responde VERDADERO.
   - Regla 3: Cruce con Kardex de entregas del Depósito Departamental (Google Sheets).
   - Regla 4: Catálogo maestro de 361 lotes activos. Enriquecer laboratorio automáticamente.
   - Regla 5: Suma de 11 causas == Total Pérdidas. Vómito Franco solo para vacunas orales.
3. Vacunados Extranjeros:
   - Coherencia matricial de las 6 hojas de países contra dosis aplicadas a extranjeros.

## 3. Arquitectura y Enlaces del Proyecto
- **Portal Municipal en Producción:** [https://auditorpai-informes.up.railway.app](https://auditorpai-informes.up.railway.app)
- **Tablero Departamental (Gobernación):** [https://auditorpai-informes.up.railway.app/departamental](https://auditorpai-informes.up.railway.app/departamental)
- **Servidor Local:** FastAPI en `http://localhost:8000`
- **engine/**: Validadores matemáticos, agente IA (Gemini) y consolidador MinSalud.
- **templates_base/**: Plantillas oficiales MinSalud 2026 en blanco.
- **storage/**: Catálogos, radicados municipales y consolidados finales.
- **static/**: Portal web del municipio y Tablero Departamental (Claro Clínico Pro).

