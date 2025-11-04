# game.py
# 完整修正版：事件驱动 V（蓄力）、MidBoss 可受伤、Boss 子弹伤害统一、优先加载 super_enemy.png
import pygame
import sys
import random
import os
import math

# --- 路径 & 常量 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
FPS = 60

WHITE = (255,255,255)
BLACK = (0,0,0)
RED = (255,50,50)
YELLOW = (255,255,0)
GREEN = (0,255,0)
GRAY = (100,100,100)
CYAN = (0,255,255)

# 可调常量
ENEMY_BULLET_DAMAGE = 10    # 敌方子弹（包括中boss）单颗伤害
PLAYER_COLLIDE_DAMAGE = 20
IWA_COLLIDE_DAMAGE = 30
MID_BOSS_SPAWN_SCORE = 5    # 中ボス出现阈值（改为50也可）

# --- 初始化 ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Xevious Style Shooter (V-fixed, MidBoss hits)")
clock = pygame.time.Clock()

# --- 资源加载（安全）---
if not os.path.exists(fig_dir):
    os.makedirs(fig_dir)

def safe_load(path, fallback_size=(40,40), fillcolor=(120,120,120)):
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill(fillcolor)
        return surf

PLAYER_IMAGE = safe_load(os.path.join(fig_dir, "koukaton.png"), (40,40))
ENEMY_IMAGE = safe_load(os.path.join(fig_dir, "enemy.png"), (40,40))
PLAYER_BULLET_IMAGE = safe_load(os.path.join(fig_dir, "beam.png"), (25,15))
ENEMY_BULLET_IMAGE = safe_load(os.path.join(fig_dir, "beam.png"), (30,15))
IWA_IMAGE = safe_load(os.path.join(fig_dir, "iwa_01.png"), (100,100))
LAZER_IMAGE = safe_load(os.path.join(fig_dir, "lazer.png"), (20, SCREEN_HEIGHT))
HEAL_ITEM_IMAGE = safe_load(os.path.join(fig_dir, "heal.png"), (30,30))
ATTACK_ITEM_IMAGE = safe_load(os.path.join(fig_dir, "attack.png"), (30,30))
EXPLOSION_IMAGE_SINGLE = safe_load(os.path.join(fig_dir, "explosion.gif"), (60,60))
BOSS_IMAGE = safe_load(os.path.join(fig_dir, "boss.png"), (120,100))

# 优先加载 super_enemy.png
if os.path.exists(os.path.join(fig_dir, "super_enemy.png")):
    MID_BOSS_IMAGE = safe_load(os.path.join(fig_dir, "super_enemy.png"), (120,120))
else:
    MID_BOSS_IMAGE = safe_load(os.path.join(fig_dir, "final_enemy.png"), (120,120))

# explosion frames
EXPLOSION_FRAMES = []
for i in range(100):
    p = os.path.join(fig_dir, f"explosion_{i:02d}.png")
    if os.path.exists(p):
        try:
            EXPLOSION_FRAMES.append(pygame.image.load(p).convert_alpha())
        except Exception:
            pass
if not EXPLOSION_FRAMES:
    EXPLOSION_FRAMES = [EXPLOSION_IMAGE_SINGLE]

# --- 字体 ---
score_font = pygame.font.SysFont(None, 36)
game_over_font = pygame.font.SysFont(None, 64, bold=True)
boss_font = pygame.font.SysFont(None, 48, bold=True)
boss_warning_font = pygame.font.SysFont(None, 72, bold=True)
info_font = pygame.font.SysFont(None, 30)

# --- 帮助函数 ---
def draw_text(surface, text, font, color, x, y, align="topright"):
    surf = font.render(text, True, color)
    r = surf.get_rect()
    if align == "topright":
        r.topright = (x, y)
    elif align == "center":
        r.center = (x, y)
    elif align == "topleft":
        r.topleft = (x, y)
    surface.blit(surf, r)

def create_stars(n):
    return [[random.randrange(0, SCREEN_WIDTH), random.randrange(0, SCREEN_HEIGHT), random.randrange(1,4), random.randrange(1,4)] for _ in range(n)]

def draw_stars(surface, stars, speed_level=0):
    modifier = 1.0 + speed_level * 0.15
    for s in stars:
        pygame.draw.circle(surface, WHITE, (s[0], s[1]), s[3])
        s[1] += s[2] * modifier
        if s[1] > SCREEN_HEIGHT:
            s[0] = random.randrange(0, SCREEN_WIDTH)
            s[1] = 0

