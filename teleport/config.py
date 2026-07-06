import os
import sys

# ==========================================
# CONFIGURAÇÕES GERAIS E VARIÁVEIS DE ESTADO
# ==========================================
UDP_PORT = 50000
TCP_PORT = 50001

global_icon = None
peer_ip = None
local_ip = None
network_holder_ip = None

state = {
    "camera_enabled": True,
    "sharing_enabled": True,
    "debug_mode": True,  # Abre a janela da câmera para ver o que está acontecendo
    "running": True,
    "current_file": None,
    "current_file_name": None,
    "selecting_file": False,
    # Variáveis adicionadas para o AirGrab interativo
    "clipboard_history": [],
    "cursor_x": 0,
    "cursor_y": 0,
    "pinch_active": False,
    "fist_active": False,
    "is_overlay_active": False,
    "cancel_requested": False
}

def force_exit(sig=None, frame=None):
    """Fecha o aplicativo e encerra o processo imediatamente."""
    print("\n[SISTEMA] Sinal de encerramento recebido (Ctrl+C). Fechando aplicativo...")
    state["running"] = False
    try:
        if global_icon:
            global_icon.stop()
    except:
        pass
    os._exit(0)
