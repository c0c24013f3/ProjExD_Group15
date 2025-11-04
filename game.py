# game_final_redbullet_jp_fixed.py
import pygame
import sys
import random
import os
import math

# --- 常量 (Constants) ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# --- Pygame 初期化 / Initialize pygame ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Xevious Style Shooter - Final Red Bullets (Fixed)")
clock = pygame.time.Clock()

# --- 资源路径设置 / Asset path ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")
if not os.path.exists(fig_dir):
    os.makedirs(fig_dir)

# --- 安全加载图片函数（找不到则生成占位图）---
def safe_load(path, fallback_size=(40,40), fillcolor=(120,120,120)):
    try:
        img = pygame.image.load(path).convert_alpha()
        return img
    except Exception:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill(fillcolor)
        return surf

# 读取主要图片资源
PLAYER_IMAGE = safe_load(os.path.join(fig_dir, "koukaton.png"), (40,40))
ENEMY_IMAGE = safe_load(os.path.join(fig_dir, "enemy.png"), (40,40))
MID_BOSS_IMAGE = safe_load(os.path.join(fig_dir, "final_enemy.png"), (120,120))
PLAYER_BULLET_IMAGE = safe_load(os.path.join(fig_dir, "beam.png"), (15,15))

# --- 爆炸帧の読み込み / Load explosion frames ---
EXPLOSION_FRAMES = []
for i in range(100):
    fn = f"explosion_{i:02d}.png"
    p = os.path.join(fig_dir, fn)
    if os.path.exists(p):
        try:
            EXPLOSION_FRAMES.append(pygame.image.load(p).convert_alpha())
        except Exception as e:
            print(f"Warning loading {p}: {e}")

if not EXPLOSION_FRAMES:
    gif_path = os.path.join(fig_dir, "explosion.gif")
    if os.path.exists(gif_path):
        try:
            gif_img = pygame.image.load(gif_path).convert_alpha()
            EXPLOSION_FRAMES = [gif_img]
        except Exception as e:
            print(f"Error loading explosion.gif: {e}")

if not EXPLOSION_FRAMES:
    fallback = pygame.Surface((60,60), pygame.SRCALPHA)
    pygame.draw.circle(fallback, RED, (30,30), 30)
    EXPLOSION_FRAMES = [fallback]

# --- 字体设置 / Fonts ---
score_font = pygame.font.SysFont(None, 36)
game_over_font = pygame.font.SysFont(None, 64, bold=True)
preferred_fonts = ["meiryo", "msgothic", "msmincho", "ms gothic", "arialunicode", "simhei", "simsun"]
boss_font = None
for name in preferred_fonts:
    fpath = pygame.font.match_font(name)
    if fpath:
        boss_font = pygame.font.Font(fpath, 48)
        break
if not boss_font:
    boss_font = pygame.font.SysFont(None, 48, bold=True)

# --- 文本绘制辅助 / Helper to draw text ---
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

# --- クラス定義 / Classes ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.transform.scale(PLAYER_IMAGE, (40,40))
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 30
        self.speed_x = 0
        self.shoot_delay = 200
        self.last_shot = pygame.time.get_ticks()
        self.hidden = False

    def update(self):
        if self.hidden:
            return
        self.speed_x = 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.speed_x = -7
        if keys[pygame.K_RIGHT]:
            self.speed_x = 7
        self.rect.x += self.speed_x
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

    def shoot(self, all_sprites, bullets_group):
        if self.hidden:
            return
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            b = PlayerBullet(self.rect.centerx, self.rect.top)
            all_sprites.add(b)
            bullets_group.add(b)

    def hide(self):
        self.hidden = True
        self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, speed_level=0):
        super().__init__()
        self.image = pygame.transform.scale(ENEMY_IMAGE, (40,40))
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        base_speed_min = 2
        base_speed_max = 5
        speed_increase = speed_level * 0.4
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        if max_speed <= min_speed:
            max_speed = min_speed + 1
        self.speed_y = random.randrange(min_speed, max_speed)
        self.health = 1
        self.score_value = 1

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

    def hit(self):
        self.health -= 1
        return self.health <= 0