def draw_charge_gauge(surface, cur, mx, player_bottom_y):
    gauge_width = 60
    gauge_height = 8
    x = (SCREEN_WIDTH - gauge_width)//2
    y = player_bottom_y + 10
    fill_ratio = cur / max(mx, 1)
    fill = int(fill_ratio * gauge_width)
    pygame.draw.rect(surface, GRAY, (x, y, gauge_width, gauge_height))
    pygame.draw.rect(surface, YELLOW if fill_ratio >= 1 else GREEN, (x, y, fill, gauge_height))
    pygame.draw.rect(surface, WHITE, (x, y, gauge_width, gauge_height), 1)

def draw_health_bar(surface, x, y, pct):
    pct = max(0, pct)
    BAR_LENGTH, BAR_HEIGHT = 150, 15
    fill = (pct / 100) * BAR_LENGTH
    bar_color = GREEN if pct > 60 else YELLOW if pct > 30 else RED
    pygame.draw.rect(surface, bar_color, (x, y, fill, BAR_HEIGHT))
    pygame.draw.rect(surface, WHITE, (x, y, BAR_LENGTH, BAR_HEIGHT), 2)

# --- 精灵类 ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.transform.scale(PLAYER_IMAGE, (40,40))
        self.rect = self.image.get_rect(centerx=SCREEN_WIDTH//2, bottom=SCREEN_HEIGHT-30)
        self.speed_x = 0
        self.hidden = False
        self.max_health = 100
        self.health = self.max_health
        # 充能相关（由事件驱动）
        self.is_charging = False
        self.charge_start_time = 0
        self.charge_max_time = 1000
        self.charge_value = 0
        # 射击 / 强化
        self.shoot_delay = 250
        self.last_shot = pygame.time.get_ticks()
        self.powerup_level = 0
        self.powerup_duration = 7000
        self.powerup_end_time = 0
        self.active_laser = None

    def update(self, keys, all_sprites, bullets_group, charge_bullets_group):
        if self.hidden:
            return
        self.speed_x = 0
        if keys[pygame.K_LEFT]:
            self.speed_x = -7
        if keys[pygame.K_RIGHT]:
            self.speed_x = 7
        self.rect.x += self.speed_x
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

        # powerup 过期处理
        if self.powerup_level > 0 and pygame.time.get_ticks() > self.powerup_end_time:
            self.powerup_level = 0
            if self.active_laser:
                self.active_laser.kill()
                self.active_laser = None

        # 注意：蓄力由事件驱动（KEYDOWN/KEYUP），此处不再轮询 K_v

        # 按空格自动射击（持续）
        now = pygame.time.get_ticks()
        if keys[pygame.K_SPACE]:
            self.shoot(all_sprites, bullets_group, now)

    def shoot(self, all_sprites, bullets_group, now):
        if self.hidden:
            return
        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            if self.powerup_level == 0:
                b = PlayerBullet(self.rect.centerx, self.rect.top)
                all_sprites.add(b); bullets_group.add(b)
            elif self.powerup_level == 1:
                b1 = PlayerBullet(self.rect.centerx, self.rect.top, 0)
                b2 = PlayerBullet(self.rect.centerx, self.rect.top, -3)
                b3 = PlayerBullet(self.rect.centerx, self.rect.top, 3)
                all_sprites.add(b1,b2,b3); bullets_group.add(b1,b2,b3)
            else:
                b2 = PlayerBullet(self.rect.centerx, self.rect.top, -4)
                b3 = PlayerBullet(self.rect.centerx, self.rect.top, 4)
                all_sprites.add(b2,b3); bullets_group.add(b2,b3)

    def shoot_charge_shot(self, all_sprites, charge_bullets_group):
        if self.hidden:
            return
        cs = PlayerChargeShot(self.rect.centerx, self.rect.top)
        all_sprites.add(cs); charge_bullets_group.add(cs)

    def take_damage(self, amount):
        self.health -= amount
        self.health = max(0, self.health)
        return self.health <= 0

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def power_up(self):
        self.powerup_level = min(2, self.powerup_level + 1)
        self.powerup_end_time = pygame.time.get_ticks() + self.powerup_duration

    def hide(self):
        self.hidden = True
        self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None):
        super().__init__()
        self.image = pygame.transform.scale(ENEMY_IMAGE, (40,40))
        self.rect = self.image.get_rect(x=random.randrange(0, SCREEN_WIDTH-40), y=random.randrange(-100,-40))
        base_min, base_max = 2, 5
        inc = speed_level * 0.4
        min_speed = int(base_min + inc); max_speed = int(base_max + inc)
        if max_speed <= min_speed: max_speed = min_speed + 1
        self.speed_y = random.randrange(min_speed, max_speed)
        self.all_sprites = all_sprites_ref
        self.enemy_bullets_group = enemy_bullets_group_ref
        self.enemy_shoot_delay = 2500
        self.last_shot = pygame.time.get_ticks() - random.randrange(0, self.enemy_shoot_delay)
        self.health = 1
        self.score_value = 1

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()
        # 简易射击
        if self.all_sprites and self.enemy_bullets_group and random.random() < 0.002:
            b = EnemyBullet(self.rect.centerx, self.rect.bottom, 6)
            self.all_sprites.add(b); self.enemy_bullets_group.add(b)

    def hit(self):
        self.health -= 1
        return self.health <= 0

