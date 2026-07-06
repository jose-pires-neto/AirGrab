import sys
import os
import ctypes
import subprocess
import time
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
    """Recupera caminhos de arquivos copiados no clipboard (área de transferência) de forma multiplataforma."""
    files = []

    # Windows (Lendo CF_HDROP com ctypes para evitar dependências pesadas)
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
            print(f"[REDE] Erro ao ler clipboard do Windows: {e}")

    # Linux (Lendo MIME text/uri-list gerado por Nautilus/Dolphin via xclip)
    elif sys.platform.startswith("linux"):
        try:
            out = subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-t", "text/uri-list", "-o"],
                stderr=subprocess.DEVNULL
            )
            lines = out.decode("utf-8").strip().split("\n")
            for line in lines:
                if line.startswith("file://"):
                    # Decodifica URL-encoded (ex: %20 para espaço)
                    path = unquote(line[7:])
                    # Remove quebra de linha extra se houver
                    path = path.replace("\r", "").replace("\n", "")
                    if os.path.exists(path):
                        files.append(path)
        except Exception:
            pass

    # macOS (Lendo classes furl da área de transferência nativa via osascript)
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(
                ["osascript", "-e", "get POSIX path of (the clipboard as «class furl»)"],
                stderr=subprocess.DEVNULL
            )
            path = out.decode("utf-8").strip()
            if os.path.exists(path):
                files.append(path)
        except Exception:
            pass

    return files

def clipboard_history_tracker():
    """Rastreador executado em background para manter um histórico dos últimos 5 caminhos de arquivos copiados."""
    last_detected = None
    print("[SISTEMA] Rastreador de histórico da área de transferência ativo.")
    while config.state["running"]:
        try:
            files = get_copied_files()
            if files:
                new_file = files[0]
                if new_file != last_detected:
                    last_detected = new_file
                    history = config.state["clipboard_history"]
                    
                    # Remove ocorrência anterior do mesmo arquivo para movê-lo ao topo
                    history = [h for h in history if h != new_file]
                    history.insert(0, new_file)
                    config.state["clipboard_history"] = history[:5]
                    print(f"[CLIPBOARD] Histórico atualizado. Topo: '{os.path.basename(new_file)}'")
        except Exception as e:
            pass
        time.sleep(0.5)
