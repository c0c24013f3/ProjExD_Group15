import pygame
import sys
import random
import os

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
RED = (255, 50, 50)     
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0) 
GRAY = (100, 100, 100) 

# --- ゲームの初期化 (Game Initialization) ---
pygame.init()
pygame.font.init() 
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Xevious Style Shooter")
clock = pygame.time.Clock()


# --- 画像ファイルの読み込み (Load Images) ---
if not os.path.exists(fig_dir):
    os.makedirs(fig_dir)
    print(f"Warning: '{fig_dir}' directory not found. Created an empty one.")
    print("Please place 'koukaton.png', 'enemy.png', 'beam.png' and explosion frames (e.g., 'explosion_00.png', 'explosion_01.png'...) inside 'fig' folder.")

try:
    PLAYER_IMAGE = pygame.image.load(os.path.join(fig_dir, "koukaton.png")).convert_alpha()
    ENEMY_IMAGE = pygame.image.load(os.path.join(fig_dir, "enemy.png")).convert_alpha()
    # プレイヤーの弾も beam.png を読み込むようにする
    PLAYER_BULLET_IMAGE = pygame.image.load(os.path.join(fig_dir, "beam.png")).convert_alpha() 
    ENEMY_BULLET_IMAGE = pygame.image.load(os.path.join(fig_dir, "beam.png")).convert_alpha()

    # 爆発エフェクトの連番フレームを読み込む
    EXPLOSION_FRAMES = []
    # explosion_00.png, explosion_01.png, ... の連番を想定
    for i in range(10): # 10フレーム (00～09)
        frame_filename = os.path.join(fig_dir, f"explosion_{i:02d}.png")
        if os.path.exists(frame_filename):
            EXPLOSION_FRAMES.append(pygame.image.load(frame_filename).convert_alpha())
        else:
            # 連番フレームが見つからない場合
            if i == 0: 
                # 最初のフレーム(00)すらない場合、explosion.gifにフォールバック
                print(f"Warning: Explosion frame {frame_filename} not found. Trying to load explosion.gif as a single image.")
                try:
                    single_explosion_image = pygame.image.load(os.path.join(fig_dir, "explosion.gif")).convert_alpha()
                    EXPLOSION_FRAMES = [single_explosion_image]
                except pygame.error as gif_e:
                    print(f"Error loading explosion.gif: {gif_e}")
            break # 連番が途切れた時点でループを抜ける
            
    if not EXPLOSION_FRAMES: # 何も読み込めなかった場合
        print("Warning: No explosion images (frames or gif) found. Using a fallback red circle.")
        # フォールバックとして赤い円を作成
        fallback_image = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(fallback_image, RED, (30, 30), 30)
        EXPLOSION_FRAMES = [fallback_image]

except pygame.error as e:
    print(f"Error loading image: {e}")
    if "cannot convert without pygame.display initialized" in str(e):
        print("Pygame display was not initialized before image conversion.")
    print("Make sure 'koukaton.png', 'enemy.png', 'beam.png' and explosion frames (e.g., 'explosion_00.png', 'explosion_01.png'...) or 'explosion.gif' exist in 'fig' folder.")
    pygame.quit() 
    sys.exit() 


# --- プレイヤー クラス (Player Class) ---
class Player(pygame.sprite.Sprite):
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
        self.charge_max_time = 1000 # チャージ最大時間 (ms)
        self.charge_value = 0 # 現在のチャージ量

    def update(self, keys, all_sprites, bullets_group, charge_bullets_group):
        if self.hidden:
            return

        # 左右の移動 (Left/Right movement)
        self.speed_x = 0
        if keys[pygame.K_LEFT]:
            self.speed_x = -7
        if keys[pygame.K_RIGHT]:
            self.speed_x = 7
        self.rect.x += self.speed_x
        
        # 画面端の処理 (Screen boundary check)
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if self.rect.left < 0:
            self.rect.left = 0

        # Vキー: チャージと射撃
        now = pygame.time.get_ticks()

        if keys[pygame.K_v]:
            # Vキーが押されている
            if not self.is_charging:
                # 押された瞬間
                self.is_charging = True
                self.charge_start_time = now
                self.charge_value = 0
            else:
                # 押され続けている
                self.charge_value = now - self.charge_start_time
                if self.charge_value > self.charge_max_time:
                    self.charge_value = self.charge_max_time # 最大値でストップ
        
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
            
            # K_SPACE: 通常ショット (Vキー短押しとは別)
            if keys[pygame.K_SPACE]:
                 self.shoot(all_sprites, bullets_group, now)


    def shoot(self, all_sprites, bullets_group, now):
        """(通常)弾を発射する"""
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