class BigEnemy(Enemy):
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None, player_ref=None):
        super().__init__(speed_level, all_sprites_ref, enemy_bullets_group_ref)
        self.player = player_ref
        self.image = pygame.transform.scale(BOSS_IMAGE, (120,100))
        self.rect = self.image.get_rect(x=(SCREEN_WIDTH-120)//2, y=-100)
        self.speed_y = 1; self.speed_x = 3; self.target_y = 100
        self.health = 30; self.score_value = 50
        self.enemy_shoot_delay = 1000
        self.last_shot = pygame.time.get_ticks()

    def update(self):
        if self.rect.y < self.target_y:
            self.rect.y += self.speed_y
        else:
            self.rect.x += self.speed_x
            if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
                self.speed_x *= -1
                self.rect.x += self.speed_x
        self.shoot()

    def shoot(self):
        if self.all_sprites is None or self.enemy_bullets_group is None:
            return
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            b_left = EnemyBullet(self.rect.centerx - 40, self.rect.bottom, 10, self.player)
            b_right = EnemyBullet(self.rect.centerx + 40, self.rect.bottom, 10, self.player)
            self.all_sprites.add(b_left, b_right); self.enemy_bullets_group.add(b_left, b_right)

class Iwa(pygame.sprite.Sprite):
    def __init__(self, speed_level=0, all_sprites_ref=None):
        super().__init__()
        self.image = pygame.transform.scale(IWA_IMAGE, (100,100))
        self.rect = self.image.get_rect(x=random.randrange(0, SCREEN_WIDTH-100), y=random.randrange(-100,-40))
        base_min, base_max = 5, 9
        inc = speed_level * 0.4
        min_s = int(base_min + inc); max_s = int(base_max + inc)
        if max_s <= min_s: max_s = min_s + 1
        self.speed_y = random.randrange(min_s, max_s)
        self.all_sprites = all_sprites_ref

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_x=0):
        super().__init__()
        raw = pygame.transform.scale(PLAYER_BULLET_IMAGE, (25,15))
        self.image = pygame.transform.rotate(raw, 90)
        self.rect = self.image.get_rect(bottom=y, centerx=x)
        self.speed_y = -10; self.speed_x = speed_x

    def update(self):
        self.rect.y += self.speed_y; self.rect.x += self.speed_x
        if self.rect.bottom < 0: self.kill()

