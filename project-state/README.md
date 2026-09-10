# Estado de los productos

Codex principal mantiene `<nombre>/state.md` a partir de
`../factory/project-template.md`. Los scripts pueden guardar resultados de
comandos en `<nombre>/runs/`, pero no deciden si el producto está terminado.

El estado debe reflejar hechos: requerimiento, aceptación, decisiones, tareas,
responsables, contratos, pruebas, defectos y cómo ejecutar en localhost. Nunca
incluyas credenciales. No copies historiales completos si un resumen y enlaces
a evidencia bastan.

Los productos que existían antes de la migración no tienen un estado inventado.
Al trabajar sobre uno, Codex debe inspeccionarlo y documentar su situación real.
La plantilla no constituye evidencia de pruebas ni un motor de ejecución.

Git conserva solo este documento y `.gitkeep`. Los estados, eventos, capturas y
resultados de ejecución quedan locales por defecto: pueden contener datos del
producto, comandos o información temporal. Los extractos públicos de evidencia
deben ser mínimos y revisados por separado. No fuerces la inclusión de runs o
eventos sin inspeccionar su contenido.
