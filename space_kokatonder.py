import math
import os
import pygame as pg
import random
import sys

# スクリプトのパスを基準にディレクトリを設定
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")

# 定数
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
FPS = 60

# 色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)
CYAN = (0, 255, 255)

# 意味深な叫び声
call = "逃げるなァ!!!!!逃げるな卑怯者!!!!!"

# --- ゲームの初期化 ---
pg.init()
pg.font.init()
screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pg.display.set_caption("Xevious Style Shooter")
clock = pg.time.Clock()


# 画像ファイルの読み込み
if not os.path.exists(fig_dir):
    os.makedirs(fig_dir)
    print(f"Warning: '{fig_dir}' directory not found. Created an empty one.")

# 画像読み込み用の関数
def safe_load(path, fallback_size=(40, 40), fillcolor = (120, 120, 120)):
    try:
        return pg.image.load(os.path.join(fig_dir, path)).convert_alpha()
    except Exception:
        surf = pg.Surface(fallback_size, pg.SRCAPHA)
        surf.fill(fillcolor)
        return surf
    
PLAYER_IMAGE = safe_load("koukaton.png", (40, 40))
ENEMY_IMAGE = safe_load("enemy.png", (40, 40))
PLAYER_BULLET_IMAGE = safe_load("beam.png", (25, 15))
ENEMY_BULLET_IMAGE = safe_load("beam.png", (30, 15))
IWA_IMAGE = safe_load("iwa_01.png", (100, 100))
LAZER_IMAGE = safe_load("lazer.png", (20, 20))
HEAL_ITEM_IMAGE = safe_load("heal.png", (30, 30))
ATTACK_ITEM_IMAGE = safe_load("attack.png", (30, 30))
EXPLOSION_IMAGE_SINGLE = safe_load("explosion.gif", (60, 60))
BOSS_IMAGE = safe_load("boss.png", (120, 100))
MID_BOSS_IMAGE = safe_load("super_enemy.png", (120, 120))

EXPLOSION_FRAMES = []
for i in range(100):
    p = os.path.join(fig_dir, f"explosion_{i:02d}.png")
    if os.path.exists(p):
        try:
            EXPLOSION_FRAMES += [pg.image.load(p).convert_alpha()]
        except Exception:
            pass

if not EXPLOSION_FRAMES:
    EXPLOSION_FRAMES = [EXPLOSION_IMAGE_SINGLE]

# フォント
score_font = pg.font.SysFont(None, 36)
game_over_font = pg.font.SysFont(None, 64, bold=True)
boss_warning_font = pg.font.SysFont(None, 72, bold=True)
info_font = pg.font.SysFont(None, 30)

