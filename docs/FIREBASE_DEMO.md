# Bloque 1: conexión exclusiva de EduManager DEMO

## Alcance

`firebase_demo_service.py` es el único módulo que crea aplicaciones Firebase.
`firebase_service.py` y `firebase_selector.py` conservan los imports existentes
sin seleccionar producción ni utilizar la aplicación Firebase predeterminada.
No se han cambiado app.py, auth.py, config.py, estilos ni vistas.

La conexión exige `ENTORNO=demo` (valor predeterminado si no se define), el
proyecto `edumanager-demo` en las credenciales y en la aplicación reutilizada,
y el mismo proyecto en el cliente Firestore antes de entregarlo a las vistas.
Una configuración inválida cancela la conexión sin fallback.
La aplicación con nombre propio se inicializa bajo un bloqueo para sesiones
concurrentes. Las credenciales de una aplicación ya inicializada no se recargan;
una rotación de credenciales requiere reiniciar el proceso.

## Configuración existente y almacenamiento

Se conserva la prioridad del archivo local `credenciales_demo.json` sobre la
sección `[firebase_demo]` de Streamlit Secrets. No se modifican estos archivos.
No se admiten credenciales implícitas del servidor como alternativa.

Para subir archivos, configurar explícitamente `FIREBASE_DEMO_STORAGE_BUCKET`
con el bucket real del proyecto, una vez comprobado por el responsable:

- `edumanager-demo.appspot.com`, o
- `edumanager-demo.firebasestorage.app`.

No se supone que alguno exista. Sin la variable, Firestore sigue disponible
pero las subidas retornan None y muestran un error seguro. No se añadió ni se
cambió configuración de despliegue. Los buckets personalizados no se admiten.
La existencia, propiedad efectiva e IAM del bucket requieren validación remota
posterior. Los nombres de objetos incorporan UUID para evitar sobrescrituras
accidentales y se validan rutas y nombres antes de subir.

Se conserva el retorno de URL con token Firebase para compatibilidad. Esa URL
es accesible a quien posea el enlace: no equivale a autorización por rol y no
debe registrarse ni publicarse. No se hacen públicos los buckets mediante ACL.
No se implementan aquí descargas privadas ni gestión/revocación de enlaces.

## Compatibilidad

- `conectar_firebase()` devuelve `(db, None)` o `(None, mensaje_seguro)`.
- `conectar_firebase_demo()` devuelve `(db, None)` o genera `ErrorFirebaseDemo`.
- `obtener_usuario()` conserva `usuarios/<usuario>`, password_hash y retorno None
  si no existe o falla la consulta. No cambia ni reescribe contraseñas.
- `subir_archivo()` y `subir_archivo_demo()` conservan argumentos y URL o None.
- `verificar_conexion_demo()` valida configuración local; no prueba red ni IAM.

Las lecturas y escrituras de las vistas reciben el cliente del proyecto validado.
Esto aísla el backend; no sustituye permisos por rol. Firebase Admin utiliza IAM,
no las reglas cliente de Firestore. Autorización por módulo, alcance docente,
operaciones destructivas y resultados parciales de formularios ante una subida
fallida quedan para los bloques siguientes. No deben habilitarse módulos hasta
validar esos controles. Los scripts de mantenimiento no se ejecutaron ni cambiaron.

## Pruebas sin datos reales

Desde la raíz del repositorio:

```sh
python -m unittest discover -s tests -v
```

La suite de aislamiento sustituye Firebase y Streamlit con dobles. La suite SDK
usa requirements.txt, genera claves efímeras en memoria e inicializa clientes
reales sin consultar ni escribir documentos ni subir archivos. Se bloquean las
conexiones de socket durante ambas suites. Las pruebas SDK se omiten con aviso
si faltan sus dependencias. No se necesitan secrets, archivos de credenciales
ni un emulador. Las variables de endpoints de emulador se rechazan en el runtime
normal; no hay fallback silencioso a servicios remotos. Si se introducen pruebas
con emuladores posteriormente, necesitarán una configuración aislada explícita.

Pendiente: arranque conectado con credenciales DEMO, IAM, lecturas/escrituras,
persistencia real y carga/descarga del bucket autorizado. No usar producción.

## Resultado de validación del bloque

- 32 pruebas aprobadas con las dependencias reales instaladas en un entorno
  virtual externo al repositorio; ninguna omitida.
- Incluye arranque de `app.py` mediante Streamlit AppTest ante conexión
  rechazada: muestra error controlado y detiene el flujo sin renderizar login.
- 30 archivos Python compilados en memoria sin errores de sintaxis.
- `pip check`: sin dependencias incompatibles; `git diff --check`: correcto.
- Sin acceso a bases remotas, subida real, migraciones, reseteos o despliegues.
- main permanece en c6b48c0 y la referencia demo-comercial en fbba42d.
