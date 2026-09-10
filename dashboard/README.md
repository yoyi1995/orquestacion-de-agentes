# Dashboard local de la fábrica

Observador sin dependencias externas. Requiere Python 3.10+; Windows compatible.
Desde `G:\Orquestacion`:

```powershell
py -3 -B -S -m dashboard.server --port 8787
```

Abrir http://localhost:8787/ . Detener con Ctrl+C en esa terminal. No requiere
instalación. El puerto es configurable; escucha exclusivamente en 127.0.0.1.

## Arquitectura y datos

`dashboard/server.py` sirve cuatro rutas estáticas y `GET /api/snapshot`.
`dashboard/data.py` proyecta `project-state/<nombre>/state.md`, `events/*.json`,
`runs/*.json` y registros en `runs/*.json` de raíz con campo project correspondiente.
La interfaz consulta cada dos segundos. Solo registra actividad que realmente
ocurrió: no interpreta archivos modificados como delegaciones ni ejecuta agentes.
Los roles sin eventos aparecen inactivos; `Sin subagentes:` en el estado histórico
permite marcarlos omitidos. La selección inicial es el proyecto con evidencia
más reciente; se puede cambiar para inspeccionar cualquier proyecto local.
calculadora_demo solo aparecerá donde existan sus datos: el producto generado
y su estado no se distribuyen en Git. Un clon limpio muestra el estado vacío.

El Markdown histórico se muestra como texto y los comandos históricos con su
código de salida; un comando exitoso no se convierte automáticamente en prueba.
No se deducen archivos modificados ni tiempos de agente a partir del historial.
Las URL son referencias registradas, no certifican que el producto siga activo.
`working` significa último estado registrado: no existe heartbeat ni conexión
a la sesión interna de Codex. Una interrupción sin evento de cierre requiere
registrar posteriormente waiting/error/completed con evidencia.

## Generar eventos operativos

Desde la raíz, Codex y los subagentes usan el mismo CLI; solo Codex declara inicio
y cierre del proyecto. No es necesario modificar los auxiliares existentes.

```powershell
py -3 -B -S -m factory.activity --project mi_proyecto --type project_started --status working --task "Implementar requerimiento"
py -3 -B -S -m factory.activity --project mi_proyecto --role frontend --type task_delegated --status waiting --task "Construir interfaz"
py -3 -B -S -m factory.activity --project mi_proyecto --role frontend --type agent_working --status working --task "Construir interfaz"
py -3 -B -S -m factory.activity --project mi_proyecto --type file_changed --file proyectos/mi_proyecto/index.html --message "Formulario creado"
py -3 -B -S -m factory.activity --project mi_proyecto --type test_passed --command "node --test" --returncode 0 --duration-seconds 1.2 --message "Pruebas verificadas"
py -3 -B -S -m factory.activity --project mi_proyecto --role frontend --type agent_finished --status completed
py -3 -B -S -m factory.activity --project mi_proyecto --type project_finished --status completed --url http://localhost:8000/
```

Tipos: project_started, task_created, task_delegated, agent_working, file_changed,
command_executed, test_passed, test_failed, error, correction, agent_finished,
project_finished, knowledge_created, knowledge_updated, knowledge_reused.
Los eventos de memoria registran operaciones sobre knowledge/; no cambian por sí
solos el estado del agente. Estados: working, completed, waiting, error, skipped, inactive,
unknown. Roles: codex, architect, backend, frontend, reviewer, qa, devops.
Campos opcionales: task, message, file (repetible), command, returncode,
duration-seconds, url. `unknown` no cambia el estado previo del nodo.

Cada evento incluye UUID y fecha UTC generados por el escritor. Se escribe un
archivo temporal y se renombra atómicamente: lectores ignoran temporales y
agentes concurrentes no comparten archivo. API Python: `record_event(...)` en
factory.activity. No hay endpoint web de escritura. El registro manual exige
disciplina operacional; llamadas nativas no instrumentadas no aparecen solas.

## Seguridad y límites

No se sirven directorios, .env, stdout/stderr ni archivos de producto. Rutas y
enlaces fuera del workspace se rechazan. Host restringido a localhost/127.0.0.1,
sin CORS, sin comandos ni dependencias externas. Los datos se renderizan como
texto. Se redactan patrones comunes de secretos como defensa adicional: no es
un detector universal; nunca registrar credenciales ni comandos sensibles.
El lector limita cada archivo a 512 KB, los eventos/runs a 2000 archivos por
fuente y la respuesta a 200 eventos y 100 comandos por proyecto. Advierte sobre
registros ilegibles o truncados. El resumen por agente usa los eventos leídos.
Para volúmenes mayores será necesario archivar eventos o añadir un índice.

## Verificación

```powershell
py -3 -B -S -m unittest discover -s tests -p test_dashboard.py -v
```

La evidencia de la entrega original permanece local en `project-state/dashboard/`;
no se distribuyen sesiones, capturas ni registros operativos en Git.

Comprobación real de navegador (opcional, Node 22+ y Chrome local):
`node dashboard/browser_check.mjs`. Inicia Chrome headless con perfil temporal y
CDP en 127.0.0.1:9229; cierra su árbol de procesos al terminar. Requiere el dashboard
activo en 8787. `DASHBOARD_CHROME` y `DASHBOARD_PYTHON` permiten especificar las
rutas de ambos ejecutables; los valores predeterminados corresponden a este equipo.
Es una comprobación de integración local opcional: exige `calculadora_demo` y
sus registros originales. No se debe ejecutar como prueba de un clon limpio.
La prueba registra un evento real de observación en dashboard, genera capturas y
browser-check.json. Tres comprobaciones de casos límite usan fixtures solo en
memoria del navegador, nunca eventos ficticios en el registro de la fábrica.