class MidBoss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = pygame.transform.scale(MID_BOSS_IMAGE, (120,120))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.y = -150

        self.speed_x = 3
        self.speed_y = 2
        self.direction = 1

        self.shoot_delay = 900
        self.last_shot = pygame.time.get_ticks()
        self.shoot_pattern = 0
        self.pattern_timer = 0
        self.spiral_angle = 0.0

        self.has_appeared = False
        self.health = 30
        self.max_health = 30
        self.score_value = 50

        self.is_special_moving = False
        self.special_move_timer = 0

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
                self.is_special_moving = False
                self.special_move_timer = 0
        else:
            self.rect.x += self.speed_x * self.direction
            if self.rect.right >= SCREEN_WIDTH - 10:
                self.direction = -1
            elif self.rect.left <= 10:
                self.direction = 1
            self.rect.y += math.sin(pygame.time.get_ticks() * 0.005) * 1.5

        self.shoot()

        self.pattern_timer += 1
        if self.pattern_timer >= 180:
            self.shoot_pattern = (self.shoot_pattern + 1) % 2
            self.pattern_timer = 0

        if not self.is_special_moving and random.random() < 0.003:
            self.is_special_moving = True
            self.special_move_timer = 0

    def shoot(self):
        # 直接使用模块级全局分组，确保子弹被加入 enemy_bullets_group
        global all_sprites, enemy_bullets_group
        now = pygame.time.get_ticks()
        if now - self.last_shot < self.shoot_delay:
            return
        self.last_shot = now

        if self.shoot_pattern == 0:
            bullets_per_wave = 10
            angle_step = 360.0 / bullets_per_wave
            base_angle = self.spiral_angle
            for i in range(bullets_per_wave):
                ang = base_angle + i * angle_step
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
        bar_width = 100
        bar_height = 10
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.top - 20
        pygame.draw.rect(surface, RED, (bar_x, bar_y, bar_width, bar_height))
        health_width = int((self.health / self.max_health) * bar_width)
        pygame.draw.rect(surface, YELLOW, (bar_x, bar_y, health_width, bar_height))

class MidBossBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle_deg, mode="spiral"):
        super().__init__()
        radius = 12
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 50, 50), (radius, radius), radius)
        self.image = surf
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.pos_x = float(self.rect.centerx)
        self.pos_y = float(self.rect.centery)
        self.mode = mode

        rad = math.radians(angle_deg)
        dir_x = math.cos(rad)
        dir_y = math.sin(rad)

        if mode == "spiral":
            speed = 5.5
        elif mode == "scatter":
            speed = 6.0
        else:
            speed = 5.0

        self.vx = dir_x * speed
        self.vy = dir_y * speed

    def update(self):
        self.pos_x += self.vx
        self.pos_y += self.vy
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)

        if (self.rect.top > SCREEN_HEIGHT + 60 or self.rect.bottom < -60 or
            self.rect.left > SCREEN_WIDTH + 60 or self.rect.right < -60):
            self.kill()

class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        raw = pygame.transform.scale(PLAYER_BULLET_IMAGE, (12,12))
        self.image = pygame.transform.flip(raw, False, True)
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -10

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()

class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, size="normal"):
        super().__init__()
        self.frames = EXPLOSION_FRAMES
        if size == "large":
            self.frames = [pygame.transform.scale(f, (90,90)) for f in self.frames]
            self.frame_rate = 100
        else:
            self.frames = [pygame.transform.scale(f, (60,60)) for f in self.frames]
            self.frame_rate = 70

        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=center)
        self.last_update = pygame.time.get_ticks()

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.kill()
            else:
                center = self.rect.center
                self.image = self.frames[self.current_frame]
                self.rect = self.image.get_rect(center=center)

def create_stars(number):
    stars = []
    for _ in range(number):
        star_x = random.randrange(0, SCREEN_WIDTH)
        star_y = random.randrange(0, SCREEN_HEIGHT)
        star_speed = random.randrange(1,4)
        star_size = random.randrange(1,4)
        stars.append([star_x, star_y, star_speed, star_size])
    return stars

def draw_stars(surface, stars, speed_level=0):
    speed_modifier = 1.0 + speed_level * 0.15
    for star in stars:
        pygame.draw.circle(surface, WHITE, (star[0], star[1]), star[3])
        star[1] += star[2] * speed_modifier
        if star[1] > SCREEN_HEIGHT:
            star[1] = 0
            star[0] = random.randrange(0, SCREEN_WIDTH)

# --- ゲーム初期化 / Setup groups and game objects ---
stars = create_stars(100)
all_sprites = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()
player_bullets_group = pygame.sprite.Group()
enemy_bullets_group = pygame.sprite.Group()
mid_boss_group = pygame.sprite.Group()

player = Player()
all_sprites.add(player)

