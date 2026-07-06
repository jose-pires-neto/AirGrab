import pygame
import os
import sys
import ctypes
import math
import time
import threading

# Cores
COLOR_KEY = (255, 0, 255) # Magenta (será transparente no Windows)
CARD_BG = (28, 28, 30, 230) # Cinza escuro translúcido (Glassmorphism)
CARD_BORDER = (100, 100, 100, 100)
GLOW_COLOR = (0, 255, 128) # Verde brilhante (AirGrab)
DROP_GLOW_COLOR = (0, 191, 255) # Azul brilhante (AirDrop)
CANCEL_GLOW_COLOR = (255, 69, 58) # Vermelho brilhante (Cancel)
TEXT_COLOR = (255, 255, 255)
SUBTEXT_COLOR = (200, 200, 200)

class Ripple:
    def __init__(self, x, y, max_radius=200, speed=4, color=(0, 255, 128)):
        self.x = x
        self.y = y
        self.radius = 0
        self.max_radius = max_radius
        self.speed = speed
        self.color = color

    def update(self):
        self.radius += self.speed

    def draw(self, surface):
        if self.radius < self.max_radius:
            alpha = int(255 * (1 - (self.radius / self.max_radius)))
            # Desenha círculo com alpha
            surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            # Desenha linha com espessura de 3 pixels
            pygame.draw.circle(surf, (*self.color, alpha), (self.radius, self.radius), self.radius, 3)
            surface.blit(surf, (self.x - self.radius, self.y - self.radius))

class Particle:
    def __init__(self, x, y, color=(0, 255, 128)):
        self.x = x
        self.y = y
        self.vx = (math.sin(time.time()) * 2) + (os.urandom(1)[0] / 255.0 - 0.5) * 2
        self.vy = - (1 + (os.urandom(1)[0] / 255.0) * 3)
        self.life = 255
        self.decay = 5 + (os.urandom(1)[0] / 255) * 5
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay

    def draw(self, surface):
        if self.life > 0:
            surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, int(self.life)), (4, 4), 3)
            surface.blit(surf, (int(self.x - 4), int(self.y - 4)))

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/1024**2:.1f} MB"

def draw_glass_card(surface, x, y, width, height, glow_color):
    # Desenha o fundo do card com cantos arredondados translúcidos
    card_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Desenha retângulo com bordas arredondadas e preenchimento
    pygame.draw.rect(card_surf, CARD_BG, (0, 0, width, height), border_radius=16)
    
    # Desenha borda brilhante
    pygame.draw.rect(card_surf, CARD_BORDER, (0, 0, width, height), width=1, border_radius=16)
    # Glow sutil na borda inferior/superior
    pygame.draw.rect(card_surf, (*glow_color, 80), (0, 0, width, height), width=2, border_radius=16)
    
    surface.blit(card_surf, (x, y))

def draw_default_icon(surface, x, y, color):
    # Desenha um ícone de documento futurista com linhas usando vetores do pygame
    icon_surf = pygame.Surface((60, 70), pygame.SRCALPHA)
    # Retângulo principal com dobra de folha
    pts = [(0, 0), (45, 0), (60, 15), (60, 70), (0, 70)]
    pygame.draw.polygon(icon_surf, (*color, 40), pts)
    pygame.draw.polygon(icon_surf, color, pts, 2)
    # Dobra da folha
    fold_pts = [(45, 0), (45, 15), (60, 15)]
    pygame.draw.polygon(icon_surf, color, fold_pts, 2)
    # Linhas de texto simuladas
    pygame.draw.line(icon_surf, color, (15, 30), (45, 30), 2)
    pygame.draw.line(icon_surf, color, (15, 42), (45, 42), 2)
    pygame.draw.line(icon_surf, color, (15, 54), (30, 54), 2)
    
    surface.blit(icon_surf, (x, y))

def load_thumbnail(file_path):
    # Tenta carregar uma miniatura caso o arquivo seja uma imagem
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
        try:
            img = pygame.image.load(file_path)
            # Redimensiona mantendo o aspect ratio
            w, h = img.get_size()
            max_size = 70
            if w > h:
                new_w = max_size
                new_h = int(h * (max_size / w))
            else:
                new_h = max_size
                new_w = int(w * (max_size / h))
            img = pygame.transform.smoothscale(img, (new_w, new_h))
            return img
        except:
            pass
    return None

