import os
import sys
from teleport.state import StateManager

# ==========================================
# CONFIGURAÇÕES GERAIS E VARIÁVEIS DE ESTADO
# ==========================================
UDP_PORT = 50000
TCP_PORT = 50001

global_icon = None
peer_ip = None
local_ip = None
network_holder_ip = None

# Substituindo dicionário global pelo StateManager thread-safe
app_state = StateManager({
    "camera_enabled": False,
    "sharing_enabled": True,
    "debug_mode": False,  # Abre a janela da câmera para ver o que está acontecendo
    "running": True,
    "current_file": None,
    "current_file_name": None,
    "selecting_file": False,
    "clipboard_history": [],
    "cursor_x": 0,
    "cursor_y": 0,
    "pinch_active": False,
    "fist_active": False,
    "is_overlay_active": False,
    "cancel_requested": False,
    "shortcut": "ctrl+shift+a"
})

def load_settings():
    settings_file = os.path.join(os.path.dirname(__file__), "..", "settings.json")
    if os.path.exists(settings_file):
        try:
            import json
            with open(settings_file, "r") as f:
                data = json.load(f)
                if "shortcut" in data:
                    app_state.set("shortcut", data["shortcut"])
        except: pass

def save_settings():
    settings_file = os.path.join(os.path.dirname(__file__), "..", "settings.json")
    try:
        import json
        with open(settings_file, "w") as f:
            json.dump({"shortcut": app_state.get("shortcut")}, f)
    except: pass

load_settings()

def force_exit(sig=None, frame=None):
    """Fecha o aplicativo e encerra o processo imediatamente."""
    print("\n[SISTEMA] Sinal de encerramento recebido (Ctrl+C). Fechando aplicativo...")
    app_state.set("running", False)
    save_settings()
    try:
        if global_icon:
            global_icon.stop()
    except:
        pass
    os._exit(0)