# --- 敵 クラス (Enemy Class) ---
class Enemy(pygame.sprite.Sprite):
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None):
        super().__init__()
        self.image = pygame.transform.scale(ENEMY_IMAGE, (40, 40)) 
        self.rect = self.image.get_rect()
        self.rect.x = random.randrange(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randrange(-100, -40)
        
        # スピードレベルに基づいて速度を計算
        base_speed_min = 2
        base_speed_max = 5
        speed_increase = speed_level * 0.4 
        min_speed = int(base_speed_min + speed_increase)
        max_speed = int(base_speed_max + speed_increase)
        if max_speed <= min_speed:
            max_speed = min_speed + 1
            
        self.speed_y = random.randrange(min_speed, max_speed) # 落下速度

        self.all_sprites = all_sprites_ref 
        self.enemy_bullets_group = enemy_bullets_group_ref 
        
        self.enemy_shoot_delay = 2500 # (ms)
        
        # 最初の発射タイミングをランダムにする
        # (スポーン時に 0〜2500ms 経過したことにする)
        self.last_shot = pygame.time.get_ticks() - random.randrange(0, self.enemy_shoot_delay)


        self.health = 1 # 通常の敵の体力
        self.score_value = 1 # 倒したときのスコア

    def update(self):
        # まっすぐ下に移動
        self.rect.y += self.speed_y
        # 画面外に出たら削除
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

        # 敵のビーム発射
        self.shoot()

    def shoot(self):
        """敵がビームを発射する"""
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            enemy_bullet = EnemyBullet(self.rect.centerx, self.rect.bottom) 
            self.all_sprites.add(enemy_bullet)
            self.enemy_bullets_group.add(enemy_bullet)

    # def shoot_debug(self):
    #     """デバッグ用: 強制的にビームを発射する（タイマー無視）"""
    #     enemy_bullet = EnemyBullet(self.rect.centerx, self.rect.bottom) 
    #     self.all_sprites.add(enemy_bullet)
    #     self.enemy_bullets_group.add(enemy_bullet)
    #     # print("DEBUG: Enemy forced to shoot.")

    def hit(self):
        """弾が当たった時の処理"""
        self.health -= 1
        if self.health <= 0:
            return True # 破壊された
        return False # まだ生きている

# --- プレイヤー弾 クラス (Player Bullet Class) ---
class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # beam.png をスケーリング・回転
        raw_image = pygame.transform.scale(PLAYER_BULLET_IMAGE, (25, 15))
        self.image = pygame.transform.rotate(raw_image, 90) 
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -10 # 上に移動

    def update(self):
        self.rect.y += self.speed_y
        # 画面外に出たら削除
        if self.rect.bottom < 0:
            self.kill()

# --- プレイヤー・チャージショット クラス (Player Charge Shot Class) ---
class PlayerChargeShot(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 元のビーム画像を大きくスケーリング
        raw_image = pygame.transform.scale(PLAYER_BULLET_IMAGE, (120, 60))
        # 左に90度回転
        self.image = pygame.transform.rotate(raw_image, 90)
        
        # 色を黄色に変更 (BLEND_RGBA_MULT)
        color_surface = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        color_surface.fill(RED)
        self.image.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT) 

        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -12 # 通常弾より速く

    def update(self):
        self.rect.y += self.speed_y
        # 画面外に出たら削除
        if self.rect.bottom < 0:
            self.kill()


# --- 敵のビーム クラス (Enemy Bullet Class) ---
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # beam.png をスケーリング・回転
        raw_image = pygame.transform.scale(ENEMY_BULLET_IMAGE, (30, 15))
        raw_image_rotated = pygame.transform.rotate(raw_image, -90)
        self.image = raw_image_rotated.copy() # .copy() で元画像保護
        
        # 色を変更 (BLEND_RGBA_MULT)
        color_surface = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        color_surface.fill(YELLOW)
        self.image.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        self.rect = self.image.get_rect()
        self.rect.top = y
        self.rect.centerx = x
        
        self.speed_y = 7 # 真下に移動
        self.speed_x = 0

    def update(self):
        self.rect.y += self.speed_y
        self.rect.x += self.speed_x
        
        # 画面外に出たら削除
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

# --- 爆発エフェクト クラス (Explosion Class) ---
class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, size="normal"):
        super().__init__()
        # EXPLOSION_FRAMES をコピーして使用 (元リスト保護のため)
        self.frames = list(EXPLOSION_FRAMES) 
        
        if size == "large":
            # 大きな爆発
            self.frames = [pygame.transform.scale(f, (90, 90)) for f in self.frames]
            self.frame_rate = 100 # フレーム表示速度 (ms)
        else:
            # 通常の爆発
            self.frames = [pygame.transform.scale(f, (60, 60)) for f in self.frames]
            self.frame_rate = 70 # フレーム表示速度 (ms)

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
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.kill() # 全フレーム表示したら消滅
            else:
                center = self.rect.center # 中心座標を保持
                self.image = self.frames[self.current_frame]
                self.rect = self.image.get_rect(center=center)


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

