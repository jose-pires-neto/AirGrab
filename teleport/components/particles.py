import pygame
import math
import os

def _rb():
    return os.urandom(1)[0] / 255.0

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

class GlowParticle:
    def __init__(self, x, y, color=(0,255,255)):
        self.x=x; self.y=y
        self.vx=(_rb()-0.5)*4; self.vy=(_rb()-0.5)*4-2.0
        self.life=255; self.decay=6+_rb()*8; self.color=color
        
    def update(self): 
        self.x+=self.vx; self.y+=self.vy; self.life-=self.decay
        
    def draw(self,surface):
        if self.life>0:
            s=pygame.Surface((10,10),pygame.SRCALPHA)
            pygame.draw.circle(s,(*self.color,int(self.life)),(5,5),4)
            surface.blit(s,(int(self.x-5),int(self.y-5)))
