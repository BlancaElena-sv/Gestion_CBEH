# Bloque 3 — Homologación visual inicial

Referencia visual: main, commit c6b48c0. Base de implementación: b414d7c.
Rama de trabajo: refactor/demo-homologacion. No se modifica main ni demo-comercial.

## Alcance y cambios

### 3.1 Estilos globales y login

- styles.py reproduce el archivo de referencia de main: variables de paleta,
  tipografía, espaciados, botones, campos, métricas, tablas, formularios y alertas.
- Se aplican los estilos globales después del control de acceso, igual que en
  main, para que no sobrescriban el fondo ni la tipografía del login.
- Login reutiliza CSS, distribución, textos de ayuda, tarjeta, campos y botón
  de producción. Logo, título e institución usan la configuración DEMO.
- El bloque `if submitted` de autenticación conserva exactamente el AST del
  bloque 2: consultas, bcrypt, estado activo, roles admitidos y sesión.

### 3.2 Sidebar

- Se conserva el CSS de producción y se retiran sus interferencias al usar
  styles.py de main. No se modifica el catálogo central, permisos ni destinos.
- Se utiliza LOGO_INSTITUCIONAL, APP_NAME y CICLO_LECTIVO de DEMO.
- El logo horizontal DEMO se contiene en el mismo espacio cuadrado del logo de
  producción sin deformarlo. Los selectores de identidad admiten stImage y
  stImageContainer para compatibilidad con Streamlit.
- Distribución, botones, secciones y opción activa mantienen la referencia.

### 3.3 Dashboards

- Se reutilizan cabeceras, métricas, tarjetas financieras con acentos de color,
  fecha de agenda, etiquetas de estado, iconos y distribución de main.
- Se conserva la carga de configuración, agenda, alumnos, maestros, finanzas,
  perfil y cargas mediante Firestore. Sus llamadas collection/where/document/
  stream tienen el mismo AST que en b414d7c. No se incorporan consultas Supabase.
- El docente sigue recibiendo TeacherStore desde el despachador autorizado.
- Textos externos se escapan antes de insertarlos en HTML.
- Los fallos de lectura presentan advertencias con el formato de producción y
  un detalle seguro: «consulta no disponible». No se muestran errores del SDK.
- No se cambian cálculos financieros, reglas académicas ni controles de acceso.

## 3.4 Método de comparación en navegador

Chromium 156.0.8078.79, Streamlit 1.67.0, tema claro, escala de dispositivo 1.
Tamaños: escritorio 1440 × 1000 y móvil 390 × 844.

Se ejecutan dos servidores locales aislados con datos ficticios equivalentes:

1. Referencia: CSS, sidebar, función de login y dashboard extraídos de main.
   Un doble de Supabase responde en memoria; no se importa el servicio real ni
   se ejecuta el app.py completo de producción, su configuración o credenciales.
2. DEMO: app.py real de la rama de trabajo con el servicio de conexión y la
   consulta inicial de usuarios sustituidos en el harness externo por FakeDB.
   Navegación, autorización, TeacherStore y bcrypt siguen ejecutándose.

La referencia de dashboard usa el mismo ciclo e institución de prueba que DEMO
para comparar estados equivalentes. Login/sidebar conservan los elementos de
identidad originales de main en las capturas de referencia. En las comparaciones
normalizadas se enmascaran imágenes y textos de identidad; no se enmascaran
formularios, botones, métricas, tarjetas, agenda ni alertas.

Casos: login y dashboards de ambos roles con datos, vacíos y error de lectura,
en ambos tamaños (14 pares). Se capturan además login con usuario inexistente,
sidebar móvil cerrado y parte inferior de dashboards tras desplazarse. Se
comprueba en navegador la contraseña incorrecta y el acceso correcto por rol.

Se comparan posiciones, dimensiones, color, fondo, familia y tamaño de fuente,
padding, radios y borde izquierdo de los componentes presentes. Se calcula la
fracción de píxeles que difieren más de 12 niveles en algún canal RGB en las
capturas normalizadas. Esa medida es específica de estas capturas y no equivale
a una certificación visual de toda la aplicación ni de otros navegadores.

El harness, las capturas y las mediciones se conservan como archivos de trabajo
locales en /workspace/work/visual-block3; no son código ejecutable de producción
ni incorporan un modo de omitir autenticación a la aplicación entregada.

## Pruebas y protecciones

- Las 70 pruebas anteriores permanecen incluidas en la suite.
- Se añaden 5 pruebas de presentación: escape de agenda, fecha inválida,
  formato financiero, fecha de calendario y advertencias sin datos sensibles.
- AppTest continúa comprobando todos los módulos habilitados y los rechazos
  por sesión, rol, grado, materia y ciclo.
- Comparación AST del bloque de autenticación y las llamadas Firestore: iguales
  a b414d7c. styles.py es idéntico al archivo de main.
- Los servicios Firebase, auth.py, config.py, catálogo, autorización, adaptador
  docente, despachador, dependencias y vistas individuales ajenas al alcance
  permanecen idénticos a b414d7c.

## Límites y pendientes

- No se valida el despliegue real ni se utilizan credenciales o datos reales.
- Quedan pendientes otros navegadores, resoluciones y versiones de Streamlit.
  Las dependencias actuales no están fijadas; una actualización puede cambiar
  selectores o geometría y requiere revisar las capturas.
- El diseño móvil conserva el apilamiento y desplazamiento de main. No se
  rediseña el login ni se reduce su espacio de logo para evitar desplazamiento.
- Los errores reales pueden variar; se mantiene un mensaje seguro uniforme.
- La homologación individual de módulos académicos, administrativos, financieros
  y sus reportes no forma parte de este bloque. Solo reciben los estilos comunes.
- Mi Perfil, expediente docente, boletas docentes y borrado masivo conservan
  los bloqueos documentados en el bloque 2.
- Continúan pendientes IAM, índices, persistencia remota y Storage del proyecto
  DEMO. No hubo migraciones, reseteos, despliegues ni push.

## Resultados finales

- **75 pruebas aprobadas**, ninguna omitida: 70 existentes y 5 nuevas.
- 36 archivos Python compilados en memoria; revisión de formato correcta.
- **14 pares comparados en Chromium**: las posiciones, dimensiones y propiedades
  de estilo medidas coinciden en todos los casos; sin desbordamiento horizontal.
- Capturas normalizadas: 0 % de píxeles con diferencia mayor de 12 niveles por
  canal en login y móvil; máximo 0,000764 % en dashboards de escritorio.
  Se excluyen únicamente las zonas de identidad descritas. No se afirma
  igualdad de píxeles de las capturas sin máscara ni de todos los estados posibles.
- Detalle cuantitativo en `docs/visual-comparison.json`.
- Altura de contenido tras cerrar sidebar y desplazar hasta el final: referencia
  y demo coinciden, tanto en escritorio (administrador 1271 px, docente 1286 px)
  como en móvil (administrador 2137 px, docente 2061 px), con los datos de prueba.
- Chromium verifica usuario inexistente, contraseña incorrecta y acceso correcto
  de administrador/docente; el docente no recibe el botón Finanzas.
- Revisión visual de capturas de login, dashboard administrativo y dashboard
  docente, incluyendo contenido móvil con sidebar cerrado y zona inferior.

La equivalencia verificada corresponde al alcance, estados, tamaños y entorno
indicados. No certifica las pantallas individuales de los módulos pendientes.

Prueba adicional en Chromium de Inscripción, Maestros, Notas y Finanzas: controles
renderizados sin excepciones y sin enviar formularios ni escribir datos. No se
han homologado sus contenidos individuales ni corregido sus textos heredados.
