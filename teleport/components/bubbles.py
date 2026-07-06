import pygame
import os
import math
import time

def _rb():
    return os.urandom(1)[0] / 255.0

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
    if ext in ("PDF",): return (180, 20, 20), (240, 80, 80)
    elif ext in ("DOC", "DOCX", "TXT"): return (20, 80, 180), (50, 130, 255)
    elif ext in ("XLS", "XLSX", "CSV"): return (15, 110, 50), (45, 175, 95)
    elif ext in ("PPT", "PPTX"): return (210, 70, 15), (250, 130, 45)
    elif ext in ("ZIP", "RAR", "7Z", "TAR", "GZ"): return (160, 110, 15), (230, 180, 45)
    elif ext in ("MP3", "WAV", "OGG", "M4A"): return (120, 20, 180), (190, 70, 255)
    elif ext in ("MP4", "AVI", "MKV", "MOV"): return (15, 130, 150), (45, 195, 215)
    else: return (15, 23, 42), (40, 55, 90)

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
    try: fnt = pygame.font.SysFont("Segoe UI", max(14, radius // 2), bold=True)
    except Exception: fnt = pygame.font.Font(None, max(18, radius // 2 + 4))
    tl = fnt.render(label, True, (255, 255, 255))
    tsh = fnt.render(label, True, (0, 8, 25))
    bx = radius - tl.get_width() // 2
    by = radius - tl.get_height() // 2
    surf.blit(tsh, (bx + 1, by + 1))
    surf.blit(tl, (bx, by))
    return surf

def _draw_folder_icon(surface, cx, cy, radius, color):
    w = int(radius * 0.9); h = int(w * 0.72)
    x = cx - w // 2; y = cy - h // 2
    pts_back = [(x, y + 8), (x + int(w * 0.35), y + 8), (x + int(w * 0.48), y + 2), (x + w, y + 2), (x + w, y + h), (x, y + h)]
    pygame.draw.polygon(surface, (10, 45, 100, 255), pts_back)
    pygame.draw.polygon(surface, (255, 255, 255, 180), pts_back, 2)
    sheet = [(x + 6, y + 5), (x + w - 6, y + 5), (x + w - 6, y + h - 5), (x + 6, y + h - 5)]
    pygame.draw.polygon(surface, (255, 255, 255, 230), sheet)
    pts_front = [(x, y + 14), (x + int(w * 0.4), y + 14), (x + int(w * 0.5), y + 10), (x + w, y + 10), (x + w, y + h), (x, y + h)]
    pygame.draw.polygon(surface, (20, 90, 180, 255), pts_front)
    pygame.draw.polygon(surface, (255, 255, 255, 220), pts_front, 2)

class WaterRipple:
    def __init__(self, x, y, max_radius=1200, speed=26, color=(0, 200, 255)):
        self.x = x; self.y = y; self.radius = 0.0
        self.max_radius = max_radius; self.speed = speed; self.color = color
    def update(self): self.radius += self.speed
    def is_done(self): return self.radius >= self.max_radius
    def draw(self, surface):
        if self.is_done(): return
        t = self.radius / self.max_radius
        rings = [(0, 2), (-20, 1), (-40, 1)]
        for offset, thick in rings:
            r = int(self.radius) + offset
            if r <= 1: continue
            white_ratio = min(1.0, t * 1.2)
            rc = int(self.color[0] * (1 - white_ratio) + 255 * white_ratio)
            gc = int(self.color[1] * (1 - white_ratio) + 255 * white_ratio)
            bc = int(self.color[2] * (1 - white_ratio) + 255 * white_ratio)
            pygame.draw.circle(surface, (rc, gc, bc, 255), (self.x, self.y), r, thick)

def format_size(b):
    if b < 1024: return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.1f} MB"

def _draw_label_pill(surface, name, size_str, cx, bottom_y, hovered=False):
    try: fn = pygame.font.SysFont("Segoe UI", 13, bold=True); fs = pygame.font.SysFont("Segoe UI", 11)
    except Exception: fn = pygame.font.Font(None, 18); fs = pygame.font.Font(None, 15)
    tn = fn.render(name, True, (245, 250, 255))
    ts = fs.render(size_str, True, (155, 185, 220))
    pw = max(tn.get_width(), ts.get_width()) + 32; ph = 44
    pill = pygame.Surface((pw, ph), pygame.SRCALPHA)
    bg_color = (14, 20, 38, 255) if not hovered else (24, 40, 72, 255)
    brd_color = (80, 100, 140, 255) if not hovered else (0, 235, 255, 255)
    pygame.draw.rect(pill, bg_color, (0, 0, pw, ph), border_radius=22)
    pygame.draw.rect(pill, brd_color, (0, 0, pw, ph), 1, border_radius=22)
    pill.blit(tn, ((pw - tn.get_width()) // 2, 8))
    pill.blit(ts, ((pw - ts.get_width()) // 2, 26))
    surface.blit(pill, (cx - pw // 2, bottom_y + 12))

class ExplorerBubble:
    def __init__(self, cx, cy, radius=82):
        self.x = cx; self.y = cy; self.radius = radius
        self.scale = 0.05; self.target_scale = 1.0
        self.is_hovered = False; self.is_popped = False
    def update(self):
        if not self.is_popped:
            self.target_scale = 1.14 if self.is_hovered else 1.0
            self.scale += (self.target_scale - self.scale) * 0.11
        else: self.scale += 0.11
    def draw(self, surface):
        r = int(self.radius * self.scale)
        if r < 4: return
        content_r = r - 8
        if content_r > 4:
            d = content_r * 2; bg = pygame.Surface((d, d), pygame.SRCALPHA)
            col_start, col_end = (10, 95, 210), (30, 195, 255)
            for dr in range(content_r, 0, -2):
                t = dr / content_r
                rc = int(col_start[0] * (1 - t) + col_end[0] * t)
                gc = int(col_start[1] * (1 - t) + col_end[1] * t)
                bc = int(col_start[2] * (1 - t) + col_end[2] * t)
                pygame.draw.circle(bg, (rc, gc, bc, 255), (content_r, content_r), dr)
            mask = pygame.Surface((d, d), pygame.SRCALPHA)
            mask.fill((0, 0, 0, 255)); pygame.draw.circle(mask, (0, 0, 0, 0), (content_r, content_r), content_r)
            bg.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            _draw_folder_icon(bg, content_r, content_r, content_r - 2, (255, 255, 255))
            surface.blit(bg, (self.x - content_r, self.y - content_r))
        if content_r > 4:
            sheen = pygame.Surface((content_r * 2, content_r * 2), pygame.SRCALPHA)
            for dr in range(content_r, 0, -2):
                t = dr / content_r; a = int(45 * (1.0 - t)**1.4)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r, content_r), dr)
            for dr in range(content_r // 2, 0, -1):
                t = dr / (content_r // 2); a = int(55 * (1.0 - t)**1.8)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r // 2, content_r // 2), dr)
            surface.blit(sheen, (self.x - content_r, self.y - content_r))
        if self.is_hovered:
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r, 2)
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r - 3, 1)
        else:
            pygame.draw.circle(surface, (255, 255, 255, 255), (self.x, self.y), r, 1)
            pygame.draw.circle(surface, (255, 255, 255, 140), (self.x, self.y), r - 3, 1)
        arc_r = r - 2; arc_rect = pygame.Rect(self.x - arc_r, self.y - arc_r, arc_r * 2, arc_r * 2)
        pygame.draw.arc(surface, (255, 255, 255, 255), arc_rect, math.pi * 0.6, math.pi * 1.15, 3)
        dot_dist = int(r * 0.45)
        pygame.draw.circle(surface, (255, 255, 255, 255), (self.x - dot_dist, self.y - dot_dist), max(2, r // 12))
        pygame.draw.arc(surface, (180, 230, 255, 255), arc_rect, math.pi * 1.6, math.pi * 2.1, 1)
        _draw_label_pill(surface, "Buscar Arquivo", "Explorar PC", self.x, self.y + r, hovered=self.is_hovered)

class Bubble:
    def __init__(self, index, path, radius=82):
        self.index = index; self.path = path; self.name = os.path.basename(path)
        self.ext = os.path.splitext(self.name)[1].upper().lstrip(".")
        self.size_str = "?"
        try: self.size_str = format_size(os.path.getsize(path))
        except Exception: pass
        self.radius = radius; self.ox = self.oy = self.x = self.y = 0
        self.phase_x = _rb() * math.pi * 2; self.phase_y = _rb() * math.pi * 2
        self.float_spd = 0.45 + _rb() * 0.45
        self.is_hovered = False; self.is_popped = False
        self.scale = 0.05; self.target_scale = 1.0
        self.thumb_base = _load_thumbnail_base(path, max_size=200)
        self._thumb_r = -1; self._thumb_s = None
        self._icon_r  = -1; self._icon_s  = None
    def _get_thumb(self, r):
        if r != self._thumb_r and self.thumb_base:
            self._thumb_s = _make_circular_thumb(self.thumb_base, r * 2); self._thumb_r = r
        return self._thumb_s
    def _get_icon(self, r):
        if r != self._icon_r:
            self._icon_s = _make_icon_bg(r, self.ext); self._icon_r = r
        return self._icon_s
    def update(self):
        if not self.is_popped:
            t = time.time() * self.float_spd
            self.x = int(self.ox + math.sin(t + self.phase_x) * 13)
            self.y = int(self.oy + math.cos(t + self.phase_y) * 9)
            self.target_scale = 1.14 if self.is_hovered else 1.0
            self.scale += (self.target_scale - self.scale) * 0.11
        else: self.scale += 0.11
    def draw(self, surface):
        r = int(self.radius * self.scale)
        if r < 4: return
        content_r = r - 8
        if content_r > 4:
            if self.thumb_base:
                ct = self._get_thumb(content_r)
                if ct: surface.blit(ct, (self.x - content_r, self.y - content_r))
            else:
                ic = self._get_icon(content_r)
                if ic: surface.blit(ic, (self.x - content_r, self.y - content_r))
        if content_r > 4:
            sheen = pygame.Surface((content_r * 2, content_r * 2), pygame.SRCALPHA)
            for dr in range(content_r, 0, -2):
                t = dr / content_r; a = int(45 * (1.0 - t)**1.4)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r, content_r), dr)
            for dr in range(content_r // 2, 0, -1):
                t = dr / (content_r // 2); a = int(55 * (1.0 - t)**1.8)
                pygame.draw.circle(sheen, (255, 255, 255, a), (content_r // 2, content_r // 2), dr)
            surface.blit(sheen, (self.x - content_r, self.y - content_r))
        if self.is_hovered:
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r, 2)
            pygame.draw.circle(surface, (0, 235, 255, 255), (self.x, self.y), r - 3, 1)
        else:
            pygame.draw.circle(surface, (255, 255, 255, 255), (self.x, self.y), r, 1)
            pygame.draw.circle(surface, (255, 255, 255, 140), (self.x, self.y), r - 3, 1)
        arc_r = r - 2; arc_rect = pygame.Rect(self.x - arc_r, self.y - arc_r, arc_r * 2, arc_r * 2)
        pygame.draw.arc(surface, (255, 255, 255, 255), arc_rect, math.pi * 0.6, math.pi * 1.15, 3)
        dot_dist = int(r * 0.45)
        pygame.draw.circle(surface, (255, 255, 255, 255), (self.x - dot_dist, self.y - dot_dist), max(2, r // 12))
        pygame.draw.arc(surface, (180, 230, 255, 255), arc_rect, math.pi * 1.6, math.pi * 2.1, 1)
        _draw_label_pill(surface, self.name if len(self.name) <= 18 else self.name[:15] + "...", self.size_str, self.x, self.y + r, hovered=self.is_hovered)

def draw_hud_header(surface, sw, sh, font_main, font_sub, popping=False):
    if popping: return
    cw = min(sw - 80, 680); ch = 76
    cx2 = (sw - cw) // 2; cy2 = int(sh * 0.15)
    card = pygame.Surface((cw, ch), pygame.SRCALPHA)
    pygame.draw.rect(card, (10, 14, 32, 255), (0, 0, cw, ch), border_radius=38)
    pygame.draw.rect(card, (80, 100, 140, 255), (0, 0, cw, ch), 1, border_radius=38)
    t1 = font_main.render("SELECIONE O ARQUIVO A TRANSFERIR", True, (245, 250, 255))
    t2 = font_sub.render("Aproxime a mao e faca o gesto de pinca para selecionar", True, (140, 180, 220))
    card.blit(t1, ((cw - t1.get_width()) // 2, 13))
    card.blit(t2, ((cw - t2.get_width()) // 2, 46))
    surface.blit(card, (cx2, cy2))
