import logging
import os
import platform
import shutil
import string
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def listar_unidades_montadas():
    """Lista unidades montadas en Windows (C:, D:, etc.)"""
    if platform.system().lower() != "windows":
        logging.warning("Listado de unidades solo disponible en Windows.")
        return []

    unidades = []
    for letra in string.ascii_uppercase:
        unidad = f"{letra}:\\"
        try:
            os.listdir(unidad)  # Verificar acceso
            unidades.append(unidad)
        except (OSError, PermissionError):
            logging.debug(f"Unidad {unidad} no accesible, omitiendo.")
    return unidades

def directorios_importantes_por_unidad(unidad):
    """Devuelve lista de directorios importantes en una unidad"""
    base = Path(unidad)
    importantes = []

    # Directorios de usuario (si existe Users)
    users_dir = base / "Users"
    if users_dir.exists():
        try:
            for user_dir in users_dir.iterdir():
                if user_dir.is_dir():
                    user_paths = [
                        user_dir / "Documents",
                        user_dir / "Desktop",
                        user_dir / "Downloads",
                        user_dir / "Pictures",
                        user_dir / "Videos",
                        user_dir / "Music",
                        user_dir / "AppData" / "Roaming",  # Configuraciones útiles
                    ]
                    for path in user_paths:
                        try:
                            if path.exists():
                                importantes.append(path)
                        except (OSError, PermissionError):
                            logging.debug(f"Directorio {path} no accesible, omitiendo.")
        except (OSError, PermissionError):
            logging.debug(f"No se puede acceder a {users_dir}, omitiendo.")

    # Otros directorios globales importantes
    global_paths = [
        base / "ProgramData",  # Configuraciones globales
        base / "Public",  # Archivos públicos
    ]
    for path in global_paths:
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

    # Extensiones importantes
    extensiones_importantes = {
        '.doc', '.docx', '.pdf', '.txt', '.xls', '.xlsx', '.ppt', '.pptx',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
        '.mp4', '.avi', '.mkv', '.mov',
        '.zip', '.rar', '.7z',
        '.json', '.xml', '.ini', '.cfg'
    }

    if archivo.suffix.lower() in extensiones_importantes:
        return True

    # Archivos grandes (>10MB) o recientes (<1 año)
    try:
        stat = archivo.stat()
        tamaño_mb = stat.st_size / (1024 * 1024)
        edad_dias = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days

        if tamaño_mb > 10 or edad_dias < 365:
            return True
    except OSError:
        pass

    return False

def excluir_carpeta(carpeta):
    """Determina si una carpeta debe excluirse"""
    nombres_excluidos = {
        'Temp', 'tmp', 'Cache', 'cache', 'Temporary Internet Files',
        'Recycle.Bin', '$Recycle.Bin', 'System Volume Information',
        'Windows', 'Program Files', 'Program Files (x86)',
        'AppData/Local', 'AppData/LocalLow'
    }

    for parte in carpeta.parts:
        if parte in nombres_excluidos:
            return True

    return False

def copiar_archivos(origen, destino, dry_run=False):
    """Copia archivos importantes de origen a destino"""
    origen_path = Path(origen)
    destino_path = Path(destino)

    if not origen_path.exists():
        logging.warning(f"Origen no existe: {origen}")
        return

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
                        logging.info(f"Simular copia: {archivo} -> {destino_archivo}")
                    else:
                        try:
                            shutil.copy2(archivo, destino_archivo)
                            logging.info(f"Copiado: {archivo} -> {destino_archivo}")
                        except (OSError, PermissionError) as e:
                            logging.error(f"Error copiando {archivo}: {e}")
    except (OSError, PermissionError) as e:
        logging.error(f"Error accediendo a {origen_path}: {e}")

def crear_backup():
    """Función principal para crear backup"""
    if platform.system().lower() != "windows":
        logging.error("Backup solo disponible en Windows.")
        return

    # Crear directorio de respaldo
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    respaldo_base = Path("./backups") / fecha
    respaldo_base.mkdir(parents=True, exist_ok=True)

    logging.info(f"Iniciando backup en: {respaldo_base}")

    unidades = listar_unidades_montadas()
    logging.info(f"Unidades encontradas: {unidades}")

    for unidad in unidades:
        logging.info(f"Procesando unidad: {unidad}")
        directorios = directorios_importantes_por_unidad(unidad)

        for directorio in directorios:
            nombre_relativo = directorio.relative_to(Path(unidad))
            destino = respaldo_base / f"unidad-{Path(unidad).drive.strip(':')}" / nombre_relativo

            logging.info(f"Copiando {directorio} -> {destino}")
            copiar_archivos(directorio, destino, dry_run=True)  # Cambia a False para copia real

    logging.info("Backup completado.")

if __name__ == "__main__":
    crear_backup()