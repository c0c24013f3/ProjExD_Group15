import pygame
import sys
import random
import os

# --- スクリプトのパスを基準にディレクトリを設定 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")

# --- 定数 ---
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
BOSS_GREEN = (0, 150, 50) 

# --- ゲームの初期化 ---
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Xevious Style Shooter")
clock = pygame.time.Clock()


# --- 画像ファイルの読み込み ---
if not os.path.exists(fig_dir):
    os.makedirs(fig_dir)
    print(f"Warning: '{fig_dir}' directory not found. Created an empty one.")
    print("Please place 'koukaton.png', 'enemy.png', 'beam.png' and explosion frames inside 'fig' folder.")

try:
    PLAYER_IMAGE = pygame.image.load(os.path.join(fig_dir, "koukaton.png")).convert_alpha()
    ENEMY_IMAGE = pygame.image.load(os.path.join(fig_dir, "enemy.png")).convert_alpha()
    PLAYER_BULLET_IMAGE = pygame.image.load(os.path.join(fig_dir, "beam.png")).convert_alpha()
    ENEMY_BULLET_IMAGE = pygame.image.load(os.path.join(fig_dir, "beam.png")).convert_alpha()
    ####IWA画像の読み込み####
    IWA_IMAGE = pygame.image.load(os.path.join(fig_dir, "iwa_01.png")).convert_alpha()


    try:
        BOSS_IMAGE = pygame.image.load(os.path.join(fig_dir, "boss.png")).convert_alpha()
    except pygame.error:
        print("Warning: 'boss.png' not found. Using a fallback green rectangle.")
        BOSS_IMAGE = pygame.Surface((120, 100))
        BOSS_IMAGE.fill(BOSS_GREEN)

    # 爆発エフェクトの連番フレームを読み込む (例: explosion_00.png, 01.png...)
    EXPLOSION_FRAMES = []
    for i in range(10): # 00～09 の10フレームを想定
        frame_filename = os.path.join(fig_dir, f"explosion_{i:02d}.png")
        if os.path.exists(frame_filename):
            EXPLOSION_FRAMES.append(pygame.image.load(frame_filename).convert_alpha())
        else:
            if i == 0:
                print(f"Warning: Explosion frame {frame_filename} not found. Trying 'explosion.gif'.")
                try:
                    single_explosion_image = pygame.image.load(os.path.join(fig_dir, "explosion.gif")).convert_alpha()
                    EXPLOSION_FRAMES = [single_explosion_image]
                except pygame.error as gif_e:
                    print(f"Error loading explosion.gif: {gif_e}")
            break

    if not EXPLOSION_FRAMES: # 何も読み込めなかった場合
        print("Warning: No explosion images found. Using a fallback red circle.")
        fallback_image = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(fallback_image, RED, (30, 30), 30)
        EXPLOSION_FRAMES = [fallback_image]

except pygame.error as e:
    print(f"Error loading image: {e}")
    print("Make sure 'koukaton.png', 'enemy.png', 'beam.png' and explosion frames exist in 'fig' folder.")
    pygame.quit()
    sys.exit()


