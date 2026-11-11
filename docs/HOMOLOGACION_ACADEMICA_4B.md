# Bloque 4B — Notas, históricos, expedientes y boletas

Base: `29ccd8f`. Rama de trabajo: `refactor/demo-homologacion`.
Referencia visual: `main` / `origin/main`, `c6b48c0`.

## Alcance y cambios

Se conservaron Firebase DEMO, sus contratos, autenticación, autorización, catálogo de navegación, estilos globales y dashboards. No se modificaron reglas de evaluación, ponderaciones, redondeos ni estados académicos.

### 1. Notas administrativas y docentes

Se recuperó el respaldo mensual imprimible de producción mediante `components/academic_reports.py`, componente de presentación sin acceso a base de datos. Incluye identidad DEMO, grado, materia, ciclo, alumnos, actividades, promedio y firmas. El docente lo recibe exclusivamente desde su vista y almacén restringidos a asignaciones vigentes; no incluye datos de responsables ni contactos.

La pantalla administrativa reproduce mensajes de carga, ausencia de registros y recuperación del promedio individual cuando no hay detalle mensual. La recuperación exige el ciclo explícito actual: no se atribuyen registros sin ciclo ni de años anteriores. Cuando solo existe el promedio guardado, el respaldo conserva ese promedio y muestra «–» en actividades desconocidas; no inventa su desglose. El formulario mantiene la captura de actividades y el cálculo existente al guardar.

Correcciones indispensables para persistencia segura: detalle mensual y notas individuales se guardan en un mismo batch; los identificadores canónicos incluyen ciclo; las colisiones con documentos de otro ciclo se rechazan antes de confirmar el batch; la validación de servidor exige números finitos entre 0 y 10, igual al rango del editor. Repetir una captura actualiza los mismos identificadores. No se eliminan documentos antiguos ni se migran registros heredados. La lectura heredada del ciclo 2026 sigue disponible según el contrato previo.

Los pesos permanecen 25/25/10/10/30, con `redondear_mined`; Conducta conserva su tratamiento directo. No se sustituyen promedios guardados por ceros durante la presentación del respaldo.

### 2. Históricos

La vista existente ya sigue la organización de producción: ciclo, grado, alumno, indicadores, materias, meses, trimestres y promedio final, con impresión. Se protegieron los textos interpolados en HTML sin alterar consultas ni cálculos. Continúa siendo de solo lectura y exclusiva del administrador.

Se preserva expresamente el contrato DEMO: los registros históricos sin ciclo se interpretan como 2026. No se adopta una atribución dinámica al año actual. Las pruebas comprueban separación entre 2026 y 2027, selección vacía y ausencia de escrituras.

### 3. Expediente y alcance del maestro guía

No se habilitan `Expediente Alumnos` ni `Boletas de Notas` del docente. El bloqueo del bloque 2 sigue intacto, incluso si `es_guia` es verdadero.

| Información / operación | Administrador | Docente, incluido guía |
| --- | --- | --- |
| Captura y edición de notas vigentes | Sí | Solo grado, materia y ciclo asignados |
| Respaldo mensual de esas notas | Sí | Solo su asignación; nombre y NIE mínimos |
| Histórico completo de estudiante | Sí, lectura | Bloqueado |
| Boleta individual, anual o por lote de todas las materias | Sí | Bloqueado |
| Expediente completo, contactos, documentos y bitácora | Sí, según módulos existentes | Bloqueado |
| Información financiera | Según permisos existentes | Denegada |

La identidad docente usa `id_docente` y asignaciones del ciclo vigente mediante la autorización existente. El vínculo heredado por nombre exige coincidencia única, como antes. Una bandera de guía no amplía por sí sola el acceso a todas las materias.

Motivos del bloqueo: la bitácora consultada por NIE no proporciona un contrato seguro de ciclo, audiencia o sensibilidad; el expediente puede contener contactos, documentos y comentarios personales; la edición de cargas no garantiza un guía único por grado/ciclo. Falta definir la política ante guías ambiguos y un adaptador de lectura con proyección mínima y autorización explícita para expedientes y boletas completas. No se habilitó parcialmente un expediente inseguro.

### 4. Boletas y reportes administrativos

Se conservaron los diseños de producción para reporte anual, boletas por lote y boleta individual dentro de Consulta Alumnos. La boleta individual ahora filtra las notas por el ciclo del alumno, igual a producción; antes podía mezclar años de un mismo NIE. El encabezado impreso identifica expresamente el ciclo y el guía mostrado debe pertenecer a ese ciclo. Estos cambios no conceden permisos ni modifican calificaciones.

