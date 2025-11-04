import pygame
import sys
import random
import os # osモジュールをインポート
import math # 角度計算のために math をインポート

# --- スクリプトのパスを基準にディレクトリを設定 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fig_dir = os.path.join(script_dir, "fig")

# --- 定数 (Constants) ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
FPS = 60

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 色 (Colors)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)     
YELLOW = (255, 255, 0) 

# --- ゲームの初期化 (Game Initialization) ---
# ★★重要: 画像をロードする前に初期化と画面設定を完了させます★★
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

    # explosion.gif のアニメーションフレームを読み込む
    EXPLOSION_FRAMES = []
    # 例えば explosion_00.png, explosion_01.png, ... のように連番で保存されていると仮定
    for i in range(10): # 例として10フレーム (explosion_00.png から explosion_09.png)
        frame_filename = os.path.join(fig_dir, f"explosion_{i:02d}.png")
        if os.path.exists(frame_filename):
            EXPLOSION_FRAMES.append(pygame.image.load(frame_filename).convert_alpha())
        else:
            # フレームが見つからない場合、単一のgifファイルを読むか、エラーにする
            # 今回は単一のgifファイルを読み込み、後でそれを使うようにフォールバックする
            print(f"Warning: Explosion frame {frame_filename} not found. Trying to load explosion.gif as a single image.")
            try:
                single_explosion_image = pygame.image.load(os.path.join(fig_dir, "explosion.gif")).convert_alpha()
                EXPLOSION_FRAMES = [single_explosion_image] # 単一フレームとしてセット
            except pygame.error as gif_e:
                print(f"Error loading explosion.gif: {gif_e}")
            break # 最初のフレームが見つからない時点でループを抜ける
            
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
            bullet = PlayerBullet(self.rect.centerx, self.rect.top) 
            all_sprites.add(bullet)
            bullets_group.add(bullet)

    def hide(self):
        self.hidden = True
        self.kill() 


# --- 敵 クラス (Enemy Class) ---
class Enemy(pygame.sprite.Sprite):
    # player_ref を引数に追加
    def __init__(self, speed_level=0, all_sprites_ref=None, enemy_bullets_group_ref=None, player_ref=None):
        super().__init__()
        self.image = pygame.transform.scale(ENEMY_IMAGE, (40, 40)) 
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

        self.all_sprites = all_sprites_ref 
        self.enemy_bullets_group = enemy_bullets_group_ref 
        self.enemy_shoot_delay = random.randrange(1000, 2500) # 1秒〜2.5秒に変更
        self.last_shot = pygame.time.get_ticks()
        self.player = player_ref # プレイヤーへの参照を保存

        self.health = 1 
        self.score_value = 1 

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.top > SCREEN_HEIGHT + 10:
            self.kill()

        self.shoot()

    def shoot(self):
        now = pygame.time.get_ticks()
        if now - self.last_shot > self.enemy_shoot_delay:
            self.last_shot = now
            # EnemyBullet に self.speed_y と self.player を渡す
            enemy_bullet = EnemyBullet(self.rect.centerx, self.rect.bottom, self.speed_y, self.player) 
            if self.all_sprites and self.enemy_bullets_group:
                self.all_sprites.add(enemy_bullet)
                self.enemy_bullets_group.add(enemy_bullet)

    def hit(self):
        self.health -= 1
        if self.health <= 0:
            return True 
        return False 

# --- プレイヤー弾 クラス (Player Bullet Class) ---
class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # beam.png をスケーリングし、上下反転させる
        # 元画像をリサイズ (敵の弾と合わせる)
        raw_image = pygame.transform.scale(PLAYER_BULLET_IMAGE, (15, 15))
        # Y軸(垂直)方向に反転させて上向きにする
        self.image = pygame.transform.flip(raw_image, False, True) 
        self.rect = self.image.get_rect()
        self.rect.bottom = y
        self.rect.centerx = x
        self.speed_y = -10 

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0:
            self.kill()

# --- 敵のビーム クラス (Enemy Bullet Class) ---
class EnemyBullet(pygame.sprite.Sprite):
    # enemy_speed_y と player_obj を引数に追加
    def __init__(self, x, y, enemy_speed_y, player_obj):
        super().__init__()
        self.image = pygame.transform.scale(ENEMY_BULLET_IMAGE, (15, 15)) 
        self.rect = self.image.get_rect()
        self.rect.top = y
        self.rect.centerx = x
        
        # --- プレイヤーへの方向と速度を計算 ---
        
        # 1. ターゲット座標を設定
        target_x, target_y = self.rect.centerx, self.rect.bottom + 100 # デフォルト（真下）
        if player_obj and not player_obj.hidden:
            # プレイヤーが有効なら、プレイヤーの中心を狙う
            target_x = player_obj.rect.centerx
            target_y = player_obj.rect.centery

        # 2. 差分（ベクトル）を計算
        dx = target_x - self.rect.centerx
        dy = target_y - self.rect.centery
        
        # 3. 距離を計算 (math.hypot は 0 除算を回避するのに便利)
        distance = math.hypot(dx, dy)
        
        # 4. (要件1) 速度を計算 (敵機の2.5倍、ただし最低速度は7)
        total_speed = max(7.0, enemy_speed_y * 2.5)

        # 5. (要件2) 速度ベクトルを計算
        if distance == 0:
            # ターゲットが真上（あり得ないが念のため）なら真下に撃つ
            self.speed_x = 0
            self.speed_y = total_speed
        else:
            # ベクトルを正規化 (長さを1に) してから速度を掛ける
            self.speed_x = (dx / distance) * total_speed
            self.speed_y = (dy / distance) * total_speed
        # --- 計算ここまで ---

    def update(self):
        # 浮動小数点数で座標を更新（より滑らかになる）
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y
        # 画面外に出たら削除
        if self.rect.top > SCREEN_HEIGHT or self.rect.bottom < 0 or self.rect.left > SCREEN_WIDTH or self.rect.right < 0:
            self.kill()

