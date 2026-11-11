# Corrección puntual — Estado y Baja

Base: ff3a520. Rama: refactor/demo-homologacion.
Referencia de organización: main, c6b48c0.

## Cambio realizado

En views/alumnos.py el bloque administrativo estaba al final de `with tabs[6]`
(Historial Académico). Se traslada a `with tabs[5]` (Estado y Baja), después del
resumen de estado existente y antes de abrir la sección de historial.

Controles trasladados juntos, con sus claves y callbacks originales:

- Motivo de baja, campo «Otro» y botón Dar de baja.
- Mensaje de estado retirado y botón Reactivar.
- Zona de peligro: advertencia, NIE de confirmación, checkbox y botón de
  eliminación definitiva.

No se cambian etiquetas, condiciones, estados, payloads, consultas Firestore,
actualizaciones, eliminación de registros relacionados ni confirmaciones.
Tampoco se cambian Firebase, autorización, autenticación, catálogo de navegación,
estilos globales, dashboard ni otras vistas.

La comparación AST antes/después verifica que el nuevo bloque de Estado y Baja
es la concatenación exacta de sus elementos anteriores y los 14 elementos
administrativos trasladados. El historial conserva exactamente sus elementos
anteriores sin ese bloque administrativo. No se duplican nodos ni operaciones.
La diferencia de Git puede presentar el historial como bloque movido: ambos
bloques se han reordenado, sin reescribir su contenido funcional.

## Historial académico

Conserva la tabla completa, columnas, orden descendente por ciclo, trayectoria,
mensajes de vacío y datos originales. Se mantienen las otras pestañas de la ficha.
Los controles administrativos no forman parte de su árbol de renderizado.

## Pruebas

Comando, desde la raíz del repositorio con sus dependencias instaladas:

```sh
python -m unittest discover -s tests -v
```

105 pruebas aprobadas, ninguna omitida: las 96 anteriores y 9 nuevas.

Las nuevas pruebas cubren:

1. Alumno activo: baja y eliminación solo en Estado y Baja y sin duplicados.
2. Alumno retirado: reactivación solo en Estado y Baja y sin duplicados.
3. Historial con registros: todas las filas, columnas, orden y trayectoria.
4. Historial vacío: mensajes conservados y ausencia de entradas administrativas.
5. Motivo «Otro» vacío: baja rechazada sin escritura.
6. Baja simulada: una escritura, estado actualizado e historial intacto.
7. Reactivación simulada: una escritura e historial intacto.
8. Eliminación: rechazo por NIE incorrecto y por falta de checkbox, sin escritura.
9. Docente: acceso administrativo rechazado antes de renderizar las pestañas.

Los datos de estas pruebas son diccionarios en memoria, con conexiones de socket
bloqueadas. No se ejecuta una eliminación definitiva real ni se habilita borrado
masivo. Las pruebas anteriores mantienen el bloqueo del callback de reseteo.

## Comparación visual

Chromium local, escritorio 1440 × 1000 y móvil 390 × 844, tema claro y escala 1.
El harness externo está en /workspace/work/student-placement. La referencia usa
la vista extraída de main con un doble de Supabase; la demo usa su app.py y la
conexión sustituida por Firestore simulado. No se carga ningún servicio real.

Se revisan siete estados por tamaño, en ambas versiones:

- Estado y Baja de alumno activo.
- Zona de peligro y confirmaciones.
- Rechazo de eliminación por NIE incorrecto.
- Rechazo de baja sin especificar el motivo «Otro».
- Historial con registros y trayectoria.
- Estado y Baja de alumno retirado, con reactivación.
- Historial vacío.

El navegador verifica que baja/eliminación aparecen una vez en Estado y Baja,
que reactivación aparece para el estado retirado y que el historial no contiene
ninguno de esos controles. Se comprueba también el historial renderizado y los
rechazos de confirmación, sin ejecutar operaciones contra servicios remotos.

La organización de las secciones coincide con producción en los estados
comparados. Se conservan diferencias anteriores de textos/iconos de DEMO y de
advertencias que describen la eliminación Firebase: no se modifican en esta
corrección ni se afirma identidad total de píxeles.

## Límites y cierre

- No se certifica ejecución contra Firebase real, IAM ni persistencia remota.
- La eliminación definitiva exitosa no se ejecuta en navegador; sus ramas y
  operaciones se preservan mediante la comparación estructural exacta.
- No se modifican datos existentes, credenciales, documentos reales o reglas.
- main y demo-comercial permanecen intactas, sin migraciones, reseteos, despliegues
  ni push. Los servidores locales de comparación se detienen al cerrar.
- Se resuelve la salvedad de ubicación documentada en el bloque 4A. No se inicia 4B.

Resultado visual: 14 pares de capturas (28 imágenes) para los siete estados,
en escritorio y móvil. Pasan las comprobaciones de ubicación, separación y
confirmaciones en las cuatro combinaciones de tamaño/versión. Se inspeccionan
las capturas de Estado y Baja y de historial en ambos tamaños.

Verificaciones finales: 38 archivos Python compilados en memoria sin errores;
git diff --check correcto. Solo se cambia la disposición de views/alumnos.py,
se añade la suite específica y se actualiza documentación. No se inicia 4B.
