import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math
import time
import threading
import os
from teleport import config
from teleport.utils import ensure_model_exists
from teleport.network import broadcast_message, send_file
from teleport.gui import prompt_file_selection

# Índices dos landmarks da mão
WRIST = 0
THUMB_TIP = 4
INDEX_FINGER_TIP = 8
PINKY_TIP = 20

# Conexões para desenhar o esqueleto da mão
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Polegar
    (0, 5), (5, 6), (6, 7), (7, 8),        # Indicador
    (5, 9), (9, 10), (10, 11), (11, 12),    # Médio
    (9, 13), (13, 14), (14, 15), (15, 16),  # Anelar
    (13, 17), (17, 18), (18, 19), (19, 20), # Mínimo
    (0, 17)                                # Base da palma
]

def check_hand_pose(hand_landmarks):
    """Retorna o estado das pontas dos dedos e identifica o gesto."""
    wrist = hand_landmarks[WRIST]
    
    def get_dist(p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)
        
    d_index_tip = get_dist(hand_landmarks[INDEX_FINGER_TIP], wrist)
    d_index_mcp = get_dist(hand_landmarks[5], wrist)
    
    d_middle_tip = get_dist(hand_landmarks[12], wrist)
    d_middle_mcp = get_dist(hand_landmarks[9], wrist)
    
    d_ring_tip = get_dist(hand_landmarks[16], wrist)
    d_ring_mcp = get_dist(hand_landmarks[13], wrist)
    
    d_pinky_tip = get_dist(hand_landmarks[PINKY_TIP], wrist)
    d_pinky_mcp = get_dist(hand_landmarks[17], wrist)
    
    # Razões tip/mcp em relação ao pulso
    r_index = d_index_tip / d_index_mcp if d_index_mcp > 0 else 0
    r_middle = d_middle_tip / d_middle_mcp if d_middle_mcp > 0 else 0
    r_ring = d_ring_tip / d_ring_mcp if d_ring_mcp > 0 else 0
    r_pinky = d_pinky_tip / d_pinky_mcp if d_pinky_mcp > 0 else 0
    
    # Dedos abertos se o tip estiver bem mais longe do pulso do que o MCP
    # Dedos fechados se o tip estiver mais perto ou muito próximo do MCP em relação ao pulso
    index_open = r_index > 1.15
    middle_open = r_middle > 1.15
    ring_open = r_ring > 1.15
    pinky_open = r_pinky > 1.15
    
    index_closed = r_index < 0.95
    middle_closed = r_middle < 0.95
    ring_closed = r_ring < 0.95
    pinky_closed = r_pinky < 0.95
    
    # Gesto do punho fechado (Fist): todos os 4 dedos principais fechados
    is_fist = index_closed and middle_closed and ring_closed and pinky_closed
    
    # Gesto da mão aberta: todos os 4 dedos abertos
    is_open = index_open and middle_open and ring_open and pinky_open
    
    # Gesto de Cancelamento (Paz/V): Indicador e Médio abertos, Anelar e Mínimo fechados
    is_cancel = index_open and middle_open and ring_closed and pinky_closed
    
    return is_fist, is_open, is_cancel

