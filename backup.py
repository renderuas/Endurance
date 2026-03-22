import logging
import os
import platform
import shutil
import string
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


DEFAULT_CONFIG = {
    "backup": {
        "dry_run": True,
        "exclude_drives": ["W", "X", "Y", "Z"],
        "important_extensions": [],
        "min_file_size_mb": 10,
        "max_file_age_days": 365,
        "exclude_folders": [],
        "user_directories": [],
        "global_directories": [],
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s",
    },
}


def cargar_configuracion(archivo_config="config.yaml"):
    """Carga la configuracion desde YAML y aplica valores por defecto."""
    config_path = Path(archivo_config)

    if not config_path.exists():
        raise FileNotFoundError(f"Archivo de configuracion no encontrado: {archivo_config}")

    if yaml is None:
        raise ModuleNotFoundError("PyYAML no esta instalado. Ejecuta pip install -r requirements.txt")

    with open(config_path, "r", encoding="utf-8") as handle:
        user_config = yaml.safe_load(handle) or {}

    config = {
        "backup": {**DEFAULT_CONFIG["backup"], **user_config.get("backup", {})},
        "logging": {**DEFAULT_CONFIG["logging"], **user_config.get("logging", {})},
    }
    print(f"Configuracion cargada desde: {archivo_config}")
    return config


def configurar_logging(config):
    """Configura el logging basado en la configuracion."""
    logging_config = config.get("logging", {})
    level = getattr(logging, logging_config.get("level", "INFO").upper(), logging.INFO)
    format_str = logging_config.get("format", "%(asctime)s - %(levelname)s - %(message)s")
    logging.basicConfig(level=level, format=format_str, force=True)


def listar_unidades_montadas(config):
    """Lista unidades montadas en Windows (C:, D:, etc.)."""
    if platform.system().lower() != "windows":
        logging.warning("Listado de unidades solo disponible en Windows.")
        return []

    exclude_drives = config.get("backup", {}).get("exclude_drives", ["W", "X", "Y", "Z"])
    unidades_excluidas = {f"{drive}:\\" for drive in exclude_drives}

    unidades = []
    for letra in string.ascii_uppercase:
        unidad = f"{letra}:\\"
        try:
            os.listdir(unidad)
            if unidad in unidades_excluidas:
                logging.info(f"Unidad {unidad} encontrada pero excluida (configuracion).")
                continue
            unidades.append(unidad)
        except (OSError, PermissionError):
            logging.debug(f"Unidad {unidad} no accesible, omitiendo.")
    return unidades


def directorios_importantes_por_unidad(unidad, config):
    """Devuelve lista de directorios importantes en una unidad."""
    base = Path(unidad)
    importantes = []

    user_dirs = config.get("backup", {}).get("user_directories", [])
    global_dirs = config.get("backup", {}).get("global_directories", [])

    users_dir = base / "Users"
    if users_dir.exists():
        try:
            for user_dir in users_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                for dir_name in user_dirs:
                    path = user_dir
                    for part in str(dir_name).split("/"):
                        path = path / part
                    try:
                        if path.exists():
                            importantes.append(path)
                    except (OSError, PermissionError):
                        logging.debug(f"Directorio {path} no accesible, omitiendo.")
        except (OSError, PermissionError):
            logging.debug(f"No se puede acceder a {users_dir}, omitiendo.")

    for dir_name in global_dirs:
        path = base / dir_name
        try:
            if path.exists():
                importantes.append(path)
        except (OSError, PermissionError):
            logging.debug(f"Directorio {path} no accesible, omitiendo.")

    return importantes


def es_archivo_importante(archivo, config):
    """Determina si un archivo es importante por extension, tamano o antiguedad."""
    if not archivo.is_file():
        return False

    extensiones_importantes = {
        extension.lower() for extension in config.get("backup", {}).get("important_extensions", [])
    }
    if archivo.suffix.lower() in extensiones_importantes:
        return True

    min_size_mb = config.get("backup", {}).get("min_file_size_mb", 10)
    max_age_days = config.get("backup", {}).get("max_file_age_days", 365)

    try:
        stat = archivo.stat()
        tamano_mb = stat.st_size / (1024 * 1024)
        edad_dias = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
        if tamano_mb > min_size_mb or edad_dias < max_age_days:
            return True
    except OSError:
        pass

    return False


def _normalizar_partes(path_like):
    return [part.lower() for part in Path(path_like).parts if part not in ("\\", "/")]


def _contiene_subruta(partes, patron):
    if len(patron) > len(partes):
        return False

    for index in range(len(partes) - len(patron) + 1):
        if partes[index:index + len(patron)] == patron:
            return True
    return False


