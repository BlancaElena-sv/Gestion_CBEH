# Bloque 4A — Homologación académica

Base: 2ac4131. Referencia visual: main en c6b48c0.
Rama: refactor/demo-homologacion.

**Cierre con una salvedad:** Alumnos queda parcialmente homologado. La revisión
final detecta que baja/reactivación/eliminación están dentro de Historial
Académico en DEMO. Se detiene la intervención sobre esa distribución reservada,
sin modificarla ni cambiar reglas de negocio; requiere aprobación específica.

## Alcance y orden de trabajo

1. Inscripción: cambio visual, pruebas completas y Chromium.
2. Consulta y gestión de alumnos: cambio visual, pruebas completas y Chromium.
3. Maestros/cargas: verificación de equivalencia existente, regresiones y Chromium.
4. Asistencia administrativa/docente: verificación de equivalencia existente,
   regresiones y Chromium.

Se conserva código que ya produce la presentación de main. No se reemplazan
archivos completos ni se adaptan consultas de producción. Los cambios de código
se limitan a views/inscripcion.py y views/alumnos.py; no fue necesario modificar
views/docentes.py, views/asistencia.py ni views/docente_panel.py.

## Inscripción

- Encabezado sin el icono adicional de DEMO, mismo estilo de main y ciclo tomado
  de CICLO_LECTIVO: la demo no muestra el literal heredado «2026».
- Botón y mensaje de campos obligatorios iguales a producción.
- Se conservan las tres comprobaciones obligatorias, strip, duplicado de NIE,
  listas de grados/turnos, archivos admitidos, esquema anidado encargado y
  documentos, estado activo y SERVER_TIMESTAMP.
- Regresiones: cada campo obligatorio, NIE duplicado, registro simulado válido,
  esquema anidado y rechazo del rol docente.

## Alumnos

- Se alinean el icono de maestro guía, etiqueta de documentos y pestaña Estado
  y Baja con la referencia.
- Campos de contacto ausentes muestran texto vacío en lugar de None, solo en
  presentación. No se aplanan ni reescriben datos de Firebase.
- Se conservan las búsquedas, filtros, edición, estados, confirmaciones,
  documentos actuales y doc_url legacy. No se modifica ninguna consulta,
  escritura, eliminación ni diccionario de persistencia.
- Regresiones: búsqueda inexistente/existente, filtro por grado, ficha, edición
  anidada y copia de sesión, rechazo de eliminación sin confirmación y enlace
  a documento legacy. Las escrituras y eliminaciones probadas son simuladas.
- Finanzas, boletas y contenidos históricos permanecen sin homologar. La etiqueta
  Historial Académico conserva su icono DEMO porque esa sección queda reservada.
  En DEMO, el bloque de baja/reactivación/eliminación está dentro de tabs[6]
  (Historial Académico), mientras en main está en tabs[5] (Estado y Baja).
  Es una discrepancia relevante de distribución y navegación existente. Se
  detiene la intervención sobre esa parte por la exclusión explícita de históricos.
  No se mueve el bloque ni se cambia su lógica. Incluso la etiqueta del botón
  Reactivar se mantiene intacta para no modificar el contenido reservado.
  Requiere aprobación específica para recolocar esos controles y verificar ambos
  tabs. Por este motivo Alumnos NO se declara completamente homologado.

## Maestros y cargas

La estructura existente ya coincide con main: formulario de alta, tarjeta de
perfil, edición, pestañas, columnas de asignación y carga actual, multiselect,
expansores, validación de materias y mensajes vacíos. No se cambia su código.

Regresiones: nombre obligatorio, alta, edición conservando ID documental,
rechazo de carga sin materias, guardado de lista de materias/id_docente/ciclo y
eliminación exclusiva de una carga simulada. El perfil financiero no se homologa.

## Asistencia

Los controles, columnas, editor, estados de asistencia, botones, tabla, mensajes
y distribución ya coinciden con main. Se conservan los timestamps Firestore,
los cálculos administrativos y TeacherStore sin cambios.

Regresiones: rango invertido, alumnos ausentes, registros ausentes, totales y
observaciones, editor docente limitado al grado asignado y persistencia simulada
en el ciclo actual. Los controles anteriores de permisos por materia/grado/ciclo
siguen incluidos en la suite completa.

## Método visual

Chromium local, 1440 × 1000 y 390 × 844, escala 1 y tema claro. Se usa un harness
externo a la aplicación en /workspace/work/visual-block4a, con copias de las
vistas main y las vistas reales de DEMO. La referencia usa respuestas simuladas
con campos planos; DEMO conserva Firestore simulado y sus campos anidados.
No se carga la configuración ni el servicio Supabase de producción.