ADD_ENEMY = pygame.USEREVENT + 1
initial_spawn_rate = 1000
current_spawn_rate = initial_spawn_rate
pygame.time.set_timer(ADD_ENEMY, current_spawn_rate)

score = 0
game_speed_level = 0
game_over = False
mid_boss_spawned = False
mid_boss_defeated = False
mid_boss_warning_timer = 0

# --- メインループ / Main game loop ---
running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == ADD_ENEMY and not game_over:
            if not mid_boss_spawned or mid_boss_defeated:
                new_enemy = Enemy(game_speed_level)
                all_sprites.add(new_enemy)
                enemies_group.add(new_enemy)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE] and not game_over:
        player.shoot(all_sprites, player_bullets_group)

    if not game_over:
        all_sprites.update()

        if score >= 5 and not mid_boss_spawned and not mid_boss_defeated:
            mid_boss_spawned = True
            mid_boss_warning_timer = 180
            print("中ボス出現！")
            mid_boss = MidBoss()
            all_sprites.add(mid_boss)
            mid_boss_group.add(mid_boss)
            pygame.time.set_timer(ADD_ENEMY, 0)

        if mid_boss_warning_timer > 0:
            mid_boss_warning_timer -= 1
    else:
        for s in list(all_sprites):
            if isinstance(s, Explosion):
                s.update()

    # 衝突判定 / Collisions
    if not game_over:
        enemies_destroyed_this_frame = 0

        hits_normal = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, False)
        for bullet, enemies_hit in hits_normal.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit():
                    explosion = Explosion(enemy_hit.rect.center, "normal")
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill()

        if mid_boss_spawned and not mid_boss_defeated:
            mid_boss_hits = pygame.sprite.groupcollide(player_bullets_group, mid_boss_group, True, False)
            for bullet, mid_bosses_hit in mid_boss_hits.items():
                for mid_boss_hit in mid_bosses_hit:
                    if mid_boss_hit.hit():
                        if mid_boss_hit.health <= 0:
                            explosion = Explosion(mid_boss_hit.rect.center, "large")
                            all_sprites.add(explosion)
                            score += mid_boss_hit.score_value
                            mid_boss_defeated = True
                            mid_boss_hit.kill()
                            print("中ボス撃破！")
                            pygame.time.set_timer(ADD_ENEMY, current_spawn_rate)

        if enemies_destroyed_this_frame > 0:
            new_speed_level = score // 10
            if new_speed_level > game_speed_level:
                game_speed_level = new_speed_level
                current_spawn_rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level)))
                pygame.time.set_timer(ADD_ENEMY, 0)
                pygame.time.set_timer(ADD_ENEMY, current_spawn_rate)

        player_enemy_hits = pygame.sprite.spritecollide(player, enemies_group, True)
        if player_enemy_hits:
            explosion = Explosion(player.rect.center, "large")
            all_sprites.add(explosion)
            player.hide()
            game_over = True
            print("Game Over! (Collided with enemy)")
            pygame.time.set_timer(ADD_ENEMY, 0)

        # 关键：检测玩家与敌机子弹的碰撞（包括Boss子弹）
        player_beam_hits = pygame.sprite.spritecollide(player, enemy_bullets_group, True)
        if player_beam_hits:
            print(f"DEBUG: Player hit by {len(player_beam_hits)} enemy bullets")
            explosion = Explosion(player.rect.center, "normal")
            all_sprites.add(explosion)
            player.hide()
            game_over = True
            print("Game Over! (Hit by enemy beam)")
            pygame.time.set_timer(ADD_ENEMY, 0)

        if mid_boss_spawned and not mid_boss_defeated:
            player_mid_boss_hits = pygame.sprite.spritecollide(player, mid_boss_group, False)
            if player_mid_boss_hits:
                explosion = Explosion(player.rect.center, "large")
                all_sprites.add(explosion)
                player.hide()
                game_over = True
                print("Game Over! (Collided with Mid Boss)")
                pygame.time.set_timer(ADD_ENEMY, 0)

    screen.fill(BLACK)
    draw_stars(screen, stars, game_speed_level)
    all_sprites.draw(screen)

    if mid_boss_spawned and not mid_boss_defeated:
        for mb in mid_boss_group:
            mb.draw_health_bar(screen)

    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH - 10, 10, align="topright")
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")

    if mid_boss_warning_timer > 0 and mid_boss_warning_timer % 30 < 15:
        draw_text(screen, "中ボス出現！", boss_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, align="center")

    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    pygame.display.flip()

pygame.quit()
sys.exit()