def vision_loop():
    """Thread principal da câmera para processar os gestos."""
    model_file = ensure_model_exists()
    
    # Configura o detector do MediaPipe Tasks
    base_options = python.BaseOptions(model_asset_path=model_file)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1
    )
    detector = vision.HandLandmarker.create_from_options(options)
    
    cap = cv2.VideoCapture(0)
    
    # Variáveis de estado do fluxo de gestos
    hand_was_open = False
    hand_was_fist = False
    
    print("[IA] Câmera iniciada. Abra a mão e feche o punho para agarrar um arquivo!")

    while config.state["running"]:
        if not config.state["camera_enabled"]:
            time.sleep(0.5)
            if config.state["debug_mode"]:
                cv2.destroyAllWindows()
            continue

        ret, frame = cap.read()
        if not ret: 
            continue

        # Espelhar o frame horizontalmente para ficar intuitivo (como um espelho)
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # O detector do MediaPipe Tasks espera um mp.Image em formato RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Processar IA
        try:
            results = detector.detect(mp_image)
        except Exception as e:
            if config.state["debug_mode"]:
                print(f"[IA] Erro na detecção: {e}")
            continue
            
        gesture_text = "NENHUM"
        status_text = ""
        
        if results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                if config.state["debug_mode"]:
                    # Desenhar as conexões
                    for connection in HAND_CONNECTIONS:
                        start_idx, end_idx = connection
                        p1 = hand_landmarks[start_idx]
                        p2 = hand_landmarks[end_idx]
                        pt1 = (int(p1.x * w), int(p1.y * h))
                        pt2 = (int(p2.x * w), int(p2.y * h))
                        cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
                    
                    # Desenhar os pontos das articulações
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                
                # Identifica pose do gesto
                is_fist, is_open, is_cancel = check_hand_pose(hand_landmarks)
                
                # Define texto para renderização no modo debug
                if is_fist:
                    gesture_text = "PUNHO FECHADO"
                elif is_open:
                    gesture_text = "MAO ABERTA"
                elif is_cancel:
                    gesture_text = "CANCELAR (V)"
                
                # 1. Fluxo de Agarrar Arquivo (PC de Origem)
                if is_open:
                    hand_was_open = True
                    
                if is_fist and hand_was_open:
                    hand_was_open = False # Reseta a transição
                    if config.state["current_file"] is None:
                        print("[GESTO] Punho fechado detectado após mão aberta! Abrindo seletor...")
                        threading.Thread(target=prompt_file_selection, daemon=True).start()
                
                # 2. Fluxo de Cancelamento (PC de Origem)
                if is_cancel:
                    if config.state["current_file"] is not None:
                        print(f"[GESTO] Cancelamento detectado! Soltando arquivo '{config.state['current_file_name']}'...")
                        config.state["current_file"] = None
                        config.state["current_file_name"] = None
                        broadcast_message("HOLDING:NONE")
                        hand_was_open = False
                        time.sleep(1.0) # Delay para evitar detecções consecutivas
                
                # 3. Fluxo de Soltar/Receber Arquivo (PC de Destino)
                if is_fist:
                    hand_was_fist = True
                    
                if is_open and hand_was_fist:
                    hand_was_fist = False # Reseta a transição
                    if config.network_holder_ip and config.network_holder_ip != config.local_ip:
                        print(f"[GESTO] Mão aberta detectada após punho fechado! Resgatando do PC {config.network_holder_ip}...")
                        broadcast_message(f"GIVE_ME:{config.local_ip}")
                        config.network_holder_ip = None
                        time.sleep(2.0)
                        
                # Textos de status para desenhar no frame
                if hand_was_open:
                    status_text = "Pronto para fechar e agarrar"
                elif hand_was_fist:
                    status_text = "Pronto para abrir e soltar"
        else:
            # Se nenhuma mão for detectada, reinicia as transições de pose locais
            hand_was_open = False
            hand_was_fist = False

        # Mostra a janela se estiver no modo debug
        if config.state["debug_mode"]:
            # Desenha status dos gestos no frame
            cv2.putText(frame, f"Gesto: {gesture_text}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            if status_text:
                cv2.putText(frame, f"Status: {status_text}", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if config.state["current_file_name"]:
                cv2.putText(frame, f"Segurando: {config.state['current_file_name']}", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
            cv2.imshow("AI Teleport - Debug", frame)
            
            # Detecta se a janela foi fechada pelo botão "X"
            try:
                if cv2.getWindowProperty("AI Teleport - Debug", cv2.WND_PROP_VISIBLE) < 1:
                    print("[SISTEMA] Janela de visualização fechada pelo usuário. Encerrando o aplicativo...")
                    config.state["running"] = False
                    if config.global_icon:
                        config.global_icon.stop()
                    os._exit(0)
            except Exception:
                pass

            # Permite fechar a janela com 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[SISTEMA] Tecla 'q' pressionada. Encerrando o aplicativo...")
                config.state["running"] = False
                if config.global_icon:
                    config.global_icon.stop()
                os._exit(0)
        else:
            # Força fechamento se o usuário desabilitou o debug pelo menu
            cv2.destroyAllWindows()

    detector.close()
    cap.release()
    cv2.destroyAllWindows()
