# Endurance Migration Tool

Scripts en Python para auditar y respaldar un entorno Windows antes de una migracion.

## Alcance actual

### Fase 1: Auditoria e inventario
- Exporta aplicaciones instaladas desde `winget` cuando esta disponible.
- Exporta aplicaciones detectadas en el registro de Windows desde `HKLM` 64-bit, `HKLM` Wow6432Node y `HKCU`.
- Genera artefactos en `outputs/discovery/`.

### Fase 2: Backup selectivo
- Escanea unidades montadas en Windows y excluye drives configurados, como NAS o externos.
- Copia solo archivos relevantes segun extension, tamano o antiguedad.
- Omite carpetas temporales o no deseadas segun `config.yaml`.
- Organiza el respaldo por fecha en `backups/YYYY-MM-DD/`.
- Usa `dry_run: true` por defecto para validar el alcance sin copiar archivos ni crear carpetas destino.

## Requisitos
- Python 3.10+
- Windows para ejecutar discovery completo y backup real
- Dependencias: `pip install -r requirements.txt`

## Configuracion
El comportamiento del backup se controla desde [`config.yaml`](/home/renderuas/Migracion/Endurance/config.yaml).

Ajustes principales:
- `backup.dry_run`: modo simulacion seguro
- `backup.exclude_drives`: unidades a omitir
- `backup.important_extensions`: extensiones que siempre se respaldan
- `backup.min_file_size_mb`: tamano minimo para incluir archivos grandes
- `backup.max_file_age_days`: ventana para incluir archivos recientes
- `backup.exclude_folders`: carpetas o subrutas a excluir
- `backup.user_directories`: directorios por perfil de usuario
- `backup.global_directories`: directorios globales a revisar

## Uso
Ejecuta primero el inventario y despues el backup.

### Inventario
```bash
python inventory.py
```

### Backup
```bash
python backup.py
```

### Destino personalizado
```bash
python backup.py D:/migracion/backups
```

Para ejecutar una copia real, cambia `backup.dry_run` a `false` en `config.yaml`.

## Tests
```bash
pytest
```

La suite valida reglas de exclusion, seleccion de archivos, comportamiento de `dry_run` y parseo del inventario.

## Estructura
- `inventory.py`: discovery de aplicaciones instaladas
- `backup.py`: backup selectivo configurable
- `config.yaml`: configuracion del backup y logging
- `tests/`: cobertura automatizada de la logica critica
