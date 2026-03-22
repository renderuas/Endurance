# Endurance Migration Tool

Batería de scripts en Python para automatizar la migración de un entorno Windows antiguo a una nueva arquitectura.

## Fases del Proyecto

1. **Fase 1: Auditoría e Inventario (Discovery)**
   - Exportación de software instalado (Winget y Registro).
   - Análisis de almacenamiento y detección de archivos pesados.
   - Identificación de archivos duplicados (MD5/SHA256).
   - Localización de configuraciones esenciales.

2. **Fase 2: Extracción y Respaldo (Backup)**
   - Escaneo inteligente de unidades montadas (excluye NAS W:, X:, Y:, Z:).
   - Copia selectiva de archivos importantes (documentos, multimedia, configuraciones).
   - Exclusión de carpetas temporales y basura (Temp, Cache, Recycle.Bin, Windows, etc.).
   - Estructura organizada en `backups/YYYY-MM-DD/` (un directorio por día).
   - Modo simulación por defecto (`dry_run=True`) para pruebas seguras.

3. **Fase 3: Restauración y Despliegue (Restore)**
   - Instalación masiva vía Winget.
   - Restauración de configuraciones.

## Requisitos
- Python 3.10+
- Plataforma: Windows (requiere acceso a unidades locales).
- Dependencias: `pip install -r requirements.txt` (pandas, pywin32, pytest).

## Uso
Ejecutar los scripts en orden secuencial comenzando por `inventory.py` (fase 1), luego `backup.py` (fase 2).

### backup.py
- **Comando**: `python backup.py` (destino por defecto: `./backups`)
- **Destino personalizado**: `python backup.py /ruta/al/destino`
- **Modo real**: Cambia `dry_run=True` a `False` en el código para copiar archivos de verdad.
- **Filtro de archivos**: Solo copia archivos con extensiones importantes (.docx, .jpg, .mp4, etc.), >10MB, o modificados en el último año.
- **Exclusiones**: Unidades NAS se detectan pero se excluyen con mensaje INFO. Carpetas temp/cache se omiten.
- **Estructura**: Crea subcarpetas por unidad (ej: `unidad-C/Documents/`).

## Notas
- Ejecuta desde PowerShell en Windows para acceso completo a unidades.
- El backup es selectivo: enfocado en datos de usuario, no en apps o sistema.
- Para migración completa, combina con `inventory.py` para software y configuraciones.
- Cambios recientes: Exclusión de NAS, timestamp diario, modo simulación por defecto.