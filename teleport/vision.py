import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math
import time
import threading
import os
import sys
import ctypes
from teleport import config
from teleport.utils import ensure_model_exists
from teleport.network import broadcast_message, send_file
from teleport.clipboard import get_copied_files
from teleport.overlay import trigger_grab_overlay, trigger_cancel_overlay, trigger_interactive_hud
from teleport.kalman import KalmanFilter2D

# Índices dos landmarks da mão
WRIST = 0
INDEX_FINGER_TIP = 8
PINKY_TIP = 20
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]

# Variáveis globais para o fluxo assíncrono
hand_was_open = False
hand_was_fist = False
last_gesture_text = "NENHUM"
last_status_text = ""
latest_frame_lock = threading.Lock()
latest_landmarks = None

last_valid_wrist_pos = None
last_valid_time = 0

# Kalman Filter instance
kalman = KalmanFilter2D(process_variance=2e-4, measurement_variance=0.03)

def check_hand_pose(hand_landmarks):
    wrist = hand_landmarks[WRIST]
    def get_dist(p1, p2): return math.hypot(p1.x - p2.x, p1.y - p2.y)
        
    d_index_tip = get_dist(hand_landmarks[INDEX_FINGER_TIP], wrist)
    d_index_mcp = get_dist(hand_landmarks[5], wrist)
    d_middle_tip = get_dist(hand_landmarks[12], wrist)
    d_middle_mcp = get_dist(hand_landmarks[9], wrist)
    d_ring_tip = get_dist(hand_landmarks[16], wrist)
    d_ring_mcp = get_dist(hand_landmarks[13], wrist)
    d_pinky_tip = get_dist(hand_landmarks[PINKY_TIP], wrist)
    d_pinky_mcp = get_dist(hand_landmarks[17], wrist)
    
    r_index = d_index_tip / d_index_mcp if d_index_mcp > 0 else 0
    r_middle = d_middle_tip / d_middle_mcp if d_middle_mcp > 0 else 0
    r_ring = d_ring_tip / d_ring_mcp if d_ring_mcp > 0 else 0
    r_pinky = d_pinky_tip / d_pinky_mcp if d_pinky_mcp > 0 else 0
    
    index_open = r_index > 1.15
    middle_open = r_middle > 1.15
    ring_open = r_ring > 1.15
    pinky_open = r_pinky > 1.15
    
    index_closed = r_index < 0.95
    middle_closed = r_middle < 0.95
    ring_closed = r_ring < 0.95
    pinky_closed = r_pinky < 0.95
    
    is_fist = index_closed and middle_closed and ring_closed and pinky_closed
    is_open = index_open and middle_open and ring_open and pinky_open
    is_cancel = index_open and middle_open and ring_closed and pinky_closed
    return is_fist, is_open, is_cancel

def get_screen_resolution():
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except: pass
    try:
        import tkinter as tk
        root = tk.Tk()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return sw, sh
    except: return 1920, 1080

