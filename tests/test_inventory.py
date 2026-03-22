import inventory


def test_normalizar_resultado_json_con_objeto():
    data = inventory.normalizar_resultado_json('{"DisplayName": "App"}')

    assert data == [{"DisplayName": "App"}]


def test_normalizar_resultado_json_con_lista():
    data = inventory.normalizar_resultado_json('[{"DisplayName": "App1"}, {"DisplayName": "App2"}]')

    assert len(data) == 2
    assert data[1]["DisplayName"] == "App2"


def test_construir_comando_registro_incluye_ramas_principales():
    comando = inventory.construir_comando_registro()

    assert "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*" in comando
    assert "HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*" in comando
    assert "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*" in comando
    assert "Sort-Object DisplayName -Unique" in comando
