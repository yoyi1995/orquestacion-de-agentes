# Fábrica de software con Codex

Abre `G:\Orquestacion` en Codex y describe el producto que quieres construir.
Codex conserva la visión global, programa, decide si necesita ayuda de
subagentes y verifica el resultado dentro de `proyectos/<nombre>/`.

## Uso

En la aplicación, selecciona esta carpeta e inicia una conversación. Por CLI:

```powershell
codex -C G:\Orquestacion
```

Ejemplo de requerimiento:

> Crea un gestor de inventario para una tienda en proyectos/inventario_tienda.
> Necesito productos, entradas, salidas y consulta de existencias. Decide la
> tecnología adecuada, delega solo si aporta valor, prueba el software y
> documenta cómo usarlo en localhost.

Para continuar un producto, indica su nombre y el cambio deseado. Codex debe
leer su estado y comprobar el código antes de continuar. Desde la CLI también
puedes utilizar `codex resume` para seleccionar una sesión anterior.

Inicia Codex desde esta raíz para cargar `AGENTS.md`. En un workspace sin Git,
abrir únicamente una subcarpeta no garantiza descubrir las instrucciones de la
raíz. Para aplicar las instrucciones a futuras conversaciones, abre una nueva
sesión en esta carpeta.

## Estructura

```text
AGENTS.md                  Dirección técnica e instrucciones para Codex
roles/                     Seis especialidades opcionales
factory/
  rules.md                 Calidad, permisos y ejecución
  workflow.md              Flujo adaptable y protocolo de delegación
  project-template.md      Plantilla del estado persistente
  tools.py                 Rutas y comandos finitos reutilizados
  workspace.py             Creación de proyectos sin sobrescrituras
  activity.py              Registro operativo de eventos reales
  knowledge.py             Consulta y escritura de memoria técnica selectiva
dashboard/                 Observador local de estados y eventos
knowledge/                 Memoria Markdown compatible con Obsidian
project-state/             Decisiones, pendientes y evidencia por producto
scripts/                   Utilidades locales, sin motor de agentes
tests/                     Pruebas de las utilidades de la fábrica
proyectos/                 Productos independientes
backups/                   Respaldos históricos locales, excluidos de Git
```

La orquestación no necesita servidor ni Uvicorn; el dashboard es un observador HTTP opcional.
El trabajo se realiza en Codex con su autenticación y herramientas existentes.
No se necesita configurar una clave de proveedor en `.env` para usarla.
Las utilidades opcionales requieren Python 3.10+ y solo biblioteca estándar.
Cada producto declara y utiliza sus propias dependencias.

## Subagentes reales

Se comprobó localmente Codex CLI **0.153.4**, con `multi_agent` habilitado.
En la sesión de migración se utilizó delegación nativa. Los perfiles de `roles/`
se leen y se transmiten a los subagentes; no se presentan como tipos registrados
ni como funciones Python. No se fijan modelos ni se altera la configuración
global del usuario. Si una sesión no expone delegación, el principal trabaja
directamente y lo informa.

Codex soporta instrucciones de proyecto y subagentes. La disponibilidad y el
control concreto pertenecen a la sesión, no a este repositorio:
[instrucciones AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
y [subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents).

## Utilidades opcionales

Ejecuta los ejemplos desde `G:\Orquestacion`. No es necesario crear primero la
carpeta manualmente: Codex puede invocar este auxiliar al comenzar un producto.

```powershell
py -3 -B -m scripts.new_project inventario_tienda --request 'Gestionar productos y existencias'
py -3 -B -m scripts.run_command --project inventario_tienda --timeout 30 --command 'dir'
```

El primer comando crea un proyecto vacío y su estado, sin imponer tecnología.
Rechaza nombres inseguros y carpetas existentes. Para un producto ya existente,
Codex inspecciona sus archivos y crea su estado a partir de la plantilla sin
recrear ni sobrescribir el producto.

El segundo ejecuta un comando finito en la carpeta del producto, escribe registros
en stderr, devuelve JSON por stdout y guarda un resultado único en
`project-state/<nombre>/runs/`. Timeout: entero de 1 a 600 segundos; salida: últimos
12.000 bytes de cada flujo. El código de salida del auxiliar es 124 para timeout
y distinto de cero para errores. En Windows el shell de este auxiliar es `cmd`;
para sintaxis PowerShell invoca PowerShell explícitamente.

No uses el auxiliar finito para mantener un servidor activo. Usa una sesión de
terminal administrada por Codex, comprueba el arranque y registra cómo detenerla.
No existe un gestor adicional de servicios en esta fábrica.

```powershell
py -3 -B -S -m unittest discover -s tests -v
```

`-S` permite verificar las utilidades sin cargar paquetes de site-packages.
No se requiere instalar dependencias de la fábrica. El entorno `.venv` existente
se conserva por compatibilidad local, pero no es necesario para operar la fábrica.
La migración no modifica los productos existentes ni los marca como verificados.
El inventario final, las pruebas y cualquier diferencia respecto del respaldo
están documentados en [el informe de migración](factory/migration-report.md).

## Dashboard y memoria

Desde la raíz:

```powershell
py -3 -B -S -m dashboard.server --port 8787
py -3 -B -S -m factory.knowledge search "iframe"
py -3 -B -S -m factory.knowledge check
```

Dashboard: http://localhost:8787/; detener con Ctrl+C. Lee los registros reales de
la carpeta local; una copia recién clonada comienza sin proyectos ni actividad.
Consulta [dashboard/README.md](dashboard/README.md) y [knowledge/index.md](knowledge/index.md).
`knowledge/` puede abrirse directamente como vault existente en Obsidian.

## Contenido del repositorio

Se versionan las instrucciones, perfiles, utilidades, dashboard, memoria,
documentación y pruebas. `proyectos/` conserva solo `.gitkeep`; `project-state/`
conserva su guía y `.gitkeep`. Productos, eventos, capturas, logs y ejecuciones
permanecen locales. También se excluyen secretos, entornos, dependencias,
cachés, backups y preferencias/temas personales de Obsidian.

La memoria inicial conserva un extracto pequeño y revisado de evidencia histórica
de la calculadora en `tests/fixtures/`, sin publicar el producto generado. Las
pruebas normales usan espacios temporales; la comprobación opcional contra la
calculadora real se omite cuando sus datos locales no existen. El comprobador
Chrome del dashboard requiere esa calculadora local y no forma parte de la suite
de un clon limpio. No se genera actividad ficticia para llenar el dashboard.
