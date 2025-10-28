import pygame
import sys
import random
import os
import math

# --- スクリプトのパスを基準にディレクトリを設定 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")

# --- 定数 (Constants) ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
FPS = 60

# 色 (Colors)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)

# --- ゲームの初期化 (Game Initialization) ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Xevious Style Shooter")
clock = pygame.time.Clock()

# --- 画像ファイルの読み込み (Load Images) ---
if not os.path.exists(fig_dir):
    os.makedirs(fig_dir)
    print(f"Warning: '{fig_dir}' directory not found. Please place images inside.")

try:
    PLAYER_IMAGE = pygame.image.load(os.path.join(fig_dir, "koukaton.png")).convert_alpha()
    ENEMY_IMAGE = pygame.image.load(os.path.join(fig_dir, "enemy.png")).convert_alpha()
    PLAYER_BULLET_IMAGE = pygame.image.load(os.path.join(fig_dir, "beam.png")).convert_alpha()
    try: LAZER_IMAGE = pygame.image.load(os.path.join(fig_dir, "lazer.png")).convert_alpha()
    except pygame.error: print("Warning: lazer.png not found."); LAZER_IMAGE = pygame.Surface((20, SCREEN_HEIGHT)); LAZER_IMAGE.fill(CYAN); LAZER_IMAGE.set_colorkey(BLACK)
    try: HEAL_ITEM_IMAGE = pygame.image.load(os.path.join(fig_dir, "heal.png")).convert_alpha()
    except pygame.error: HEAL_ITEM_IMAGE = pygame.Surface((25, 25)); HEAL_ITEM_IMAGE.fill(GREEN)
    try: ATTACK_ITEM_IMAGE = pygame.image.load(os.path.join(fig_dir, "attack.png")).convert_alpha()
    except pygame.error: ATTACK_ITEM_IMAGE = pygame.Surface((25, 25)); ATTACK_ITEM_IMAGE.fill(YELLOW)
    try: EXPLOSION_IMAGE = pygame.image.load(os.path.join(fig_dir, "explosion.png")).convert_alpha()
    except pygame.error: print("Warning: explosion.png not found."); EXPLOSION_IMAGE = pygame.Surface((60, 60), pygame.SRCALPHA); pygame.draw.circle(EXPLOSION_IMAGE, RED, (30, 30), 30)
except pygame.error as e:
    print(f"Error loading image: {e}"); pygame.quit(); sys.exit()

