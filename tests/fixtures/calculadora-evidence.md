# Evidencia histórica mínima: calculadora_demo

Extracto revisado para conservar el aprendizaje sin publicar el producto generado,
logs completos, capturas, datos de sesión ni rutas personales. No es una ejecución
nueva ni un conjunto de pruebas que pueda reproducirse sin el producto original.

## Prueba de interfaz en iframe (2026-09-09 UTC)

| Artefacto local original | Resultado observado |
| --- | --- |
| project-state/calculadora_demo/browser-check-before-fix.json | 02:13:58 UTC; proceso salida 0; prueba status failed; asignación de value sobre elemento nulo |
| project-state/calculadora_demo/browser-check.json | 02:15:00 UTC; proceso salida 0; status passed; 14 aserciones aprobadas, 0 fallidas |
| project-state/calculadora_demo/browser-run.json | Salida 0, duración 0,724 s; DOM data-status passed |
| proyectos/calculadora_demo/tests/browser.html | La ruta inmediata exige documento complete y presencia de #calculator-form; en otro caso espera load una sola vez |

Alcance: página estática de mismo origen en Chrome headless. No demuestra
inicialización asíncrona de una SPA ni acceso DOM entre orígenes distintos.
El código de salida del navegador no basta para acreditar las aserciones.

Los originales permanecen locales, excluidos por .gitignore. Este extracto solo
permite auditar la conclusión histórica; una validación nueva requiere recuperar
los originales o reproducir el caso y registrar evidencia nueva.
