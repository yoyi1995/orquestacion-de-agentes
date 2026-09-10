---
title: "Esperar el documento real de un iframe en pruebas DOM"
category: "errors-solutions"
created: "2026-09-10"
last_validated: "2026-09-09"
status: "comprobado"
evidence: ["tests/fixtures/calculadora-evidence.md"]
---

# Esperar el documento real de un iframe en pruebas DOM

## Problema

El comprobador intentaba asignar valores a entradas inexistentes. El documento
inicial del iframe podía estar `complete` antes de cargar la página esperada.
Se observó `Cannot set properties of null` pese a que Chrome salió con código 0.

## Contexto y tecnologías relacionadas

Prueba DOM de una página estática en un iframe del mismo origen, JavaScript
nativo y Chrome headless. Comprobado en [[projects/calculadora_demo|Calculadora demo]].
El formulario esperado se identifica con `#calculator-form`.

## Solución y por qué funcionó

En la ruta de ejecución inmediata se exige que el documento esté `complete`
y contenga el formulario esperado. Si no, la prueba espera el evento `load`
del iframe, una sola vez. Así no toma el documento inicial `about:blank` como
evidencia de que la calculadora ya está disponible.

Además, la verificación inspecciona `data-status` y las aserciones reportadas
por la página. El código de salida 0 del proceso del navegador no basta para
concluir que pasaron las pruebas de interfaz.

## Cuándo usarla

Comprobadores pequeños de páginas estáticas del mismo origen donde los controles
se crean al cargar el documento. Elegir un elemento característico de la página,
no copiar el identificador de la calculadora en otra aplicación.

## Cuándo no usarla

No demuestra que una aplicación con inicialización asíncrona esté lista después
de `load`; en ese caso hace falta una condición observable propia y espera acotada.
No permite acceso DOM entre orígenes distintos, ni cubre navegaciones repetidas
del iframe. No es un remedio para fallos de carga o rutas incorrectas.

## Evidencia histórica

Prueba ejecutada el 2026-09-09 UTC; extracción de memoria el 2026-09-10 UTC.
Se inspeccionaron los artefactos y el código actuales, sin reejecutar la prueba
al escribir esta nota ni cambiar su fecha de validación.

- Antes, 02:13:58 UTC: `project-state/calculadora_demo/browser-check-before-fix.json`,
  `returncode: 0`, `status: failed`, asignación sobre elemento nulo.
- Después, 02:15:00 UTC: `project-state/calculadora_demo/browser-check.json`,
  `status: passed`, 14 aserciones aprobadas y 0 fallidas.
- `project-state/calculadora_demo/browser-run.json`:
  salida 0, sin timeout, 0,724 s, DOM con `data-status="passed"`.
- `proyectos/calculadora_demo/tests/browser.html`:
  contiene la condición y la espera de carga. No se duplica su código aquí.

Estas rutas originales son relativas a la raíz de la fábrica y solo están
disponibles en el workspace original. Al publicar se conserva un
[extracto histórico revisado](../../tests/fixtures/calculadora-evidence.md),
referenciado en `evidence`; no se publican el producto ni los registros completos.
Se conservan aquí las referencias originales para trazabilidad. La evidencia
valida este caso delimitado, no todos los navegadores ni estrategias de inicio.
La preparación de Git no constituye una nueva validación de esta solución.
