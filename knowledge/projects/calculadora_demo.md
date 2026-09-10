---
title: "Calculadora demo: aprendizaje de pruebas DOM"
category: "projects"
created: "2026-09-10"
last_validated: "2026-09-09"
status: "comprobado"
evidence: ["tests/fixtures/calculadora-evidence.md"]
updated: "2026-09-10"
---

# Calculadora demo

Proyecto pequeño de HTML/CSS/JavaScript nativos. Su aportación a la memoria es un
fallo de sincronización del comprobador iframe, resuelto y contrastado con 14
aserciones de interfaz. Evidencia histórica del 2026-09-09, no prueba nueva.

El código sigue en `proyectos/calculadora_demo/` y la evidencia en
`project-state/calculadora_demo/`. Este resumen no conserva operaciones aritméticas,
logs, puertos, procesos ni el README. El redondeo del producto tampoco se adopta
como patrón general.

El repositorio público conserva un [extracto de evidencia](../../tests/fixtures/calculadora-evidence.md).
El producto y los registros originales siguen solo en el workspace local; este
resumen y su extracto no equivalen a una reejecución de las pruebas.

## Actualización 2026-09-10

## Aprendizaje conectado

[[errors-solutions/iframe-documento-inicial|Esperar el documento real de un iframe en pruebas DOM]].
