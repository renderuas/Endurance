from datetime import datetime, timedelta
from pathlib import Path
import os

import pytest

import backup


@pytest.fixture
def base_config():
    return {
        "backup": {
            "dry_run": True,
            "exclude_drives": ["W", "X", "Y", "Z"],
            "important_extensions": [".txt", ".docx"],
            "min_file_size_mb": 1,
            "max_file_age_days": 30,
            "exclude_folders": ["SkipFolder", "Profile/LocalData"],
            "user_directories": ["Documents"],
            "global_directories": ["Public"],
        },
        "logging": {
            "level": "INFO",
            "format": "%(message)s",
        },
    }


def test_cargar_configuracion_aplica_valores_por_defecto(tmp_path):
    if backup.yaml is None:
        pytest.skip("PyYAML no esta disponible en este interprete")

    config_file = tmp_path / "config.yaml"
    config_file.write_text("backup:\n  dry_run: false\n", encoding="utf-8")

    config = backup.cargar_configuracion(config_file)

    assert config["backup"]["dry_run"] is False
    assert config["backup"]["min_file_size_mb"] == 10
    assert config["logging"]["level"] == "INFO"


def test_excluir_carpeta_soporta_subrutas(base_config):
    assert backup.excluir_carpeta(Path("C:/Users/Ana/Profile/LocalData/Cache"), base_config) is True
    assert backup.excluir_carpeta(Path("C:/Users/Ana/Documents"), base_config) is False


def test_es_archivo_importante_por_extension(base_config, tmp_path):
    archivo = tmp_path / "nota.txt"
    archivo.write_text("contenido", encoding="utf-8")

    assert backup.es_archivo_importante(archivo, base_config) is True


def test_es_archivo_importante_por_tamano(base_config, tmp_path):
    archivo = tmp_path / "video.bin"
    archivo.write_bytes(b"a" * (2 * 1024 * 1024))

    assert backup.es_archivo_importante(archivo, base_config) is True


def test_es_archivo_importante_por_antiguedad(base_config, tmp_path):
    archivo = tmp_path / "reciente.bin"
    archivo.write_bytes(b"123")
    reciente = datetime.now() - timedelta(days=2)
    timestamp = reciente.timestamp()
    os.utime(archivo, (timestamp, timestamp))

    assert backup.es_archivo_importante(archivo, base_config) is True


def test_copiar_archivos_en_dry_run_no_crea_directorios(base_config, tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "documento.txt").write_text("hola", encoding="utf-8")
    destino = tmp_path / "destino"

    copiados = backup.copiar_archivos(origen, destino, base_config, dry_run=True)

    assert copiados == 1
    assert destino.exists() is False


def test_copiar_archivos_copia_en_modo_real(base_config, tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "documento.txt").write_text("hola", encoding="utf-8")
    destino = tmp_path / "destino"

    copiados = backup.copiar_archivos(origen, destino, base_config, dry_run=False)

    assert copiados == 1
    assert (destino / "documento.txt").read_text(encoding="utf-8") == "hola"


def test_estimar_tamano_backup_omite_rutas_excluidas(base_config, tmp_path):
    docs = tmp_path / "Users" / "Ana" / "Documents"
    docs.mkdir(parents=True)
    (docs / "keep.txt").write_text("hola", encoding="utf-8")
    excluded = tmp_path / "Users" / "Ana" / "Profile" / "LocalData"
    excluded.mkdir(parents=True)
    (excluded / "cache.txt").write_text("hola", encoding="utf-8")

    mb, gb, archivos = backup.estimar_tamano_backup([tmp_path], base_config)

    assert archivos == 1
    assert mb > 0
    assert gb >= 0