# --- クラス定義 ---
class Player(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pg.transform.scale(PLAYER_IMAGE, (40, 40))
        self.rect = self.image.get_rect(centerx=SCREEN_WIDTH // 2, bottom=SCREEN_HEIGHT - 30)
        self.speed_x = 0
        self.hidden = False
        self.max_health = 100
        self.health = self.max_health
        self.is_charging = False
        self.charge_start_time = 0
        self.charge_max_time = 1000
        self.charge_value = 0
        self.shoot_delay = 250
        self.last_shot = pg.time.get_ticks()
        self.powerup_level = 0
        self.powerup_duration = 7000
        self.powerup_end_time = 0
        self.active_laser = None

    def update(self, keys, all_sprites, bullets_group, charge_bullets_group):
        if self.hidden:
            return

        self.speed_x = 0
        if keys[pg.K_LEFT]:
            self.speed_x = -7
        if keys[pg.K_RIGHT]:
            self.speed_x = 7

        self.rect.x += self.speed_x

        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

        if (
            self.powerup_level > 0
            and pg.time.get_ticks() > self.powerup_end_time
        ):
            self.powerup_level = 0
            if self.active_laser:
                self.active_laser.kill()
                self.active_laser = None
            print("Power-up ended.")

        now = pg.time.get_ticks()

        if keys[pg.K_v]:
            if not self.is_charging:
                self.is_charging = True
                self.charge_start_time = now
                self.charge_value = 0
            else:
                self.charge_value = min(now - self.charge_start_time, self.charge_max_time)
        else:
            if self.is_charging:
                if self.charge_value >= self.charge_max_time:
                    self.shoot_charge_shot(all_sprites, charge_bullets_group)
                else:
                    self.shoot(all_sprites, bullets_group, now)
                self.is_charging = False
                self.charge_value = 0

        if keys[pg.K_SPACE]:
            self.shoot(all_sprites, bullets_group, now)

    def shoot(self, all_sprites, bullets_group, now):
        if self.hidden:
            return
        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            if self.powerup_level == 0:
                bullet = PlayerBullet(self.rect.centerx, self.rect.top)
                all_sprites.add(bullet)
                bullets_group.add(bullet)
            elif self.powerup_level == 1:
                b1 = PlayerBullet(self.rect.centerx, self.rect.top, speed_x=0)
                b2 = PlayerBullet(self.rect.centerx, self.rect.top, speed_x=-3)
                b3 = PlayerBullet(self.rect.centerx, self.rect.top, speed_x=3)
                all_sprites.add(b1, b2, b3)
                bullets_group.add(b1, b2, b3)
            elif self.powerup_level >= 2:
                b2 = PlayerBullet(self.rect.centerx, self.rect.top, speed_x=-4)
                b3 = PlayerBullet(self.rect.centerx, self.rect.top, speed_x=4)
                all_sprites.add(b2, b3)
                bullets_group.add(b2, b3)

    def shoot_charge_shot(self, all_sprites, charge_bullets_group):
        if self.hidden:
            return
        charge_shot = PlayerChargeShot(self.rect.centerx, self.rect.top)
        all_sprites.add(charge_shot)
        charge_bullets_group.add(charge_shot)

    def take_damage(self, amount):
        self.health -= amount
        self.health = max(0, self.health)
        return self.health <= 0

    def heal(self, amount):
        self.health = min(self.health + amount, self.max_health)

    def power_up(self):
        self.powerup_level = min(2, self.powerup_level + 1)
        self.powerup_end_time = pg.time.get_ticks() + self.powerup_duration
        print(f"Power-up! Level {self.powerup_level}")

    def hide(self):
        self.hidden = True
        self.kill()


class Enemy(pg.sprite.Sprite):
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None):
        super().__init__()
        self.image = pg.transform.scale(ENEMY_IMAGE, (40, 40))
        self.rect = self.image.get_rect(
            x=random.randrange(0, SCREEN_WIDTH - 40), y=random.randrange(-100, -40)
        )
        base_speed_min = 2
        base_speed_max = 5
        speed_increase = speed_level * 0.4
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        self.speed_y = random.randrange(min_speed, max_speed)
        self.all_sprites = all_sprites_ref
        self.enemy_bullets_group = enemy_bullets_group_ref
        self.enemy_shoot_delay = 2500
        self.last_shot = pg.time.get_ticks() - random.randrange(0, self.enemy_shoot_delay)
        self.health = 1
        self.score_value = 1

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()
        self.shoot()

    def shoot(self):
        now = pg.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            b = EnemyBullet(self.rect.centerx, self.rect.bottom)
            if self.all_sprites:
                self.all_sprites.add(b)
            if self.enemy_bullets_group:
                self.enemy_bullets_group.add(b)

    def hit(self):
        self.health -= 1
        return self.health <= 0


class BigEnemy(Enemy):
    def __init__(
        self,
        speed_level=0,
        all_sprites_ref=None,
        enemy_bullets_group_ref=None,
        player_ref=None,
    ):
        super().__init__(speed_level, all_sprites_ref, enemy_bullets_group_ref)
        self.player = player_ref
        self.width = 120
        self.height = 100
        self.image = pg.transform.scale(BOSS_IMAGE, (self.width, self.height))
        self.rect = self.image.get_rect(x=(SCREEN_WIDTH - 120) // 2, y=-100)
        self.scale = 1.0
        self.speed_y = 1
        self.speed_x = 3
        self.target_y = 100
        self.health = 100
        self.score_value = 50
        self.enemy_shoot_delay = 1000
        self.last_shot = pg.time.get_ticks()
        self.last_threshold = 100

    def update(self):
        if self.rect.y < self.target_y:
            self.rect.y += self.speed_y
        else:
            self.rect.x += self.speed_x

            if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
                self.speed_x *= -1
                self.rect.x += self.speed_x
        self.shoot()

        current_health = self.health

        if current_health <= 80 and self.last_threshold == 100:
            self.scale *= 0.5
            self.last_threshold = 80
            self.image = pg.transform.scale(BOSS_IMAGE, (self.width * self.scale, self.height * self.scale))
            self.rect = self.image.get_rect(center=self.rect.center)
            print(call)

        elif current_health <= 60 and self.last_threshold == 80:
            self.scale *= 0.5
            self.last_threshold = 60
            self.image = pg.transform.scale(BOSS_IMAGE, (self.width * self.scale, self.height * self.scale))
            self.rect = self.image.get_rect(center=self.rect.center)
            print(call)

        elif current_health <= 40 and self.last_threshold == 60:
            self.scale *= 0.5
            self.last_threshold = 40
            self.image = pg.transform.scale(BOSS_IMAGE, (self.width * self.scale, self.height * self.scale))
            self.rect = self.image.get_rect(center=self.rect.center)
            print(call)

        if current_health <= 20 and self.last_threshold == 40:
            self.scale *= 0.5
            self.last_threshold = 20
            self.image = pg.transform.scale(BOSS_IMAGE, (self.width * self.scale, self.height * self.scale))
            self.rect = self.image.get_rect(center=self.rect.center)
            print(call)

    def shoot(self):
        if self.all_sprites is None or self.enemy_bullets_group is None:
            return
        now = pg.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            b_left = EnemyBullet(self.rect.centerx - 40, self.rect.bottom, 10, self.player)
            b_right = EnemyBullet(self.rect.centerx + 40, self.rect.bottom, 10, self.player)
            self.all_sprites.add(b_left, b_right)
            self.enemy_bullets_group.add(b_left, b_right)


class Iwa(pg.sprite.Sprite):
    def __init__(self, speed_level=0, all_sprites_ref=None):
        super().__init__()
        self.image = pg.transform.scale(IWA_IMAGE, (100, 100))
        self.rect = self.image.get_rect(
            x=random.randrange(0, SCREEN_WIDTH - 100), y=random.randrange(-100, -40)
        )
        base_speed_min = 5
        base_speed_max = 9
        speed_increase = speed_level * 0.4
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        self.speed_y = random.randrange(min_speed, max_speed) # +1を除外
        self.all_sprites = all_sprites_ref

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()


class PlayerBullet(pg.sprite.Sprite):
    def __init__(self, x, y, speed_x=0):
        super().__init__()
        raw_image = pg.transform.scale(PLAYER_BULLET_IMAGE, (25, 15))
        self.image = pg.transform.rotate(raw_image, 90)
        self.rect = self.image.get_rect(bottom=y, centerx=x)
        self.speed_y = -10
        self.speed_x = speed_x

    def update(self):
        self.rect.y += self.speed_y
        self.rect.x += self.speed_x
        if self.rect.bottom < 0:
            self.kill()


class PlayerChargeShot(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        raw_image = pg.transform.scale(PLAYER_BULLET_IMAGE, (120, 60))
        self.image = pg.transform.rotate(raw_image, 90)
        color_surface = pg.Surface(self.image.get_size(), pg.SRCALPHA)
        color_surface.fill(RED)
        self.image.blit(color_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        self.rect = self.image.get_rect(bottom=y, centerx=x)
        self.speed_y = -12

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()


class EnemyBullet(pg.sprite.Sprite):
    def __init__(self, x, y, speed_y_val=7, player_ref=None):
        super().__init__()
        raw_image = pg.transform.scale(ENEMY_BULLET_IMAGE, (30, 15))
        self.image = pg.transform.rotate(raw_image, -90)
        color_surface = pg.Surface(self.image.get_size(), pg.SRCALPHA)
        color_surface.fill(YELLOW)
        self.image.blit(color_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        self.rect = self.image.get_rect(top=y, centerx=x)
        self.speed_y = speed_y_val
        self.speed_x = 0
        self.player = player_ref

        if self.player and not self.player.hidden and self.player.rect.centery > self.rect.centery:
            dx = self.player.rect.centerx - self.rect.centerx
            dy = self.player.rect.centery - self.rect.centery
            try:
                self.speed_x = (dx / dy) * self.speed_y
            except ZeroDivisionError:
                self.speed_x = 0
            max_speed_x = self.speed_y * 1.5
            self.speed_x = max(-max_speed_x, min(self.speed_x, max_speed_x))

    def update(self):
        self.rect.y += self.speed_y
        self.rect.x += self.speed_x
        if not screen.get_rect().colliderect(self.rect):
            self.kill()


class SuperLaser(pg.sprite.Sprite):
    def __init__(self, player_obj):
        super().__init__()
        self.player = player_obj
        self.image = pg.transform.scale(LAZER_IMAGE, (20, SCREEN_HEIGHT))
        self.rect = self.image.get_rect()
        self.update()

    def update(self):
        self.rect.centerx = self.player.rect.centerx
        self.rect.bottom = self.player.rect.top


class Item(pg.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.rect = self.image.get_rect(center=center)
        self.speed_y = 3

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()


class HealItem(Item):
    def __init__(self, center):
        self.image = pg.transform.scale(HEAL_ITEM_IMAGE, (30, 30))
        super().__init__(center)

    def apply_effect(self, player):
        player.heal(25)


class AttackUpItem(Item):
    def __init__(self, center):
        self.image = pg.transform.scale(ATTACK_ITEM_IMAGE, (30, 30))
        super().__init__(center)

    def apply_effect(self, player):
        player.power_up()


class Explosion(pg.sprite.Sprite):
    def __init__(self, center, size="normal", is_anime=True):
        super().__init__()
        self.is_anime = is_anime
        if self.is_anime and EXPLOSION_FRAMES:
            self.frames = list(EXPLOSION_FRAMES)
            scale = (90, 90) if size == "large" else (60, 60)
            self.frames = [pg.transform.scale(f, scale) for f in self.frames]
            self.frame_rate = 70
            self.current_frame = 0
            self.image = self.frames[self.current_frame]
            self.rect = self.image.get_rect(center=center)
            self.last_update = pg.time.get_ticks()
        else:
            self.is_anime = False
            scale = (90, 90) if size == "large" else (60, 60)
            self.image = pg.transform.scale(EXPLOSION_IMAGE_SINGLE, scale)
            self.rect = self.image.get_rect(center=center)
            self.duration = 400
            self.creation_time = pg.time.get_ticks()

    def update(self):
        if self.is_anime:
            now = pg.time.get_ticks()
            if now - self.last_update > self.frame_rate:
                self.last_update = now
                self.current_frame += 1
                if self.current_frame >= len(self.frames):
                    self.kill()
                else:
                    self.image = self.frames[self.current_frame]
        else:
            if pg.time.get_ticks() - self.creation_time > self.duration:
                self.kill()


class MidBoss(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pg.transform.scale(MID_BOSS_IMAGE, (120, 120))
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.y = -150
        self.speed_x = 3
        self.speed_y = 2
        self.direction = 1
        self.shoot_delay = 900
        self.last_shot = pg.time.get_ticks()
        self.shoot_pattern = 0
        self.pattern_timer = 0
        self.spiral_angle = 0.0
        self.has_appeared = False
        self.health = 30
        self.max_health = 30
        self.score_value = 0
        self.is_special_moving = False
        self.special_moving_timer = 0

    def update(self):
        if not self.has_appeared:
            self.rect.y += self.speed_y
            if self.rect.y >= 50:
                self.has_appeared = True
            return
        
        if self.is_special_moving:
            self.special_moving_timer += 1
            if self.special_moving_timer < 60:
                self.rect.x += self.speed_x * 3 * self.direction
                self.rect.y += math.sin(pg.time.get_ticks() * 0.01) * 3
            else:
                self.is_special_moving = False
                self.special_moving_timer = 0
        else:
            self.rect.x += self.speed_x * self.direction
            if self.rect.right >= SCREEN_WIDTH - 10:
                self.direction = -1
            elif self.rect.left <= 10:
                self.direction = 1
            self.rect.y += math.sin(pg.time.get_ticks() * 0.005) * 1.5

        self.shoot()
        self.pattern_timer += 1
        if self.pattern_timer >= 180:
            self.shoot_pattern = (self.shoot_pattern + 1) % 2
            self.pattern_timer = 0

        if not self.is_special_moving and random.random() < 0.003:
            self.is_special_moving = True
            self.special_moving_timer = 0

    def shoot(self):
        global all_sprites
        global enemy_bullets_group
        now = pg.time.get_ticks()
        if now - self.last_shot < self.shoot_delay:
            return
        self.last_shot = now
        if self.shoot_pattern == 0:
            cnt = 10
            step = 360.0 / cnt
            base = self.spiral_angle
            for i in range(cnt):
                ang = base + i * step
                b = MidBossBullet(self.rect.centerx, self.rect.centery, ang, mode="spiral")
                all_sprites.add(b)
                enemy_bullets_group.add(b)
            self.spiral_angle = (self.spiral_angle + 10) % 360
        else:
            spread_count = 10
            spread_width = 100
            center_angle = 90
            start = center_angle - spread_width / 2
            step = spread_width / (spread_count - 1) if spread_count > 1 else 0
            for i in range(spread_count):
                ang = start + i * step
                b = MidBossBullet(self.rect.centerx, self.rect.centery + 20, ang, mode="scatter")
                all_sprites.add(b)
                enemy_bullets_group.add(b)

    def hit(self):
        self.health -= 1
        return self.health <= 0
    
    def draw_health_bar(self, surface):
        bw = 100
        bh = 10
        bx = self.rect.centerx - bw // 2
        by = self.rect.top - 20
        pg.draw.rect(surface, RED, (bx, by, bw, bh))
        hw = int((self.health / self.max_health) * bw)
        pg.draw.rect(surface, YELLOW, (bx, by, hw, bh))


class MidBossBullet(pg.sprite.Sprite):
    def __init__(self, x, y, angle_deg, mode="spriral"):
        super().__init__()
        r = 12
        surf = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
        pg.draw.circle(surf, (255, 50, 50), (r, r), r)
        self.image = surf
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos_x = float(self.rect.centerx)
        self.pos_y = float(self.rect.centery)
        self.mode = mode
        rad = math.radians(angle_deg)
        dx = math.cos(rad)
        dy = math.sin(rad)
        if mode == "spiral":
            speed = 5.5
        elif mode == "scatter":
            speed = 6.0
        else:
            speed = 5.0
        self.vx = dx * speed
        self.vy = dy * speed

    def update(self):
        self.pos_x += self.vx
        self.pos_y += self.vy
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)
        if (self.rect.top > SCREEN_HEIGHT + 60 or self.rect.bottom < -60 or self.rect.left > SCREEN_WIDTH + 60 or self.rect.right < -60):
            self.kill()


def create_stars(number):
    return [[random.randrange(0, SCREEN_WIDTH), random.randrange(0, SCREEN_HEIGHT), random.randrange(1, 4), random.randrange(1, 4)] for _ in range(number)]


def draw_stars(surface, stars, speed_level=0):
    modifier = 1.0 + speed_level * 0.15
    for star in stars:
        pg.draw.circle(surface, WHITE, (star[0], star[1]), star[3])
        star[1] += star[2] * modifier
        if star[1] > SCREEN_HEIGHT:
            star.clear()
            star += [random.randrange(0, SCREEN_WIDTH), 0, random.randrange(1, 4), random.randrange(1, 4)]


def draw_text(surface, text, font, color, x, y, align="topright"):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "topright":
        text_rect.topright = (x, y)
    elif align == "center":
        text_rect.center = (x, y)
    elif align == "topleft":
        text_rect.topleft = (x, y)
    surface.blit(text_surface, text_rect)


def draw_charge_gauge(surface, current_charge, max_charge, player_bottom_y):
    if current_charge > 0:
        gauge_width = 60
        gauge_height = 8
        x_pos = (SCREEN_WIDTH - gauge_width) // 2
        y_pos = player_bottom_y + 10
        fill_ratio = current_charge / max_charge
        fill_width = int(fill_ratio * gauge_width)

        outline_rect = pg.Rect(x_pos, y_pos, gauge_width, gauge_height)
        fill_rect = pg.Rect(x_pos, y_pos, fill_width, gauge_height)
        color = YELLOW if fill_ratio >= 1.0 else GREEN

        pg.draw.rect(surface, GRAY, outline_rect)
        pg.draw.rect(surface, color, fill_rect)
        pg.draw.rect(surface, WHITE, outline_rect, 1)


def draw_health_bar(surface, x, y, pct):
    pct = max(0, pct)
    BAR_LENGTH = 150
    BAR_HEIGHT = 15
    fill = (pct / 100) * BAR_LENGTH
    bar_color = GREEN if pct > 60 else YELLOW if pct > 30 else RED
    pg.draw.rect(surface, bar_color, (x, y, fill, BAR_HEIGHT))
    pg.draw.rect(surface, WHITE, (x, y, BAR_LENGTH, BAR_HEIGHT), 2)

stars = create_stars(100)

all_sprites = pg.sprite.Group()
enemies_group = pg.sprite.Group()
player_bullets_group = pg.sprite.Group()
player_charge_bullets_group = pg.sprite.Group()
enemy_bullets_group = pg.sprite.Group()
iwa_group = pg.sprite.Group()
items_group = pg.sprite.Group()
laser_group = pg.sprite.Group()
mid_boss_group = pg.sprite.Group()

player = Player()
all_sprites.add(player)

ADD_ENEMY = pg.USEREVENT + 1
initial_spawn_rate = 1000
current_spawn_rate = initial_spawn_rate
pg.time.set_timer(ADD_ENEMY, initial_spawn_rate)

score = 0
game_speed_level = 0
game_over = False
running = True
level_up_message_time = 0

mid_boss_spawned = False
mid_boss_defeated = False
mid_boss_warning_timer = 0
mid_boss_defeat_time = 0
MID_BOSS_SPAWN_SCORE = 5

boss_spawned = False
boss_spawn_time = 30000
boss_warning_time = 0
game_start_time = pg.time.get_ticks()


while running:
    clock.tick(FPS)
    now = pg.time.get_ticks()

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

        elif game_over and event.type == pg.KEYDOWN:
            running = False

        elif event.type == ADD_ENEMY and not game_over:
            if not boss_spawned:
                new_enemy = Enemy(game_speed_level, all_sprites, enemy_bullets_group)
                all_sprites.add(new_enemy)
                enemies_group.add(new_enemy)

                new_iwa = Iwa(game_speed_level, all_sprites)
                all_sprites.add(new_iwa)
                iwa_group.add(new_iwa)

    keys = pg.key.get_pressed()

    if not game_over:
        player.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)

    if player.powerup_level >= 2 and not game_over:
        if keys[pg.K_SPACE]:
            if not player.active_laser:
                player.active_laser = SuperLaser(player)
                all_sprites.add(player.active_laser)
                laser_group.add(player.active_laser)
        else:
            if player.active_laser:
                player.active_laser.kill()
                player.active_laser = None
    else:
        if player.active_laser:
            player.active_laser.kill()
            player.active_laser = None

    boss_spawn_delay = 10000

    if mid_boss_defeated and not boss_spawned:
        time_since_defeat = now - mid_boss_defeat_time

        if time_since_defeat > (boss_spawn_delay - 2000) and boss_warning_time == 0:
            boss_warning_time = now

    if mid_boss_defeated and not boss_spawned:
        time_since_defeat = now - mid_boss_defeat_time

        if time_since_defeat > boss_spawn_delay:
            boss = BigEnemy(game_speed_level, all_sprites, enemy_bullets_group, player)
            all_sprites.add(boss)
            enemies_group.add(boss)
            boss_spawned = True
            boss_warning_time = 0
            pg.time.set_timer(ADD_ENEMY, 0)

    if score >= MID_BOSS_SPAWN_SCORE and not mid_boss_spawned and not mid_boss_defeated:
        mid_boss_spawned = True
        mid_boss_warning_timer = 180
        mid_boss = MidBoss()
        all_sprites.add(mid_boss)
        mid_boss_group.add(mid_boss)
        pg.time.set_timer(ADD_ENEMY, 0)

    if mid_boss_warning_timer > 0:
        mid_boss_warning_timer -= 1

    if not game_over:
        sprites_to_update = [s for s in all_sprites if s != player]
        for sprite in sprites_to_update:
            try:
                sprite.update()
            except TypeError:
                try:
                    sprite.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)
                except Exception:
                    pass
    else:
        for s in list(all_sprites):
            if isinstance(s, Explosion):
                s.update()

    if not game_over:
        hits_normal = pg.sprite.groupcollide(player_bullets_group, enemies_group, True, False)
        hits_charge = pg.sprite.groupcollide(player_charge_bullets_group, enemies_group, False, False)
        hits_laser = pg.sprite.groupcollide(laser_group, enemies_group, False, True)

        enemies_destroyed_this_frame = 0
        enemies_to_process = set()

        for bullet, enemies_hit in {**hits_normal, **hits_charge}.items():
            for e in enemies_hit:
                enemies_to_process.add(e)

        for laser, enemies_hit in hits_laser.items():
            for e in enemies_hit:
                enemies_to_process.add(e)

        for enemy_hit in enemies_to_process:
            if enemy_hit.hit():
                size = "large" if isinstance(enemy_hit, BigEnemy) else "normal"
                all_sprites.add(Explosion(enemy_hit.rect.center, size, is_anime=False))
                score += enemy_hit.score_value
                enemies_destroyed_this_frame += 1
                enemy_hit.kill()
                if random.random() > 0.8:
                    item = random.choice([HealItem, AttackUpItem])(enemy_hit.rect.center)
                    all_sprites.add(item)
                    items_group.add(item)

        if mid_boss_spawned and not mid_boss_defeated:
            mb_hits = pg.sprite.groupcollide(player_bullets_group, mid_boss_group, True, False)
            for bullet, mbs in mb_hits.items():
                for mb in mbs:
                    if mb.hit():
                        all_sprites.add(Explosion(mb.rect.center, "large"))
                        score += mb.score_value
                        mid_boss_defeated = True
                        mb.kill()
                        pg.time.set_timer(ADD_ENEMY, current_spawn_rate)
                        mid_boss_defeat_time = now

            mb_hits_charge = pg.sprite.groupcollide(player_charge_bullets_group, mid_boss_group, False, False)
            for bullet, mbs in mb_hits_charge.items():
                for mb in mbs:
                    if mb.hit():
                        all_sprites.add(Explosion(mb.rect.center, "large"))
                        score += mb.score_value
                        mid_boss_defeated = True
                        mb.kill()
                        pg.time.set_timer(ADD_ENEMY, current_spawn_rate)
                        mid_boss_defeat_time = now

        if boss_spawned and not enemies_group:
            screen.fill((0, 0, 0))
            font = pg.font.Font(None, 74)
            text = font.render("YOU-WIN!", True, (255, 255, 0))
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text, text_rect)
            pg.display.flip()

            pg.time.wait(3000)
            running = False

        if enemies_destroyed_this_frame > 0 and not boss_spawned:
            new_speed_level = score // 10
            if new_speed_level > game_speed_level:
                game_speed_level = new_speed_level
                level_up_message_time = pg.time.get_ticks()
                rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level)))
                pg.time.set_timer(ADD_ENEMY, 0)
                pg.time.set_timer(ADD_ENEMY, rate)

        # 被弾に関する設定
        player_enemy_hits = pg.sprite.spritecollide(player, enemies_group, True)
        if player_enemy_hits:
            if player.take_damage(20):
                game_over = True
                all_sprites.add(Explosion(player.rect.center, "large", is_anime=False))
                player.hide()
            else:
                all_sprites.add(Explosion(player.rect.center, "normal", is_anime=False))

        player_beam_hits = pg.sprite.spritecollide(player, enemy_bullets_group, True)
        if player_beam_hits:
            if player.take_damage(10):
                game_over = True
                all_sprites.add(Explosion(player.rect.center, "large", is_anime=False))
                player.hide()
            else:
                all_sprites.add(Explosion(player.rect.center, "normal", is_anime=False))

        player_iwa_hits = pg.sprite.spritecollide(player, iwa_group, True)
        if player_iwa_hits:
            if player.take_damage(30):
                game_over = True
                all_sprites.add(Explosion(player.rect.center, "large", is_anime=False))
                player.hide()
            else:
                all_sprites.add(Explosion(player.rect.center, "normal", is_anime=False))

        for item in pg.sprite.spritecollide(player, items_group, True):
            item.apply_effect(player)

        if mid_boss_spawned and not mid_boss_defeated:
            player_mid_hits = pg.sprite.spritecollide(player,mid_boss_group, False)
            if player_mid_hits:
                all_sprites.add(Explosion(player.rect.center, "large"))
                game_over = True
                pg.time.set_timer(ADD_ENEMY, 0)

    screen.fill(BLACK)
    draw_stars(screen, stars, game_speed_level)
    all_sprites.draw(screen)


    if mid_boss_spawned and not mid_boss_defeated:
        for mb in mid_boss_group:
            mb.draw_health_bar(screen)


    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH - 10, 10, align="topright")
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")
    draw_health_bar(screen, 10, 40, player.health)

    if not player.hidden:
        draw_charge_gauge(screen, player.charge_value, player.charge_max_time, player.rect.bottom)

    if now - level_up_message_time < 1000 and not game_over:
        draw_text(screen, "LEVEL UP!", game_over_font, YELLOW, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    if boss_warning_time > 0 and not game_over and (now - boss_warning_time) % 1000 < 500:
        draw_text(screen, "!! WARNING !!", boss_warning_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, "center")
        draw_text(
            screen, "Press any key to exit", info_font, WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, "center"
        )

    pg.display.flip()

pg.quit()
sys.exit()