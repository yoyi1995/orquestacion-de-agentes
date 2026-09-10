# Verificación de la migración

Fecha de verificación: 2026-09-09 UTC (2026-09-08 en Guayaquil).

## Resultado técnico

- Dirección, planificación, herramientas y delegación a cargo de la sesión
  nativa de Codex. CLI inspeccionado: 0.153.4; función multiagente habilitada.
- Perfiles architect/backend/frontend/reviewer/qa/devops bajo demanda, transmitidos
  como instrucciones. No son tipos registrados por la mera existencia del MD.
- Árbol `agente/` retirado después de verificar respaldo y destinos absolutos.
- `factory/tools.py` coincide byte por byte con el auxiliar corregido anterior.
- Una variable de proveedor retirada de `.env`; no había otras variables y el
  archivo quedó vacío. Ningún valor de credencial se imprimió ni se respaldó.
- Inspección AST de `factory/`, `scripts/` y `tests/`: todas las importaciones son
  de biblioteca estándar o módulos locales. Sin dependencias externas de la fábrica.
- Búsqueda en archivos activos y código propio de productos: sin referencias al
  proveedor retirado, sus modelos, fallbacks o bucle manual de turnos.
- `.venv` y dependencias de productos son instalaciones históricas conservadas;
  no forman parte de las dependencias funcionales del controlador nuevo.

## Pruebas

Comando ejecutado desde la raíz con Python 3.14.7:

```powershell
py -3 -B -S -m unittest discover -s tests -v
```

Resultado: 17 pruebas descubiertas, 16 aprobadas y 1 omitida. Tiempo informado
por unittest: 5,577 segundos. La omitida necesita permiso para crear un enlace
simbólico en Windows; las pruebas de escape por ruta absoluta y `..` sí pasaron.

Cobertura: comandos con éxito/error/timeout, salida parcial, terminación real de
un descendiente Windows, timeout inválido, operaciones de archivos y rutas,
creación de productos sin stack, prevención de sobrescrituras, registro JSON y
separación stdout/stderr. Integración real de los CLI en un workspace temporal:
crear producto, compilar un archivo con `py_compile`, registrar el resultado,
rechazar una colisión y devolver fallo/timeout con códigos de salida no cero.

No se instalaron paquetes ni se ejecutaron las aplicaciones de los productos
anteriores. La suite no acredita la calidad funcional de esos productos.
La delegación nativa se ejerció en esta sesión durante auditoría, implementación
y revisión; no se simuló una API de subagentes dentro de los scripts.

## Respaldo y productos existentes

Archivo: `backups/pre-migration-20260909T014524Z.zip`.

Referencia histórica local: los backups y productos generados no se distribuyen
con el repositorio. Este informe no implica que el ZIP esté disponible en un clon.

- 41 archivos propios verificados contra el manifiesto; 53.233 bytes de ZIP.
- SHA-256: `4989b17b4e1bcf9bb3e8e64e6a9d41ab4042caefb1ee5d2adad23e22cdd97fe6`.
- Sin `.venv`, `node_modules`, cachés ni archivos de variables de entorno/claves.
- Incluye los archivos propios de ambos productos presentes al inicio.
- Los 15 archivos propios de `prueba_fabrica_02` mantienen sus hashes originales.

Durante la comprobación final se detectó la ausencia de `prueba_fabrica_01`, que
sí existía al tomar el respaldo. Ningún comando de migración se dirigió a eliminar
o modificar esa carpeta. Sus siete archivos propios siguen disponibles en el ZIP;
no se restauran automáticamente para evitar deshacer una posible acción del usuario.
