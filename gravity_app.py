from __future__ import annotations

import math
import random
import sys
from collections import deque
from dataclasses import dataclass

import pygame

from gravity_sim import Body, NBodySimulation

WIDTH, HEIGHT = 1100, 720
BACKGROUND = (10, 13, 22)
GRID = (26, 31, 44)
TEXT = (225, 230, 240)
MUTED = (150, 160, 180)
ACCENT = (95, 180, 255)
PANEL = (19, 24, 36)
PANEL_HOVER = (31, 39, 56)
LOCK_COLOR = (255, 235, 120)

PALETTE = [
    (140, 220, 255), (255, 150, 120), (180, 255, 160), (225, 180, 255),
    (255, 220, 110), (245, 245, 245), (120, 150, 255), (255, 110, 180),
]
GALAXY_COLORS = [(235,240,255),(190,210,255),(150,180,255),(255,238,200),(255,210,155)]


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    description: str


SCENARIOS = [
    Scenario("solar", "Solar System", "Sun + 8 planets with realistic relative masses and orbital spacing."),
    Scenario("binary", "Binary Star System", "Two stars orbiting each other with circumbinary planets."),
    Scenario("random", "Randomized System", "A fresh random star cluster / planetary system every time."),
    Scenario("galaxy", "Spiral Galaxy", "Dense bulge + four spiral arms with about 1,200 stars."),
]


def solar_system() -> list[Body]:
    au = 18.0
    sun = Body(0, 0, 0, 0, 1.0, 14, (255,210,80), "Sun")
    data = [
        ("Mercury", .387, 1.66e-7, 3.0, (170,165,155)),
        ("Venus", .723, 2.45e-6, 4.5, (220,185,105)),
        ("Earth", 1.0, 3e-6, 4.8, (70,145,255)),
        ("Mars", 1.524, 3.23e-7, 4.0, (215,95,65)),
        ("Jupiter", 5.203, 9.54e-4, 8.8, (220,175,125)),
        ("Saturn", 9.537, 2.86e-4, 8.0, (225,200,135)),
        ("Uranus", 19.191, 4.37e-5, 6.7, (135,220,230)),
        ("Neptune", 30.069, 5.15e-5, 6.5, (75,115,245)),
    ]
    phases = [.2,1.1,2.2,3.1,4.0,5.0,.9,2.7]
    bodies = [sun]
    for (name,a,mass,radius,color),phase in zip(data,phases):
        r=a*au; speed=math.sqrt(sun.mass/r)
        bodies.append(Body(math.cos(phase)*r, math.sin(phase)*r,
                           -math.sin(phase)*speed, math.cos(phase)*speed,
                           mass,radius,color,name))
    return bodies


def binary_system() -> list[Body]:
    m1,m2=700.0,520.0; separation=95.0; total=m1+m2
    r1=separation*m2/total; r2=separation*m1/total; omega=math.sqrt(total/separation**3)
    bodies=[Body(-r1,0,0,-omega*r1,m1,12,(255,215,120),"Helios A"),
            Body(r2,0,0,omega*r2,m2,10,(255,150,110),"Helios B")]
    configs=[(190,5,5,(100,175,255)),(285,9,6,(180,240,155)),(405,15,7,(215,155,240))]
    for idx,(r,mass,radius,color) in enumerate(configs,1):
        phase=.8+idx*1.7; speed=math.sqrt(total/r)
        bodies.append(Body(math.cos(phase)*r,math.sin(phase)*r,-math.sin(phase)*speed,
                           math.cos(phase)*speed,mass,radius,color,f"Circumbinary {idx}"))
    return bodies


def randomized_system(count: int = 120) -> list[Body]:
    star_mass=random.uniform(900,1800)
    bodies=[Body(0,0,0,0,star_mass,14,(255,210,95),"Primary")]
    for i in range(count):
        r=random.uniform(55,520); phase=random.random()*math.tau
        tangent=math.sqrt(star_mass/r)*random.uniform(.78,1.18); radial=random.uniform(-.15,.15)
        mass=10**random.uniform(-1,1.2); color=random.choice(PALETTE)
        radius=max(2.5,min(8.5,2.4+math.sqrt(mass)))
        bodies.append(Body(math.cos(phase)*r,math.sin(phase)*r,
                           -math.sin(phase)*tangent+math.cos(phase)*radial,
                           math.cos(phase)*tangent+math.sin(phase)*radial,
                           mass,radius,color,f"Random {i+1}"))
    return bodies


