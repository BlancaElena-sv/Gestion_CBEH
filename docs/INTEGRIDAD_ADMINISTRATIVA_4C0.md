# Bloque 4C.0 — Integridad de usuarios y promoción

Base aprobada: `a8e055e`. Rama: `refactor/demo-homologacion`.
Esta intervención no incluye homologación visual ni Finanzas.

## Causas confirmadas

1. El formulario de usuarios escribía dos veces consecutivas el mismo diccionario mediante `set(..., merge=True)`. Era una duplicación del código, no una necesidad de Streamlit.
2. Las protecciones de usuario propio y superadministrador no comprobaban la existencia de otro administrador activo al cambiar roles. Una comprobación aislada antes del guardado tampoco resolvería las carreras entre administradores.
3. Promoción incrementaba los contadores antes de ejecutar `update`. Un fallo podía dejar una cifra de éxito incorrecta.
4. El historial de promoción se construía a partir de la consulta inicial de la pantalla y se reemplazaba después sin relectura transaccional. Una edición concurrente podía perderse.

## Usuarios: protocolo transaccional

`integrity_service.mutate_user` centraliza creación/actualización, baja, reactivación y eliminación. Las cuatro rutas de gestión en Configuración utilizan este servicio; no hay fallback a escrituras directas.

Antes de iniciar, se conserva la autorización DEMO existente. Dentro de la transacción se vuelve a leer la cuenta del actor y se exige `activo is True` y `rol == 'admin'`. Un cambio concurrente de sus permisos provoca conflicto/reintento o denegación.

Cada mutación lee:

- El administrador que realiza la operación.
- El documento común `_integrity/administradores`.
- El usuario afectado.
- Los usuarios con `rol == 'admin'` y `activo == True`.

Se calcula el conjunto resultante antes de escribir; debe quedar al menos un administrador activo. Se mantienen además las prohibiciones anteriores de autoeliminación, autobaja y modificación no autorizada del superadministrador. No se introducen roles nuevos.

La transacción escribe una revisión nueva del documento común y **una sola mutación del usuario**, o no escribe nada si el estado solicitado ya coincide. El documento común fuerza un conflicto entre cambios concurrentes, incluso cuando sus usuarios afectados son distintos y el documento de coordinación todavía no existe. El SDK reintenta leyendo el estado vigente. No se almacena un conteo de administradores que pueda desactualizarse.

### Justificación del documento adicional

`_integrity/administradores` contiene únicamente `revision`, un entero. Es metadato de coordinación; no contiene credenciales ni datos personales. Se crea dentro de la primera mutación válida, atómicamente con ella: no requiere migración, inicialización remota, reseteo ni cambios de la conexión Firebase. El esquema de los documentos existentes de usuarios permanece intacto.

Si no hay soporte transaccional, no se puede leer/escribir ese documento o su revisión es inválida, la operación falla cerrada. No se ejecuta una escritura alternativa. Todas las escrituras futuras de gestión de usuarios deben respetar este mismo protocolo.

La generación y verificación bcrypt de `auth.py` no se modificaron. Los campos existentes, incluido `id_docente`, y el estado de una cuenta inactiva se conservan al editarla. La pantalla mantiene los mismos formularios, botones, validaciones y confirmaciones.

Una acción de formulario produce una mutación lógica: usuario y coordinación se confirman en un commit. Esto supone dos escrituras de documentos cuando hay cambios, no dos guardados del usuario. Un reintento interno del SDK no produce commits duplicados. La prueba de interfaz comprueba además que una reejecución de Streamlit no vuelve a enviar el formulario.

## Promoción: transacción por estudiante

`promotion_service.promote_student` relee y revalida dentro de la transacción el actor y el alumno seleccionado por su ID real de documento. Comprueba grado, estado Activo, ciclo de origen y ausencia de un cierre anterior para ese ciclo. El historial debe ser una lista de objetos; los formatos incompatibles se bloquean sin reinterpretarlos ni sobrescribirlos.

El nuevo historial se construye con la lectura vigente. Historial, grado, turno, estado, ciclo y metadatos de cierre se actualizan en **un único documento y un único commit**. Una modificación concurrente del alumno provoca conflicto y relectura; una promoción competidora ya confirmada se reconoce y rechaza.

No se escribe en notas, asistencia, finanzas, cargas ni otras colecciones académicas. Las reglas anteriores de repetición, graduación y cambio vespertino de Cuarto a Quinto permanecen iguales. La comparación con el código de `a8e055e` confirmó igualdad del diccionario completo para 72 combinaciones de grado, decisión y turno. Se conserva el tratamiento previo de alumnos sin ciclo explícito: pertenecen al origen solicitado; no se migran.

### Resultados y recuperación

La pantalla cuenta resultados únicamente después de que la llamada transaccional confirme el commit:

