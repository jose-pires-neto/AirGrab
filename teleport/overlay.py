import pygame, os, sys, ctypes, math, time, threading
from teleport import config
from teleport.network import broadcast_message

# ── Color Palette ──────────────────────────────────────────────────────────────
COLOR_KEY     = (1, 1, 1)          # transparent window color key (almost black)
TEXT_COLOR    = (255, 255, 255)
SUBTEXT_COLOR = (180, 200, 225)
GLOW_HOVER    = (0, 235, 255)      # Cyan
GLOW_GRAB     = (0, 255, 140)      # Green
GLOW_WARN     = (255, 70, 55)      # Red

def _rb():
    return os.urandom(1)[0] / 255.0


# ─────────────────────────────────────────────────────────────────────────────
# FILE DIALOG TRIGGER
# ─────────────────────────────────────────────────────────────────────────────
def open_file_explorer_dialog():
    """Opens a native OS file dialog to select any file from the PC."""
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


# ─────────────────────────────────────────────────────────────────────────────
# THUMBNAIL & ICON HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _load_thumbnail_base(path, max_size=200):
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
        return None
    try:
        img = pygame.image.load(path)
        w, h = img.get_size()
        if w >= h:
            nw, nh = max_size, max(1, int(h * max_size / w))
        else:
            nw, nh = max(1, int(w * max_size / h)), max_size
        img = pygame.transform.smoothscale(img, (nw, nh))
        result = pygame.Surface((nw, nh), pygame.SRCALPHA)
        result.blit(img, (0, 0))
        return result
    except Exception:
        return None


def _make_circular_thumb(img_base, diameter):
    d = max(2, diameter)
    r = d // 2
    dest = pygame.Surface((d, d), pygame.SRCALPHA)
    scaled = pygame.transform.smoothscale(img_base, (d, d))
    dest.blit(scaled, (0, 0))
    
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 255))
    pygame.draw.circle(mask, (0, 0, 0, 0), (r, r), r)
    
    dest.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    return dest


def _get_ext_colors(ext):
    ext = ext.upper()
    if ext in ("PDF",):
        return (180, 20, 20), (240, 80, 80)
    elif ext in ("DOC", "DOCX", "TXT"):
        return (20, 80, 180), (50, 130, 255)
    elif ext in ("XLS", "XLSX", "CSV"):
        return (15, 110, 50), (45, 175, 95)
    elif ext in ("PPT", "PPTX"):
        return (210, 70, 15), (250, 130, 45)
    elif ext in ("ZIP", "RAR", "7Z", "TAR", "GZ"):
        return (160, 110, 15), (230, 180, 45)
    elif ext in ("MP3", "WAV", "OGG", "M4A"):
        return (120, 20, 180), (190, 70, 255)
    elif ext in ("MP4", "AVI", "MKV", "MOV"):
        return (15, 130, 150), (45, 195, 215)
    else:
        return (15, 23, 42), (40, 55, 90)