def excluir_carpeta(carpeta, config):
    """Determina si una carpeta debe excluirse, aceptando nombres simples o subrutas."""
    nombres_excluidos = config.get("backup", {}).get("exclude_folders", [])
    partes_carpeta = _normalizar_partes(carpeta)

    for nombre in nombres_excluidos:
        patron = [part.lower() for part in str(nombre).replace("\\", "/").split("/") if part]
        if not patron:
            continue
        if len(patron) == 1 and patron[0] in partes_carpeta:
            return True
        if len(patron) > 1 and _contiene_subruta(partes_carpeta, patron):
            return True

    return False


def estimar_tamano_backup(directorios, config):
    """Estima el tamano total de los archivos a copiar en MB."""
    total_bytes = 0
    archivos_contados = 0

    for directorio in directorios:
        try:
            for root, dirs, files in os.walk(directorio):
                root_path = Path(root)
                dirs[:] = [directory for directory in dirs if not excluir_carpeta(root_path / directory, config)]

                for file_name in files:
                    archivo = root_path / file_name
                    if es_archivo_importante(archivo, config):
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


def copiar_archivos(origen, destino, config, dry_run=False):
    """Copia archivos importantes de origen a destino."""
    origen_path = Path(origen)
    destino_path = Path(destino)
    archivos_copiados = 0

    if not origen_path.exists():
        logging.warning(f"Origen no existe: {origen}")
        return 0

    try:
        for root, dirs, files in os.walk(origen_path):
            root_path = Path(root)
            dirs[:] = [directory for directory in dirs if not excluir_carpeta(root_path / directory, config)]

            for file_name in files:
                archivo = root_path / file_name
                if not es_archivo_importante(archivo, config):
                    continue

                relativa = archivo.relative_to(origen_path)
                destino_archivo = destino_path / relativa

                if dry_run:
                    logging.debug(f"Simular copia: {archivo} -> {destino_archivo}")
                else:
                    try:
                        destino_archivo.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(archivo, destino_archivo)
                        logging.debug(f"Copiado: {archivo} -> {destino_archivo}")
                    except (OSError, PermissionError) as error:
                        logging.error(f"Error copiando {archivo}: {error}")
                        continue
                archivos_copiados += 1
    except (OSError, PermissionError) as error:
        logging.error(f"Error accediendo a {origen_path}: {error}")

    return archivos_copiados


def crear_backup(config, destino_base="./backups"):
    """Funcion principal para crear backup."""
    if platform.system().lower() != "windows":
        logging.error("Backup solo disponible en Windows.")
        return

    dry_run = config.get("backup", {}).get("dry_run", True)
    fecha = datetime.now().strftime("%Y-%m-%d")
    respaldo_base = Path(destino_base) / fecha
    if not dry_run:
        respaldo_base.mkdir(parents=True, exist_ok=True)

    logging.info(f"Iniciando backup en: {respaldo_base}")
    logging.info(f"Modo simulacion: {dry_run}")

    unidades = listar_unidades_montadas(config)
    logging.info(f"Unidades encontradas: {unidades}")

    todos_directorios = []
    for unidad in unidades:
        logging.info(f"Procesando unidad: {unidad}")
        directorios = directorios_importantes_por_unidad(unidad, config)
        todos_directorios.extend(directorios)

    if not todos_directorios:
        logging.warning("No se encontraron directorios importantes para respaldar.")
        return

    mb, gb, num_archivos = estimar_tamano_backup(todos_directorios, config)
    logging.info(f"Estimacion: {num_archivos} archivos, ~{mb:.2f} MB ({gb:.2f} GB)")

    total_archivos = 0
    for unidad in unidades:
        directorios = directorios_importantes_por_unidad(unidad, config)
        for directorio in directorios:
            nombre_relativo = directorio.relative_to(Path(unidad))
            destino = respaldo_base / f"unidad-{Path(unidad).drive.strip(':')}" / nombre_relativo
            logging.info(f"Copiando {directorio} -> {destino}")
            total_archivos += copiar_archivos(directorio, destino, config, dry_run=dry_run)

    logging.info(f"Backup completado. Total archivos procesados: {total_archivos}")


if __name__ == "__main__":
    import sys

    config_file = "config.yaml"
    yaml_error = getattr(yaml, "YAMLError", ValueError) if yaml is not None else ValueError
    try:
        config = cargar_configuracion(config_file)
    except (FileNotFoundError, ModuleNotFoundError, yaml_error) as error:
        print(f"No se puede continuar sin configuracion valida: {error}")
        sys.exit(1)

    configurar_logging(config)

    destino = sys.argv[1] if len(sys.argv) > 1 else "./backups"
    crear_backup(config, destino)