- Promovidos, no promovidos y graduados confirmados.
- Omitidos por selección `No procesar`, sin escritura del alumno.
- Rechazados: duplicados, cambios de alcance/estado/ciclo, autorización revocada, datos incompatibles o decisiones inválidas.
- Errores de escritura o de confirmación: no se presentan como éxitos.

Los alumnos excluidos por ciclo o ya procesados no vuelven a entrar en la selección. Los historiales incompatibles generan una advertencia y quedan fuera del procesamiento.

No hay atomicidad global: un lote es una secuencia de transacciones independientes por alumno. Los éxitos previos no se revierten cuando otro alumno falla. El resumen parcial permanece visible; se eliminó el `rerun` automático que lo descartaba. Esto es una corrección de información al usuario, no un rediseño.

Estrategia segura: recargar la selección antes de reintentar; los alumnos confirmados quedan excluidos por su ciclo/historial, mientras que los pendientes se vuelven a validar. Ante pérdida de respuesta después de un commit, se informa que no se pudo confirmar: no se suma como éxito ni se supone que hubo rollback. La siguiente lectura y el historial permiten conciliar el resultado; reintentar no duplica el cierre. No se intenta una compensación destructiva.

## Pruebas

La suite automática conserva las 138 pruebas previas y añade pruebas de servicio e interfaz con simulación optimista de transacciones: control de versiones, commits atómicos, conflictos, reintentos, fallos y confirmaciones perdidas. No se parchea la autorización para simular permisos concedidos.

Cobertura añadida: último administrador, bajas/eliminaciones concurrentes, degradaciones simultáneas, creación y actualización única, preservación de vínculos y cuentas inactivas, errores sin cambios parciales, reejecución de formulario, bcrypt, docente denegado, permisos revocados antes del commit, duplicados de promoción, historial concurrente, ciclos anteriores, repetición/graduación/turnos, estados obsoletos, omisiones y contadores de resultados parciales.

**Resultado final: 178 pruebas aprobadas** (138 anteriores y 40 nuevas), sin omisiones, en 59,917 segundos. Las seis pruebas adicionales del emulador también aprobaron. Compilación de fuentes, comprobación de dependencias y `git diff --check`: correctos.

Comando de la suite:

```bash
python -m unittest discover -s tests
```

También se utilizó Firestore Emulator 1.19.8, Java 21, en `127.0.0.1:8787`. Las seis pruebas de integración utilizan el SDK real y `AnonymousCredentials`: último administrador, degradación concurrente, creación/guardado idempotente, promoción repetida, promoción simultánea y escritura concurrente de historial. El ejecutable exige exactamente ese endpoint local y aborta si no está configurado; no busca credenciales ni tiene fallback remoto.

```bash
FIRESTORE_EMULATOR_HOST=127.0.0.1:8787 python tests/emulator_integrity.py
```

Los documentos de integración son ficticios (`integrity-*`) y existen únicamente en el emulador local. No se ejecutan reseteos ni se utilizan datos reales. El JAR del emulador y los registros son herramientas temporales fuera del repositorio; no se añadieron dependencias de ejecución.

No se declara comparación visual con producción: este bloque no cambia estilos ni distribución. Las pruebas AppTest verifican renderizado, confirmaciones y mensajes de ambos formularios; la homologación visual del Bloque 4C sigue pendiente.

## Límites y operaciones bloqueadas

- La garantía del último administrador depende de que todos los escritores de gestión de usuarios utilicen el protocolo común. Acceso manual al Admin SDK, herramientas externas o versiones antiguas que lo omitan no quedan controlados por este código. No se modificaron IAM ni reglas remotas.
- No se probaron disponibilidad, latencia, cuotas o índices de Firebase remoto. Un conflicto que agote los reintentos queda como error pendiente; no habilita guardados directos.
- El lote de promoción no dispone de un commit global ni de un registro persistente del resumen de pantalla. El documento del alumno y su historial confirmado son la fuente de conciliación por estudiante.
- Un historial incompatible, un documento de coordinación inválido, una sesión revocada o una infraestructura sin transacciones mantienen bloqueada la escritura afectada. No se reparan datos automáticamente.
- El reseteo de base de datos sigue bloqueado por el despachador existente. No se ejecutaron herramientas de borrado ni scripts de creación/migración.

Archivos modificados: `views/configuracion.py`, `views/promocion.py`.
Añadidos: `integrity_service.py`, `promotion_service.py`, `tests/test_integrity_transactions.py`, `tests/emulator_integrity.py` y este documento.

Permanecen intactos la autenticación, conexión Firebase, permisos generales, roles, estilos, dashboards y los módulos del Bloque 4B. `main` y `demo-comercial` no se modificaron. No hubo operaciones remotas, migraciones, reseteos, despliegues ni push. El trabajo se detiene antes de retomar la homologación visual del Bloque 4C.
