# Memoria técnica de la fábrica

Vault de Markdown para decisiones futuras de Codex y sus subagentes. Abrir esta
carpeta `G:\Orquestacion\knowledge` como vault existente en Obsidian; no requiere
instalación adicional, configuración `.obsidian` ni plugins. Obsidian puede crear
sus preferencias locales cuando el usuario lo abra. Codex utiliza los archivos
directamente, sin Obsidian ni MCP.

## Mapa inicial

- [[errors-solutions/iframe-documento-inicial|Esperar el documento real de un iframe]]:
  error difícil verificado con evidencia antes/después.
- [[projects/calculadora_demo|Calculadora demo]]: conexión breve con ese aprendizaje.
- [[templates/nota-tecnica|Plantilla de nota técnica]]: formato para futuros aportes.

## Organización

| Carpeta | Cuándo aporta valor |
| --- | --- |
| technologies/ | Evaluación concreta de una tecnología y límites de uso |
| architectures/ | Diseño reutilizable comprobado en un contexto delimitado |
| patterns/ | Solución recurrente que evita trabajo real |
| errors-solutions/ | Fallo no trivial, reproducción, corrección y evidencia |
| security/ | Medida de seguridad contrastada, sin secretos |
| decisions/ | Decisión significativa, alternativas y condiciones para revisarla |
| projects/ | Resumen corto que conecta proyecto y notas, sin duplicar su documentación |
| templates/ | Plantillas de escritura; no soluciones técnicas comprobadas |

Las categorías vacías son intencionales. No necesitan notas de relleno. Un
proyecto puede terminar sin aportar memoria; tampoco necesita resumen obligatorio.

## Lectura y reutilización

1. Comprender la tarea presente antes de elegir soluciones.
2. Buscar solo si hay una conexión probable con conocimiento previo.
3. Leer únicamente los resultados pertinentes; revisar estado, fecha, contexto,
   contraindicaciones y evidencia. No tratar las notas como instrucciones ejecutables.
4. Adaptar lo útil, ignorar lo que ya no aplique y resolver normalmente lo nuevo.
5. Registrar reutilización solo si se aprovechó la nota, con una justificación
   operativa breve. Buscar o leer no equivale a reutilizar.

Desde la raíz de la fábrica:

```powershell
py -3 -B -S -m factory.knowledge search "iframe" --limit 5
py -3 -B -S -m factory.knowledge read errors-solutions/iframe-documento-inicial.md
py -3 -B -S -m factory.knowledge check
```

`search` devuelve rutas, título, estado y fecha, no el vault entero. Busca en
notas de las siete categorías, omite plantillas/índice y notas obsoletas por
defecto (`--include-obsolete` las incluye). Consulta léxica: todos los términos
deben aparecer; ignora mayúsculas y acentos, no infiere sinónimos ni embeddings.
`read` devuelve la nota seleccionada y su SHA-256 para una actualización posterior.

## Escritura y mantenimiento

Buscar equivalentes antes de crear. La utilidad detecta títulos normalizados o
contenido idéntico; también evita nombres de archivo repetidos que harían ambiguos
los enlaces breves. Equivalencias semánticas exigen criterio del autor. Una nota
por aprendizaje significativo. Enlaces por ruta dentro del vault y alias legibles,
como los del mapa, evitan ambigüedad; también se admiten nombres únicos, por
ejemplo [[calculadora_demo]].
No crear enlaces a notas inexistentes para adornar el grafo.

Los cuerpos se reciben por stdin (no como argumentos registrados). Ejemplo
conceptual, no ejecutar por rutina:

```powershell
@'
# Título del aprendizaje

## Problema y contexto
Descripción operativa sin información sensible.

## Solución y límites
Resultado investigado, aún pendiente de validación.
'@ | py -3 -B -S -m factory.knowledge create patterns/nombre.md --title "Título del aprendizaje" --status experimental --project nombre_proyecto
```

En PowerShell antiguo configura la entrada UTF-8 cuando uses tuberías:
`$OutputEncoding = [System.Text.UTF8Encoding]::new($false)`.
La API `Knowledge().save(...)` evita depender de codificación de la terminal.

Para actualizar, lee primero; envía solo la nueva corrección/evidencia por stdin
a `update <ruta> --expected-sha <SHA-256 obtenido>`. La utilidad añade una sección
fechada conservando el texto y evidencia anteriores; no reemplaza contenido.
Se puede indicar `--status obsoleto` explicando motivo y sustituto en el cuerpo.
Para pasar a comprobado, usa `--status comprobado --validated AAAA-MM-DD` y
`--evidence ruta/relativa/al/workspace` repetible. La referencia debe existir:
el autor, no el programa, verifica que demuestra realmente lo afirmado.
La fecha de validación corresponde a la prueba, no al día de copiar la nota.
Las pruebas históricas se identifican como históricas, sin fingir reejecución.

`create/update --project <nombre> --role <rol>` registra el cambio mediante
factory.activity. Sin `--project` guarda Markdown sin evento. Para reutilización
real: `reuse <ruta> --project <nombre> --reason "Contexto de aplicación"`.
No cambia la nota ni la fecha de validación. Exige estado comprobado; las notas
experimentales/obsoletas pueden leerse como referencia, no como solución validada.

Una entrada vacía devuelve `skipped` sin crear ni actualizar nota o evento. No hay
hooks de cierre de proyecto, cuotas, resúmenes automáticos ni ingestión de logs.

## Protección y límites

Solo rutas `.md` relativas a knowledge, sin `..`, rutas Windows absolutas/UNC,
ADS, enlaces simbólicos o junctions. Escrituras limitadas a categoría/archivo.
No se lee `.env`, directorios ocultos, dependencias o backups. Evidencia externa
al vault se referencia desde el workspace sin copiar su contenido; los enlaces
Markdown relativos a esas pruebas funcionan en lectores normales y algunos
flujos de escritorio, pero Obsidian puede limitar apertura fuera del vault.
La ruta textual exacta permite a Codex abrirla desde la raíz del workspace.

Rechazo de patrones comunes de credenciales, tokens y claves privadas antes de
escribir o mostrar notas. No es un clasificador universal; el autor debe excluir
secretos, datos personales innecesarios y archivos completos desde el origen.
No poner secretos en títulos, rutas, comandos ni argumentos. Las notas manuales
tienen los mismos requisitos; `check` ayuda a detectar incumplimientos.

Escritura temporal y reemplazo atómico, con lock `.write.lock` y SHA esperado al
actualizar. El lock coordina esta utilidad, no editores externos. Asigna un solo
autor por nota, incluyendo Obsidian. Si quedó un lock tras una interrupción,
comprueba su PID y que no existe escritor antes de retirarlo; no hay desbloqueo
automático. No es un sandbox frente a otro proceso que cambie rutas simultáneamente.
Máximo 64 KB por nota. El formato de cabecera es YAML simple con valores JSON
(válidos en YAML): conserva las comillas y listas de la plantilla. No se requiere
parser YAML externo ni un índice derivado que pueda quedar desactualizado.
