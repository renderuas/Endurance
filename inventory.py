import json
import platform
import shutil
import subprocess
from pathlib import Path

import pandas as pd


def crear_directorio_salida(ruta_base: str) -> Path:
    directorio = Path(ruta_base)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def normalizar_resultado_json(stdout: str) -> list[dict]:
    """Convierte la salida JSON de PowerShell en una lista de diccionarios."""
    datos = json.loads(stdout)
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        return [datos]
    return []


def exportar_winget(directorio_salida: Path) -> None:
    if platform.system().lower() != "windows":
        print("winget no esta disponible en este sistema (WSL/Linux/macOS). Se omite exportacion de winget.")
        return

    if shutil.which("winget") is None:
        print("winget no se encontro en PATH. Asegurate de ejecutar desde Windows con winget instalado.")
        return

    archivo_json = directorio_salida / "winget_apps.json"
    comando = ["winget", "export", "-o", str(archivo_json), "--accept-source-agreements"]

    print("Iniciando exportacion de Winget...")
    resultado = subprocess.run(comando, capture_output=True, text=True)

    if resultado.returncode == 0:
        print(f"Exportacion de Winget completada: {archivo_json}")
    else:
        print(f"Error al exportar Winget. Codigo: {resultado.returncode}")


def construir_comando_registro():
    rutas_registro = [
        r"HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        r"HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    ]
    rutas_serializadas = ", ".join(f"'{ruta}'" for ruta in rutas_registro)
    return (
        f"$paths = @({rutas_serializadas}); "
        "$items = foreach ($path in $paths) { Get-ItemProperty $path -ErrorAction SilentlyContinue }; "
        "$items | Select-Object DisplayName, DisplayVersion, Publisher, InstallLocation "
        "| Where-Object { $_.DisplayName } "
        "| Sort-Object DisplayName -Unique "
        "| ConvertTo-Json"
    )


def exportar_registro_windows(directorio_salida: Path) -> None:
    if platform.system().lower() != "windows":
        print("Registro de Windows no disponible en este sistema (WSL/Linux/macOS). Se omite exportacion de registro.")
        return

    archivo_csv = directorio_salida / "registry_apps.csv"
    comando_ps = construir_comando_registro()

    print("Iniciando escaneo del registro via PowerShell...")
    resultado = subprocess.run(["powershell", "-Command", comando_ps], capture_output=True, text=True)

    if resultado.returncode == 0 and resultado.stdout.strip():
        datos_json = normalizar_resultado_json(resultado.stdout)
        df = pd.DataFrame(datos_json)
        df = df.dropna(subset=["DisplayName"]).sort_values("DisplayName").drop_duplicates()
        df.to_csv(archivo_csv, index=False, encoding="utf-8")
        print(f"Exportacion del registro completada: {archivo_csv}")
    else:
        print("Error al leer el registro o no se encontraron aplicaciones.")


def ejecutar_inventario():
    ruta_salida = crear_directorio_salida("./outputs/discovery")
    exportar_winget(ruta_salida)
    exportar_registro_windows(ruta_salida)


if __name__ == "__main__":
    ejecutar_inventario()