# --- プレイヤークラス ---
class Player(pygame.sprite.Sprite):
    """
    プレイヤー機を管理するクラス。
    移動、通常ショット、チャージショットの発射を処理する。
    """
    def __init__(self):
        super().__init__()
        self.image = pygame.transform.scale(PLAYER_IMAGE, (40, 40))
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - 30
        self.speed_x = 0
        self.hidden = False # ゲームオーバー時の非表示フラグ

        # 通常ショット用
        self.shoot_delay = 250 # (ms)
        self.last_shot = pygame.time.get_ticks()

        # チャージショット用
        self.is_charging = False
        self.charge_start_time = 0
        self.charge_max_time = 1000 # 最大チャージ時間 (ms)
        self.charge_value = 0

    def update(self, keys, all_sprites, bullets_group, charge_bullets_group):
        """
        プレイヤーの状態を毎フレーム更新する。
        移動処理と、Vキーによるチャージ・射撃判定を行う。
        """
        if self.hidden:
            return

        # 左右の移動
        self.speed_x = 0
        if keys[pygame.K_LEFT]:
            self.speed_x = -7
        if keys[pygame.K_RIGHT]:
            self.speed_x = 7
        self.rect.x += self.speed_x

        # 画面端の処理
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

        # Vキー: チャージと射撃
        now = pygame.time.get_ticks()

        if keys[pygame.K_v]:
            # Vキーが押されている（チャージ中）
            if not self.is_charging:
                # 押された瞬間
                self.is_charging = True
                self.charge_start_time = now
                self.charge_value = 0
            else:
                # 押され続けている
                self.charge_value = min(now - self.charge_start_time, self.charge_max_time)

        else:
            # Vキーが離されている
            if self.is_charging:
                # 離された瞬間
                if self.charge_value >= self.charge_max_time:
                    # 1. チャージ完了 -> チャージショット発射
                    self.shoot_charge_shot(all_sprites, charge_bullets_group)
                else:
                    # 2. チャージ未完了 (タップ) -> 通常ショット発射
                    self.shoot(all_sprites, bullets_group, now)
                self.is_charging = False
                self.charge_value = 0

            # K_SPACE: Vキーとは別の通常ショット
            if keys[pygame.K_SPACE]:
                 self.shoot(all_sprites, bullets_group, now)


    def shoot(self, all_sprites, bullets_group, now):
        """通常弾を発射する（連射ディレイあり）"""
        if self.hidden:
            return

        if now - self.last_shot > self.shoot_delay:
            self.last_shot = now
            bullet = PlayerBullet(self.rect.centerx, self.rect.top)
            all_sprites.add(bullet)
            bullets_group.add(bullet)

    def shoot_charge_shot(self, all_sprites, charge_bullets_group):
        """チャージショットを発射する"""
        if self.hidden:
            return

        print("FIRE CHARGE SHOT!")
        charge_shot = PlayerChargeShot(self.rect.centerx, self.rect.top)
        all_sprites.add(charge_shot)
        charge_bullets_group.add(charge_shot)

    def hide(self):
        """プレイヤーを一時的に隠す（ゲームオーバー処理）"""
        self.hidden = True
        self.kill() # スプライトグループから削除


# --- 敵クラス ---
class Enemy(pygame.sprite.Sprite):
    """
    敵機を管理するクラス。
    画面上からランダムな速度で降下し、弾を発射する。
    """
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None):
        super().__init__()
        self.image = pygame.transform.scale(ENEMY_IMAGE, (40, 40))
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)

        # ゲームレベルに応じて落下速度を決定
        base_speed_min = 2
        base_speed_max = 5
        speed_increase = speed_level * 0.4
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        if max_speed <= min_speed:
            max_speed = min_speed + 1

        self.speed_y = random.randrange(min_speed, max_speed)
        
        # --- ★★★ クラッシュ回避に必須 ★★★ ---
        self.all_sprites = all_sprites_ref
        self.enemy_bullets_group = enemy_bullets_group_ref
        # --- ★★★★★★★★★★★★★★★★ ---

        self.enemy_shoot_delay = 2500 # (ms)
        # 最初の発射タイミングをずらす
        self.last_shot = pygame.time.get_ticks() - random.randrange(0, self.enemy_shoot_delay)

        self.health = 1
        self.score_value = 1

    def update(self):
        """敵を下に移動させ、画面外に出たら削除する。定期的に弾を発射する。"""
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

        self.shoot()

    def shoot(self):
        """敵がビームを発射する（連射ディレイあり）"""
         

        now = pygame.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            # ★★★ 修正点1で差し替えたため、 EnemyBullet は speed_y_val と player_ref を省略可能 ★★★
            enemy_bullet = EnemyBullet(self.rect.centerx, self.rect.bottom) 
            self.all_sprites.add(enemy_bullet)
            self.enemy_bullets_group.add(enemy_bullet)

    def hit(self):
        """弾が当たった時の処理。体力を減らし、0以下ならTrue（破壊）を返す。"""
        self.health -= 1
        if self.health <= 0:
            return True # 破壊された
        return False # まだ生きている

