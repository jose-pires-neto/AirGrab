import os
import sys
import urllib.request

def ensure_model_exists():
    """Garante que o arquivo de modelo do MediaPipe existe e retorna seu caminho correto."""
    # 1. Primeiro tenta o caminho temporário do PyInstaller (caso esteja embutido)
    try:
        meipass_path = os.path.join(sys._MEIPASS, "hand_landmarker.task")
        if os.path.exists(meipass_path):
            return meipass_path
    except AttributeError:
        pass

    # 2. Se não estiver no PyInstaller ou não estiver embutido, usa o diretório local
    local_path = "hand_landmarker.task"
    if not os.path.exists(local_path):
        print("[SISTEMA] Arquivo hand_landmarker.task não encontrado no diretório local. Iniciando download...")
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        try:
            urllib.request.urlretrieve(url, local_path)
            print("[SISTEMA] Download concluído com sucesso!")
        except Exception as e:
            print(f"[ERRO] Falha ao baixar o modelo: {e}")
            raise e
    return local_path
