# Bloque 2 — Navegación y permisos

Base: c308ebc. Trabajo exclusivo en refactor/demo-homologacion.

## Arquitectura y recorrido

- `navigation.py`: catálogo único de nombres, roles, etiquetas, secciones,
  destinos y motivos de bloqueo. Sidebar y despachador consumen este catálogo.
- `authorization.py`: sesión válida, usuario existente y explícitamente activo,
  rol conocido que coincide con el documento actual, conexión edumanager-demo y
  módulo autorizado. Falla cerrado ante errores de lectura. No cachea permisos.
- `view_dispatch.py`: autorización antes de importar/renderizar la vista,
  adaptación de argumentos originales y callbacks financieros Firestore.
- `teacher_store.py`: adaptador limitado; no entrega referencias SDK a las vistas,
  deniega colecciones no admitidas, filtra lecturas y valida escrituras.
- Las funciones públicas `mostrar_*` de las vistas administrativas intervenidas
  llevan control de acceso, incluso al llamarlas fuera del despachador.
  `mostrar_panel_docente` comprueba permisos y construye su propio adaptador y
  listas de grados/materias autorizados, ignorando listas externas más amplias.
- Dashboard conserva su archivo y presentación: se invoca tras autorización
  desde el despachador y recibe el adaptador de lectura para el rol docente.
  Las funciones originales de presentación del dashboard no son endpoints
  independientes. No deben invocarse con un cliente sin controles desde otra UI.
- Logout e invalidación de sesión limpian todo el estado, incluidos filtros y
  datos previos de formularios. La cuenta se verifica de nuevo en cada ejecución.

No se modifican los servicios Firebase del bloque 1, credenciales, requisitos,
estilos, recursos gráficos ni código del dashboard. No se cambia la ponderación
ni el redondeo académico. Notas individuales y detalle mensual docente se envían
ahora en un mismo batch para evitar guardar solo una de esas partes.

## Identidad y alcance docente

Se utiliza `usuarios.id_docente` si existe, verificando que el perfil exista y
esté activo. Si ese campo falta, se admite el esquema legacy únicamente cuando
`usuarios.nombre` coincide exactamente con un único `maestros_perfil.nombre`.
No hay coincidencias parciales, normalización de nombres ni migración de datos.
Un vínculo explícito inválido nunca recurre al nombre como alternativa.

Las asignaciones se leen por `carga_academica.id_docente` y ciclo entero explícito
igual al ciclo configurado. Solo esas parejas grado/materia se autorizan.
Los alumnos deben estar activos y pertenecer explícitamente al mismo grado y
ciclo. Las cargas incompletas, ciclos ausentes, tipos incompatibles o identidad
ambigua no amplían permisos. Un docente sin cargas puede ver Inicio y sus cargas
vacías; las operaciones académicas muestran un aviso y no se ejecutan.

Antes de escribir se vuelve a consultar la cuenta, identidad y asignaciones.
Se verifican ciclo, grado, materia, mes, ID canónico, pertenencia de alumnos,
campos permitidos y calificaciones finitas en rango 0–10. Un lote con algún
registro no autorizado no se envía a Firestore. Se rechazan referencias externas,
reescrituras de documentos con metadatos incompatibles y lotes mayores de 500.
Las consultas de alumnos solo devuelven identidad académica mínima; no devuelven
direcciones, datos financieros ni enlaces al expediente. El perfil del dashboard
solo devuelve nombre, foto, teléfono, email y estado. La agenda docente limita
la audiencia a Todos/Docentes; la configuración permite únicamente dashboard.

## Matriz implementada