# --- ★★★ ボスクラス ★★★ ---
class BigEnemy(Enemy):
    """
    でかい敵（ボス）クラス。
    Enemyを継承し、体力、サイズ、移動パターン、射撃頻度を変更する。
    """
    # 修正点 1: __init__ で player_ref を受け取る
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None, player_ref=None):
        
        # --- ★★★ クラッシュ回避に最重要 ★★★ ---
        super().__init__(speed_level, all_sprites_ref, enemy_bullets_group_ref)
        # --- ★★★★★★★★★★★★★★★★★★★★ ---

        # 修正点 2: プレイヤーへの参照を保存
        self.player = player_ref 

        self.image = pygame.transform.scale(BOSS_IMAGE, (120, 100))
        self.rect = self.image.get_rect()
        self.rect.x = (SCREEN_WIDTH - self.rect.width) // 2
        self.rect.y = -self.rect.height 

        self.speed_y = 1  # 降りてくる速度
        self.speed_x = 3
        self.target_y = 100 

        self.health = 30 
        self.score_value = 50 

        self.enemy_shoot_delay = 1000 # 射撃頻度
        self.last_shot = pygame.time.get_ticks()

    def update(self):
        """ボス専用の移動パターンと射撃"""
        
        if self.rect.y < self.target_y:
            self.rect.y += self.speed_y
        else:
            self.rect.x += self.speed_x
            if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
                self.speed_x *= -1 
                self.rect.x += self.speed_x 

        # 下で定義したホーミング弾用の射撃メソッドを呼ぶ
        self.shoot() 

        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

    # 修正点 3: shoot メソッドを上書き (オーバーライド)
    def shoot(self):
        """敵がホーミングビームを発射する"""
        
        if not self.all_sprites or not self.enemy_bullets_group:
            return

        now = pygame.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            
            bullet_speed_y = 10 
            
            # ★★★ 修正点1で差し替えた EnemyBullet を呼び出す ★★★
            # 左の弾 (ホーミング)
            bullet_left = EnemyBullet(self.rect.centerx - 40, self.rect.bottom, bullet_speed_y, self.player)
            # 右の弾 (ホーミング)
            bullet_right = EnemyBullet(self.rect.centerx + 40, self.rect.bottom, bullet_speed_y, self.player)
            
            self.all_sprites.add(bullet_left)
            self.all_sprites.add(bullet_right)
            self.enemy_bullets_group.add(bullet_left)
            self.enemy_bullets_group.add(bullet_right)

    # --- ★★★ 修正点2: 重複していた2つ目の update メソッドを削除 ★★★ ---
    # (元々ここに 424行目～442行目のコードがありましたが、削除しました)
    
# --- ★★★ 変更点ここまで ★★★ ---


####岩の最終コード####
class Iwa(pygame.sprite.Sprite):
    def __init__(self, speed_level=0, all_sprites_ref=None):
        super().__init__()
        self.image = pygame.transform.scale(IWA_IMAGE, (50, 50))
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)

        base_speed_min = 3
        base_speed_max = 5
        speed_increase = speed_level * 0.4 
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        if max_speed <= min_speed:
            max_speed = min_speed + 1
        self.speed_y = random.randrange(min_speed, max_speed)      
        self.all_sprites = all_sprites_ref

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()


# --- プレイヤー弾クラス ---
class PlayerBullet(pygame.sprite.Sprite):
    """プレイヤーの通常弾。上にまっすぐ飛ぶ。"""
    def __init__(self, x, y):
        super().__init__()
        raw_image = pygame.transform.scale(PLAYER_BULLET_IMAGE, (25, 15))
        self.image = pygame.transform.rotate(raw_image, 90)
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -10

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()

# --- プレイヤー・チャージショットクラス ---
class PlayerChargeShot(pygame.sprite.Sprite):
    """プレイヤーのチャージ弾。大きく高速で、貫通はしないが当たり判定が広い。"""
    def __init__(self, x, y):
        super().__init__()
        raw_image = pygame.transform.scale(PLAYER_BULLET_IMAGE, (120, 60))
        self.image = pygame.transform.rotate(raw_image, 90)

        # 色を赤に変更
        color_surface = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        color_surface.fill(RED)
        self.image.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -12

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()


