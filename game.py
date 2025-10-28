import os
import pygame as pg
import random
import sys

# --- 定数 (Constants) ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
FPS = 60

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 色 (Colors)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)     # 敵の色 (Enemy color)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0) # 弾の色 (Bullet color)
CYAN = (0, 255, 255)   # プレイヤーの色 (Player color)

# --- プレイヤー クラス (Player Class) ---
class Player(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # プレイヤーの画像 (三角形) を作成
        koukaton_img = pg.image.load("fig/koukaton.png")
        self.image = pg.transform.scale(koukaton_img, (10, 10))
        # self.image.set_colorkey(BLACK) # 黒を透明色に
        # pygame.draw.polygon(self.image, CYAN, [(15, 0), (0, 40), (30, 40)])
        
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 30
        self.speed_x = 0
        self.shoot_delay = 250 # 弾の発射間隔 (ミリ秒)
        self.last_shot = pg.time.get_ticks()

    def update(self):
        # 左右の移動 (Left/Right movement)
        self.speed_x = 0
        keys = pg.key.get_pressed()
        if keys[pg.K_LEFT]:
            self.speed_x = -7
        if keys[pg.K_RIGHT]:
            self.speed_x = 7
        
        self.rect.x += self.speed_x
        
        # 画面端の処理 (Screen boundary check)
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

    def shoot(self, all_sprites, bullets_group):
        """弾を発射する"""
        now = pg.time.get_ticks()
        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            bullet = Bullet(self.rect.centerx, self.rect.top)
            all_sprites.add(bullet)
            bullets_group.add(bullet)

# --- 敵 クラス (Enemy Class) ---
class Enemy(pg.sprite.Sprite):
    def __init__(self, speed_level=0): # スピードレベルを受け取る
        super().__init__()
        # 敵の画像 (円) を作成
        self.image = pg.Surface((25, 25))
        self.image.set_colorkey(BLACK)
        pg.draw.circle(self.image, RED, (12, 12), 12)
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        
        # スピードレベルに基づいて速度を計算
        base_speed_min = 2
        base_speed_max = 5
        # 難易度レベルごとに速度を少し上げる
        speed_increase = speed_level * 0.4 
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        
        # 速度が同じにならないように、最低でも1の範囲を持たせる
        if max_speed <= min_speed:
            max_speed = min_speed + 1
            
        self.speed_y = random.randrange(min_speed, max_speed) # 落下速度

    def update(self):
        # まっすぐ下に移動
        self.rect.y += self.speed_y
        # 画面外に出たら削除
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

# --- 弾 クラス (Bullet Class) ---
class Bullet(pg.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pg.Surface((5, 15))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -10 # 上に移動

    def update(self):
        self.rect.y += self.speed_y
        # 画面外に出たら削除
        if self.rect.bottom < 0:
            self.kill()

# --- 星（背景）の管理 (Star Background Management) ---
def create_stars(number):
    """指定された数の星のリストを作成する"""
    stars = []
    for _ in range(number):
        star_x = random.randrange(0, SCREEN_WIDTH)
        star_y = random.randrange(0, SCREEN_HEIGHT)
        star_speed = random.randrange(1, 4) # 星の速度 (1, 2, 3)
        star_size = random.randrange(1, 4)  # 星のサイズ (1, 2, 3)
        stars.append([star_x, star_y, star_speed, star_size]) # [x, y, speed, size]
    return stars

def draw_stars(surface, stars, speed_level=0): # スピードレベルを受け取る
    """星を描画し、スクロールさせる"""
    # スピードレベルに応じて背景のスクロール速度も上げる
    speed_modifier = 1.0 + speed_level * 0.15 
    
    for star in stars:
        # 星を描画 (star[3] = size)
        pg.draw.circle(surface, WHITE, (star[0], star[1]), star[3])
        # 星を下に移動 (star[2] = speed)
        star[1] += star[2] * speed_modifier
        
        # 画面外に出たら、上に戻す
        if star[1] > SCREEN_HEIGHT:
            star[1] = 0
            star[0] = random.randrange(0, SCREEN_WIDTH)

# --- ゲームの初期化 (Game Initialization) ---
pg.init()
screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pg.display.set_caption("Xevious Style Shooter")
clock = pg.time.Clock()

# 背景用の星を作成
stars = create_stars(100)

# --- スプライトグループの作成 (Sprite Groups) ---
all_sprites = pg.sprite.Group()
enemies_group = pg.sprite.Group()
bullets_group = pg.sprite.Group()

# プレイヤーの作成
player = Player()
all_sprites.add(player)

# 敵を定期的に生成するためのカスタムイベント
ADD_ENEMY = pg.USEREVENT + 1
initial_spawn_rate = 500 # 最初のスポーンレート
current_spawn_rate = initial_spawn_rate
pg.time.set_timer(ADD_ENEMY, current_spawn_rate) # 1000ミリ秒 (1秒) ごとに敵を生成

# スコアとゲームレベル
score = 0
game_speed_level = 0

# --- メインゲームループ (Main Game Loop) ---
running = True
while running:
    # 1. フレームレートの制御 (Control frame rate)
    clock.tick(FPS)

    # 2. イベント処理 (Event handling)
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        elif event.type == ADD_ENEMY:
            # 敵を生成 (現在のゲームレベルを渡す)
            new_enemy = Enemy(game_speed_level)
            all_sprites.add(new_enemy)
            enemies_group.add(new_enemy)

    # 射撃 (スペースキーが押され続けているかチェック)
    keys = pg.key.get_pressed()
    if keys[pg.K_SPACE]:
        player.shoot(all_sprites, bullets_group)

    # 3. 更新 (Update)
    all_sprites.update()

    # 4. 衝突判定 (Collision Detection)
    # 弾と敵の衝突
    hits = pg.sprite.groupcollide(bullets_group, enemies_group, True, True)
    # True, True は弾も敵も両方消すという意味
    
    enemies_destroyed_this_frame = 0
    # 複数の弾が同時に当たった場合もカウントするため
    for bullet, enemies_hit in hits.items():
        enemies_destroyed_this_frame += len(enemies_hit)
        
    if enemies_destroyed_this_frame > 0:
        score += enemies_destroyed_this_frame
        print(f"Score: {score}")
        
        # 10機倒すごとにレベルアップ
        new_speed_level = score // 10
        if new_speed_level > game_speed_level:
            game_speed_level = new_speed_level
            print(f"--- SPEED LEVEL UP! Level: {game_speed_level} ---")
            
            # 敵の出現頻度を上げる（スポーン間隔を短くする）
            # レベルが上がるごとにスポーン間隔を 0.9 倍にする
            current_spawn_rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level))) # 最低150ms
            pg.time.set_timer(ADD_ENEMY, 0) # 既存のタイマーをキャンセル
            pg.time.set_timer(ADD_ENEMY, current_spawn_rate) # 新しいタイマーを設定
            print(f"New Spawn Rate: {current_spawn_rate} ms")

    
    # プレイヤーと敵の衝突
    player_hits = pg.sprite.spritecollide(player, enemies_group, False) # ぶつかった敵のリスト
    if player_hits:
        # プレイヤーが敵に当たったらゲームオーバー
        print("Game Over!")
        running = False

    # 5. 描画 (Draw / Render)
    screen.fill(BLACK) # 画面を黒で塗りつぶす
    draw_stars(screen, stars, game_speed_level) # 星空を描画 (スピードレベルを渡す)
    all_sprites.draw(screen) # 全てのスプライトを描画

    # 6. 画面のフリップ (Flip display)
    pg.display.flip()

# --- 終了処理 (Exit) ---
pg.quit()
sys.exit()