# --- クラス定義 ---
class Player(pygame.sprite.Sprite):
    def __init__(self):super().__init__();self.image=pygame.transform.scale(PLAYER_IMAGE,(40,40));self.rect=self.image.get_rect(centerx=SCREEN_WIDTH//2,bottom=SCREEN_HEIGHT-30);self.speed_x=0;self.hidden=False;self.max_health=100;self.health=self.max_health;self.shoot_delay=250;self.last_shot=pygame.time.get_ticks();self.powerup_level=0;self.powerup_duration=7000;self.powerup_end_time=0;self.active_laser=None
    def update(self):
        if self.hidden:return
        self.speed_x=0;keys=pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:self.speed_x=-7
        if keys[pygame.K_RIGHT]:self.speed_x=7
        self.rect.x+=self.speed_x
        if self.rect.right>SCREEN_WIDTH:self.rect.right=SCREEN_WIDTH
        if self.rect.left<0:self.rect.left=0
        if self.powerup_level>0 and pygame.time.get_ticks()>self.powerup_end_time:self.powerup_level=0; (self.active_laser.kill(), setattr(self, 'active_laser', None)) if self.active_laser else None; print("Power-up ended.")
    def shoot(self,all_sprites,bullets_group):
        if self.hidden:return
        now=pygame.time.get_ticks()
        if now-self.last_shot>self.shoot_delay:
            self.last_shot=now
            if self.powerup_level==0:bullet=PlayerBullet(self.rect.centerx,self.rect.top);all_sprites.add(bullet);bullets_group.add(bullet)
            elif self.powerup_level==1:bullet1=PlayerBullet(self.rect.centerx,self.rect.top,speed_x=0);bullet2=PlayerBullet(self.rect.centerx,self.rect.top,speed_x=-3);bullet3=PlayerBullet(self.rect.centerx,self.rect.top,speed_x=3);all_sprites.add(bullet1,bullet2,bullet3);bullets_group.add(bullet1,bullet2,bullet3)
            elif self.powerup_level>=2:bullet2=PlayerBullet(self.rect.centerx,self.rect.top,speed_x=-4);bullet3=PlayerBullet(self.rect.centerx,self.rect.top,speed_x=4);all_sprites.add(bullet2,bullet3);bullets_group.add(bullet2,bullet3)
    def take_damage(self,amount):self.health-=amount;self.health=max(0,self.health);return self.health<=0
    def heal(self,amount):self.health+=amount;self.health=min(self.health,self.max_health)
    def power_up(self):self.powerup_level=min(2,self.powerup_level+1);self.powerup_end_time=pygame.time.get_ticks()+self.powerup_duration;print(f"Power-up! Level {self.powerup_level}")
    def hide(self):self.hidden=True;self.kill()
class Enemy(pygame.sprite.Sprite):
    def __init__(self,speed_level=0,player_ref=None):super().__init__();self.image=pygame.transform.scale(ENEMY_IMAGE,(40,40));self.rect=self.image.get_rect(x=random.randrange(0,SCREEN_WIDTH-40),y=random.randrange(-100,-40));speed_increase=speed_level*0.4;self.speed_y=random.randrange(int(2+speed_increase),int(5+speed_increase)+1);self.player=player_ref;self.health=1;self.score_value=1
    def update(self):self.rect.y+=self.speed_y; (self.kill() if self.rect.top>SCREEN_HEIGHT+10 else None)
    def hit(self):self.health-=1;return self.health<=0
class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self,x,y,speed_x=0):super().__init__();self.image=pygame.transform.scale(PLAYER_BULLET_IMAGE,(10,25));self.rect=self.image.get_rect(center=(x,y));self.speed_y=-10;self.speed_x=speed_x
    def update(self):self.rect.y+=self.speed_y;self.rect.x+=self.speed_x; (self.kill() if not screen.get_rect().colliderect(self.rect) else None)
class SuperLaser(pygame.sprite.Sprite):
    def __init__(self,player_obj):super().__init__();self.player=player_obj;self.image=pygame.transform.scale(LAZER_IMAGE,(20,SCREEN_HEIGHT));self.rect=self.image.get_rect();self.update()
    def update(self):self.rect.centerx=self.player.rect.centerx;self.rect.bottom=self.player.rect.top
class Item(pygame.sprite.Sprite):
    def __init__(self,center):super().__init__();self.rect=self.image.get_rect(center=center);self.speed_y=3
    def update(self):self.rect.y+=self.speed_y; (self.kill() if self.rect.top>SCREEN_HEIGHT else None)
class HealItem(Item):
    def __init__(self,center):self.image=pygame.transform.scale(HEAL_ITEM_IMAGE,(30,30));super().__init__(center)
    def apply_effect(self,player):player.heal(25)
class AttackUpItem(Item):
    def __init__(self,center):self.image=pygame.transform.scale(ATTACK_ITEM_IMAGE,(30,30));super().__init__(center)
    def apply_effect(self,player):player.power_up()
class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, size="normal"):
        super().__init__()
        self.original_image = EXPLOSION_IMAGE
        scale = (90, 90) if size == "large" else (60, 60)
        self.image = pygame.transform.scale(self.original_image, scale)
        self.rect = self.image.get_rect(center=center)
        self.duration = 400
        self.creation_time = pygame.time.get_ticks()
    def update(self):
        if pygame.time.get_ticks() - self.creation_time > self.duration: self.kill()

# --- 描画関数群 ---
def draw_stars(surface, stars, speed_level=0):
    speed_modifier=1.0+speed_level*0.15
    for star in stars:pygame.draw.circle(surface,WHITE,(star[0],star[1]),star[3]);star[1]+=star[2]*speed_modifier; (star.clear(),star.extend([random.randrange(0,SCREEN_WIDTH),0,random.randrange(1,4),random.randrange(1,4)]))if star[1]>SCREEN_HEIGHT else None
def draw_text(surface, text, font, color, x, y, align="topright"):
    text_surface=font.render(text,True,color);text_rect=text_surface.get_rect()
    if align=="topright":text_rect.topright=(x,y)
    elif align=="center":text_rect.center=(x,y)
    elif align=="topleft":text_rect.topleft=(x,y)
    surface.blit(text_surface,text_rect)