def run_overlay_loop(mode, file_path=None, custom_title=None, custom_status=None):
    """Loop do Pygame para desenhar a interface animada."""
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    pygame.init()
    pygame.font.init()
    
    width, height = 550, 350
    
    # Configurações de cores e títulos por modo
    if mode == "grab":
        glow_color = GLOW_COLOR
        title_text = custom_title if custom_title else "AirGrabbed!"
        status_text = custom_status if custom_status else "Arquivo capturado da área de transferência"
    elif mode == "drop":
        glow_color = DROP_GLOW_COLOR
        title_text = custom_title if custom_title else "AirDropped!"
        status_text = custom_status if custom_status else "Arquivo recebido com sucesso!"
    else: # cancel / warning
        glow_color = CANCEL_GLOW_COLOR
        title_text = custom_title if custom_title else "Cancelado"
        status_text = custom_status if custom_status else "Transferência de arquivo abortada."

    # Inicializa janela
    screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
    pygame.display.set_caption("AirGrab Overlay")
    
    # Aplica transparência de fundo no Windows
    if sys.platform == "win32":
        hwnd = pygame.display.get_wm_info()['window']
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, -20)
        user32.SetWindowLongW(hwnd, -20, style | 0x80000)
        user32.SetLayeredWindowAttributes(hwnd, 0xFF00FF, 0, 1) # Magenta como transparente

    # Carrega fontes
    try:
        font_title = pygame.font.SysFont("Outfit", 26, bold=True)
        font_body = pygame.font.SysFont("Inter", 16)
        font_sub = pygame.font.SysFont("Inter", 13)
    except:
        font_title = pygame.font.Font(None, 32)
        font_body = pygame.font.Font(None, 20)
        font_sub = pygame.font.Font(None, 16)

    # Detalhes do arquivo
    file_name = ""
    file_size = ""
    thumb_img = None
    if file_path and os.path.exists(file_path):
        file_name = os.path.basename(file_path)
        try:
            file_size = format_size(os.path.getsize(file_path))
        except:
            file_size = "Tamanho desconhecido"
        # Tenta carregar miniatura em background
        thumb_img = load_thumbnail(file_path)

    # Variáveis de animação
    ripples = []
    particles = []
    
    clock = pygame.time.Clock()
    start_time = time.time()
    duration = 2.5 if mode != "cancel" else 1.5
    
    # Adiciona a primeira onda
    ripples.append(Ripple(width//2, height//2, max_radius=220, speed=5, color=glow_color))
    
    running = True
    while running:
        # Fechar se ultrapassar a duração ou se o usuário fechar/apertar ESC
        if time.time() - start_time > duration:
            running = False
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN]:
                    running = False

        # Preenche fundo (Magenta no Windows para transparência de Desktop, preto no fallback)
        if sys.platform == "win32":
            screen.fill((255, 0, 255))
        else:
            # No fallback, preenche com um fundo preto bem escuro e transparente simulado
            screen.fill((15, 15, 18))

        # Atualiza e desenha ondas de água (ripples)
        # Cria novas ondas de tempos em tempos
        elapsed = time.time() - start_time
        if len(ripples) < 3 and elapsed < 1.0:
            # Adiciona onda a cada 0.25 segundos
            if int(elapsed * 4) > len(ripples):
                ripples.append(Ripple(width//2, height//2, max_radius=220, speed=5, color=glow_color))
                
        for r in ripples:
            r.update()
            r.draw(screen)
            
        # Adiciona partículas subindo do centro
        if elapsed < 1.2 and len(particles) < 40:
            particles.append(Particle(width//2 + (os.urandom(1)[0]/255 - 0.5)*150, height//2 + 40, color=glow_color))
            
        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)
            else:
                p.draw(screen)

        # Desenha o Card Central (Glassmorphism)
        card_w, card_h = 420, 160
        card_x = (width - card_w) // 2
        card_y = (height - card_h) // 2
        draw_glass_card(screen, card_x, card_y, card_w, card_h, glow_color)
        
        # Renderiza textos do Card
        # Título
        text_title = font_title.render(title_text, True, TEXT_COLOR)
        screen.blit(text_title, (card_x + 120, card_y + 25))
        
        # Descrição/Status
        text_status = font_sub.render(status_text, True, SUBTEXT_COLOR)
        screen.blit(text_status, (card_x + 120, card_y + 55))
        
        if mode != "cancel" and file_name:
            # Nome do arquivo (truncado se for muito grande)
            display_name = file_name
            if len(display_name) > 30:
                display_name = display_name[:27] + "..."
            text_file = font_body.render(display_name, True, TEXT_COLOR)
            screen.blit(text_file, (card_x + 120, card_y + 85))
            
            # Tamanho do arquivo
            text_size = font_sub.render(file_size, True, SUBTEXT_COLOR)
            screen.blit(text_size, (card_x + 120, card_y + 110))
            
            # Desenha visualizador/ícone
            if thumb_img:
                # Desenha a miniatura centralizada no espaço à esquerda
                tw, th = thumb_img.get_size()
                tx = card_x + 30 + (70 - tw) // 2
                ty = card_y + 40 + (70 - th) // 2
                screen.blit(thumb_img, (tx, ty))
                # Borda sutil na imagem
                pygame.draw.rect(screen, glow_color, (tx-1, ty-1, tw+2, th+2), 1, border_radius=4)
            else:
                draw_default_icon(screen, card_x + 35, card_y + 40, glow_color)
        else:
            # Caso seja modo cancel, centraliza o título e status um pouco mais
            # ou desenha um grande ícone de "X" vermelho
            if mode == "cancel":
                # Desenha ícone de cancelar (X)
                pygame.draw.line(screen, CANCEL_GLOW_COLOR, (card_x + 50, card_y + 55), (card_x + 85, card_y + 90), 4)
                pygame.draw.line(screen, CANCEL_GLOW_COLOR, (card_x + 85, card_y + 55), (card_x + 50, card_y + 90), 4)

        pygame.display.flip()
        clock.tick(60)
        
    pygame.display.quit()
    pygame.quit()

def trigger_grab_overlay(file_path):
    threading.Thread(target=run_overlay_loop, args=("grab", file_path), daemon=True).start()

def trigger_drop_overlay(file_path):
    threading.Thread(target=run_overlay_loop, args=("drop", file_path), daemon=True).start()

def trigger_cancel_overlay(title=None, status=None):
    threading.Thread(target=run_overlay_loop, args=("cancel", None, title, status), daemon=True).start()
