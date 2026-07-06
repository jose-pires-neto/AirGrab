import pygame, os, sys, ctypes, math, time, threading
from teleport import config
from teleport.network import broadcast_message
from teleport.components.bubbles import Bubble, ExplorerBubble, WaterRipple, draw_hud_header, format_size, _load_thumbnail_base, _make_circular_thumb
from teleport.components.particles import BubblePopParticle, GlowParticle

COLOR_KEY     = (1, 1, 1)          
TEXT_COLOR    = (255, 255, 255)
SUBTEXT_COLOR = (180, 200, 225)
GLOW_HOVER    = (0, 235, 255)      
GLOW_GRAB     = (0, 255, 140)      
GLOW_WARN     = (255, 70, 55)      

def _rb(): return os.urandom(1)[0] / 255.0

def open_file_explorer_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(title="Selecione um arquivo para transferir")
        root.destroy()
        return selected
    except Exception as e:
        print(f"[HUD] Erro ao abrir dialog de arquivos: {e}")
        return None

def run_interactive_overlay():
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pygame.init(); pygame.font.init()
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    if sw == 0 or sh == 0: sw, sh = 1920, 1080

    screen = pygame.display.set_mode((sw, sh), pygame.NOFRAME)
    pygame.display.set_caption("AirGrab HUD")

    if sys.platform == "win32":
        hwnd = pygame.display.get_wm_info()["window"]
        u32 = ctypes.windll.user32
        style = u32.GetWindowLongW(hwnd, -20)
        u32.SetWindowLongW(hwnd, -20, style | 0x80000)
        ck = (COLOR_KEY[2] << 16) | (COLOR_KEY[1] << 8) | COLOR_KEY[0]
        u32.SetLayeredWindowAttributes(hwnd, ck, 0, 1)

    history = config.app_state.get("clipboard_history", [])
    has_history = len(history) > 0
    bubbles = []
    br = 82
    
    cx = sw // 2; cy = int(sh * 0.56)
    explorer_b = ExplorerBubble(cx, cy, br)
    
    n = len(history)
    if n > 0:
        orbit_radius = 210 + n * 8 
        angle_step = (2 * math.pi) / n
        start_angle = -math.pi / 2 
        for i, path in enumerate(history):
            b = Bubble(i, path, br)
            ang = start_angle + i * angle_step
            b.ox = cx + int(math.cos(ang) * orbit_radius)
            b.oy = cy + int(math.sin(ang) * orbit_radius)
            b.x = b.ox; b.y = b.oy
            bubbles.append(b)

    particles = []
    ripples = [WaterRipple(sw//2, sh//2, max_radius=max(sw,sh), speed=30, color=(0,180,255))]

    try:
        fmain = pygame.font.SysFont("Segoe UI", 22, bold=True)
        fsub  = pygame.font.SysFont("Segoe UI", 13)
        fwarn = pygame.font.SysFont("Segoe UI", 20, bold=True)
        finfo = pygame.font.SysFont("Segoe UI", 13)
    except Exception:
        fmain = pygame.font.Font(None, 28); fsub  = pygame.font.Font(None, 18)
        fwarn = pygame.font.Font(None, 26); finfo = pygame.font.Font(None, 18)

    hand_x = hand_y = sw // 2
    last_seen = time.time()
    clock = pygame.time.Clock()
    running = True; sel = None
    popping = False; closing = False; close_t = 0.0
    trigger_dialog_file = False

    print("[HUD] Liquid Bubble Selector inicializado.")

    while running:
        if not config.app_state.get("running") or not config.app_state.get("is_overlay_active"):
            running = False

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                if not closing:
                    closing = True; close_t = time.time()
                    ripples.append(WaterRipple(sw//2,sh//2,max(sw,sh),32,GLOW_WARN))

        cam_x = config.app_state.get("cursor_x"); cam_y = config.app_state.get("cursor_y")
        pinch = config.app_state.get("pinch_active")

        if config.app_state.get("cancel_requested"):
            # O estado já foi resetado lá, mas não importa, recebemos o sinal!
            if not closing:
                closing = True; close_t = time.time()
                ripples.append(WaterRipple(sw//2,sh//2,max(sw,sh),32,GLOW_WARN))

        if cam_x > 0 and cam_y > 0:
            last_seen = time.time()
            hand_x = int(hand_x * 0.65 + cam_x * 0.35)
            hand_y = int(hand_y * 0.65 + cam_y * 0.35)
        elif time.time() - last_seen > 5.0 and not closing:
            closing = True; close_t = time.time()
            ripples.append(WaterRipple(sw//2,sh//2,max(sw,sh),32,GLOW_WARN))

        screen.fill(COLOR_KEY)
        asurf = pygame.Surface((sw, sh), pygame.SRCALPHA)

        draw_hud_header(asurf, sw, sh, fmain, fsub, popping=popping)

        if not popping and not closing:
            explorer_b.is_hovered = False
            for b in bubbles: b.is_hovered = False
            closest = None
            min_d = float("inf")
            
            d_exp = math.hypot(hand_x - explorer_b.x, hand_y - explorer_b.y)
            if d_exp < 175:
                min_d = d_exp; closest = explorer_b
                
            for b in bubbles:
                d = math.hypot(hand_x - b.x, hand_y - b.y)
                if d < 175 and d < min_d:
                    min_d = d; closest = b
                    
            if closest:
                closest.is_hovered = True
                ang = math.atan2(hand_y - closest.y, hand_x - closest.x)
                if closest == explorer_b:
                    closest.x = cx + int(math.cos(ang) * 12)
                    closest.y = cy + int(math.sin(ang) * 12)
                else:
                    closest.x += int(math.cos(ang) * 3.5)
                    closest.y += int(math.sin(ang) * 3.5)
                    
                if pinch:
                    if closest == explorer_b:
                        explorer_b.is_popped = True
                        popping = True
                        trigger_dialog_file = True
                        for b in bubbles:
                            for _ in range(15): particles.append(BubblePopParticle(b.x, b.y, (100, 210, 255)))
                    else:
                        sel = closest
                        popping = True
                        sel.is_popped = True
                        for _ in range(24): particles.append(BubblePopParticle(explorer_b.x, explorer_b.y, (100, 210, 255)))
                        for b in bubbles:
                            if b != sel:
                                for _ in range(20): particles.append(BubblePopParticle(b.x, b.y, (100, 210, 255)))
            else:
                explorer_b.x = int(explorer_b.x * 0.8 + cx * 0.2)
                explorer_b.y = int(explorer_b.y * 0.8 + cy * 0.2)

        if not popping or trigger_dialog_file:
            explorer_b.update()
            if popping and trigger_dialog_file and explorer_b.scale >= 1.5 and not closing:
                for _ in range(45): particles.append(BubblePopParticle(explorer_b.x, explorer_b.y, GLOW_GRAB))
                closing = True; close_t = time.time()
                ripples.append(WaterRipple(explorer_b.x, explorer_b.y, max_radius=max(sw, sh), speed=32, color=GLOW_GRAB))
            else: explorer_b.draw(asurf)

        for b in bubbles:
            if not popping or b == sel:
                b.update()
                if popping and b == sel and b.scale >= 1.5 and not closing:
                    for _ in range(45): particles.append(BubblePopParticle(b.x, b.y, GLOW_GRAB))
                    closing = True; close_t = time.time()
                    ripples.append(WaterRipple(b.x, b.y, max_radius=max(sw, sh), speed=32, color=GLOW_GRAB))
                    config.app_state.set("current_file", sel.path)
                    config.app_state.set("current_file_name", sel.name)
                    broadcast_message(f"HOLDING:{config.local_ip}")
                    sel = None
                else: b.draw(asurf)

        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
            else: p.draw(asurf)

        for rp in ripples[:]:
            rp.update()
            if rp.is_done(): ripples.remove(rp)
            else: rp.draw(asurf)

        if not has_history:
            draw_outlined = lambda s, text, f, x_c, y_pos, col: s.blit(f.render(text, True, col), (x_c - f.render(text, True, col).get_width() // 2, y_pos))
            draw_outlined(asurf, "Área de Transferência Vazia", fwarn, cx, cy - 130, GLOW_WARN)
            draw_outlined(asurf, "Selecione o botao central para escolher um arquivo do computador", finfo, cx, cy - 100, SUBTEXT_COLOR)

        if cam_x > 0 and not closing:
            ro = 9 if pinch else 15
            cc = GLOW_GRAB if pinch else GLOW_HOVER
            pygame.draw.circle(asurf,cc,(hand_x,hand_y),ro+9,1)
            pygame.draw.circle(asurf,cc,(hand_x,hand_y),ro,2)
            pygame.draw.circle(asurf,cc,(hand_x,hand_y),3)

        if closing and (time.time() - close_t > 0.65): running = False

        screen.blit(asurf,(0,0))
        pygame.display.flip()
        clock.tick(60)

    pygame.display.quit(); pygame.quit()
    config.app_state.set("is_overlay_active", False)
    
    if trigger_dialog_file:
        selected_file = open_file_explorer_dialog()
        if selected_file and os.path.exists(selected_file):
            config.app_state.set("current_file", selected_file)
            config.app_state.set("current_file_name", os.path.basename(selected_file))
            broadcast_message(f"HOLDING:{config.local_ip}")


def run_overlay_loop(mode, file_path=None, custom_title=None, custom_status=None):
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pygame.init(); pygame.font.init()
    w,h = 550,350
    GC=(0,255,128); DC=(0,191,255); CC=(255,69,58)
    if   mode=="grab": gc,tt,st=GC, custom_title or "AirGrabbed!",  custom_status or "Arquivo capturado"
    elif mode=="drop": gc,tt,st=DC, custom_title or "AirDropped!",  custom_status or "Arquivo recebido com sucesso!"
    else:              gc,tt,st=CC, custom_title or "Cancelado",     custom_status or "Transferencia abortada."

    screen = pygame.display.set_mode((w,h), pygame.NOFRAME)
    if sys.platform=="win32":
        hwnd=pygame.display.get_wm_info()["window"]
        u32=ctypes.windll.user32
        u32.SetWindowLongW(hwnd,-20,u32.GetWindowLongW(hwnd,-20)|0x80000)
        u32.SetLayeredWindowAttributes(hwnd,0xFF00FF,0,1)

    try:
        ft=pygame.font.SysFont("Segoe UI",26,bold=True)
        fb=pygame.font.SysFont("Segoe UI",16)
        fs=pygame.font.SysFont("Segoe UI",13)
    except Exception:
        ft=pygame.font.Font(None,32); fb=pygame.font.Font(None,20); fs=pygame.font.Font(None,16)

    fname=fsize=""; thumb=None
    if file_path and os.path.exists(file_path):
        fname=os.path.basename(file_path)
        try: fsize=format_size(os.path.getsize(file_path))
        except Exception: fsize=""
        thumb=_load_thumbnail_base(file_path,max_size=80)

    ripples=[WaterRipple(w//2,h//2,max_radius=220,speed=5,color=gc)]
    particles=[]; clock=pygame.time.Clock()
    t0=time.time(); dur=2.5 if mode!="cancel" else 1.5
    running=True

    while running:
        if time.time()-t0>dur: running=False
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            elif ev.type==pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                running=False

        screen.fill((255,0,255) if sys.platform=="win32" else (15,15,18))
        elapsed=time.time()-t0
        if len(ripples)<3 and elapsed<1.0 and int(elapsed * 4)>len(ripples):
            ripples.append(WaterRipple(w//2,h//2,max_radius=220,speed=5,color=gc))
        for rp in ripples: rp.update(); rp.draw(screen)
        if elapsed<1.2 and len(particles)<40:
            particles.append(GlowParticle(w//2+(_rb()-0.5)*150,h//2+40,color=gc))
        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
            else: p.draw(screen)

        cw2,ch2=420,160; cx4=(w-cw2)//2; cy4=(h-ch2)//2
        cs=pygame.Surface((cw2,ch2),pygame.SRCALPHA)
        pygame.draw.rect(cs,(14,18,34,255),(0,0,cw2,ch2),border_radius=16)
        pygame.draw.rect(cs,(*gc,255),(0,0,cw2,ch2),2,border_radius=16)
        screen.blit(cs,(cx4,cy4))
        screen.blit(ft.render(tt,True,TEXT_COLOR),(cx4+115,cy4+22))
        screen.blit(fs.render(st,True,SUBTEXT_COLOR),(cx4+115,cy4+54))

        if mode!="cancel" and fname:
            dn=fname if len(fname)<=30 else fname[:27]+"..."
            screen.blit(fb.render(dn,True,TEXT_COLOR),(cx4+115,cy4+82))
            screen.blit(fs.render(fsize,True,SUBTEXT_COLOR),(cx4+115,cy4+108))
            if thumb:
                tw2=pygame.transform.smoothscale(thumb,(60,60))
                tw2_masked = _make_circular_thumb(tw2, 60)
                screen.blit(tw2_masked,(cx4+32,cy4+46))
                pygame.draw.circle(screen,gc,(cx4+62,cy4+76),30,1)
            else:
                is2=pygame.Surface((58,68),pygame.SRCALPHA)
                pts=[(0,0),(43,0),(58,15),(58,68),(0,68)]
                pygame.draw.polygon(is2,(*gc,40),pts)
                pygame.draw.polygon(is2,gc,pts,2)
                pygame.draw.polygon(is2,gc,[(43,0),(43,15),(58,15)], 2)
                for yl in (28,40,52): pygame.draw.line(is2,gc,(13,yl),(43,yl),2)
                screen.blit(is2,(cx4+33,cy4+38))
        elif mode=="cancel":
            pygame.draw.line(screen,CC,(cx4+48,cy4+52),(cx4+83,cy4+88),4)
            pygame.draw.line(screen,CC,(cx4+83,cy4+52),(cx4+48,cy4+88),4)

        pygame.display.flip(); clock.tick(60)
    pygame.display.quit(); pygame.quit()


def trigger_grab_overlay(fp): threading.Thread(target=run_overlay_loop,args=("grab",fp),daemon=True).start()
def trigger_drop_overlay(fp): threading.Thread(target=run_overlay_loop,args=("drop",fp),daemon=True).start()
def trigger_cancel_overlay(title=None, status=None): threading.Thread(target=run_overlay_loop,args=("cancel",None,title,status),daemon=True).start()
def trigger_interactive_hud():
    config.app_state.set("is_overlay_active", True)
    threading.Thread(target=run_interactive_overlay, daemon=True).start()