# --- ★★★ 修正点1: EnemyBullet クラスを完全に差し替え ★★★ ---
class EnemyBullet(pygame.sprite.Sprite):
    """
    敵の弾。
    player_ref が渡された場合は、プレイヤーを狙うホーミング弾になる。
    """
    
    # __init__ の引数を変更 (speed_y_val と player_ref を受け取れるようにする)
    def __init__(self, x, y, speed_y_val=7, player_ref=None):
        super().__init__()
        raw_image = pygame.transform.scale(ENEMY_BULLET_IMAGE, (30, 15))
        raw_image_rotated = pygame.transform.rotate(raw_image, -90)
        self.image = raw_image_rotated.copy()

        # 色を黄色に変更
        color_surface = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        color_surface.fill(YELLOW)
        self.image.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self.rect = self.image.get_rect()
        self.rect.top = y
        self.rect.centerx = x

        # 速度とプレイヤー参照を設定
        self.speed_y = speed_y_val # 渡されたY速度を使用 (デフォルト 7)
        self.speed_x = 0
        self.player = player_ref   # プレイヤーへの参照

        # ホーミング弾ロジック (発射時に一度だけ狙う)
        # プレイヤーが渡され、かつ隠れていない場合
        if self.player and not self.player.hidden:
            dx = self.player.rect.centerx - self.rect.centerx
            dy = self.player.rect.centery - self.rect.centery
            
            # プレイヤーがボスより下にいる場合のみホーミング
            if dy > 0:
                try:
                    # Y速度 (self.speed_y) を基準にX速度を計算
                    self.speed_x = (dx / dy) * self.speed_y
                except ZeroDivisionError:
                    self.speed_x = 0
                    
                # X速度が速すぎないように制限 (Y速度の1.5倍まで)
                max_speed_x = self.speed_y * 1.5
                self.speed_x = max(-max_speed_x, min(self.speed_x, max_speed_x))
            # (プレイヤーが上にいる場合は、そのまま (speed_x=0) まっすぐ下に撃つ)

    def update(self):
        # 発射時に計算された速度でまっすぐ飛ぶ
        self.rect.y += self.speed_y
        self.rect.x += self.speed_x
        
        # 画面外 (上下左右) に出たら削除
        if self.rect.top > SCREEN_HEIGHT or self.rect.bottom < 0 or \
           self.rect.left > SCREEN_WIDTH or self.rect.right < 0:
            self.kill()
# --- ★★★ 修正点1 ここまで ★★★ ---


# --- 爆発エフェクトクラス ---
class Explosion(pygame.sprite.Sprite):
    """
    爆発のアニメーションを再生するクラス。
    指定されたフレーム画像を順に表示し、終わると消滅する。
    """
    def __init__(self, center, size="normal"):
        super().__init__()
        self.frames = list(EXPLOSION_FRAMES) # 元リストを保護

        if size == "large":
            self.frames = [pygame.transform.scale(f, (90, 90)) for f in self.frames]
            self.frame_rate = 100 # (ms)
        else:
            self.frames = [pygame.transform.scale(f, (60, 60)) for f in self.frames]
            self.frame_rate = 70 # (ms)

        self.current_frame = 0
        try:
            self.image = self.frames[self.current_frame]
        except IndexError:
            # フォールバック (EXPLOSION_FRAMES が空だった場合)
            self.image = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(self.image, RED, (30, 30), 30)
            self.frames = [self.image]

        self.rect = self.image.get_rect(center=center)
        self.last_update = pygame.time.get_ticks()

    def update(self):
        """フレームレートに基づいてアニメーションを更新する"""
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.kill() # アニメーション終了
            else:
                center = self.rect.center
                self.image = self.frames[self.current_frame]
                self.rect = self.image.get_rect(center=center)


# --- 星（背景）の管理 ---
def create_stars(number):
    """指定された数の星 [x, y, speed, size] のリストを作成する"""
    stars = []
    for _ in range(number):
        stars.append([
            random.randrange(0, SCREEN_WIDTH),
            random.randrange(0, SCREEN_HEIGHT),
            random.randrange(1, 4), # speed
            random.randrange(1, 4)  # size
        ])
    return stars

def draw_stars(surface, stars, speed_level=0):
    """星を描画し、スクロールさせる。ゲームレベルに応じて速度が上がる。"""
    speed_modifier = 1.0 + speed_level * 0.15

    for star in stars:
        pygame.draw.circle(surface, WHITE, (star[0], star[1]), star[3])
        star[1] += star[2] * speed_modifier # 速度に応じて下に移動

        # 画面外に出たら、上に戻す
        if star[1] > SCREEN_HEIGHT:
            star[1] = 0
            star[0] = random.randrange(0, SCREEN_WIDTH)

# --- テキスト描画用のヘルパー関数 ---
def draw_text(surface, text, font, color, x, y, align="topright"):
    """指定された位置・基準でテキストを描画する"""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "topright":
        text_rect.topright = (x, y)
    elif align == "center":
        text_rect.center = (x, y)
    elif align == "topleft":
        text_rect.topleft = (x, y)
    surface.blit(text_surface, text_rect)

