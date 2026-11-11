# EduManager DEMO — Informe ejecutivo de cierre comercial

Rama de entrega: `refactor/demo-homologacion`. Base: `bcd910d`.
Estado: alcance de implementación comercial completado y preparado para validación final del entorno DEMO. Sin despliegue ni push. No se certifica funcionamiento remoto que no se haya comprobado.

## Módulos terminados y verificación

| Módulo / proceso | Resultado comprobado |
| --- | --- |
| Login, dashboard y navegación | Login válido/incorrecto y cierre de sesión en Chromium; recorrido real por sidebar como administrador y docente. Autorización del servidor conservada. |
| Inscripción, alumnos, maestros y cargas, asistencia | Regresiones académicas anteriores conservadas y pantallas accesibles en el recorrido integral por rol. No se reescribieron estos módulos. |
| Notas, históricos y boletas administrativas | Se mantienen las pruebas de cálculos, ciclos, escrituras, restricciones y reportes del cierre anterior. No se alteraron fórmulas ni ponderaciones. |
| Finanzas | Presentación de main confirmada para corte, cobros, gastos, filtros, indicadores, reportes y comprobantes. Cobros y gastos con datos ficticios, validaciones, duplicados e impresión/PDF comprobados. |
| Configuración de usuarios | Se conserva la presentación de producción y la protección transaccional del último administrador. Creación, edición, roles, bajas/reactivaciones, eliminación protegida y bcrypt continúan bajo las pruebas existentes. |
| Configuración de dashboard | Avisos, títulos, estado de presentación y agenda: guardar, crear, ocultar/publicar y eliminar comprobados con simulaciones y SDK real en emulador. |
| Promoción | Presentación de producción confirmada; transacciones por alumno, históricos, ciclos, duplicados, reintentos y contadores del bloque de integridad conservados. En navegador se comprobaron selección, confirmaciones y ejecución ficticia. |
| Mi Perfil | Vista de main adaptada a Firebase: datos propios, contraseña actual/nueva con bcrypt, preferencias y fotografía. Cuenta administrativa y docente verificadas; fotografía probada con subida y descarga simuladas, nunca con Storage remoto. |

No se añadieron funciones de finanzas, reportes o evaluación que no existieran. El estado de cuenta y los informes académicos anteriores permanecen bajo su implementación y permisos existentes.

## Cambios necesarios para el cierre

### Mi Perfil

Se habilitó su destino en el catálogo centralizado; no se ampliaron los roles ni se habilitaron expedientes o boletas docentes. El servicio admite únicamente campos personales, preferencias y cambio de contraseña de la cuenta de la sesión. No permite enviar otro usuario objetivo, rol, estado activo o campos administrativos.

La contraseña actual se verifica contra el hash vigente dentro de la transacción. Los cambios concurrentes de estado, rol o vínculo docente se revalidan antes de confirmar. La lectura para la pantalla proyecta campos de presentación y no entrega el hash.

El docente se vincula por ID ya verificado o por coincidencia legacy única del nombre original. Al editarlo se conserva `id_docente` en su cuenta: evita perder la identidad y las asignaciones al cambiar el nombre personal. No se busca al maestro por el correo o nombre nuevo introducido en el formulario. La foto de usuario y maestro se confirma en la misma transacción documental. El nombre académico del maestro sigue siendo administrado en Maestros; no se cambia desde la cuenta personal.

Se admiten imágenes verificadas de hasta 5 MB. La URL debe corresponder a un bucket DEMO permitido y a `perfiles/<usuario>/`. Sin bucket configurado o si falla la subida, no se guarda una URL alternativa ni se da por guardado el perfil. No se copiaron llamadas Supabase.

### Finanzas

No se cambiaron importes mínimos del formulario, fórmulas, saldos, ciclos de pago ni la regla de duplicados. Continúa prohibido el cobro del mismo alumno/concepto en el día y el salario repetido del docente en el día; los gastos ordinarios pueden repetirse como antes.

Las escrituras releen al administrador y al alumno/docente relevante dentro de la transacción. El metadato `_integrity/finanzas` serializa las operaciones para evitar que dos comprobaciones concurrentes aprueben un duplicado. Solo contiene una revisión y se crea en la primera operación válida; no requiere migración ni altera el esquema financiero existente.

Cada envío conserva un identificador de documento durante sus reintentos y, en la sesión, hasta recibir confirmación. Si se perdió la respuesta después del commit, se recupera el movimiento confirmado en lugar de volver a escribirlo. Tras un éxito, una nueva acción sigue permitiendo un gasto ordinario legítimo. Un ID de operación no puede sobrescribir otro pago. Si la sesión se pierde tras una respuesta incierta, se debe conciliar en los reportes antes de repetir un gasto ordinario; no se promete exactamente-una-vez a través de una sesión destruida.

La búsqueda por NIE usa el campo NIE y bloquea coincidencias ambiguas, sin suponer que siempre coincide con el ID del documento. Se conservan snapshots de grado y persona, y la compatibilidad histórica de los reportes. Se escapan textos del HTML y se ocultan botones al imprimir dentro de los iframes. Los comprobantes usan identidad DEMO.

### Configuración y promoción

Los formularios, distribución y componentes de Configuración y Promoción ya seguían main; la comparación permitió conservarlos sin cambios masivos. Las escrituras de avisos y agenda ahora revalidan al administrador dentro de una transacción, incluidos los cambios de visibilidad. El helper solo dirige operaciones a presentación del dashboard o agenda, nunca a la conexión Firebase.

