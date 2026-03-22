import logging
import os
import platform
import shutil
import string
from datetime import datetime
from pathlib import Path
import yaml

# Variables globales para la configuración
config = {}

def cargar_configuracion(archivo_config="config.yaml"):
    """Carga la configuración desde un archivo YAML"""
    global config
    config_path = Path(archivo_config)
    
    if not config_path.exists():
        print(f"Archivo de configuración no encontrado: {archivo_config}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"Configuración cargada desde: {archivo_config}")
        return True
    except Exception as e:
        print(f"Error cargando configuración: {e}")
        return False

def configurar_logging():
    """Configura el logging basado en la configuración"""
    if config and 'logging' in config:
        level = getattr(logging, config['logging'].get('level', 'INFO').upper())
        format_str = config['logging'].get('format', '%(asctime)s - %(levelname)s - %(message)s')
    else:
        level = logging.INFO
        format_str = '%(asctime)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(level=level, format=format_str, force=True)

def listar_unidades_montadas():
    """Lista unidades montadas en Windows (C:, D:, etc.)"""
    if platform.system().lower() != "windows":
        logging.warning("Listado de unidades solo disponible en Windows.")
        return []

    # Unidades a excluir desde configuración
    exclude_drives = config.get('backup', {}).get('exclude_drives', ['W', 'X', 'Y', 'Z'])
    unidades_excluidas = {f"{d}:\\" for d in exclude_drives}

    unidades = []
    for letra in string.ascii_uppercase:
        unidad = f"{letra}:\\"
        try:
            os.listdir(unidad)
            if unidad in unidades_excluidas:
                logging.info(f"Unidad {unidad} encontrada pero excluida (configuración).")
                continue
            unidades.append(unidad)
        except (OSError, PermissionError):
            logging.debug(f"Unidad {unidad} no accesible, omitiendo.")
    return unidades

def directorios_importantes_por_unidad(unidad):
    """Devuelve lista de directorios importantes en una unidad"""
    base = Path(unidad)
    importantes = []

    # Directorios de usuario y globales desde configuración
    user_dirs = config.get('backup', {}).get('user_directories', [])
    global_dirs = config.get('backup', {}).get('global_directories', [])

    # Directorios de usuario (si existe Users)
    users_dir = base / "Users"
    if users_dir.exists():
        try:
            for user_dir in users_dir.iterdir():
                if user_dir.is_dir():
                    for dir_name in user_dirs:
                        path = user_dir
                        for part in dir_name.split('/'):
                            path = path / part
                        try:
                            if path.exists():
                                importantes.append(path)
                        except (OSError, PermissionError):
                            logging.debug(f"Directorio {path} no accesible, omitiendo.")
        except (OSError, PermissionError):
            logging.debug(f"No se puede acceder a {users_dir}, omitiendo.")

    # Directorios globales
    for dir_name in global_dirs:
        path = base / dir_name
        try:
            if path.exists():
                importantes.append(path)
        except (OSError, PermissionError):
            logging.debug(f"Directorio {path} no accesible, omitiendo.")

    return importantes

def es_archivo_importante(archivo):
    """Determina si un archivo es importante basado en extensión, tamaño, etc."""
    if not archivo.is_file():
        return False

    # Extensiones importantes desde configuración
    extensiones_importantes = set(config.get('backup', {}).get('important_extensions', []))

    if archivo.suffix.lower() in extensiones_importantes:
        return True

    # Parámetros desde configuración
    min_size_mb = config.get('backup', {}).get('min_file_size_mb', 10)
    max_age_days = config.get('backup', {}).get('max_file_age_days', 365)

    # Archivos grandes o recientes
    try:
        stat = archivo.stat()
        tamaño_mb = stat.st_size / (1024 * 1024)
        edad_dias = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days

        if tamaño_mb > min_size_mb or edad_dias < max_age_days:
            return True
    except OSError:
        pass

    return False

def excluir_carpeta(carpeta):
    """Determina si una carpeta debe excluirse"""
    nombres_excluidos = set(config.get('backup', {}).get('exclude_folders', []))

    for parte in carpeta.parts:
        if parte in nombres_excluidos:
            return True

    return False

def estimar_tamaño_backup(directorios):
    """Estima el tamaño total de los archivos a copiar en MB"""
    total_bytes = 0
    archivos_contados = 0

    for directorio in directorios:
        try:
            for root, dirs, files in os.walk(directorio):
                root_path = Path(root)

                # Excluir carpetas
                dirs[:] = [d for d in dirs if not excluir_carpeta(root_path / d)]

                for file in files:
                    archivo = root_path / file
                    if es_archivo_importante(archivo):
                        try:
                            total_bytes += archivo.stat().st_size
                            archivos_contados += 1
                        except (OSError, PermissionError):
                            pass
        except (OSError, PermissionError):
            pass

    total_mb = total_bytes / (1024 * 1024)
    total_gb = total_mb / 1024

    return total_mb, total_gb, archivos_contados

def copiar_archivos(origen, destino, dry_run=False):
    """Copia archivos importantes de origen a destino"""
    origen_path = Path(origen)
    destino_path = Path(destino)
    archivos_copiados = 0

    if not origen_path.exists():
        logging.warning(f"Origen no existe: {origen}")
        return 0

    try:
        for root, dirs, files in os.walk(origen_path):
            root_path = Path(root)

            # Excluir carpetas
            dirs[:] = [d for d in dirs if not excluir_carpeta(root_path / d)]

            for file in files:
                archivo = root_path / file
                if es_archivo_importante(archivo):
                    # Crear estructura relativa
                    relativa = archivo.relative_to(origen_path)
                    destino_archivo = destino_path / relativa

                    destino_archivo.parent.mkdir(parents=True, exist_ok=True)

                    if dry_run:
                        logging.debug(f"Simular copia: {archivo} -> {destino_archivo}")
                    else:
                        try:
                            shutil.copy2(archivo, destino_archivo)
                            logging.debug(f"Copiado: {archivo} -> {destino_archivo}")
                        except (OSError, PermissionError) as e:
                            logging.error(f"Error copiando {archivo}: {e}")
                            continue
                    archivos_copiados += 1
    except (OSError, PermissionError) as e:
        logging.error(f"Error accediendo a {origen_path}: {e}")

    return archivos_copiados

def crear_backup(destino_base="./backups"):
    """Función principal para crear backup"""
    if platform.system().lower() != "windows":
        logging.error("Backup solo disponible en Windows.")
        return

    # Crear directorio de respaldo
    fecha = datetime.now().strftime("%Y-%m-%d")
    respaldo_base = Path(destino_base) / fecha
    respaldo_base.mkdir(parents=True, exist_ok=True)

    logging.info(f"Iniciando backup en: {respaldo_base}")

    unidades = listar_unidades_montadas()
    logging.info(f"Unidades encontradas: {unidades}")

    # Recopilar todos los directorios importantes
    todos_directorios = []
    for unidad in unidades:
        logging.info(f"Procesando unidad: {unidad}")
        directorios = directorios_importantes_por_unidad(unidad)
        todos_directorios.extend(directorios)

    # Estimación de tamaño
    if todos_directorios:
        mb, gb, num_archivos = estimar_tamaño_backup(todos_directorios)
        logging.info(f"Estimación: {num_archivos} archivos, ~{mb:.2f} MB ({gb:.2f} GB)")
    else:
        logging.warning("No se encontraron directorios importantes para respaldar.")
        return

    # Obtener modo dry_run desde configuración
    dry_run = config.get('backup', {}).get('dry_run', True)
    logging.info(f"Modo simulación: {dry_run}")

    # Copiar archivos
    total_archivos = 0
    for unidad in unidades:
        directorios = directorios_importantes_por_unidad(unidad)
        for directorio in directorios:
            nombre_relativo = directorio.relative_to(Path(unidad))
            destino = respaldo_base / f"unidad-{Path(unidad).drive.strip(':')}" / nombre_relativo

            logging.info(f"Copiando {directorio} -> {destino}")
            total_archivos += copiar_archivos(directorio, destino, dry_run=dry_run)

    logging.info(f"Backup completado. Total archivos procesados: {total_archivos}")

if __name__ == "__main__":
    import sys
    
    # Cargar configuración
    config_file = "config.yaml"
    if not cargar_configuracion(config_file):
        print("No se puede continuar sin configuración.")
        sys.exit(1)
    
    # Configurar logging
    configurar_logging()
    
    destino = sys.argv[1] if len(sys.argv) > 1 else "./backups"
    crear_backup(destino)