# --- チャージゲージ描画用のヘルパー関数 ---
def draw_charge_gauge(surface, current_charge, max_charge, player_bottom_y):
    """プレイヤーの下にチャージゲージを描画する"""
    if current_charge > 0: # チャージ中の時だけ描画
        gauge_width = 60
        gauge_height = 8
        x_pos = (SCREEN_WIDTH - gauge_width) // 2
        y_pos = player_bottom_y + 10 # プレイヤーの少し下

        fill_ratio = current_charge / max_charge
        fill_width = int(fill_ratio * gauge_width)

        outline_rect = pygame.Rect(x_pos, y_pos, gauge_width, gauge_height)
        fill_rect = pygame.Rect(x_pos, y_pos, fill_width, gauge_height)

        color = YELLOW if fill_ratio >= 1.0 else GREEN

        pygame.draw.rect(surface, GRAY, outline_rect) # 背景
        pygame.draw.rect(surface, color, fill_rect)  # ゲージ
        pygame.draw.rect(surface, WHITE, outline_rect, 1) # 縁

# --- フォントの設定 ---
score_font = pygame.font.SysFont(None, 36)
game_over_font = pygame.font.SysFont(None, 64, bold=True)
boss_warning_font = pygame.font.SysFont(None, 72, bold=True) 

# --- ゲーム変数とスプライトグループの準備 ---
stars = create_stars(100)

all_sprites = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()
player_bullets_group = pygame.sprite.Group()
player_charge_bullets_group = pygame.sprite.Group() # チャージショット用
enemy_bullets_group = pygame.sprite.Group()
iwa_group = pygame.sprite.Group() ####iwaグループ####

player = Player()
all_sprites.add(player)

# 敵を定期的に生成するためのカスタムイベント
ADD_ENEMY = pygame.USEREVENT + 1
initial_spawn_rate = 1000 # (ms)
current_spawn_rate = initial_spawn_rate
pygame.time.set_timer(ADD_ENEMY, current_spawn_rate)

# スコアとゲームレベル
score = 0
game_speed_level = 0
game_over = False
game_over_time = None
level_up_message_time = 0

# ボス関連の変数
boss_spawned = False
boss_spawn_time = 30000 # 30秒 (ms)
boss_warning_time = 0
game_start_time = pygame.time.get_ticks() # ゲーム開始時刻を記録