def draw_stars(surface, stars, speed_level=0):
    """星を描画し、スクロールさせる"""
    # スピードレベルに応じて背景のスクロール速度も上げる
    speed_modifier = 1.0 + speed_level * 0.15 
    
    for star in stars:
        # 星を描画 (star[3] = size)
        pygame.draw.circle(surface, WHITE, (star[0], star[1]), star[3])
        # 星を下に移動 (star[2] = speed)
        star[1] += star[2] * speed_modifier
        
        # 画面外に出たら、上に戻す
        if star[1] > SCREEN_HEIGHT:
            star[1] = 0
            star[0] = random.randrange(0, SCREEN_WIDTH)

# --- テキスト描画用のヘルパー関数 (Helper function for drawing text) ---
def draw_text(surface, text, font, color, x, y, align="topright"):
    text_surface = font.render(text, True, color) # Trueはアンチエイリアス
    text_rect = text_surface.get_rect()
    if align == "topright":
        text_rect.topright = (x, y) # 右上を基準に配置
    elif align == "center":
        text_rect.center = (x, y) # 中央を基準に配置
    elif align == "topleft":
        text_rect.topleft = (x, y) # 左上を基準に配置
    surface.blit(text_surface, text_rect)

# --- チャージゲージ描画用のヘルパー関数 ---
def draw_charge_gauge(surface, current_charge, max_charge, player_bottom_y):
    """プレイヤーの下にチャージゲージを描画する"""
    if current_charge > 0: # チャージ中の時だけ描画
        gauge_width = 60
        gauge_height = 8
        x_pos = (SCREEN_WIDTH - gauge_width) // 2
        y_pos = player_bottom_y + 10 # プレイヤーの少し下

        # ゲージの溜まり具合を計算 (0.0 ~ 1.0)
        fill_ratio = current_charge / max_charge
        fill_width = int(fill_ratio * gauge_width)

        outline_rect = pygame.Rect(x_pos, y_pos, gauge_width, gauge_height)
        fill_rect = pygame.Rect(x_pos, y_pos, fill_width, gauge_height)

        # ゲージの色 (溜まるまでは緑、MAXで黄色)
        color = YELLOW if fill_ratio >= 1.0 else GREEN
        
        pygame.draw.rect(surface, GRAY, outline_rect) # ゲージ背景
        pygame.draw.rect(surface, color, fill_rect) # ゲージ本体
        pygame.draw.rect(surface, WHITE, outline_rect, 1) # ゲージ縁


# --- フォントの設定 ---
score_font = pygame.font.SysFont(None, 36) 
game_over_font = pygame.font.SysFont(None, 64, bold=True) 

# --- 背景用の星を作成 ---
stars = create_stars(100)

# --- スプライトグループの作成 (Sprite Groups) ---
all_sprites = pygame.sprite.Group()
enemies_group = pygame.sprite.Group() 
player_bullets_group = pygame.sprite.Group() 
player_charge_bullets_group = pygame.sprite.Group() # チャージショット用
enemy_bullets_group = pygame.sprite.Group() 

# --- プレイヤーの作成 ---
player = Player()
all_sprites.add(player)

# --- 敵を定期的に生成するためのカスタムイベント ---
ADD_ENEMY = pygame.USEREVENT + 1
initial_spawn_rate = 1000 # 最初のスポーンレート (ms)
current_spawn_rate = initial_spawn_rate
pygame.time.set_timer(ADD_ENEMY, current_spawn_rate) # (ms) ごとにイベント発生

# --- スコアとゲームレベル ---
score = 0
game_speed_level = 0
game_over = False
game_over_time = None 
level_up_message_time =0

