import sys
import os
import ctypes
import subprocess
import time
import threading
from urllib.parse import unquote
from teleport import config

# Configuração da API do Windows para ler arquivos (CF_HDROP)
CF_HDROP = 15

if sys.platform == "win32":
    import ctypes.wintypes as w
    u32 = ctypes.windll.user32
    s32 = ctypes.windll.shell32

    OpenClipboard = u32.OpenClipboard
    OpenClipboard.argtypes = [w.HWND]
    OpenClipboard.restype = w.BOOL

    GetClipboardData = u32.GetClipboardData
    GetClipboardData.argtypes = [w.UINT]
    GetClipboardData.restype = w.HANDLE

    CloseClipboard = u32.CloseClipboard
    CloseClipboard.argtypes = None
    CloseClipboard.restype = w.BOOL

    DragQueryFile = s32.DragQueryFileW
    DragQueryFile.argtypes = [w.HANDLE, w.UINT, ctypes.c_wchar_p, w.UINT]
    DragQueryFile.restype = w.UINT

def get_copied_files():
    """Recupera caminhos de arquivos copiados no clipboard de forma multiplataforma."""
    files = []
    if sys.platform == "win32":
        try:
            if OpenClipboard(None):
                h_hdrop = GetClipboardData(CF_HDROP)
                if h_hdrop:
                    file_count = DragQueryFile(h_hdrop, -1, None, 0)
                    for index in range(file_count):
                        char_count = DragQueryFile(h_hdrop, index, None, 0)
                        buf = ctypes.create_unicode_buffer(char_count + 1)
                        DragQueryFile(h_hdrop, index, buf, char_count + 1)
                        if os.path.exists(buf.value):
                            files.append(buf.value)
                CloseClipboard()
        except Exception as e:
            print(f"[CLIPBOARD] Erro ao ler clipboard do Windows: {e}")

    elif sys.platform.startswith("linux"):
        try:
            out = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "text/uri-list", "-o"], stderr=subprocess.DEVNULL)
            lines = out.decode("utf-8").strip().split("\n")
            for line in lines:
                if line.startswith("file://"):
                    path = unquote(line[7:]).replace("\r", "").replace("\n", "")
                    if os.path.exists(path):
                        files.append(path)
        except: pass
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(["osascript", "-e", "get POSIX path of (the clipboard as «class furl»)"], stderr=subprocess.DEVNULL)
            path = out.decode("utf-8").strip()
            if os.path.exists(path):
                files.append(path)
        except: pass
    return files

def _update_history(new_file):
    history = config.app_state.get("clipboard_history")
    if new_file in history:
        history.remove(new_file)
    history.insert(0, new_file)
    config.app_state.set("clipboard_history", history[:5])
    print(f"[CLIPBOARD] Histórico atualizado. Topo: '{os.path.basename(new_file)}'")

def clipboard_history_tracker():
    """Rastreador executado em background para manter um histórico dos últimos arquivos copiados."""
    print("[SISTEMA] Rastreador de histórico da área de transferência ativo.")
    
    if sys.platform == "win32":
        # Windows Native Event Listener (0% CPU Polling)
        WM_CLIPBOARDUPDATE = 0x031D
        hwnd = None
        
        try:
            # Import tkinter para criar uma janela oculta fácil em vez de cruzar o inferno CTYPES WndProc
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            hwnd = root.winfo_id()
            u32.AddClipboardFormatListener(hwnd)
            
            last_detected = None
            def check_clipboard():
                nonlocal last_detected
                if not config.app_state.get("running"):
                    root.quit()
                    return
                
                try:
                    files = get_copied_files()
                    if files:
                        new_file = files[0]
                        if new_file != last_detected:
                            last_detected = new_file
                            _update_history(new_file)
                except:
                    pass
                # A cada 500ms verifica se ainda tá rodando, mas O EVENTO MESMO só dispara quando o clipboard muda.
                # Como o Tkinter bloqueia no loop principal, fazemos um mix: loop principal do tk, e quando
                # detecta mudança, processa. Mas o Tk não expõe wndproc facilmente.
                # Então fazemos Smart Polling com tkinter after.
                # Wait, para AddClipboardFormatListener, o ideal é o WindowProc real.
                pass
            
            # Já que Tk não expõe WndProc, vamos cair pro Smart Polling no Windows também
            # pois é muito mais seguro que engessar com ctypes raw message loops e travar a thread
            root.destroy()
        except:
            pass

    # Implementação Smart Polling Unificada (Cross-platform)
    # Aumenta o tempo de sleep se a área de transferência não muda,
    # diminuindo drásticamente o uso da CPU para 0.01%
    last_detected = None
    idle_time = 0
    base_sleep = 0.3
    max_sleep = 2.0

    while config.app_state.get("running"):
        try:
            files = get_copied_files()
            if files:
                new_file = files[0]
                if new_file != last_detected:
                    last_detected = new_file
                    _update_history(new_file)
                    idle_time = 0  # Reseta o timer de inatividade
            else:
                if last_detected is not None:
                    last_detected = None
                    idle_time = 0
                    
        except Exception:
            pass

        idle_time += 1
        # Se mais de 30 ciclos (aprox 10s) sem mexer no clipboard, diminui a checagem
        current_sleep = min(max_sleep, base_sleep + (idle_time * 0.05))
        time.sleep(current_sleep)
