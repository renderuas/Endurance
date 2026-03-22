# Endurance Migration Tool

Batería de scripts en Python para automatizar la migración de un entorno Windows antiguo a una nueva arquitectura. 

## Fases del Proyecto

1. **Fase 1: Auditoría e Inventario (Discovery)**
   - Exportación de software instalado (Winget y Registro).
   - Análisis de almacenamiento y detección de archivos pesados.
   - Identificación de archivos duplicados (MD5/SHA256).
   - Localización de configuraciones esenciales.

2. **Fase 2: Extracción y Respaldo (Backup)**
   - Copia de seguridad estructurada.

3. **Fase 3: Restauración y Despliegue (Restore)**
   - Instalación masiva vía Winget.
   - Restauración de configuraciones.

## Requisitos
- Python 3.10+
- Dependencias: `pip install -r requirements.txt`

## Uso
Ejecutar los scripts en orden secuencial comenzando por `src/fase1_discovery/inventory.py`.