Los registros ficticios representan a los mismos alumnos, docentes, grados,
materias y ciclo. Se normalizan formatos de fecha en el doble de referencia y
se utiliza una fecha fija del ciclo DEMO para asistencia. La comparación docente
usa datos equivalentes dentro del alcance autorizado; no se amplían permisos
para reproducir consultas más generales de main.

Se capturan formularios, ficha, edición, tablas y estados de validación/vacíos;
no se limita la comprobación a las pantallas iniciales. Las máscaras excluyen
logo/textos de identidad del sidebar y, en inscripción, el encabezado cuyo ciclo
difiere del literal de producción. No se ocultan campos, botones ni validaciones.
Se calcula el porcentaje de píxeles con diferencia superior a 12 niveles por
canal RGB. Se inspeccionan capturas de fichas/formularios/reportes en ambos tamaños.

## Regresiones por etapa

| Etapa | Suite completa |
|---|---:|
| Inscripción | 80 aprobadas |
| Alumnos | 85 aprobadas |
| Maestros/cargas | 91 aprobadas |
| Asistencia | 96 aprobadas |

Se mantienen las 75 pruebas anteriores y se añaden 21. No se añaden dependencias.
Las operaciones nuevas de prueba se ejecutan exclusivamente sobre diccionarios
en memoria, con sockets bloqueados en las pruebas automatizadas. Chromium
bloquea las solicitudes HTTP externas en el harness de comparación.

## Límites y riesgos pendientes

- La equivalencia se verifica en estados concretos, no en todos los recorridos
  posibles de cada módulo. No se declara homologación completa de sus pestañas
  financieras, históricas, boletas o procesos de eliminación definitiva.
- Storage y previsualización remota de adjuntos no se prueban contra servicios
  reales. Se conserva la compatibilidad con documentos existentes, pero no se
  certifica el contenido de visores externos ni subidas reales.
- Los fallos de infraestructura real, permisos IAM, índices y persistencia remota
  siguen pendientes del entorno Firebase seguro autorizado.
- No se modifican reglas de negocio: los formatos nested/flat y fechas se
  adaptan únicamente en los dobles utilizados para comparar main con Firebase.
- La edición de nombres docentes mantiene el comportamiento previo; las cuentas
  legacy vinculadas solo por nombre pueden requerir revisar su vínculo existente.
  No se cambia autorización ni se migra información en este bloque.
- Las advertencias Streamlit de APIs antiguas se conservan; no se modifican los
  estilos ni dashboards del bloque 3 para resolverlas.
- Mi Perfil, expediente docente, boletas docentes y borrado masivo conservan sus
  bloqueos. No se trabaja en notas, históricos, finanzas, promoción o configuración.
- No se ejecutan migraciones, reseteos, despliegues ni push; main y demo-comercial
  permanecen intactas. Nunca se utilizan credenciales ni datos reales.


## Resultados finales de la comparación

48 pares de capturas (96 imágenes comparadas), además de las pruebas funcionales.
Detalle por caso en docs/visual-academic-comparison.json.

| Módulo | Pares escritorio/móvil | Estados revisados | Máxima diferencia de píxeles normalizada |
|---|---:|---|---:|
| Inscripción | 10 | Inicial, obligatorios, duplicado y mensajes al final del formulario | 0,000764 % |
| Alumnos | 10 | Vacío, inexistente, ficha, datos personales y edición | 0,064097 % |
| Maestros/cargas | 14 | Alta, nombre requerido, ficha, cargas, sin materias, edición y cargas vacías | 0,000764 % |
| Asistencia | 14 | Inicial, reporte, rango inválido, sin registros, sin alumnos, editor docente y vacío | 0,000764 % |

La diferencia residual de Alumnos aparece en el encabezado de pestañas con el
icono de Historial Académico que se mantiene fuera del alcance. Estas cifras
corresponden a capturas y máscaras concretas, no a la totalidad de un módulo.
Las posiciones de desplazamiento de formularios se igualan antes de comparar
mensajes inferiores, para no confundir scroll con diferencias de presentación.

Las 96 pruebas finales pasan sin omisiones, incluidas las 75 originales.
37 archivos Python compilados en memoria; pip check y git diff --check correctos.
Las llamadas de consulta/escritura/subida de ambos archivos modificados tienen
el mismo AST que en 2ac4131. Las pestañas de finanzas, boletas e históricos de
Alumnos también tienen AST idéntico a ese commit. No se cambian las protecciones,
estilos, dashboards ni módulos excluidos. Los servidores locales de comparación
se detienen al cerrar el bloque.
