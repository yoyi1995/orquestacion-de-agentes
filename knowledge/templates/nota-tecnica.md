# Plantilla de nota técnica

Copiar solo cuando exista un aprendizaje útil. Completar lo que corresponda;
eliminar secciones no aplicables. No crear notas por obligación. Guardar en su
categoría con nombre estable; buscar equivalentes y enlaces antes de escribir.

```markdown
---
title: "Título específico"
category: "patterns"
created: "AAAA-MM-DD"
last_validated: null
status: "experimental"
evidence: []
---

# Título específico

## Problema
Fallo o decisión que vale la pena no repetir.

## Contexto y tecnologías relacionadas
Requerimiento, entorno y condiciones que delimitan la solución.

## Solución y por qué funcionó
Pasos operativos y explicación técnica verificable; no razonamiento privado.

## Cuándo usarla
Condiciones de aplicación.

## Cuándo no usarla
Límites, riesgos y situaciones que exigen otra decisión.

## Evidencia y proyectos
Rutas precisas, fecha de prueba, comando, aserciones y resultado observado.
Enlazar el código existente, no copiarlo completo ni pegar logs.

## Relaciones
Añadir enlaces Obsidian únicamente a notas existentes y pertinentes.
```

Estados: `experimental`, `comprobado`, `obsoleto`. Para `comprobado`, fecha real
y evidencia obligatorias; nunca elevar el estado por confianza o por antigüedad.
Si la nota queda obsoleta, añadir motivo y condiciones para revisarla; conservar
evidencia anterior identificada como histórica. Un resumen de proyecto puede
usar el mismo encabezado y solo uno o dos párrafos más enlaces útiles.
