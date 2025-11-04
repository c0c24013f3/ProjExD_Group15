import pygame
import sys
import random
import os

# --- スクリプトのパスを基準にディレクトリを設定 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")

# --- 定数 ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
FPS = 60

# 色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)

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

    # 爆発エフェクトの連番フレームを読み込む (例: explosion_00.png, 01.png...)
    EXPLOSION_FRAMES = []
    for i in range(10): # 00～09 の10フレームを想定
        frame_filename = os.path.join(fig_dir, f"explosion_{i:02d}.png")
        if os.path.exists(frame_filename):
            EXPLOSION_FRAMES.append(pygame.image.load(frame_filename).convert_alpha())
        else:
            # 連番が途切れた時点でループを抜ける
            if i == 0:
                # 最初のフレームすらない場合、explosion.gif にフォールバック
                print(f"Warning: Explosion frame {frame_filename} not found. Trying 'explosion.gif'.")
                try:
                    single_explosion_image = pygame.image.load(os.path.join(fig_dir, "explosion.gif")).convert_alpha()
                    EXPLOSION_FRAMES = [single_explosion_image]
                except pygame.error as gif_e:
                    print(f"Error loading explosion.gif: {gif_e}")
            break

    if not EXPLOSION_FRAMES: # 何も読み込めなかった場合
        print("Warning: No explosion images found. Using a fallback red circle.")
        # 代替として赤い円を作成
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

        self.all_sprites = all_sprites_ref
        self.enemy_bullets_group = enemy_bullets_group_ref

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
            enemy_bullet = EnemyBullet(self.rect.centerx, self.rect.bottom)
            self.all_sprites.add(enemy_bullet)
            self.enemy_bullets_group.add(enemy_bullet)

    def hit(self):
        """弾が当たった時の処理。体力を減らし、0以下ならTrue（破壊）を返す。"""
        self.health -= 1
        if self.health <= 0:
            return True # 破壊された
        return False # まだ生きている

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


# --- 敵のビームクラス ---
class EnemyBullet(pygame.sprite.Sprite):
    """敵の弾。下にまっすぐ飛ぶ。"""
    def __init__(self, x, y):
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

        self.speed_y = 7
        self.speed_x = 0

    def update(self):
        self.rect.y += self.speed_y
        self.rect.x += self.speed_x
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

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

# --- 敵 クラス (Enemy Class) --- ... (既存のコード) ...

