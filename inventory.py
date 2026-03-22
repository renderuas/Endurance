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

def exportar_winget(directorio_salida: Path) -> None:
    if platform.system().lower() != "windows":
        print("winget no está disponible en este sistema (WSL/Linux/macOS). Se omite exportación de winget.")
        return

    if shutil.which("winget") is None:
        print("winget no se encontró en PATH. Asegúrate de ejecutar desde Windows con winget instalado.")
        return

    archivo_json = directorio_salida / "winget_apps.json"
    comando = ["winget", "export", "-o", str(archivo_json), "--accept-source-agreements"]
    
    print("Iniciando exportación de Winget...")
    resultado = subprocess.run(comando, capture_output=True, text=True)
    
    if resultado.returncode == 0:
        print(f"Exportación de Winget completada: {archivo_json}")
    else:
        print(f"Error al exportar Winget. Código: {resultado.returncode}")

def exportar_registro_windows(directorio_salida: Path) -> None:
    if platform.system().lower() != "windows":
        print("Registro de Windows no disponible en este sistema (WSL/Linux/macOS). Se omite exportación de registro.")
        return

    archivo_csv = directorio_salida / "registry_apps.csv"
    
    comando_ps = (
        "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
        "| Select-Object DisplayName, DisplayVersion, Publisher "
        "| ConvertTo-Json"
    )
    
    print("Iniciando escaneo del registro vía PowerShell...")
    resultado = subprocess.run(["powershell", "-Command", comando_ps], capture_output=True, text=True)
    
    if resultado.returncode == 0 and resultado.stdout.strip():
        datos_json = json.loads(resultado.stdout)
        df = pd.DataFrame(datos_json)
        
        df = df.dropna(subset=['DisplayName'])
        df.to_csv(archivo_csv, index=False, encoding='utf-8')
        print(f"Exportación del registro completada: {archivo_csv}")
    else:
        print("Error al leer el registro o no se encontraron aplicaciones.")

def ejecutar_inventario():
    ruta_salida = crear_directorio_salida("./outputs/discovery")
    exportar_winget(ruta_salida)
    exportar_registro_windows(ruta_salida)

if __name__ == "__main__":
    ejecutar_inventario()