class PlayerChargeShot(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        raw = pygame.transform.scale(PLAYER_BULLET_IMAGE, (120,60))
        self.image = pygame.transform.rotate(raw, 90)
        cs = pygame.Surface(self.image.get_size(), pygame.SRCALPHA); cs.fill(RED)
        self.image.blit(cs, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        self.rect = self.image.get_rect(bottom=y, centerx=x)
        self.speed_y = -12

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0: self.kill()

class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, speed_y_val=7, player_ref=None):
        super().__init__()
        raw = pygame.transform.scale(ENEMY_BULLET_IMAGE, (30,15))
        self.image = pygame.transform.rotate(raw, -90)
        col = pygame.Surface(self.image.get_size(), pygame.SRCALPHA); col.fill(YELLOW)
        self.image.blit(col, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        self.rect = self.image.get_rect(top=y, centerx=x)
        self.speed_y = speed_y_val; self.speed_x = 0; self.player = player_ref
        if self.player and not getattr(self.player, "hidden", False) and self.player.rect.centery > self.rect.centery:
            dx = self.player.rect.centerx - self.rect.centerx
            dy = self.player.rect.centery - self.rect.centery
            try:
                self.speed_x = (dx / dy) * self.speed_y
            except ZeroDivisionError:
                self.speed_x = 0
            maxsx = abs(self.speed_y) * 1.5
            self.speed_x = max(-maxsx, min(self.speed_x, maxsx))

    def update(self):
        self.rect.y += self.speed_y; self.rect.x += self.speed_x
        if not screen.get_rect().colliderect(self.rect):
            self.kill()

class SuperLaser(pygame.sprite.Sprite):
    def __init__(self, player_obj):
        super().__init__()
        self.player = player_obj
        self.image = pygame.transform.scale(LAZER_IMAGE, (20, SCREEN_HEIGHT))
        self.rect = self.image.get_rect()
        self.update()

    def update(self):
        self.rect.centerx = self.player.rect.centerx
        self.rect.bottom = self.player.rect.top

class Item(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.rect = self.image.get_rect(center=center)
        self.speed_y = 3

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT: self.kill()

class HealItem(Item):
    def __init__(self, center):
        self.image = pygame.transform.scale(HEAL_ITEM_IMAGE, (30,30)); super().__init__(center)
    def apply_effect(self, player): player.heal(25)

class AttackUpItem(Item):
    def __init__(self, center):
        self.image = pygame.transform.scale(ATTACK_ITEM_IMAGE, (30,30)); super().__init__(center)
    def apply_effect(self, player): player.power_up()

class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, size="normal", is_anime=True):
        super().__init__()
        self.is_anime = is_anime
        if self.is_anime and EXPLOSION_FRAMES:
            scale = (90,90) if size=="large" else (60,60)
            self.frames = [pygame.transform.scale(f, scale) for f in EXPLOSION_FRAMES]
            self.frame_rate = 70; self.current_frame = 0
            self.image = self.frames[self.current_frame]; self.rect = self.image.get_rect(center=center)
            self.last_update = pygame.time.get_ticks()
        else:
            self.is_anime = False
            scale = (90,90) if size=="large" else (60,60)
            self.image = pygame.transform.scale(EXPLOSION_IMAGE_SINGLE, scale)
            self.rect = self.image.get_rect(center=center); self.duration = 400; self.creation_time = pygame.time.get_ticks()

    def update(self):
        if self.is_anime:
            now = pygame.time.get_ticks()
            if now - self.last_update > self.frame_rate:
                self.last_update = now; self.current_frame += 1
                if self.current_frame >= len(self.frames): self.kill()
                else: self.image = self.frames[self.current_frame]
        else:
            if pygame.time.get_ticks() - self.creation_time > self.duration: self.kill()

# === MidBoss（中ボス） ===
class MidBoss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = pygame.transform.scale(MID_BOSS_IMAGE, (120,120))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.y = -150

        self.speed_x = 3; self.speed_y = 2; self.direction = 1
        self.shoot_delay = 900; self.last_shot = pygame.time.get_ticks()
        self.shoot_pattern = 0; self.pattern_timer = 0; self.spiral_angle = 0.0
        self.has_appeared = False
        self.health = 30; self.max_health = 30; self.score_value = 50
        self.is_special_moving = False; self.special_move_timer = 0

    def update(self):
        if not self.has_appeared:
            self.rect.y += self.speed_y
            if self.rect.y >= 50:
                self.has_appeared = True
            return

        if self.is_special_moving:
            self.special_move_timer += 1
            if self.special_move_timer < 60:
                self.rect.x += self.speed_x * 3 * self.direction
                self.rect.y += math.sin(pygame.time.get_ticks() * 0.01) * 3
            else:
                self.is_special_moving = False; self.special_move_timer = 0
        else:
            self.rect.x += self.speed_x * self.direction
            if self.rect.right >= SCREEN_WIDTH - 10: self.direction = -1
            elif self.rect.left <= 10: self.direction = 1
            self.rect.y += math.sin(pygame.time.get_ticks() * 0.005) * 1.5

        self.shoot()
        self.pattern_timer += 1
        if self.pattern_timer >= 180:
            self.shoot_pattern = (self.shoot_pattern + 1) % 2
            self.pattern_timer = 0

        if not self.is_special_moving and random.random() < 0.003:
            self.is_special_moving = True; self.special_move_timer = 0

    def shoot(self):
        global all_sprites, enemy_bullets_group
        now = pygame.time.get_ticks()
        if now - self.last_shot < self.shoot_delay: return
        self.last_shot = now
        if self.shoot_pattern == 0:
            cnt = 10; step = 360.0 / cnt
            base = self.spiral_angle
            for i in range(cnt):
                ang = base + i * step
                b = MidBossBullet(self.rect.centerx, self.rect.centery, ang, mode="spiral")
                all_sprites.add(b); enemy_bullets_group.add(b)
            self.spiral_angle = (self.spiral_angle + 10) % 360
        else:
            spread_count = 10; spread_width = 100; center_angle = 90
            start = center_angle - spread_width/2
            step = spread_width / (spread_count - 1) if spread_count > 1 else 0
            for i in range(spread_count):
                ang = start + i * step
                b = MidBossBullet(self.rect.centerx, self.rect.centery+20, ang, mode="scatter")
                all_sprites.add(b); enemy_bullets_group.add(b)

    def hit(self):
        self.health -= 1
        return self.health <= 0

    def draw_health_bar(self, surface):
        bw, bh = 100, 10
        bx = self.rect.centerx - bw//2; by = self.rect.top - 20
        pygame.draw.rect(surface, RED, (bx, by, bw, bh))
        hw = int((self.health / self.max_health) * bw)
        pygame.draw.rect(surface, YELLOW, (bx, by, hw, bh))

class MidBossBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle_deg, mode="spiral"):
        super().__init__()
        r = 12
        surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255,50,50), (r,r), r)
        self.image = surf
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos_x = float(self.rect.centerx); self.pos_y = float(self.rect.centery)
        self.mode = mode
        rad = math.radians(angle_deg)
        dx = math.cos(rad); dy = math.sin(rad)
        if mode == "spiral": speed = 5.5
        elif mode == "scatter": speed = 6.0
        else: speed = 5.0
        self.vx = dx * speed; self.vy = dy * speed

    def update(self):
        self.pos_x += self.vx; self.pos_y += self.vy
        self.rect.centerx = int(self.pos_x); self.rect.centery = int(self.pos_y)
        if (self.rect.top > SCREEN_HEIGHT + 60 or self.rect.bottom < -60 or
            self.rect.left > SCREEN_WIDTH + 60 or self.rect.right < -60):
            self.kill()