| Módulo | Administrador | Docente |
|---|---|---|
| Inicio | Dashboard administrativo | Dashboard propio y agenda docente |
| Inscripción | Habilitado | Denegado |
| Consulta Alumnos | Habilitado | Denegado |
| Maestros | Habilitado | Denegado |
| Asistencia Global | Habilitado | Denegado |
| Notas e históricos administrativos | Habilitado | Denegado |
| Finanzas | Habilitado | Denegado |
| Promoción de Grado | Habilitado con ciclo configurado | Denegado |
| Configuración de usuarios/dashboard | Habilitado, conserva restricciones internas | Denegado |
| Borrado masivo de configuración | Bloqueado | Denegado |
| Mis Listados | Sin entrada docente | Solo grados asignados y alumnos del ciclo |
| Tomar Asistencia | Mediante funciones administrativas existentes | Solo grados asignados y alumnos del ciclo |
| Cargar Notas | Mediante Notas administrativo | Solo materias/grados asignados, ciclo actual |
| Ver Mis Cargas | Mediante Maestros | Solo propias y del ciclo actual |
| Expediente Alumnos docente | Mediante Consulta Alumnos | Bloqueado |
| Boletas docente | Mediante reportes administrativos | Bloqueado |
| Mi Perfil | Bloqueado | Bloqueado |

Los botones bloqueados se conservan en el menú y al seleccionarlos muestran el
motivo; el servidor deniega antes de importar o ejecutar la vista. No se cambian
CSS, iconos, etiquetas ni estructura visual del sidebar.

## Bloqueos y motivos

- Mi Perfil: falta adaptar la vista Firebase y los campos editables.
- Expediente docente: la vista mezcla bitácora y datos personales; falta separar
  la información y decidir el alcance exacto de maestro guía.
- Boletas docentes: requieren acceso a todas las materias de un grado; no se
  concede ese acceso solo por impartir una materia. Falta adaptar el alcance guía.
- Borrado masivo: callback bloqueado; no se implementan ni ejecutan reseteos.
- Datos legacy sin ciclo explícito o vínculo docente verificable: acceso cerrado,
  sin atribuirlos automáticamente al ciclo actual ni cambiar registros.

## Verificación y límites

Ejecutar desde la raíz con requirements.txt instalado:

```sh
python -m unittest discover -s tests -v
```

Se mantienen las 32 pruebas del bloque 1 y se añaden controles de matriz,
sesión, llamadas directas a vistas, vínculo docente, alcance por grado/materia/
ciclo, datos privados, revocación, escritura y lotes. Streamlit AppTest abre
todos los módulos habilitados por rol con Firebase simulado; también prueba
la selección limitada de materias, guardado académico, asistencia, navegación
manipulada y rechazo de cuentas desactivadas tras renderizar el formulario.
Las escrituras de esas pruebas solo modifican diccionarios ficticios en memoria.

Pendiente validar Firebase remoto: IAM, índices necesarios para las consultas,
formatos de los datos existentes, Storage y flujos financieros/promoción reales.
No se ejecutó ninguna operación remota ni se cargaron credenciales reales.
Los callbacks de duplicados conservan las comprobaciones por fecha/descripción;
no añaden garantías transaccionales contra cobros concurrentes. Las operaciones
administrativas conservan su lógica y confirmaciones existentes: este bloque no
certifica todas sus reglas de negocio ni elimina operaciones de mantenimiento.
La comprobación de permisos antes del commit no es una transacción con los
registros de usuarios/cargas; una revocación concurrente al commit requiere un
endurecimiento transaccional adicional si se necesita esa garantía.

Firebase Admin sigue usando IAM, no reglas cliente. La autorización implementada
es de servidor dentro de la aplicación; no protege credenciales compartidas con
otros programas ni convierte los scripts de mantenimiento en interfaces de usuario.
Las advertencias Streamlit sobre use_container_width provienen del código visual
existente y se dejan para el bloque de homologación visual.

Resultado del bloque: 70 pruebas aprobadas (32 anteriores y 38 nuevas), ninguna
omitida; 35 archivos Python compilados en memoria; pip check y git diff --check
correctos. Comparación AST de los fragmentos de estilos de app/sidebar sin cambios.
Los servicios del bloque 1, auth.py, config.py, requirements.txt, styles.py,
views/dashboard.py y los scripts de mantenimiento siguen idénticos a c308ebc.
