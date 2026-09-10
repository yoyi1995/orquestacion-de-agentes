# Flujo adaptable de la fábrica

Codex ejecuta este flujo con sus capacidades de sesión. Es una guía de decisiones,
no una cadena obligatoria de agentes ni una máquina de estados en Python.

## De la idea al producto

1. **Comprender:** identifica usuarios, comportamiento, restricciones, datos y
   aceptación. Inspecciona el workspace y cualquier producto al que se refiera
   el usuario. Aclara solo las incertidumbres que impidan avanzar.
2. **Preparar:** elige nombre y carpeta. Para un nuevo producto puedes usar
   `python -B -m scripts.new_project <nombre> --request <requerimiento>` desde la
   raíz. Para uno existente, conserva archivos y prepara un estado inicial real.
3. **Decidir:** registra tecnología, razones, contratos y un plan proporcional.
   Una tarea pequeña puede ser una lista breve. Investiga solo decisiones que
   necesiten evidencia externa. No arranques todos los roles para planificar.
4. **Implementar:** crea archivos reales. Delega solo trabajo acotado y útil
   según el protocolo siguiente. El principal continúa trabajo independiente,
   integra resultados y conserva contexto global.
5. **Revisar y probar:** inspecciona cambios e interfaces, ejecuta pruebas y el
   producto. Usa reviewer o qa independientes cuando el riesgo justifique su
   coste; para un producto pequeño el principal asume ambas responsabilidades.
6. **Corregir:** registra cada fallo, responsable y reproducción. Devuelve el
   cambio necesario al responsable, conserva el resto y vuelve a verificar el
   fallo y sus dependencias. No reinicies todo el flujo ni repitas sin hipótesis.
7. **Entregar:** comprueba criterios de aceptación; para web, arranque y respuesta
   local. Documenta instalación, comandos, URL, parada y limitaciones en el README
   del producto. Actualiza estado con la evidencia final y pendientes reales.

## Protocolo de delegación

Antes de crear un subagente, el principal lee `roles/<especialidad>.md` y define:

```text
Especialidad y objetivo concreto:
Requerimiento global y criterios que afectan esta tarea:
Raíz absoluta del producto:
Archivos/directorios que puede modificar (o solo lectura):
Contratos/dependencias ya acordados:
Trabajo que realizan otros agentes y archivos que no debe tocar:
Resultado esperado y pruebas necesarias:
Cómo informar un bloqueo y regresar evidencia al principal:
```

Envía ese encargo y las instrucciones del perfil usando las herramientas de
subagentes expuestas por Codex. Si permiten elegir un tipo nativo, usa uno
disponible; no asumas que `backend` es un tipo registrado porque existe un MD.
Si no permiten adjuntar archivos, incluye el contenido pertinente en el mensaje.
Respeta el límite de concurrencia que informe la sesión, sin fijar seis procesos.

Espera resultados solo cuando haya una dependencia. Antes de integrar, lee los
archivos y la evidencia del subagente; resuelve conflictos explícitamente. Para
corregir un hallazgo, reutiliza el subagente responsable si sigue disponible.
Solo el principal escribe `project-state/<nombre>/state.md`; los subagentes
pueden producir informes separados si el encargo lo requiere.

## Tamaño y dependencias

| Situación | Decisión posible |
| --- | --- |
| Cambio pequeño o producto mínimo | Principal implementa, revisa, prueba y entrega |
| API e interfaz con contrato estable | Backend y frontend independientes; integración por el principal |
| Decisión estructural incierta | Consulta a architect antes del trabajo dependiente |
| Riesgo técnico importante | Reviewer con inspección independiente y hallazgos concretos |
| Integración compleja | QA independiente y correcciones dirigidas |
| Entorno o arranque no trivial | DevOps verifica dependencias, proceso y localhost |

## Retomar sin perder contexto

El estado persistente es Markdown legible; no controla herramientas ni dispara
fases. Al retomar, lee requerimiento, decisiones, contratos, evidencia y siguiente
acción. Contrasta con los archivos actuales y los servicios existentes. No des
por vigente una prueba si el código o entorno cambió. Los historiales de sesión
pertenecen a Codex; esta fábrica no implementa otra base de conversaciones.
