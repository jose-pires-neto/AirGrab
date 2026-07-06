import os
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageDraw
import pystray
from teleport import config
from teleport.network import broadcast_message

def create_image():
    """Gera um ícone verde simples (uma bolinha) para a barra de tarefas."""
    image = Image.new('RGB', (64, 64), color=(255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill=(0, 200, 0))
    return image

def toggle_camera(icon, item):
    config.app_state.set("camera_enabled", not config.app_state.get("camera_enabled"))

def toggle_sharing(icon, item):
    config.app_state.set("sharing_enabled", not config.app_state.get("sharing_enabled"))

def toggle_debug(icon, item):
    config.app_state.set("debug_mode", not config.app_state.get("debug_mode"))

def exit_app(icon, item):
    print("[SISTEMA] Encerrando pelo menu da bandeja...")
    config.app_state.set("running", False)
    icon.stop()
    os._exit(0)

def prompt_file_selection():
    """Abre uma janela nativa do SO para escolher o arquivo sem travar a IA."""
    if config.app_state.get("selecting_file"):
        return
    config.app_state.set("selecting_file", True)
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True) # Garante que apareça por cima de outras janelas
        file_path = filedialog.askopenfilename(title="AI Teleport: Selecione o arquivo para agarrar")
        root.destroy()
    except Exception as e:
        print(f"[SISTEMA] Erro ao abrir seletor de arquivos: {e}")
        file_path = None
        
    config.app_state.set("selecting_file", False)
    
    if file_path:
        config.app_state.set("current_file", file_path)
        config.app_state.set("current_file_name", os.path.basename(file_path))
        print(f"[GESTO] Arquivo '{config.app_state.get("current_file_name")}' AGARRADO!")
        broadcast_message(f"HOLDING:{config.local_ip}")
    else:
        print("[GESTO] Seleção cancelada. Mão vazia.")

def clear_current_file(icon, item):
    if config.app_state.get("current_file"):
        print(f"[SISTEMA] Arquivo '{config.app_state.get("current_file_name")}' liberado manualmente.")
        config.app_state.set("current_file", None)
        config.app_state.set("current_file_name", None)
        broadcast_message("HOLDING:NONE")

def setup_tray():
    """Cria o menu acessível ao clicar com botão direito no ícone."""
    menu = pystray.Menu(
        pystray.MenuItem(lambda text: f"Soltar Arquivo ({config.app_state.get("current_file_name")})" if config.app_state.get("current_file") else "Mão Vazia", clear_current_file, enabled=lambda item: config.app_state.get("current_file") is not None),
        pystray.MenuItem(lambda text: "Câmera: LIGADA" if config.app_state.get("camera_enabled") else "Câmera: DESLIGADA", toggle_camera),
        pystray.MenuItem(lambda text: "Compartilhamento: ON" if config.app_state.get("sharing_enabled") else "Compartilhamento: OFF", toggle_sharing),
        pystray.MenuItem(lambda text: "Modo Visual (Debug): ON" if config.app_state.get("debug_mode") else "Modo Visual (Debug): OFF", toggle_debug),
        pystray.MenuItem("Sair", exit_app)
    )
    config.global_icon = pystray.Icon("teleport", create_image(), "AI Teleport", menu)
    config.global_icon.run()