# === 初始化组/变量 ===
stars = create_stars(100)
all_sprites = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()
player_bullets_group = pygame.sprite.Group()
player_charge_bullets_group = pygame.sprite.Group()
enemy_bullets_group = pygame.sprite.Group()
iwa_group = pygame.sprite.Group()
items_group = pygame.sprite.Group()
laser_group = pygame.sprite.Group()
mid_boss_group = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

ADD_ENEMY = pygame.USEREVENT + 1
initial_spawn_rate = 1000
current_spawn_rate = initial_spawn_rate
pygame.time.set_timer(ADD_ENEMY, initial_spawn_rate)

score = 0; game_speed_level = 0; game_over = False; running = True
level_up_message_time = 0
boss_spawned = False; boss_spawn_time = 30000; boss_warning_time = 0
game_start_time = pygame.time.get_ticks()

mid_boss_spawned = False; mid_boss_defeated = False; mid_boss_warning_timer = 0

# --- 主循环（注意：事件驱动 V）---
while running:
    clock.tick(FPS)
    now = pygame.time.get_ticks()

    # 事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 按任意键在 game over 时退出
        elif game_over and event.type == pygame.KEYDOWN:
            running = False

        # 定时刷怪
        elif event.type == ADD_ENEMY and not game_over:
            if not mid_boss_spawned or mid_boss_defeated:
                e = Enemy(game_speed_level, all_sprites, enemy_bullets_group)
                all_sprites.add(e); enemies_group.add(e)
                iw = Iwa(game_speed_level, all_sprites)
                all_sprites.add(iw); iwa_group.add(iw)

        # === 蓄力事件：KEYDOWN 开始、KEYUP 释放 ===
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_v and not game_over and not player.hidden:
                # 开始充能
                player.is_charging = True
                player.charge_start_time = now
                player.charge_value = 0
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_v and not game_over and not player.hidden and player.is_charging:
                # 释放：结算并发射（满充 -> 蓄力弹；否则 -> 普通弹）
                player.charge_value = min(now - player.charge_start_time, player.charge_max_time)
                if player.charge_value >= player.charge_max_time:
                    player.shoot_charge_shot(all_sprites, player_charge_bullets_group)
                else:
                    player.shoot(all_sprites, player_bullets_group, now)
                player.is_charging = False
                player.charge_value = 0
    # keys 轮询（用于移动与空格）
    keys = pygame.key.get_pressed()

    # --- 更新逻辑 ---
    if not game_over:
        # 保证 player.update 一直被调用（其中不再处理 K_v）
        player.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)

        # 若玩家处于正在充能状态，实时更新 charge_value 以显示进度
        if player.is_charging:
            player.charge_value = min(now - player.charge_start_time, player.charge_max_time)

        # 激光
        if player.powerup_level >= 2:
            if keys[pygame.K_SPACE]:
                if not player.active_laser:
                    player.active_laser = SuperLaser(player)
                    all_sprites.add(player.active_laser); laser_group.add(player.active_laser)
            else:
                if player.active_laser:
                    player.active_laser.kill(); player.active_laser = None
        else:
            if player.active_laser:
                player.active_laser.kill(); player.active_laser = None

        # BigEnemy 时间控制（保留）
        elapsed_time = now - game_start_time
        if elapsed_time > (boss_spawn_time - 2000) and not boss_spawned and boss_warning_time == 0:
            boss_warning_time = now
        if elapsed_time > boss_spawn_time and not boss_spawned:
            boss = BigEnemy(game_speed_level, all_sprites, enemy_bullets_group, player)
            all_sprites.add(boss); enemies_group.add(boss)
            boss_spawned = True; boss_warning_time = 0
            pygame.time.set_timer(ADD_ENEMY, 0)

        # 中ボス出现
        if score >= MID_BOSS_SPAWN_SCORE and not mid_boss_spawned and not mid_boss_defeated:
            mid_boss_spawned = True; mid_boss_warning_timer = 180
            mid_boss = MidBoss()
            all_sprites.add(mid_boss); mid_boss_group.add(mid_boss)
            pygame.time.set_timer(ADD_ENEMY, 0)
            print("中ボス出現！")

        if mid_boss_warning_timer > 0:
            mid_boss_warning_timer -= 1

        # 更新除 player 之外的所有精灵
        sprites_to_update = [s for s in all_sprites if s is not player]
        for s in sprites_to_update:
            try:
                s.update()
            except TypeError:
                try:
                    s.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)
                except Exception:
                    pass
    else:
        # game over 时仍更新爆炸动画
        for s in list(all_sprites):
            if isinstance(s, Explosion):
                s.update()

    # --- 碰撞判定 ---
    if not game_over:
        enemies_destroyed = 0

        # 普通子弹命中普通敌人
        hits_normal = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, False)
        hits_charge = pygame.sprite.groupcollide(player_charge_bullets_group, enemies_group, False, False)
        hits_laser = pygame.sprite.groupcollide(laser_group, enemies_group, False, True)

        for bullet, hit_list in {**hits_normal, **hits_charge}.items():
            for enemy_hit in hit_list:
                if enemy_hit.hit():
                    all_sprites.add(Explosion(enemy_hit.rect.center, "normal"))
                    score += enemy_hit.score_value
                    enemies_destroyed += 1
                    enemy_hit.kill()
                    if random.random() > 0.8:
                        it = random.choice([HealItem, AttackUpItem])(enemy_hit.rect.center)
                        all_sprites.add(it); items_group.add(it)

        for laser, hit_list in hits_laser.items():
            for e in hit_list:
                all_sprites.add(Explosion(e.rect.center, "normal"))
                score += getattr(e, "score_value", 1)

        # --- 新增：玩家普通弹/蓄力弹命中中ボス ---
        if mid_boss_spawned and not mid_boss_defeated:
            mb_hits = pygame.sprite.groupcollide(player_bullets_group, mid_boss_group, True, False)
            for bullet, mbs in mb_hits.items():
                for mb in mbs:
                    if mb.hit():
                        all_sprites.add(Explosion(mb.rect.center, "large"))
                        score += mb.score_value
                        mid_boss_defeated = True
                        mb.kill()
                        print("中ボス撃破！")
                        pygame.time.set_timer(ADD_ENEMY, current_spawn_rate)

            mb_hits_charge = pygame.sprite.groupcollide(player_charge_bullets_group, mid_boss_group, False, False)
            for bullet, mbs in mb_hits_charge.items():
                for mb in mbs:
                    if mb.hit():
                        all_sprites.add(Explosion(mb.rect.center, "large"))
                        score += mb.score_value
                        mid_boss_defeated = True
                        mb.kill()
                        print("中ボス撃破！（蓄力）")
                        pygame.time.set_timer(ADD_ENEMY, current_spawn_rate)

        # 刷新速率调整
        if enemies_destroyed > 0 and not boss_spawned:
            new_level = score // 10
            if new_level > game_speed_level:
                game_speed_level = new_level
                level_up_message_time = pygame.time.get_ticks()
                rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level)))
                pygame.time.set_timer(ADD_ENEMY, 0)
                pygame.time.set_timer(ADD_ENEMY, rate)

        # 玩家与敌机碰撞
        player_enemy_hits = pygame.sprite.spritecollide(player, enemies_group, True)
        if player_enemy_hits:
            if player.take_damage(PLAYER_COLLIDE_DAMAGE):
                game_over = True; all_sprites.add(Explosion(player.rect.center, "large")); player.hide()
            else:
                all_sprites.add(Explosion(player.rect.center, "normal"))

        # 玩家与敌方子弹碰撞（包含 MidBoss 与 BigEnemy 的子弹） -> 统一伤害 ENEMY_BULLET_DAMAGE
        player_beam_hits = pygame.sprite.spritecollide(player, enemy_bullets_group, True)
        if player_beam_hits:
            dmg = ENEMY_BULLET_DAMAGE * len(player_beam_hits)
            if player.take_damage(dmg):
                game_over = True; all_sprites.add(Explosion(player.rect.center, "large")); player.hide()
            else:
                all_sprites.add(Explosion(player.rect.center, "normal"))

        # 玩家与岩石碰撞
        player_iwa_hits = pygame.sprite.spritecollide(player, iwa_group, True)
        if player_iwa_hits:
            if player.take_damage(IWA_COLLIDE_DAMAGE):
                game_over = True; all_sprites.add(Explosion(player.rect.center, "large")); player.hide()
            else:
                all_sprites.add(Explosion(player.rect.center, "normal"))

        # 道具拾取
        for it in pygame.sprite.spritecollide(player, items_group, True):
            it.apply_effect(player)

        # 玩家与中ボス实体碰撞
        if mid_boss_spawned and not mid_boss_defeated:
            player_mid_hits = pygame.sprite.spritecollide(player, mid_boss_group, False)
            if player_mid_hits:
                all_sprites.add(Explosion(player.rect.center, "large")); player.hide(); game_over = True
                pygame.time.set_timer(ADD_ENEMY, 0)

    # --- 绘制 ---
    screen.fill(BLACK)
    draw_stars(screen, stars, game_speed_level)
    all_sprites.draw(screen)

    if mid_boss_spawned and not mid_boss_defeated:
        for mb in mid_boss_group:
            mb.draw_health_bar(screen)

    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH-10, 10, align="topright")
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")
    draw_health_bar(screen, 10, 40, player.health)
    # 充能槽：当正在充能或有残余值时显示
    if not player.hidden and (player.is_charging or player.charge_value > 0):
        draw_charge_gauge(screen, player.charge_value, player.charge_max_time, player.rect.bottom)

    if 'level_up_message_time' in globals() and pygame.time.get_ticks() - level_up_message_time < 1000 and not game_over:
        draw_text(screen, "LEVEL UP!", game_over_font, YELLOW, SCREEN_WIDTH//2, SCREEN_HEIGHT//2, align="center")

    if boss_warning_time > 0 and not game_over and (pygame.time.get_ticks() - boss_warning_time) % 1000 < 500:
        draw_text(screen, "!! WARNING !!", boss_warning_font, RED, SCREEN_WIDTH//2, SCREEN_HEIGHT//2, align="center")

    if mid_boss_warning_timer > 0 and mid_boss_warning_timer % 30 < 15:
        draw_text(screen, "A mid-boss appears!", boss_font, RED, SCREEN_WIDTH//2, SCREEN_HEIGHT//3, align="center")

    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH//2, SCREEN_HEIGHT//2, align="center")
        draw_text(screen, "Press any key to exit", info_font, WHITE, SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50, align="center")

    pygame.display.flip()

# 退出
pygame.quit()
sys.exit()