# --- ボス敵 クラス (Boss Enemy Class) ---
class BossEnemy(pygame.sprite.Sprite):
    """
    ボスのステータスと挙動に関するクラス
    pygame.sprite.Spriteを継承
    """
    def __init__(self, all_sprites_ref=None, enemy_bullets_group_ref=None, player_ref=None):
        """
        引数1,all_sprites_ref: 全てのspriteのグループ
        引数2,enemy_bullets_group: player
        引数3,player_ref: ボスの弾のspriteのグループ
        """
        super().__init__()
        # プレイヤーの画像と敵の画像を流用 (適宜変更が必要な場合はファイルを準備してください)
        try:
            # fig/final_enemy.png の画像ファイル名を読み込む
            BOSS_IMAGE = pygame.image.load(os.path.join(fig_dir, "final_enemy.png")).convert_alpha()
        except pygame.error:
            # ファイルがない場合は、敵画像を流用するか、エラー処理を行う
            BOSS_IMAGE = ENEMY_IMAGE 
            print("Warning: 'final_enemy.png' not found. Using 'enemy.png' as fallback for Boss.")
            
        self.image = pygame.transform.scale(BOSS_IMAGE, (150, 150)) 
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2 # 画面上部の固定位置に配置
        self.rect.top = 20  # 画面上部から少し下げた位置
        
        self.all_sprites = all_sprites_ref 
        self.enemy_bullets_group = enemy_bullets_group_ref 
        self.player = player_ref 

        self.health = 50       # ライフを50に設定
        self.score_value = 50  # 撃破時のスコア
        
        self.is_active = False # ボスがアクティブになるまで攻撃しない
        
        # ボスの射撃間隔を短く設定 (例: 500ミリ秒)
        self.boss_shoot_delay = 500
        self.last_shot = pygame.time.get_ticks()

        # ボスは動かない
        self.speed_y = 0 

    def update(self):
        # 画面上部に固定するため、移動処理は不要
        
        if self.is_active:
            self.shoot()
            
    def shoot(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.boss_shoot_delay:
            self.last_shot = now
            # EnemyBullet に self.speed_y (0) と self.player を渡す
            # ボスビームは、敵の移動速度ではなく、固定の最低速度(7)が適用される
            enemy_bullet = EnemyBullet(self.rect.centerx - 20, self.rect.bottom, self.speed_y, self.player) 
            enemy_bullet_2 = EnemyBullet(self.rect.centerx + 20, self.rect.bottom, self.speed_y, self.player) 
            if self.all_sprites and self.enemy_bullets_group:
                self.all_sprites.add(enemy_bullet)
                self.enemy_bullets_group.add(enemy_bullet)
                self.all_sprites.add(enemy_bullet_2) # 2発同時に撃つ
                self.enemy_bullets_group.add(enemy_bullet_2)

    def hit(self):
        self.health -= 1
        if self.health <= 0:
            return True # 撃墜
        return False # 健在

# --- プレイヤー弾 クラス (Player Bullet Class) --- ... (既存のコード) ...

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

# --- ゲーム変数とスプライトグループの準備 ---
stars = create_stars(100)

all_sprites = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()
player_bullets_group = pygame.sprite.Group()
player_charge_bullets_group = pygame.sprite.Group() # チャージショット用
enemy_bullets_group = pygame.sprite.Group()

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

# ボス関連の変数 #
boss = None
BOSS_SPAWN_TIME = 30000
boss_spawned = False

# --- メインゲームループ (Main Game Loop) ---
start_time = pygame.time.get_ticks() #  ゲーム開始時刻を記録
# --- メインゲームループ ---
running = True
while running:
    # 1. フレームレートの制御
    clock.tick(FPS)

    # 2. イベント処理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == ADD_ENEMY and not game_over:
            new_enemy = Enemy(game_speed_level, all_sprites, enemy_bullets_group)
            all_sprites.add(new_enemy)
            enemies_group.add(new_enemy)

    keys = pygame.key.get_pressed()

    # ボスの出現をチェック #
    if not game_over and not boss_spawned:
        current_time = pygame.time.get_ticks()
        if current_time - start_time >= BOSS_SPAWN_TIME:
            boss = BossEnemy(all_sprites, enemy_bullets_group, player)
            all_sprites.add(boss)
            enemies_group.add(boss)

            pygame.time.set_timer(ADD_ENEMY, 0)
            boss_spawned = True

    # 3. 更新 (Update)

    # 3. 更新
    if not game_over:
        # プレイヤーの更新
        player.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)
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

        if boss and not boss.is_active and boss_spawned:
            boss.is_active = True
        
        enemies_destroyed_this_frame = 0 

        enemies_destroyed_this_frame = 0

        # プレイヤーの(通常)弾と敵の衝突
        hits_normal = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, False) # 弾は消える
        for bullet, enemies_hit in hits_normal.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit(): # 敵の体力が0になったら
                    explosion = Explosion(enemy_hit.rect.center, "normal")
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill() # 敵を消す

        # プレイヤーの(チャージ)弾と敵の衝突
        charge_hits = pygame.sprite.groupcollide(player_charge_bullets_group, enemies_group, False, False) # 弾は消えない
        for bullet, enemies_hit in charge_hits.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit():
                    explosion = Explosion(enemy_hit.rect.center, "normal")
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill()

        # レベルアップ処理
        if enemies_destroyed_this_frame > 0:
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


    # 5. 描画
    screen.fill(BLACK)
    draw_stars(screen, stars, game_speed_level) # 背景
    all_sprites.draw(screen) # スプライト

    # UI描画
    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH - 10, 10, align="topright")
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")

    if not player.hidden:
        draw_charge_gauge(screen, player.charge_value, player.charge_max_time, player.rect.bottom)

    now = pygame.time.get_ticks()

    # レベルアップメッセージを描画 (1秒間)
    if now - level_up_message_time < 1000:
        if not game_over: # ゲームオーバーと重ならないように
            draw_text(screen, "LEVEL UP!", game_over_font, YELLOW, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

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