# --- メインゲームループ (Main Game Loop) ---
running = True
while running:
    # 1. フレームレートの制御 (Control frame rate)
    clock.tick(FPS)

    # 2. イベント処理 (Event handling)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # # Enterキーでのデバッグ発射
        # elif event.type == pygame.KEYDOWN:
        #     if event.key == pygame.K_RETURN:
        #         print("DEBUG: Enter pressed. Forcing all enemies to shoot.")
        #         for enemy in enemies_group:
        #             enemy.shoot_debug()
        
        elif event.type == ADD_ENEMY and not game_over:
            new_enemy = Enemy(game_speed_level, all_sprites, enemy_bullets_group)
            all_sprites.add(new_enemy)
            enemies_group.add(new_enemy)

    keys = pygame.key.get_pressed()


    # 3. 更新 (Update)
    if not game_over:
        # プレイヤーの更新 (キー入力とグループ情報を渡す)
        player.update(keys, all_sprites, player_bullets_group, player_charge_bullets_group)
        # プレイヤー以外のスプライトを更新
        for sprite in all_sprites:
            if sprite != player: # プレイヤーは更新済みなので除外
                sprite.update()
    else:
        # ゲームオーバー後も爆発エフェクトは更新する
        for sprite in all_sprites:
             if isinstance(sprite, Explosion):
                 sprite.update()

    # 4. 衝突判定 (Collision Detection)
    if not game_over:
        
        enemies_destroyed_this_frame = 0 

        # プレイヤーの(通常)弾と敵の衝突
        hits_normal = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, False) # 弾は消える、敵はまだ消えない
        for bullet, enemies_hit in hits_normal.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit(): # hit() が True (体力0) になったら
                    explosion = Explosion(enemy_hit.rect.center, "normal")
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill() # 敵を消す
        
        # ★追加: プレイヤーの(チャージ)弾と敵の衝突
        # 弾(False)は消えない、敵(False)もまだ消えない
        charge_hits = pygame.sprite.groupcollide(player_charge_bullets_group, enemies_group, False, False) 
        for bullet, enemies_hit in charge_hits.items():
            for enemy_hit in enemies_hit:
                if enemy_hit.hit(): # hit() が True (体力0) になったら
                    explosion = Explosion(enemy_hit.rect.center, "normal")
                    all_sprites.add(explosion)
                    score += enemy_hit.score_value
                    enemies_destroyed_this_frame += 1
                    enemy_hit.kill() # 敵を消す
                
        # レベルアップ処理
        if enemies_destroyed_this_frame > 0:
            new_speed_level = score // 10
            if new_speed_level > game_speed_level:
                game_speed_level = new_speed_level
                print(f"--- SPEED LEVEL UP! Level: {game_speed_level} ---")
                
                level_up_message_time = pygame.time.get_ticks() # ★追加: メッセージ表示開始時刻を記録
                
                # スポーンレートを計算（レベルごとに90%に減少、最低150ms）
                current_spawn_rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level))) 
                pygame.time.set_timer(ADD_ENEMY, 0) # 古いタイマーをクリア
                pygame.time.set_timer(ADD_ENEMY, current_spawn_rate) # 新しいタイマーを設定
                print(f"New Spawn Rate: {current_spawn_rate} ms")

        # プレイヤーと敵の衝突
        player_enemy_hits = pygame.sprite.spritecollide(player, enemies_group, True) # 敵は消える
        
        if player_enemy_hits:
            if not game_over: # ★追加: 最初のゲームオーバー時のみ時刻を記録
                game_over_time = pygame.time.get_ticks()
            explosion = Explosion(player.rect.center, "large") # プレイヤーはやられたら大きな爆発
            all_sprites.add(explosion)
            player.hide() # プレイヤーを隠す
            game_over = True
            print("Game Over! (Collided with enemy)")
            pygame.time.set_timer(ADD_ENEMY, 0) # ゲームオーバーなら敵の出現を停止

        # プレイヤーと敵のビームの衝突
        player_beam_hits = pygame.sprite.spritecollide(player, enemy_bullets_group, True) # ビームは消す
        if player_beam_hits:
            if not game_over: # ★追加: 最初のゲームオーバー時のみ時刻を記録
                game_over_time = pygame.time.get_ticks()
            explosion = Explosion(player.rect.center, "normal") # ビームなら通常の爆発
            all_sprites.add(explosion)
            player.hide() # プレイヤーを隠す
            game_over = True
            print("Game Over! (Hit by enemy beam)")
            pygame.time.set_timer(ADD_ENEMY, 0) # ゲームオーバーなら敵の出現を停止


    # 5. 描画 (Draw / Render)
    screen.fill(BLACK) # 画面を黒で塗りつぶす
    draw_stars(screen, stars, game_speed_level) # 星空を描画
    all_sprites.draw(screen) # 全てのスプライトを描画

    # スコアを描画
    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH - 10, 10, align="topright")
    
    # レベルを描画
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")

    # チャージゲージを描画 (プレイヤーが生存中のみ)
    if not player.hidden:
        draw_charge_gauge(screen, player.charge_value, player.charge_max_time, player.rect.bottom)

         # メッセージ描画と自動終了判定のための現在時刻
    now = pygame.time.get_ticks()

    # ★追加: レベルアップメッセージを描画
    if now - level_up_message_time < 1000: # 1秒間表示
        # ゲームオーバーメッセージと重ならないようにする
        if not game_over: 
            draw_text(screen, "LEVEL UP!", game_over_font, YELLOW, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")


    # ゲームオーバー表示
    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    # 6. ゲームオーバー自動終了処理
    if game_over and game_over_time:
        now = pygame.time.get_ticks()
        # 3秒 (3000ms) 経過したら終了
        if now - game_over_time > 3000:
            running = False

    # 7. 画面のフリップ (Flip display)
    pygame.display.flip()

# --- 終了処理 (Exit) ---
pygame.quit()
sys.exit()