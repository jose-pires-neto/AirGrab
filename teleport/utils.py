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

def ensure_sfx_exist():
    """Gera efeitos sonoros básicos em WAV se não existirem."""
    import struct, math
    
    def generate_wav(filename, samples, sample_rate=44100):
        if os.path.exists(filename): return
        with open(filename, 'wb') as f:
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + len(samples) * 2))
            f.write(b'WAVEfmt ')
            f.write(struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
            f.write(b'data')
            f.write(struct.pack('<I', len(samples) * 2))
            for s in samples:
                f.write(struct.pack('<h', int(max(-32768, min(32767, s * 32767)))))
                
    # Pop sound
    sr = 44100
    duration = 0.15
    t_samples = int(sr * duration)
    pop_samples = []
    for i in range(t_samples):
        t = i / sr
        freq = 600 + 1500 * math.exp(-t * 40)
        env = math.exp(-t * 25)
        pop_samples.append(math.sin(2 * math.pi * freq * t) * env * 0.5)
    generate_wav('pop.wav', pop_samples)
    
    # Swoosh sound
    duration = 0.4
    t_samples = int(sr * duration)
    swoosh_samples = []
    import random
    for i in range(t_samples):
        t = i / sr
        env = math.exp(-((t - 0.1) ** 2) * 40)
        noise = random.uniform(-1, 1)
        # Apply lowpass filter effect simply by smoothing (cheap hack)
        swoosh_samples.append(noise * env * 0.3)
    
    # Simple smoothing for lowpass effect
    for i in range(1, len(swoosh_samples)):
        swoosh_samples[i] = swoosh_samples[i]*0.1 + swoosh_samples[i-1]*0.9
        
    generate_wav('swoosh.wav', swoosh_samples)
