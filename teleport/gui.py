import os
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageDraw
import pystray
from teleport import config
from teleport.network import broadcast_message
import keyboard
from tkinter import simpledialog

current_hotkey_hook = None

def trigger_camera_from_shortcut():
    current_state = config.app_state.get("camera_enabled")
    if current_state:
        print(f"[ATALHO] Câmera DESLIGADA pelo atalho {config.app_state.get('shortcut')}!")
        config.app_state.set("camera_enabled", False)
    else:
        print(f"[ATALHO] Câmera LIGADA pelo atalho {config.app_state.get('shortcut')}!")
        config.app_state.set("camera_enabled", True)
        config.app_state.set("last_hand_time", __import__('time').time())

def setup_hotkey():
    global current_hotkey_hook
    if current_hotkey_hook:
        try: keyboard.remove_hotkey(current_hotkey_hook)
        except: pass
    try:
        current_hotkey_hook = keyboard.add_hotkey(config.app_state.get("shortcut"), trigger_camera_from_shortcut)
    except Exception as e:
        print(f"[SISTEMA] Erro ao registrar atalho: {e}")

def change_shortcut(icon, item):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    new_shortcut = simpledialog.askstring("Alterar Atalho AirGrab", "Digite o novo atalho (ex: ctrl+shift+a, alt+z):", initialvalue=config.app_state.get("shortcut"))
    root.destroy()
    if new_shortcut:
        config.app_state.set("shortcut", new_shortcut.lower())
        config.save_settings()
        setup_hotkey()

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
        pystray.MenuItem(lambda text: f"Alterar Atalho ({config.app_state.get('shortcut')})", change_shortcut),
        pystray.MenuItem(lambda text: "Modo Visual (Debug): ON" if config.app_state.get("debug_mode") else "Modo Visual (Debug): OFF", toggle_debug),
        pystray.MenuItem("Sair", exit_app)
    )
    setup_hotkey()
    config.global_icon = pystray.Icon("teleport", create_image(), "AI Teleport", menu)
    config.global_icon.run()
