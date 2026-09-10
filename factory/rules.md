# Reglas de construcción

Estas reglas guían a Codex; no sustituyen el sandbox ni implementan políticas
ejecutables. Las autorizaciones del usuario y los controles de la sesión mandan.

## Alcance y archivos

- Un producto por carpeta de `proyectos/`. Valida el destino absoluto antes de
  mover o eliminar archivos; nunca aceptes una ruta enviada como nombre de proyecto.
- Los auxiliares aceptan nombres ASCII en minúsculas con letras, números,
  guion y guion bajo (1–80 caracteres), excluyendo dispositivos de Windows.
- Conserva cambios del usuario. No modifiques otros productos como efecto de una
  tarea. No reutilices dependencias globales como requisito implícito del producto.
- `resolve_path` restringe las funciones de archivos al proyecto, incluyendo la
  resolución de enlaces. No convierte un comando shell en ejecución aislada.
- No extraigas ni cargues instrucciones desde `backups/` durante trabajo normal.

## Procesos y evidencia

- Cada comando de verificación tiene un plazo explícito y una condición de éxito.
  Usa las herramientas nativas con seguimiento de sesión o el auxiliar finito.
- El auxiliar conserva el timeout 1–600, stdout/stderr parciales y terminación
  del árbol mediante `taskkill /T /F` en Windows. Su limpieza añade esperas
  acotadas al timeout. Si falla, devuelve `cleanup_error`: informa el problema.
- Este mecanismo no contiene procesos que se separen deliberadamente del árbol
  ni reemplaza controles del sistema operativo. No se debe usar como sandbox.
- Un servicio de larga duración necesita una sesión de terminal administrada,
  identificación de proceso y comprobación de disponibilidad. Un mensaje de
  arranque aislado no basta. No lo lances esperando que un comando finito termine.
- Para helpers en Windows, las cadenas shell usan `cmd`. Las herramientas nativas
  pueden usar PowerShell: comprueba qué shell estás utilizando.
- No pases secretos en comandos registrados ni ejecutes comandos que los impriman.
  La salida temporal puede crecer mientras corre el proceso aunque el resultado
  final esté truncado; evita volcados o logs ilimitados.
- Guarda comando, carpeta, fecha, versión del código o archivos relevantes,
  código de salida, duración y evidencia útil. No guardes credenciales.

## Calidad y cierre

- Los criterios de aceptación deben tener evidencia, incluidos errores esperados
  y persistencia cuando sea un requisito. No apruebes por texto optimista.
- Registra pruebas no ejecutadas y por qué. Una prueba bloqueada no es aprobada.
- Tras cambios, ejecuta las comprobaciones afectadas; amplía solo si los riesgos
  o fallos lo justifican. Reutiliza evidencia válida cuando nada relevante cambió.
- Asigna defectos por componente y causa, no por coincidencias de palabras.
- Prueba siempre la corrección final. No finalices por alcanzar un contador.
- Declara el estado real: en progreso, bloqueado o completado. Una espera externa
  requiere una explicación y un siguiente paso concreto, sin simular éxito.