def vision_callback(result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global hand_was_open, hand_was_fist, last_gesture_text, last_status_text, latest_landmarks
    global last_valid_wrist_pos, last_valid_time
    
    if not config.app_state.get("camera_enabled"):
        return
        
    screen_width, screen_height = get_screen_resolution()
    
    with latest_frame_lock:
        if result.hand_landmarks:
            config.app_state.set("last_hand_time", time.time())
            latest_landmarks = result.hand_landmarks[0]
            hand_landmarks = result.hand_landmarks[0]
            
            # Filtro Corporativo de Proximidade (Ignora pessoas no fundo da sala)
            p0 = hand_landmarks[WRIST]
            p9 = hand_landmarks[9]
            palm_size = math.hypot(p9.x - p0.x, p9.y - p0.y)
            if palm_size < 0.06:
                return # Mão muito pequena/longe, ignora completamente.
            
            # Anti-Teletransporte Espacial (Ignora saltos irreais de mão)
            current_time = time.time()
            if last_valid_wrist_pos is not None:
                dx = p0.x - last_valid_wrist_pos[0]
                dy = p0.y - last_valid_wrist_pos[1]
                dist = math.hypot(dx, dy)
                dt = current_time - last_valid_time
                
                # Se pulou mais de 35% da tela em menos de 0.5s, ignora (foi para outra pessoa)
                if dt < 0.5 and dist > 0.35:
                    return
            
            # Atualiza a posição e tempo da mão real do usuário
            last_valid_wrist_pos = (p0.x, p0.y)
            last_valid_time = current_time
            
            is_fist, is_open, is_cancel = check_hand_pose(hand_landmarks)
            
            if is_fist: last_gesture_text = "PUNHO FECHADO"
            elif is_open: last_gesture_text = "MAO ABERTA"
            elif is_cancel: last_gesture_text = "CANCELAR (V)"
            else: last_gesture_text = "NENHUM"
            
            index_tip = hand_landmarks[INDEX_FINGER_TIP]
            x_mapped = (index_tip.x - 0.2) / 0.6 * screen_width
            y_mapped = (index_tip.y - 0.2) / 0.6 * screen_height
            x_mapped = max(0, min(screen_width, x_mapped))
            y_mapped = max(0, min(screen_height, y_mapped))
            
            # Aplica o Filtro de Kalman
            kx, ky = kalman.update(x_mapped, y_mapped)
            
            config.app_state.set("cursor_x", kx)
            config.app_state.set("cursor_y", ky)
            
            # Gesto Pinça
            pinch_ratio = math.hypot(hand_landmarks[4].x - hand_landmarks[8].x, hand_landmarks[4].y - hand_landmarks[8].y) / (palm_size or 0.001)
            config.app_state.set("pinch_active", (pinch_ratio < 0.25))
            config.app_state.set("fist_active", is_fist)
            
            # Fluxo Agarrar
            if is_open: hand_was_open = True
            if is_fist and hand_was_open:
                hand_was_open = False
                if not config.app_state.get("is_overlay_active") and not config.app_state.get("current_file") and not config.network_holder_ip:
                    print("[GESTO] Punho fechado detectado após mão aberta! Abrindo HUD de tela cheia...")
                    trigger_interactive_hud()
            
            # Fluxo Cancelar
            if is_cancel:
                if config.app_state.get("is_overlay_active"):
                    config.app_state.set("cancel_requested", True)
                elif config.app_state.get("current_file") is not None:
                    fname = config.app_state.get("current_file_name")
                    print(f"[GESTO] Cancelamento detectado! Soltando arquivo '{fname}'...")
                    config.app_state.set("current_file", None)
                    config.app_state.set("current_file_name", None)
                    broadcast_message("HOLDING:NONE")
                    hand_was_open = False
                    trigger_cancel_overlay(title="Cancelado", status="Transferência de arquivo abortada.")
                    time.sleep(1.5)
            
            # Fluxo Soltar (Receber)
            if is_fist: hand_was_fist = True
            if is_open and hand_was_fist:
                hand_was_fist = False
                if config.network_holder_ip and config.network_holder_ip != config.local_ip:
                    if not config.app_state.get("is_overlay_active"):
                        print(f"[GESTO] Mão aberta detectada após punho fechado! Resgatando do PC {config.network_holder_ip}...")
                        broadcast_message(f"GIVE_ME:{config.local_ip}")
                        config.network_holder_ip = None
                        time.sleep(2.0)
            
            if hand_was_open: last_status_text = "Pronto para fechar e agarrar"
            elif hand_was_fist: last_status_text = "Pronto para abrir e soltar"
            else: last_status_text = ""
        else:
            # Se não há mão por muito tempo (2s), reinicia o estado
            if time.time() - config.app_state.get("last_hand_time", time.time()) > 2.0:
                kalman.reset()
                config.app_state.set("cursor_x", 0)
                config.app_state.set("cursor_y", 0)
                config.app_state.set("pinch_active", False)
                config.app_state.set("fist_active", False)
                last_gesture_text = ""
                last_status_text = ""
                latest_landmarks = None
                last_valid_wrist_pos = None

def vision_loop():
    model_file = ensure_model_exists()
    
    base_options = python.BaseOptions(model_asset_path=model_file)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_hands=1,
        min_hand_detection_confidence=0.75,
        min_hand_presence_confidence=0.75,
        min_tracking_confidence=0.75,
        result_callback=vision_callback
    )
    detector = vision.HandLandmarker.create_from_options(options)
    cap = cv2.VideoCapture(0)
    
    sw, sh = get_screen_resolution()
    print(f"[IA] Resolução da tela detectada: {sw}x{sh}")
    print("[IA] Câmera iniciada no modo LIVE_STREAM com Filtro de Kalman!")

    while config.app_state.get("running"):
        if not config.app_state.get("camera_enabled"):
            time.sleep(0.5)
            if config.app_state.get("debug_mode"):
                cv2.destroyAllWindows()
            continue
            
        if time.time() - config.app_state.get("last_hand_time", time.time()) > 20.0:
            print("[IA] Auto-Sleep: Câmera desligada por inatividade. Pressione o atalho para acordar.")
            config.app_state.set("camera_enabled", False)
            if config.app_state.get("debug_mode"):
                cv2.destroyAllWindows()
            continue

        ret, frame = cap.read()
        if not ret: continue

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Envia para processamento assíncrono (não trava o loop)
        try:
            timestamp_ms = int(time.time() * 1000)
            detector.detect_async(mp_image, timestamp_ms)
        except Exception as e:
            if config.app_state.get("debug_mode"):
                print(f"[IA] Erro na detecção async: {e}")
            
        if config.app_state.get("debug_mode"):
            with latest_frame_lock:
                if latest_landmarks:
                    for lm in latest_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                        
            cv2.putText(frame, f"Gesto: {last_gesture_text}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            if last_status_text:
                cv2.putText(frame, f"Status: {last_status_text}", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            c_file = config.app_state.get("current_file_name")
            if c_file:
                cv2.putText(frame, f"Segurando: {c_file}", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
            cv2.imshow("AI Teleport - Debug", frame)
            
            try:
                if cv2.getWindowProperty("AI Teleport - Debug", cv2.WND_PROP_VISIBLE) < 1:
                    config.app_state.set("running", False)
                    if config.global_icon: config.global_icon.stop()
                    os._exit(0)
            except: pass

            if cv2.waitKey(1) & 0xFF == ord('q'):
                config.app_state.set("running", False)
                if config.global_icon: config.global_icon.stop()
                os._exit(0)
        else:
            cv2.destroyAllWindows()

    detector.close()
    cap.release()
    cv2.destroyAllWindows()
