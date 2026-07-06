import threading
import time
import signal
from teleport import config
from teleport.network import udp_broadcast_listener, udp_broadcast_sender, tcp_file_receiver
from teleport.vision import vision_loop
from teleport.gui import setup_tray
from teleport.clipboard import clipboard_history_tracker

# Registra os manipuladores de sinais para capturar Ctrl+C no terminal
signal.signal(signal.SIGINT, config.force_exit)
signal.signal(signal.SIGTERM, config.force_exit)

# ==========================================
# INICIALIZAÇÃO DO SISTEMA
# ==========================================
if __name__ == "__main__":
    # Importante: O IP local já foi detectado durante a importação do teleport.network
    print(f"Iniciando AI Teleport. Meu IP local é: {config.local_ip}")
    
    # Inicia as threads em background para rede, clipboard e detecção visual
    threading.Thread(target=udp_broadcast_listener, daemon=True).start()
    threading.Thread(target=udp_broadcast_sender, daemon=True).start()
    threading.Thread(target=tcp_file_receiver, daemon=True).start()
    threading.Thread(target=clipboard_history_tracker, daemon=True).start()
    threading.Thread(target=vision_loop, daemon=True).start()
    
    # Inicia a interface (pystray) em uma thread separada (daemon) para não travar a thread principal
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # Mantém a thread principal ativa e respondendo a sinais (como Ctrl+C e fechar janela)
    try:
        while config.app_state.get("running"):
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        print("\n[SISTEMA] Encerramento solicitado...")
    finally:
        config.force_exit()