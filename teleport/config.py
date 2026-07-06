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
    "camera_enabled": True,
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
    "cancel_requested": False
})

# Por conveniência, podemos expor o "state" para ser um atalho (como um proxy), 
# mas o ideal é que todos passem a chamar app_state.get/set
# Para retrocompatibilidade rápida, vamos redefinir 'state' como app_state._state não é o ideal,
# Mas sim renomear os usos no código. Portanto, vamos remover o dict state exposto.

def force_exit(sig=None, frame=None):
    """Fecha o aplicativo e encerra o processo imediatamente."""
    print("\n[SISTEMA] Sinal de encerramento recebido (Ctrl+C). Fechando aplicativo...")
    app_state.set("running", False)
    try:
        if global_icon:
            global_icon.stop()
    except:
        pass
    os._exit(0)