def draw_health_bar(surface, x, y, pct):
    pct=max(0,pct);BAR_LENGTH,BAR_HEIGHT=150,15;fill=(pct/100)*BAR_LENGTH;bar_color=GREEN if pct>60 else YELLOW if pct>30 else RED;pygame.draw.rect(surface,bar_color,(x,y,fill,BAR_HEIGHT));pygame.draw.rect(surface,WHITE,(x,y,BAR_LENGTH,BAR_HEIGHT),2)

# --- ゲームのセットアップ ---
score_font = pygame.font.SysFont(None, 36)
game_over_font = pygame.font.SysFont(None, 64, bold=True)
info_font = pygame.font.SysFont(None, 30)
stars = [[random.randrange(0,SCREEN_WIDTH),random.randrange(0,SCREEN_HEIGHT),random.randrange(1,4),random.randrange(1,4)]for _ in range(100)]
all_sprites,enemies_group,player_bullets_group,items_group,laser_group=pygame.sprite.Group(),pygame.sprite.Group(),pygame.sprite.Group(),pygame.sprite.Group(),pygame.sprite.Group()
player = Player();all_sprites.add(player)
ADD_ENEMY = pygame.USEREVENT+1
pygame.time.set_timer(ADD_ENEMY, 1000)
score, game_speed_level, game_over, running = 0, 0, False, True

# --- メインゲームループ (Main Game Loop) ---
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:running = False
        elif game_over and event.type == pygame.KEYDOWN: running = False
        elif event.type == ADD_ENEMY and not game_over:
            enemy = Enemy(game_speed_level, player);all_sprites.add(enemy);enemies_group.add(enemy)
    keys=pygame.key.get_pressed()
    if keys[pygame.K_SPACE]and not game_over:player.shoot(all_sprites,player_bullets_group)
    if player.powerup_level>=2 and not game_over:
        if keys[pygame.K_SPACE]:
            if not player.active_laser:player.active_laser=SuperLaser(player);all_sprites.add(player.active_laser);laser_group.add(player.active_laser)
        else:
            if player.active_laser:player.active_laser.kill();player.active_laser=None
    else:
        if player.active_laser:player.active_laser.kill();player.active_laser=None
    if not game_over:all_sprites.update()
    else:
        for s in all_sprites:
            if isinstance(s,Explosion):s.update()

    # --- 衝突判定 ---
    if not game_over:
        hits = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, True)
        laser_hits = pygame.sprite.groupcollide(laser_group, enemies_group, False, True)
        hits.update(laser_hits)

        for bullet_or_laser, enemies_hit in hits.items():
            for enemy in enemies_hit:
                score += enemy.score_value
                all_sprites.add(Explosion(enemy.rect.center, "normal"))
                if random.random() > 0.8:
                    # ▼▼▼ タイプミスを修正 ▼▼▼
                    item = random.choice([HealItem, AttackUpItem])(enemy.rect.center)
                    # ▲▲▲ タイプミスを修正 ▲▲▲
                    all_sprites.add(item)
                    items_group.add(item)

        new_level=score//10
        if new_level>game_speed_level:game_speed_level=new_level;rate=max(150,int(1000*(0.9**game_speed_level)));pygame.time.set_timer(ADD_ENEMY,rate)
        if pygame.sprite.spritecollide(player,enemies_group,True):
            if player.take_damage(10):game_over=True;all_sprites.add(Explosion(player.rect.center,"large"));player.hide()
            else:all_sprites.add(Explosion(player.rect.center,"normal"))
        for item in pygame.sprite.spritecollide(player,items_group,True):item.apply_effect(player)
        
    # --- 描画処理 ---
    screen.fill(BLACK)
    draw_stars(screen, stars, game_speed_level)
    all_sprites.draw(screen)
    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH-10, 10, "topright")
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, "topleft")
    draw_text(screen, "HP", score_font, WHITE, 10, 40, "topleft")
    draw_health_bar(screen, 50, 45, player.health)
    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH//2, SCREEN_HEIGHT//2, "center")
        draw_text(screen, "Press any key to exit", info_font, WHITE, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50, "center")
    pygame.display.flip()

pygame.quit()
sys.exit()