def spiral_galaxy(star_count: int = 1200, arm_count: int = 4) -> list[Body]:
    central_mass=5200.0; disk_mass_scale=2100.0; bulge_count=max(160,star_count//5)
    outer_radius=780.0
    bodies=[Body(0,0,0,0,central_mass,11,(255,245,205),"Galactic Core")]
    def circular_speed(r: float) -> float:
        enclosed_disk=disk_mass_scale*(r/(r+220)); enclosed_bulge=650*(r/(r+70))
        return math.sqrt((central_mass+enclosed_disk+enclosed_bulge)/max(r,8))
    for i in range(bulge_count):
        r=min(190,abs(random.gauss(0,62)))+random.uniform(4,22); angle=random.random()*math.tau
        x=math.cos(angle)*r; y=math.sin(angle)*r*random.uniform(.78,1)
        speed=circular_speed(r)*random.uniform(.78,1.08)
        vx=-math.sin(angle)*speed+random.gauss(0,.35); vy=math.cos(angle)*speed+random.gauss(0,.35)
        bodies.append(Body(x,y,vx,vy,random.uniform(.7,2.2),random.uniform(1.1,2),
                           random.choice([(255,225,175),(255,205,145),(245,235,210)]),f"Bulge {i+1}"))
    for i in range(star_count-bulge_count):
        arm=i%arm_count; u=random.random()**.58; r=75+u*(outer_radius-75)
        angle=arm*math.tau/arm_count+5.15*(r/outer_radius)**.88+random.gauss(0,.11+.05*r/outer_radius)
        rr=max(28,r+random.gauss(0,8+.025*r)); x=math.cos(angle)*rr; y=math.sin(angle)*rr
        speed=circular_speed(rr)*random.uniform(.93,1.07); radial=random.gauss(0,.12)
        vx=-math.sin(angle)*speed+math.cos(angle)*radial; vy=math.cos(angle)*speed+math.sin(angle)*radial
        color=random.choices(GALAXY_COLORS,weights=(30,23,13,22,12),k=1)[0]
        bodies.append(Body(x,y,vx,vy,random.uniform(.45,1.7),random.uniform(.85,1.55),color,f"Star {i+1}"))
    return bodies


def scenario_bodies(key: str) -> tuple[list[Body], float, float]:
    if key=="solar": return solar_system(),.08,.58
    if key=="binary": return binary_system(),2.5,.95
    if key=="galaxy": return spiral_galaxy(),5.0,.62
    return randomized_system(),3.0,.92


class GravityApp:
    def __init__(self) -> None:
        pygame.init(); pygame.display.set_caption("2D Gravity Simulator")
        self.screen=pygame.display.set_mode((WIDTH,HEIGHT),pygame.RESIZABLE); self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("consolas",18); self.small_font=pygame.font.SysFont("consolas",15)
        self.big_font=pygame.font.SysFont("consolas",34,bold=True); self.title_font=pygame.font.SysFont("consolas",23,bold=True)
        self.mode="menu"; self.current_scenario="solar"; self.sim=NBodySimulation([],softening=3)
        self.paused=False; self.show_trails=True; self.time_scale=1.0; self.zoom=1.0
        self.camera_x=self.camera_y=0.0; self.trail_maxlen=600; self.trails=[]; self.drag_start=None
        self.reference_body=None; self.reference_pick_armed=False
        self.spawn_color_index=0; self.spawn_radius=6.0; self.spawn_mass=8.0; self.menu_rects={}

    def ensure_trails(self):
        while len(self.trails)<len(self.sim.bodies): self.trails.append(deque(maxlen=self.trail_maxlen))
        if len(self.trails)>len(self.sim.bodies): self.trails=self.trails[:len(self.sim.bodies)]

    def load_scenario(self,key):
        bodies,softening,zoom=scenario_bodies(key); self.current_scenario=key
        self.sim=NBodySimulation(bodies,softening=softening,fmm_order=4,fmm_leaf_capacity=48)
        self.trail_maxlen=120 if key=="galaxy" else 600; self.trails=[]; self.ensure_trails()
        self.show_trails=key!="galaxy"; self.time_scale=1; self.zoom=zoom; self.camera_x=self.camera_y=0
        self.reference_body=None; self.reference_pick_armed=False; self.paused=False; self.mode="simulation"

    def reset(self): self.load_scenario(self.current_scenario)
    def reference_index(self):
        if self.reference_body is None:return None
        for i,b in enumerate(self.sim.bodies):
            if b is self.reference_body:return i
        self.reference_body=None; return None
    def reference_origin(self):
        i=self.reference_index(); return (0,0) if i is None else (self.sim.bodies[i].x,self.sim.bodies[i].y)
    def clear_reference(self): self.reference_body=None; self.reference_pick_armed=False; self.camera_x=self.camera_y=0
    def world_to_screen(self,x,y):
        w,h=self.screen.get_size(); rx,ry=self.reference_origin()
        return int((x-rx-self.camera_x)*self.zoom+w/2),int((y-ry-self.camera_y)*self.zoom+h/2)
    def screen_to_world(self,sx,sy):
        w,h=self.screen.get_size(); rx,ry=self.reference_origin()
        return (sx-w/2)/self.zoom+self.camera_x+rx,(sy-h/2)/self.zoom+self.camera_y+ry
    def nearest_body_on_screen(self,pos,max_distance_px=28):
        best=None; bestd=max_distance_px**2
        for b in self.sim.bodies:
            sx,sy=self.world_to_screen(b.x,b.y); d=(sx-pos[0])**2+(sy-pos[1])**2
            if d<=bestd: best,bestd=b,d
        return best
    def choose_reference_body(self,pos):
        b=self.nearest_body_on_screen(pos)
        if b is not None:self.reference_body=b; self.reference_pick_armed=False; self.camera_x=self.camera_y=0
    @property
    def spawn_color(self): return PALETTE[self.spawn_color_index]
    def add_body(self,pos):
        x,y=self.screen_to_world(*pos); a=random.random()*math.tau; speed=random.uniform(.15,1)
        rvx=self.reference_body.vx if self.reference_index() is not None else 0; rvy=self.reference_body.vy if self.reference_index() is not None else 0
        self.sim.bodies.append(Body(x,y,rvx+math.cos(a)*speed,rvy+math.sin(a)*speed,self.spawn_mass,self.spawn_radius,self.spawn_color,f"Custom {len(self.sim.bodies)+1}")); self.ensure_trails()
    def remove_nearest(self,pos):
        if not self.sim.bodies:return
        x,y=self.screen_to_world(*pos); i=min(range(len(self.sim.bodies)),key=lambda k:(self.sim.bodies[k].x-x)**2+(self.sim.bodies[k].y-y)**2)
        removed=self.sim.bodies[i]; del self.sim.bodies[i]; del self.trails[i]
        if removed is self.reference_body:self.clear_reference()

    def handle_menu_event(self,e):
        if e.type==pygame.QUIT:return False
        if e.type==pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE,pygame.K_q):return False
            mapping={pygame.K_1:"solar",pygame.K_2:"binary",pygame.K_3:"random",pygame.K_4:"galaxy"}
            if e.key in mapping:self.load_scenario(mapping[e.key])
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
            for key,rect in self.menu_rects.items():
                if rect.collidepoint(e.pos):self.load_scenario(key);break
        return True

    def handle_simulation_event(self,e):
        if e.type==pygame.QUIT:return False
        if e.type==pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE,pygame.K_q):return False
            if e.key==pygame.K_SPACE:self.paused=not self.paused
            elif e.key==pygame.K_r:self.reset()
            elif e.key==pygame.K_m:self.mode="menu"
            elif e.key==pygame.K_t:self.show_trails=not self.show_trails
            elif e.key==pygame.K_b:self.sim.cycle_solver()
            elif e.key==pygame.K_f:
                if self.reference_body is not None:self.clear_reference()
                else:self.reference_pick_armed=not self.reference_pick_armed
            elif e.key==pygame.K_c:self.spawn_color_index=(self.spawn_color_index+1)%len(PALETTE)
            elif e.key in (pygame.K_RIGHTBRACKET,pygame.K_PERIOD):self.spawn_radius=min(30,self.spawn_radius+1);self.spawn_mass=min(200,self.spawn_mass*1.35)
            elif e.key in (pygame.K_LEFTBRACKET,pygame.K_COMMA):self.spawn_radius=max(2,self.spawn_radius-1);self.spawn_mass=max(.1,self.spawn_mass/1.35)
            elif e.key in (pygame.K_EQUALS,pygame.K_PLUS,pygame.K_KP_PLUS):self.time_scale=min(4096,self.time_scale*2)
            elif e.key in (pygame.K_MINUS,pygame.K_KP_MINUS):self.time_scale=max(.0625,self.time_scale/2)
        elif e.type==pygame.MOUSEWHEEL:self.zoom=max(.03,min(12,self.zoom*1.12**e.y))
        elif e.type==pygame.MOUSEBUTTONDOWN:
            if e.button==1:
                if self.reference_pick_armed:self.choose_reference_body(e.pos)
                else:self.add_body(e.pos)
            elif e.button==3:self.remove_nearest(e.pos)
            elif e.button==2 and self.reference_body is None:self.drag_start=e.pos
        elif e.type==pygame.MOUSEBUTTONUP and e.button==2:self.drag_start=None
        elif e.type==pygame.MOUSEMOTION and self.drag_start is not None:
            dx=e.pos[0]-self.drag_start[0];dy=e.pos[1]-self.drag_start[1];self.camera_x-=dx/self.zoom;self.camera_y-=dy/self.zoom;self.drag_start=e.pos
        return True
    def handle_event(self,e): return self.handle_menu_event(e) if self.mode=="menu" else self.handle_simulation_event(e)

    def update(self):
        if self.mode!="simulation":return
        if not self.paused:
            total_dt=.045*self.time_scale; n=len(self.sim.bodies)
            if self.sim.active_solver=="fmm" and n>=500:cap=2
            elif n>=500:cap=8
            elif n>=100:cap=20
            else:cap=48
            substeps=max(1,min(cap,int(math.ceil(math.sqrt(self.time_scale))))); dt=total_dt/substeps
            for _ in range(substeps):self.sim.step(dt)
        self.ensure_trails()
        for t,b in zip(self.trails,self.sim.bodies):t.append((b.x,b.y))

    def draw_grid(self):
        w,h=self.screen.get_size(); spacing=100.0; px=spacing*self.zoom
        if px<35:spacing*=math.ceil(35/max(px,.001))
        left,top=self.screen_to_world(0,0);right,bottom=self.screen_to_world(w,h)
        x=math.floor(left/spacing)*spacing
        while x<=right:
            sx,_=self.world_to_screen(x,0);pygame.draw.line(self.screen,GRID,(sx,0),(sx,h),1);x+=spacing
        y=math.floor(top/spacing)*spacing
        while y<=bottom:
            _,sy=self.world_to_screen(0,y);pygame.draw.line(self.screen,GRID,(0,sy),(w,sy),1);y+=spacing
    def transformed_trail_points(self,i):
        trail=self.trails[i]; ri=self.reference_index()
        if ri is None:return [self.world_to_screen(x,y) for x,y in trail]
        rt=self.trails[ri]; n=min(len(trail),len(rt))
        if n<2:return []
        w,h=self.screen.get_size(); out=[]
        for (x,y),(rx,ry) in zip(list(trail)[-n:],list(rt)[-n:]):out.append((int((x-rx)*self.zoom+w/2),int((y-ry)*self.zoom+h/2)))
        return out

    def draw_menu(self):
        self.screen.fill(BACKGROUND);w,h=self.screen.get_size()
        title=self.big_font.render("Choose a Starting System",True,TEXT);sub=self.font.render("Click a template or press 1 / 2 / 3 / 4",True,MUTED)
        self.screen.blit(title,(w//2-title.get_width()//2,42));self.screen.blit(sub,(w//2-sub.get_width()//2,86))
        mouse=pygame.mouse.get_pos();card_w=min(780,w-80);card_h=105;gap=12;top=130;self.menu_rects={}
        for i,s in enumerate(SCENARIOS):
            rect=pygame.Rect((w-card_w)//2,top+i*(card_h+gap),card_w,card_h);self.menu_rects[s.key]=rect
            pygame.draw.rect(self.screen,PANEL_HOVER if rect.collidepoint(mouse) else PANEL,rect,border_radius=12);pygame.draw.rect(self.screen,ACCENT,rect,2,border_radius=12)
            self.screen.blit(self.title_font.render(str(i+1),True,ACCENT),(rect.x+22,rect.y+16));self.screen.blit(self.title_font.render(s.title,True,TEXT),(rect.x+62,rect.y+15));self.screen.blit(self.small_font.render(s.description,True,MUTED),(rect.x+62,rect.y+53))
        note=self.small_font.render("B cycles Auto / FMM / Barnes-Hut / Exact while running.",True,MUTED);y=top+len(SCENARIOS)*(card_h+gap)+8;self.screen.blit(note,(w//2-note.get_width()//2,y));pygame.display.flip()

    def draw_simulation(self):
        self.screen.fill(BACKGROUND);self.draw_grid()
        if self.show_trails:
            for i,b in enumerate(self.sim.bodies):
                pts=self.transformed_trail_points(i)
                if len(pts)>=2:pygame.draw.lines(self.screen,b.color,False,pts,1)
        for b in self.sim.bodies:
            sx,sy=self.world_to_screen(b.x,b.y);radius=max(1,int(b.radius*min(self.zoom,2.2)));pygame.draw.circle(self.screen,b.color,(sx,sy),radius)
            if b is self.reference_body:pygame.draw.circle(self.screen,LOCK_COLOR,(sx,sy),radius+5,2)
        status="PAUSED" if self.paused else "RUNNING";solver=self.sim.active_solver.upper();ref=self.reference_body.name if self.reference_index() is not None else "World"
        header=f"{status}   bodies={len(self.sim.bodies)}   solver={solver}   mode={self.sim.solver_mode}   speed={self.time_scale:g}x   zoom={self.zoom:.2f}x   frame={ref}"
        self.screen.blit(self.font.render(header,True,TEXT),(16,14))
        spawn=f"New body: radius={self.spawn_radius:.0f}  mass={self.spawn_mass:.2f}  color=";surf=self.small_font.render(spawn,True,MUTED);self.screen.blit(surf,(16,43));pygame.draw.circle(self.screen,self.spawn_color,(24+surf.get_width(),51),7)
        if self.reference_pick_armed:self.screen.blit(self.font.render("REFERENCE PICK: click a body",True,LOCK_COLOR),(16,67));cy=94
        elif self.reference_body is not None:self.screen.blit(self.small_font.render(f"Reference frame: {self.reference_body.name}   F: release",True,LOCK_COLOR),(16,68));cy=92
        else:cy=68
        controls=[
            "B: cycle solver Auto -> FMM -> Barnes-Hut -> Exact   F then click: reference frame",
            "Left click: add body   Right click: remove   Middle-drag: pan   Mouse wheel: zoom",
            "C: color   [ / ]: smaller/larger   +/-: speed   T: trails   Space: pause",
            "R: reset   M: scenario menu   Esc/Q: quit",
        ]
        for i,line in enumerate(controls):self.screen.blit(self.small_font.render(line,True,MUTED),(16,cy+21*i))
        pygame.display.flip()
    def draw(self): self.draw_menu() if self.mode=="menu" else self.draw_simulation()
    def run(self):
        running=True
        while running:
            for e in pygame.event.get():
                running=self.handle_event(e)
                if not running:break
            self.update();self.draw();self.clock.tick(60)
        pygame.quit()


def main() -> int:
    try:GravityApp().run();return 0
    except pygame.error as exc:print(f"Pygame could not start: {exc}",file=sys.stderr);return 1