def _make_icon_bg(radius, ext):
    d = radius * 2
    surf = pygame.Surface((d, d), pygame.SRCALPHA)
    col_start, col_end = _get_ext_colors(ext)
    
    for dr in range(radius, 0, -2):
        t = dr / radius
        r = int(col_start[0] * (1 - t) + col_end[0] * t)
        g = int(col_start[1] * (1 - t) + col_end[1] * t)
        b = int(col_start[2] * (1 - t) + col_end[2] * t)
        pygame.draw.circle(surf, (r, g, b, 255), (radius, radius), dr)
        
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 255))
    pygame.draw.circle(mask, (0, 0, 0, 0), (radius, radius), radius)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    
    label = ext.upper()[:4] if ext else "FILE"
    try:
        fnt = pygame.font.SysFont("Segoe UI", max(14, radius // 2), bold=True)
    except Exception:
        fnt = pygame.font.Font(None, max(18, radius // 2 + 4))
        
    tl = fnt.render(label, True, (255, 255, 255))
    tsh = fnt.render(label, True, (0, 8, 25))
    bx = radius - tl.get_width() // 2
    by = radius - tl.get_height() // 2
    surf.blit(tsh, (bx + 1, by + 1))
    surf.blit(tl, (bx, by))
    return surf


def _draw_folder_icon(surface, cx, cy, radius, color):
    """Draws a beautiful vector 3D-styled folder icon."""
    w = int(radius * 0.9)
    h = int(w * 0.72)
    x = cx - w // 2
    y = cy - h // 2
    
    # 1. Back folder panel
    pts_back = [
        (x, y + 8),
        (x + int(w * 0.35), y + 8),
        (x + int(w * 0.48), y + 2),
        (x + w, y + 2),
        (x + w, y + h),
        (x, y + h)
    ]
    pygame.draw.polygon(surface, (10, 45, 100, 255), pts_back)
    pygame.draw.polygon(surface, (255, 255, 255, 180), pts_back, 2)
    
    # 2. Inside sheet
    sheet = [
        (x + 6, y + 5),
        (x + w - 6, y + 5),
        (x + w - 6, y + h - 5),
        (x + 6, y + h - 5)
    ]
    pygame.draw.polygon(surface, (255, 255, 255, 230), sheet)
    
    # 3. Front folder panel
    pts_front = [
        (x, y + 14),
        (x + int(w * 0.4), y + 14),
        (x + int(w * 0.5), y + 10),
        (x + w, y + 10),
        (x + w, y + h),
        (x, y + h)
    ]
    pygame.draw.polygon(surface, (20, 90, 180, 255), pts_front)
    pygame.draw.polygon(surface, (255, 255, 255, 220), pts_front, 2)


# ─────────────────────────────────────────────────────────────────────────────
# WATER RIPPLE (Futuristic spatial vector ripples)
# ─────────────────────────────────────────────────────────────────────────────
class WaterRipple:
    def __init__(self, x, y, max_radius=1200, speed=26, color=(0, 200, 255)):
        self.x = x
        self.y = y
        self.radius = 0.0
        self.max_radius = max_radius
        self.speed = speed
        self.color = color

    def update(self):
        self.radius += self.speed

    def is_done(self):
        return self.radius >= self.max_radius

    def draw(self, surface):
        if self.is_done():
            return
        t = self.radius / self.max_radius
        rings = [(0, 2), (-20, 1), (-40, 1)]
        for offset, thick in rings:
            r = int(self.radius) + offset
            if r <= 1:
                continue
            white_ratio = min(1.0, t * 1.2)
            rc = int(self.color[0] * (1 - white_ratio) + 255 * white_ratio)
            gc = int(self.color[1] * (1 - white_ratio) + 255 * white_ratio)
            bc = int(self.color[2] * (1 - white_ratio) + 255 * white_ratio)
            pygame.draw.circle(surface, (rc, gc, bc, 255), (self.x, self.y), r, thick)


# ─────────────────────────────────────────────────────────────────────────────
# BUBBLE POP PARTICLE
# ─────────────────────────────────────────────────────────────────────────────
class BubblePopParticle:
    def __init__(self, x, y, color=(0, 200, 255)):
        self.x = float(x)
        self.y = float(y)
        angle = _rb() * math.pi * 2
        speed = 3.0 + _rb() * 11.0
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 2.0
        self.life = 255.0
        self.decay = 8 + _rb() * 12
        self.radius = max(2, int(2 + _rb() * 4))
        sh = int((_rb() - 0.5) * 80)
        self.color = (
            min(255, max(0, color[0] + sh)),
            min(255, max(0, color[1] + sh // 2)),
            min(255, max(0, color[2] - sh // 2))
        )

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.22
        self.vx *= 0.96
        self.life -= self.decay

    def draw(self, surface):
        if self.life <= 0:
            return
        r = self.radius
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), r)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), max(1, r - 1))


def format_size(b):
    if b < 1024:    return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.1f} MB"


def _draw_label_pill(surface, name, size_str, cx, bottom_y, hovered=False):
    try:
        fn = pygame.font.SysFont("Segoe UI", 13, bold=True)
        fs = pygame.font.SysFont("Segoe UI", 11)
    except Exception:
        fn = pygame.font.Font(None, 18)
        fs = pygame.font.Font(None, 15)
    
    tn = fn.render(name, True, (245, 250, 255))
    ts = fs.render(size_str, True, (155, 185, 220))
    pw = max(tn.get_width(), ts.get_width()) + 32
    ph = 44
    
    pill = pygame.Surface((pw, ph), pygame.SRCALPHA)
    bg_color = (14, 20, 38, 255) if not hovered else (24, 40, 72, 255)
    brd_color = (80, 100, 140, 255) if not hovered else (0, 235, 255, 255)
    
    pygame.draw.rect(pill, bg_color, (0, 0, pw, ph), border_radius=22)
    pygame.draw.rect(pill, brd_color, (0, 0, pw, ph), 1, border_radius=22)
    
    pill.blit(tn, ((pw - tn.get_width()) // 2, 8))
    pill.blit(ts, ((pw - ts.get_width()) // 2, 26))
    surface.blit(pill, (cx - pw // 2, bottom_y + 12))


def _draw_hud_header(surface, sw, sh, font_main, font_sub, popping=False):
    if popping:
        return
    cw = min(sw - 80, 680)
    ch = 76
    cx2 = (sw - cw) // 2
    cy2 = int(sh * 0.15)
    
    card = pygame.Surface((cw, ch), pygame.SRCALPHA)
    pygame.draw.rect(card, (10, 14, 32, 255), (0, 0, cw, ch), border_radius=38)
    pygame.draw.rect(card, (80, 100, 140, 255), (0, 0, cw, ch), 1, border_radius=38)
    
    t1 = font_main.render("SELECIONE O ARQUIVO A TRANSFERIR", True, (245, 250, 255))
    t2 = font_sub.render("Aproxime a mao e faca o gesto de pinca para selecionar", True, (140, 180, 220))
    
    card.blit(t1, ((cw - t1.get_width()) // 2, 13))
    card.blit(t2, ((cw - t2.get_width()) // 2, 46))
    surface.blit(card, (cx2, cy2))


# ─────────────────────────────────────────────────────────────────────────────
# EXPLORER BUBBLE BUTTON
# ─────────────────────────────────────────────────────────────────────────────
class ExplorerBubble:
    def __init__(self, cx, cy, radius=82):
        self.x = cx
        self.y = cy
        self.radius = radius
        self.scale = 0.05
        self.target_scale = 1.0
        self.is_hovered = False
        self.is_popped = False

    def update(self):
        if not self.is_popped:
            self.target_scale = 1.14 if self.is_hovered else 1.0
            self.scale += (self.target_scale - self.scale) * 0.11
        else:
            self.scale += 0.11

    def draw(self, surface):
        r = int(self.radius * self.scale)
        if r < 4:
            return

        # 1. Base content: Blue gradient background with Folder icon
        content_r = r - 8
        if content_r > 4:
            d = content_r * 2
            bg = pygame.Surface((d, d), pygame.SRCALPHA)
            col_start, col_end = (10, 95, 210), (30, 195, 255)
            for dr in range(content_r, 0, -2):
                t = dr / content_r
                rc = int(col_start[0] * (1 - t) + col_end[0] * t)
                gc = int(col_start[1] * (1 - t) + col_end[1] * t)
                bc = int(col_start[2] * (1 - t) + col_end[2] * t)
                pygame.draw.circle(bg, (rc, gc, bc, 255), (content_r, content_r), dr)
                
            mask = pygame.Surface((d, d), pygame.SRCALPHA)
            mask.fill((0, 0, 0, 255))
            pygame.draw.circle(mask, (0, 0, 0, 0), (content_r, content_r), content_r)
            bg.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            
            _draw_folder_icon(bg, content_r, content_r, content_r - 2, (255, 255, 255))
            surface.blit(bg, (self.x - content_r, self.y - content_r))

        # 2. Inner glass reflection sheen
        if content_r > 4:
            sheen = pygame.Surface((content_r * 2, content_r * 2), pygame.SRCALPHA)
            for dr in range(content_r, 0, -2):
                t = dr / content_r
                a = int(45 * (1.0 - t)**1.4)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r, content_r), dr)
            for dr in range(content_r // 2, 0, -1):
                t = dr / (content_r // 2)
                a = int(55 * (1.0 - t)**1.8)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r // 2, content_r // 2), dr)
            surface.blit(sheen, (self.x - content_r, self.y - content_r))

        # 3. Outer glass highlights
        if self.is_hovered:
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r, 2)
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r - 3, 1)
        else:
            pygame.draw.circle(surface, (255, 255, 255, 255), (self.x, self.y), r, 1)
            pygame.draw.circle(surface, (255, 255, 255, 140), (self.x, self.y), r - 3, 1)

        arc_r = r - 2
        arc_rect = pygame.Rect(self.x - arc_r, self.y - arc_r, arc_r * 2, arc_r * 2)
        pygame.draw.arc(surface, (255, 255, 255, 255), arc_rect, math.pi * 0.6, math.pi * 1.15, 3)

        dot_dist = int(r * 0.45)
        pygame.draw.circle(surface, (255, 255, 255, 255), (self.x - dot_dist, self.y - dot_dist), max(2, r // 12))
        pygame.draw.arc(surface, (180, 230, 255, 255), arc_rect, math.pi * 1.6, math.pi * 2.1, 1)

        # 4. Label pill
        _draw_label_pill(surface, "Buscar Arquivo", "Explorar PC", self.x, self.y + r, hovered=self.is_hovered)


# ─────────────────────────────────────────────────────────────────────────────
# BUBBLE CLASS
# ─────────────────────────────────────────────────────────────────────────────
class Bubble:
    def __init__(self, index, path, radius=82):
        self.index = index
        self.path = path
        self.name = os.path.basename(path)
        self.ext = os.path.splitext(self.name)[1].upper().lstrip(".")
        self.size_str = "?"
        try:
            self.size_str = format_size(os.path.getsize(path))
        except Exception:
            pass

        self.radius = radius
        self.ox = self.oy = self.x = self.y = 0
        self.phase_x = _rb() * math.pi * 2
        self.phase_y = _rb() * math.pi * 2
        self.float_spd = 0.45 + _rb() * 0.45

        self.is_hovered = False
        self.is_popped = False
        self.scale = 0.05
        self.target_scale = 1.0

        self.thumb_base = _load_thumbnail_base(path, max_size=200)
        self._thumb_r = -1; self._thumb_s = None
        self._icon_r  = -1; self._icon_s  = None

    def _get_thumb(self, r):
        if r != self._thumb_r and self.thumb_base:
            self._thumb_s = _make_circular_thumb(self.thumb_base, r * 2)
            self._thumb_r = r
        return self._thumb_s

    def _get_icon(self, r):
        if r != self._icon_r:
            self._icon_s = _make_icon_bg(r, self.ext)
            self._icon_r = r
        return self._icon_s

    def update(self):
        if not self.is_popped:
            t = time.time() * self.float_spd
            self.x = int(self.ox + math.sin(t + self.phase_x) * 13)
            self.y = int(self.oy + math.cos(t + self.phase_y) * 9)
            self.target_scale = 1.14 if self.is_hovered else 1.0
            self.scale += (self.target_scale - self.scale) * 0.11
        else:
            self.scale += 0.11

    def draw(self, surface):
        r = int(self.radius * self.scale)
        if r < 4:
            return

        content_r = r - 8
        if content_r > 4:
            if self.thumb_base:
                ct = self._get_thumb(content_r)
                if ct:
                    surface.blit(ct, (self.x - content_r, self.y - content_r))
            else:
                ic = self._get_icon(content_r)
                if ic:
                    surface.blit(ic, (self.x - content_r, self.y - content_r))

        if content_r > 4:
            sheen = pygame.Surface((content_r * 2, content_r * 2), pygame.SRCALPHA)
            for dr in range(content_r, 0, -2):
                t = dr / content_r
                a = int(45 * (1.0 - t)**1.4)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r, content_r), dr)
            for dr in range(content_r // 2, 0, -1):
                t = dr / (content_r // 2)
                a = int(55 * (1.0 - t)**1.8)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r // 2, content_r // 2), dr)
            surface.blit(sheen, (self.x - content_r, self.y - content_r))

        if self.is_hovered:
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r, 2)
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r - 3, 1)
        else:
            pygame.draw.circle(surface, (255, 255, 255, 255), (self.x, self.y), r, 1)
            pygame.draw.circle(surface, (255, 255, 255, 140), (self.x, self.y), r - 3, 1)

        arc_r = r - 2
        arc_rect = pygame.Rect(self.x - arc_r, self.y - arc_r, arc_r * 2, arc_r * 2)
        pygame.draw.arc(surface, (255, 255, 255, 255), arc_rect, math.pi * 0.6, math.pi * 1.15, 3)

        dot_dist = int(r * 0.45)
        pygame.draw.circle(surface, (255, 255, 255, 255), (self.x - dot_dist, self.y - dot_dist), max(2, r // 12))
        pygame.draw.arc(surface, (180, 230, 255, 255), arc_rect, math.pi * 1.6, math.pi * 2.1, 1)

        _draw_label_pill(surface, self.name if len(self.name) <= 18 else self.name[:15] + "...",
                         self.size_str, self.x, self.y + r, hovered=self.is_hovered)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN INTERACTIVE OVERLAY
# ─────────────────────────────────────────────────────────────────────────────
def run_interactive_overlay():
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    pygame.init(); pygame.font.init()
    info = pygame.display.Info()
    sw, sh = info.current_w, info.current_h
    if sw == 0 or sh == 0: sw, sh = 1920, 1080

    screen = pygame.display.set_mode((sw, sh), pygame.NOFRAME)
    pygame.display.set_caption("AirGrab HUD")

    if sys.platform == "win32":
        hwnd   = pygame.display.get_wm_info()["window"]
        u32    = ctypes.windll.user32
        style  = u32.GetWindowLongW(hwnd, -20)
        u32.SetWindowLongW(hwnd, -20, style | 0x80000)
        ck = (COLOR_KEY[2] << 16) | (COLOR_KEY[1] << 8) | COLOR_KEY[0]
        u32.SetLayeredWindowAttributes(hwnd, ck, 0, 1)

    history     = config.state["clipboard_history"]
    has_history = len(history) > 0
    bubbles     = []
    br          = 82
    
    # Orbit Layout Configuration
    cx = sw // 2
    cy = int(sh * 0.56)
    
    # Explorer central bubble
    explorer_b = ExplorerBubble(cx, cy, br)
    
    # Arrange clipboard history bubbles in an orbit around explorer
    n = len(history)
    if n > 0:
        orbit_radius = 210 + n * 8  # Scale orbit radius slightly based on number of items
        angle_step = (2 * math.pi) / n
        start_angle = -math.pi / 2  # Start at the top
        for i, path in enumerate(history):
            b = Bubble(i, path, br)
            ang = start_angle + i * angle_step
            b.ox = cx + int(math.cos(ang) * orbit_radius)
            b.oy = cy + int(math.sin(ang) * orbit_radius)
            b.x = b.ox; b.y = b.oy
            bubbles.append(b)

    particles = []
    ripples   = [WaterRipple(sw//2, sh//2, max_radius=max(sw,sh), speed=30, color=(0,180,255))]

    try:
        fmain = pygame.font.SysFont("Segoe UI", 22, bold=True)
        fsub  = pygame.font.SysFont("Segoe UI", 13)
        fwarn = pygame.font.SysFont("Segoe UI", 20, bold=True)
        finfo = pygame.font.SysFont("Segoe UI", 13)
    except Exception:
        fmain = pygame.font.Font(None, 28)
        fsub  = pygame.font.Font(None, 18)
        fwarn = pygame.font.Font(None, 26)
        finfo = pygame.font.Font(None, 18)

    hand_x = hand_y = sw // 2
    last_seen = time.time()
    clock = pygame.time.Clock()
    running = True; sel = None
    popping = False; closing = False; close_t = 0.0
    trigger_dialog_file = False

    print("[HUD] Liquid Bubble Selector inicializado.")

    while running:
        if not config.state["running"] or not config.state["is_overlay_active"]:
            running = False

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                if not closing:
                    closing = True; close_t = time.time()
                    ripples.append(WaterRipple(sw//2,sh//2,max(sw,sh),32,GLOW_WARN))

        cam_x = config.state["cursor_x"]; cam_y = config.state["cursor_y"]
        pinch = config.state["pinch_active"]

        if config.state["cancel_requested"]:
            config.state["cancel_requested"] = False
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

        _draw_hud_header(asurf, sw, sh, fmain, fsub, popping=popping)

        # Hover and Selection Handling
        if not popping and not closing:
            explorer_b.is_hovered = False
            for b in bubbles:
                b.is_hovered = False
                
            closest = None
            min_d = float("inf")
            
            # Check explorer bubble hover
            d_exp = math.hypot(hand_x - explorer_b.x, hand_y - explorer_b.y)
            if d_exp < 175:
                min_d = d_exp
                closest = explorer_b
                
            # Check history bubbles hover
            for b in bubbles:
                d = math.hypot(hand_x - b.x, hand_y - b.y)
                if d < 175 and d < min_d:
                    min_d = d
                    closest = b
                    
            if closest:
                closest.is_hovered = True
                
                # Magnetism effect
                ang = math.atan2(hand_y - closest.y, hand_x - closest.x)
                if closest == explorer_b:
                    closest.x = cx + int(math.cos(ang) * 12)
                    closest.y = cy + int(math.sin(ang) * 12)
                else:
                    closest.x += int(math.cos(ang) * 3.5)
                    closest.y += int(math.sin(ang) * 3.5)
                    
                # Selection triggered by pinch gesture
                if pinch:
                    if closest == explorer_b:
                        explorer_b.is_popped = True
                        popping = True
                        trigger_dialog_file = True
                        print("[HUD] Explorer central selecionado. Abrindo explorador de arquivos...")
                        for b in bubbles:
                            for _ in range(15):
                                particles.append(BubblePopParticle(b.x, b.y, (100, 210, 255)))
                    else:
                        sel = closest
                        popping = True
                        sel.is_popped = True
                        print(f"[HUD] Bolha {sel.name!r} selecionada.")
                        for _ in range(24):
                            particles.append(BubblePopParticle(explorer_b.x, explorer_b.y, (100, 210, 255)))
                        for b in bubbles:
                            if b != sel:
                                for _ in range(20):
                                    particles.append(BubblePopParticle(b.x, b.y, (100, 210, 255)))
            else:
                explorer_b.x = int(explorer_b.x * 0.8 + cx * 0.2)
                explorer_b.y = int(explorer_b.y * 0.8 + cy * 0.2)

        # Update and Draw central explorer bubble
        if not popping or trigger_dialog_file:
            explorer_b.update()
            if popping and trigger_dialog_file and explorer_b.scale >= 1.5 and not closing:
                for _ in range(45):
                    particles.append(BubblePopParticle(explorer_b.x, explorer_b.y, GLOW_GRAB))
                closing = True; close_t = time.time()
                ripples.append(WaterRipple(explorer_b.x, explorer_b.y, max_radius=max(sw, sh), speed=32, color=GLOW_GRAB))
            else:
                explorer_b.draw(asurf)

        # Update and Draw history bubbles
        for b in bubbles:
            if not popping or b == sel:
                b.update()
                if popping and b == sel and b.scale >= 1.5 and not closing:
                    for _ in range(45):
                        particles.append(BubblePopParticle(b.x, b.y, GLOW_GRAB))
                    closing = True; close_t = time.time()
                    ripples.append(WaterRipple(b.x, b.y, max_radius=max(sw, sh), speed=32, color=GLOW_GRAB))
                    config.state["current_file"]      = sel.path
                    config.state["current_file_name"] = sel.name
                    broadcast_message(f"HOLDING:{config.local_ip}")
                    sel = None
                else:
                    b.draw(asurf)

        for p in particles[:]:
            p.update()
            if p.life <= 0: particles.remove(p)
            else:           p.draw(asurf)

        for rp in ripples[:]:
            rp.update()
            if rp.is_done(): ripples.remove(rp)
            else:            rp.draw(asurf)

        # Notice shown when history is empty
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
    config.state["is_overlay_active"] = False
    print("[HUD] Interface AirGrab HUD encerrada.")
    
    if trigger_dialog_file:
        selected_file = open_file_explorer_dialog()
        if selected_file and os.path.exists(selected_file):
            config.state["current_file"] = selected_file
            config.state["current_file_name"] = os.path.basename(selected_file)
            broadcast_message(f"HOLDING:{config.local_ip}")
            print(f"[HUD] Arquivo selecionado via Explorador: {selected_file}")


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION OVERLAYS (grab / drop / cancel)
# ─────────────────────────────────────────────────────────────────────────────
class GlowParticle:
    def __init__(self, x, y, color=(0,255,255)):
        self.x=x; self.y=y
        self.vx=(_rb()-0.5)*4; self.vy=(_rb()-0.5)*4-2.0
        self.life=255; self.decay=6+_rb()*8; self.color=color
    def update(self): self.x+=self.vx; self.y+=self.vy; self.life-=self.decay
    def draw(self,surface):
        if self.life>0:
            s=pygame.Surface((10,10),pygame.SRCALPHA)
            pygame.draw.circle(s,(*self.color,int(self.life)),(5,5),4)
            surface.blit(s,(int(self.x-5),int(self.y-5)))


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
            else:           p.draw(screen)

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


def trigger_grab_overlay(fp):
    threading.Thread(target=run_overlay_loop,args=("grab",fp),daemon=True).start()
def trigger_drop_overlay(fp):
    threading.Thread(target=run_overlay_loop,args=("drop",fp),daemon=True).start()
def trigger_cancel_overlay(title=None,status=None):
    threading.Thread(target=run_overlay_loop,args=("cancel",None,title,status),daemon=True).start()
def trigger_interactive_hud():
    if not config.state["is_overlay_active"]:
        config.state["is_overlay_active"] = True
        threading.Thread(target=run_interactive_overlay,daemon=True).start()