Los servicios de usuarios/promoción del commit `bcd910d` no se alteraron. La promoción continúa siendo atómica por estudiante, no por lote; su resumen parcial permanece visible, a diferencia del rerun de producción que lo descarta.

## Pruebas y evidencia

**Resultado final: 199 pruebas de la suite aprobadas (178 anteriores y 21 nuevas), más 9 pruebas adicionales del emulador (6 anteriores y 3 nuevas); sin omisiones.** La suite tardó 86,288 segundos y el emulador 9,795 segundos. Compilación de fuentes, dependencias y comprobación de diferencias: correctas. La suite de cierre conserva las 178 pruebas anteriores y añade las comprobaciones indispensables del nuevo alcance. Se actualizó una expectativa del catálogo: Mi Perfil pasa de bloqueado a habilitado; siguen denegados los otros módulos sensibles y los módulos administrativos al docente.

```bash
python -m unittest discover -s tests
FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 python tests/emulator_integrity.py
```

El segundo comando exige exactamente ese emulador local y usa credenciales anónimas. No busca credenciales reales ni tiene fallback remoto. El emulador utilizado fue Firestore 1.19.8 con Java 21. No se añadió una dependencia de ejecución.

Además de las regresiones previas: cobros/salarios duplicados, gastos permitidos, finitos/rango de montos, fallos sin escrituras parciales, recuperación de confirmación perdida, acceso a perfiles propios, campos administrativos rechazados, maestros ambiguos, fotografía limitada a la cuenta, contraseña bcrypt, sesión revocada, avisos y agenda, comprobantes y HTML escapado.

Chromium 156, escritorio 1440×1000 y móvil 390×844:

- 48 pares de capturas en estados iniciales, formularios, validaciones, reportes y resultados de los módulos pendientes.
- 6 pares adicionales de estados vacíos: Finanzas, agenda y Promoción.
- 16 PDF ficticios de corte, ingreso, egreso y reporte; llamada a `window.print()` y ocultamiento de botones verificados en DEMO.
- Fotografía de perfil comprobada en el navegador con adaptadores de almacenamiento y visualización locales, sin solicitar una URL remota.
- 20 comprobaciones del recorrido real por login, menú, restricciones y logout: ambos roles, 16 destinos permitidos y 2 destinos docentes bloqueados.

La referencia ejecutó las vistas extraídas de main con un adaptador de datos ficticios. No se arrancó el backend de producción ni se consultó Supabase. Se normalizaron los encabezados de impresión a DEMO; la referencia del sidebar conserva la identidad de producción. Los recursos externos del navegador estuvieron bloqueados.

La evidencia estructurada se guarda en `docs/visual-commercial-checks.json`. No se declara equivalencia píxel a píxel ni validación física de impresoras. Los estados de resultado de promoción y la impresión contienen las diferencias de seguridad descritas; no se ocultaron para declarar igualdad.

## Funciones bloqueadas y clasificación de pendientes

**CRÍTICO:** no se detectó un bloqueo crítico sin contener en el alcance local validado. La publicación no se realizó ni se certificaron servicios remotos.

**IMPORTANTE:**

- Expediente completo y boletas de todas las materias para docentes, incluidos maestros guía, siguen bloqueados. Falta el contrato seguro de alcance por ciclo, datos personales y guías ambiguos. No afecta la demostración administrativa de boletas.
- La conexión efectiva, IAM, índices y bucket del entorno Firebase DEMO requieren validación final autorizada antes de publicar. Las pruebas locales no garantizan esos recursos remotos. Sin almacenamiento configurado, las subidas se rechazan con seguridad; el resto de Mi Perfil sigue disponible.
- Cuentas docentes sin un vínculo único y activo con Maestros no pueden acceder a sus módulos protegidos, incluido Mi Perfil. No se crean vínculos ficticios para habilitarlas.
- El borrado masivo y el reseteo permanecen bloqueados. Historiales incompatibles y coordinadores transaccionales inválidos mantienen bloqueada exclusivamente su operación dependiente.

**MEJORA FUTURA:**

- Las tablas anchas de producción conservan desplazamiento horizontal en móvil; no se rediseñaron.
- Tema y notificaciones se guardan como en main; no se agregó un motor de temas ni envío de correos que producción no implementa.
- Una imagen subida antes de un fallo documental puede quedar sin referencia en el bucket. No se ejecutaron limpiezas destructivas ni se promete atomicidad entre Storage y Firestore.
- Los protocolos de coordinación requieren que escritores externos y futuras rutas de administración los respeten. No controlan modificaciones manuales mediante Admin SDK ni versiones antiguas que los omitan. La promoción mantiene conciliación por alumno, no atomicidad global.

## Archivos y estado del repositorio

Modificados: `navigation.py`, `views/finanzas.py`, `views/configuracion_dashboard.py`, `tests/test_navigation_permissions.py`, `tests/emulator_integrity.py`.

Añadidos: `views/perfil.py`, `profile_service.py`, `finance_service.py`, `tests/test_commercial_completion.py`, este informe y la evidencia JSON.

La autenticación, conexión Firebase, autorización general, reglas académicas, dashboard y estilos globales permanecen intactos. No se modificaron `main` ni `demo-comercial`. No se utilizaron datos reales, credenciales de producción o scripts de migración/reseteo. No hubo despliegue ni push.

El commit de cierre se registra localmente en la rama de trabajo. El alcance se detiene aquí, listo para revisión final y decisión de publicación del responsable.
