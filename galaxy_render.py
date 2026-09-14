"""Cached additive lighting; this module never changes physical particles.

The central light represents the existing fixed Plummer bulge. Purple disk
colors are an intentionally stylized palette, not spectral/temperature data.
"""
import math
import random

import pygame


class GalaxyLighting:
    def __init__(self):
        self.glows = {}
        self.bulge = pygame.Surface((520,520)).convert()
        self.bulge.fill((0,0,0))
        # Projected Plummer-like surface brightness, with a warm unresolved core.
        for r in range(259,0,-1):
            density = (1+(r/65)**2)**-2
            color = (int(150*density),int(84*density),int(114*density))
            pygame.draw.circle(self.bulge,color,(260,260),r)
        rng = random.Random(2048)
        for _ in range(4200):
            u=rng.random()*.94
            r=65*math.sqrt(u/(1-u))
            angle=rng.random()*math.tau
            x,y=round(260+r*math.cos(angle)),round(260+r*math.sin(angle))
            if 0<=x<520 and 0<=y<520:
                brightness=rng.randrange(35,140)
                self.bulge.set_at((x,y),(brightness,int(brightness*.72),int(brightness*.75)))
        self._scaled = None
        self._size = None

    def draw_bulge(self, screen, center, zoom):
        size=max(1,round(520*zoom))
        rect=pygame.Rect(0,0,size,size)
        rect.center=center
        visible=rect.clip(screen.get_rect())
        if not visible.width or not visible.height:
            return
        if size <= 1600:
            if size != self._size:
                self._scaled=pygame.transform.smoothscale(self.bulge,(size,size))
                self._size=size
            screen.blit(self._scaled,rect,special_flags=pygame.BLEND_RGB_ADD)
        else:
            # At extreme zoom scale only the visible portion, avoiding huge textures.
            source=pygame.Rect(int((visible.x-rect.x)/zoom),int((visible.y-rect.y)/zoom),
                               math.ceil(visible.width/zoom)+1,math.ceil(visible.height/zoom)+1)
            source=source.clip(self.bulge.get_rect())
            if source.width and source.height:
                patch=pygame.transform.smoothscale(self.bulge.subsurface(source),visible.size)
                screen.blit(patch,visible,special_flags=pygame.BLEND_RGB_ADD)

    def draw_star(self, screen, body, center, zoom):
        radius=max(3,min(20,round((6+body.radius*4)*math.sqrt(zoom))))
        key=(body.color,radius)
        if key not in self.glows:
            glow=pygame.Surface((radius*2+1,radius*2+1)).convert()
            glow.fill((0,0,0))
            for r in range(radius,0,-1):
                strength=.20*(1-r/(radius+1))**2
                pygame.draw.circle(glow,tuple(int(c*strength) for c in body.color),(radius,radius),r)
            self.glows[key]=glow
        screen.blit(self.glows[key],(center[0]-radius,center[1]-radius),special_flags=pygame.BLEND_RGB_ADD)