Se escapan los textos identificativos del HTML. El botón del reporte anual se oculta al imprimir mediante CSS local al iframe; producción lo deja visible. No se alteraron estilos globales. Las demás pestañas de Alumnos, incluido Historial Académico y Estado y Baja, conservan su código: se verificó su estructura AST contra la base.

## Archivos

Modificados: `views/notas.py`, `views/docente_panel.py`, `views/notas_historicas.py`, `views/alumnos.py`.

Añadidos: `components/academic_reports.py`, `tests/test_grades_reports.py`, `tests/test_academic_history_access.py`, este documento y `docs/visual-academic-4b-checks.json`.

## Pruebas y resultados

- Suite anterior: 105 pruebas aprobadas después de la primera adaptación.
- Notas: 121 pruebas aprobadas.
- Históricos y autorización: 131 pruebas aprobadas.
- Cierre con boletas: **138 pruebas aprobadas**, sin omisiones (57,241 segundos). Son las 105 anteriores y 33 nuevas; no se modificaron pruebas anteriores.
- Cobertura nueva: fórmulas y límites de redondeo, Conducta, valores inválidos/NaN, persistencia canónica sin duplicados, batch fallido sin escrituras parciales, colisiones y separación de ciclos, recuperación de promedios, consulta histórica sin escrituras, generación de reportes, escape HTML y protección de datos personales.
- Acceso directo docente a históricos y módulos sensibles: denegado. Ser guía o tener guías ambiguos no desbloquea expedientes ni boletas completas.
- Las operaciones de escritura usan simulaciones. Las pruebas nuevas bloquean conexiones de red; no se utilizaron datos reales.
- Compilación de fuentes Python, comprobación de dependencias y `git diff --check`: correctos.

## Comparación visual y de impresión

Chromium 156 y Streamlit 1.67, escritorio 1440×1000 y móvil 390×844. Se ejecutó la aplicación DEMO con servicios ficticios y las vistas extraídas de main con un adaptador simulado; no se arrancó producción ni se consultó Supabase. Identidad, logo y sello se normalizaron a DEMO en la referencia para comparar datos equivalentes.

| Módulo | Estados y evidencia |
| --- | --- |
| Notas administrador/docente | 20 pares: inicial, captura, respaldo, vacío y promedio sin detalle; asignatura Comunicación, pesos y promedio 9 |
| Históricos | 8 pares: inicial, ciclo vacío, ciclo 2026 con promedio 6 e impresión; ciclo actual 2027 con promedio 9 |
| Boletas administrativas | 6 pares: anual, lote e individual, ambas resoluciones; promedio 9 y ciclo actual |
| Protección docente | 8 comprobaciones adicionales: expediente/boletas, guía/no guía y ambas resoluciones; sin iframe, tabla ni datos personales |

Total: 34 pares comparativos, 8 capturas adicionales de bloqueo y 16 PDF ficticios (históricos y boletas). Se verificó la llamada a `window.print()` y el ocultamiento del botón en medio de impresión. Los PDF se generaron desde el HTML local del iframe; esto no certifica una impresora física.

Resultados estructurados en `visual-academic-4b-checks.json`. Los campos falsos del reporte de referencia documentan diferencias observadas: main no imprime el ciclo en el encabezado de la boleta individual y mantiene visible el botón del reporte anual. La DEMO corrige ambos casos.

No se declara equivalencia completa ni pixel a pixel. La boleta individual mantiene la tabla ancha de producción: en móvil exige desplazamiento y algunas columnas quedan fuera del encuadre inicial. No se rediseñó ese comportamiento. La recuperación de promedios individuales del docente conserva el contrato seguro DEMO aunque la referencia no muestre el mismo estado; las fechas de impresión DEMO utilizan la zona horaria institucional. Los históricos conservan la interpretación heredada de ciclo descrita arriba.

## Límites y pendientes

No se verificaron IAM, índices, reglas remotas, Storage ni concurrencia real contra Firebase; no se tocaron credenciales ni datos. La atomicidad y las restricciones se verificaron con dobles de prueba, no con una conexión remota. No se certifican todos los volúmenes de datos, otros navegadores, impresoras físicas o todos los casos heredados.

La ausencia de actividades detalladas no permite reconstruirlas a partir del promedio. Los expedientes y boletas completas docentes requieren el contrato de seguridad descrito antes de su habilitación. No se añadieron exportaciones distintas de la impresión/PDF ya existente.

No se modificaron `main` ni `demo-comercial`; no hubo migraciones, reseteos, despliegues o push. Finanzas, Configuración y Promoción quedan fuera de este bloque. El trabajo se detiene al cerrar este commit local.