# --- メインゲームループ ---
running = True
while running:
    # 1. フレームレートの制御
    clock.tick(FPS)
    
    now = pygame.time.get_ticks()

    # 2. イベント処理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == ADD_ENEMY and not game_over:
            new_enemy = Enemy(game_speed_level, all_sprites, enemy_bullets_group)
            all_sprites.add(new_enemy)
            enemies_group.add(new_enemy)

            ####iwa生成####
            new_iwa = Iwa(game_speed_level, all_sprites)
            all_sprites.add(new_iwa)#岩の生成に必要
            iwa_group.add(new_iwa)


    keys = pygame.key.get_pressed()


    # 3. 更新
    if not game_over:
        # プレイヤーの更新
        player.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)
        
        # ボス出現処理
        elapsed_time = now - game_start_time
        
        # 28秒経過したら警告表示開始
        if elapsed_time > (boss_spawn_time - 2000) and not boss_spawned and boss_warning_time == 0:
             boss_warning_time = now

        # 30秒経過したらボス出現
        if elapsed_time > boss_spawn_time and not boss_spawned:
            print("--- BOSS SPAWN! ---")
            
            # BigEnemy を生成する際、player オブジェクトを渡す
            boss = BigEnemy(game_speed_level, all_sprites, enemy_bullets_group, player) 
            
            all_sprites.add(boss)
            enemies_group.add(boss) 
            boss_spawned = True
            boss_warning_time = 0 
            
            # ボスが出たらザコ敵の出現を停止
            pygame.time.set_timer(ADD_ENEMY, 0)
            print("Stopping regular enemy spawns.")

        # プレイヤー以外のスプライトを更新 (プレイヤーは更新済みなので除外)
        sprites_to_update = [s for s in all_sprites if s != player]
        for sprite in sprites_to_update:
            sprite.update()
    else:
        # ゲームオーバー後も爆発エフェクトは更新する
        for sprite in all_sprites:
             if isinstance(sprite, Explosion):
                 sprite.update()

    # 4. 衝突判定 (ゲームオーバーでない場合のみ)
    if not game_over:

        enemies_destroyed_this_frame = 0

        # プレイヤーの(通常)弾と敵の衝突
        hits_normal = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, False) # 弾は消える
        for bullet, enemies_hit in hits_normal.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit(): # 敵の体力が0になったら
                    # ボスを倒した場合は大きな爆発
                    size = "large" if isinstance(enemy_hit, BigEnemy) else "normal"
                    explosion = Explosion(enemy_hit.rect.center, size)
                    
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill() # 敵を消す

        # プレイヤーの(チャージ)弾と敵の衝突
        charge_hits = pygame.sprite.groupcollide(player_charge_bullets_group, enemies_group, False, False) # 弾は消えない
        for bullet, enemies_hit in charge_hits.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit():
                    size = "large" if isinstance(enemy_hit, BigEnemy) else "normal"
                    explosion = Explosion(enemy_hit.rect.center, size)
                    
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill()

        # レベルアップ処理 (ボス出現中はレベルアップしない)
        if enemies_destroyed_this_frame > 0 and not boss_spawned:
            new_speed_level = score // 10
            if new_speed_level > game_speed_level:
                game_speed_level = new_speed_level
                print(f"--- SPEED LEVEL UP! Level: {game_speed_level} ---")
                level_up_message_time = pygame.time.get_ticks() # メッセージ表示開始

                # スポーンレートを計算（レベルごとに短縮、最低150ms）
                current_spawn_rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level)))
                pygame.time.set_timer(ADD_ENEMY, 0) # 古いタイマーをクリア
                pygame.time.set_timer(ADD_ENEMY, current_spawn_rate) # 新しいタイマーを設定
                print(f"New Spawn Rate: {current_spawn_rate} ms")

        # プレイヤーと敵の衝突
        player_enemy_hits = pygame.sprite.spritecollide(player, enemies_group, True) # 敵は消える
        if player_enemy_hits:
            if not game_over:
                game_over_time = pygame.time.get_ticks()
            explosion = Explosion(player.rect.center, "large")
            all_sprites.add(explosion)
            player.hide()
            game_over = True
            pygame.time.set_timer(ADD_ENEMY, 0) # 敵の出現を停止

        # プレイヤーと敵のビームの衝突
        player_beam_hits = pygame.sprite.spritecollide(player, enemy_bullets_group, True) # ビームは消す
        if player_beam_hits:
            if not game_over:
                game_over_time = pygame.time.get_ticks()
            explosion = Explosion(player.rect.center, "normal")
            all_sprites.add(explosion)
            player.hide()
            game_over = True
            pygame.time.set_timer(ADD_ENEMY, 0) # 敵の出現を停止

         ####プレイヤーと岩の衝突判定####
        player_iwa_hits = pygame.sprite.spritecollide(player, iwa_group, True) 
        if player_iwa_hits:
            explosion = Explosion(player.rect.center, "large") 
            all_sprites.add(explosion)
            player.hide() 
            game_over = True
            print("Game Over! (Collided with rock)")
            pygame.time.set_timer(ADD_ENEMY, 0)


    # 5. 描画
    screen.fill(BLACK)
    draw_stars(screen, stars, game_speed_level) # 背景
    all_sprites.draw(screen) # スプライト

    # UI描画
    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH - 10, 10, align="topright")
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")

    if not player.hidden:
        draw_charge_gauge(screen, player.charge_value, player.charge_max_time, player.rect.bottom)

    # レベルアップメッセージを描画 (1秒間)
    if now - level_up_message_time < 1000:
        if not game_over: # ゲームオーバーと重ならないように
            draw_text(screen, "LEVEL UP!", game_over_font, YELLOW, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")
            
    # ボス警告表示
    if boss_warning_time > 0 and not game_over:
        # 点滅処理 (0.5秒ごと)
        if (now - boss_warning_time) % 1000 < 500:
             draw_text(screen, "!! WARNING !!", boss_warning_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    # ゲームオーバー表示
    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    # 6. ゲームオーバー自動終了処理
    if game_over and game_over_time:
        if now - game_over_time > 3000: # 3秒経過したら終了
            running = False

    # 7. 画面のフリップ
    pygame.display.flip()

# --- 終了処理 ---
pygame.quit()
sys.exit()