# --- 爆発エフェクト クラス (Explosion Class) ---
class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, size="normal"):
        super().__init__()
        self.frames = EXPLOSION_FRAMES
        
        if size == "large":
            # 大きな爆発の場合、フレームを大きくスケール
            self.frames = [pygame.transform.scale(f, (90, 90)) for f in self.frames]
            self.frame_rate = 100 # フレーム表示速度 (ミリ秒)
        else:
            self.frames = [pygame.transform.scale(f, (60, 60)) for f in self.frames]
            self.frame_rate = 70 # フレーム表示速度 (ミリ秒)

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
                self.kill() # 全フレーム表示したら消滅
            else:
                center = self.rect.center # 中心座標を保持
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

# --- 星（背景）の管理 (Star Background Management) ---
def create_stars(number):
    stars = []
    for _ in range(number):
        star_x = random.randrange(0, SCREEN_WIDTH)
        star_y = random.randrange(0, SCREEN_HEIGHT)
        star_speed = random.randrange(1, 4) 
        star_size = random.randrange(1, 4)  
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

# --- テキスト描画用のヘルパー関数 (Helper function for drawing text) ---
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

# --- フォントの設定 ---
score_font = pygame.font.SysFont(None, 36) 
game_over_font = pygame.font.SysFont(None, 64, bold=True) 

# --- 背景用の星を作成 ---
stars = create_stars(100)

# --- スプライトグループの作成 (Sprite Groups) ---
all_sprites = pygame.sprite.Group()
enemies_group = pygame.sprite.Group() 
player_bullets_group = pygame.sprite.Group() 
enemy_bullets_group = pygame.sprite.Group() 

# --- プレイヤーの作成 ---
player = Player()
all_sprites.add(player)

# --- 敵を定期的に生成するためのカスタムイベント ---
ADD_ENEMY = pygame.USEREVENT + 1
initial_spawn_rate = 1000 
current_spawn_rate = initial_spawn_rate
pygame.time.set_timer(ADD_ENEMY, current_spawn_rate) 

# --- スコアとゲームレベル ---
score = 0
game_speed_level = 0
game_over = False

# ボス関連の変数 #
boss = None
BOSS_SPAWN_TIME = 30000
boss_spawned = False

# --- メインゲームループ (Main Game Loop) ---
start_time = pygame.time.get_ticks() #  ゲーム開始時刻を記録
running = True
while running:
    # 1. フレームレートの制御 (Control frame rate)
    clock.tick(FPS)

    # 2. イベント処理 (Event handling)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == ADD_ENEMY and not game_over:
            # Enemy生成時に player オブジェクトを渡す
            new_enemy = Enemy(game_speed_level, all_sprites, enemy_bullets_group, player)
            all_sprites.add(new_enemy)
            enemies_group.add(new_enemy)

    # 射撃 (スペースキーが押され続けているかチェック)
    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE] and not game_over:
        player.shoot(all_sprites, player_bullets_group)

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
    if not game_over:
        all_sprites.update()
    else:
        # ゲームオーバー後も爆発エフェクトは更新する
        # explosionオブジェクトがkillされるまでupdateを続ける
        for sprite in all_sprites:
             if isinstance(sprite, Explosion):
                 sprite.update()

    # 4. 衝突判定 (Collision Detection)
    if not game_over:

        if boss and not boss.is_active and boss_spawned:
            boss.is_active = True
        
        enemies_destroyed_this_frame = 0 

        # プレイヤーの弾と敵の衝突
        hits_normal = pygame.sprite.groupcollide(player_bullets_group, enemies_group, True, False) 
        for bullet, enemies_hit in hits_normal.items():
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
                
                current_spawn_rate = max(150, int(initial_spawn_rate * (0.9 ** game_speed_level))) 
                pygame.time.set_timer(ADD_ENEMY, 0) 
                pygame.time.set_timer(ADD_ENEMY, current_spawn_rate) 
                print(f"New Spawn Rate: {current_spawn_rate} ms")

        # プレイヤーと敵の衝突
        player_enemy_hits = pygame.sprite.spritecollide(player, enemies_group, True) 
        
        if player_enemy_hits:
            explosion = Explosion(player.rect.center, "large") 
            all_sprites.add(explosion)
            player.hide() 
            game_over = True
            print("Game Over! (Collided with enemy)")
            pygame.time.set_timer(ADD_ENEMY, 0) 

        # プレイヤーと敵のビームの衝突
        player_beam_hits = pygame.sprite.spritecollide(player, enemy_bullets_group, True) 
        if player_beam_hits:
            explosion = Explosion(player.rect.center, "normal") 
            all_sprites.add(explosion)
            player.hide() 
            game_over = True
            print("Game Over! (Hit by enemy beam)")
            pygame.time.set_timer(ADD_ENEMY, 0) 


    # 5. 描画 (Draw / Render)
    screen.fill(BLACK) 
    draw_stars(screen, stars, game_speed_level) 
    all_sprites.draw(screen) 

    # スコアを描画
    draw_text(screen, f"SCORE: {score}", score_font, WHITE, SCREEN_WIDTH - 10, 10, align="topright")
    
    # レベルを描画
    draw_text(screen, f"LEVEL: {game_speed_level}", score_font, WHITE, 10, 10, align="topleft")

    # ゲームオーバー表示
    if game_over:
        draw_text(screen, "GAME OVER", game_over_font, RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, align="center")

    # 6. 画面のフリップ (Flip display)
    pygame.display.flip()

# --- 終了処理 (Exit) ---
pygame.quit()
sys.exit()

