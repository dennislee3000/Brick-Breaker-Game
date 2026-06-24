import array
import io
import math
import os
import random
import sys
import pygame
import warnings
import asyncio  # Required for browser loop integration via pygbag

# Suppress harmless Python 3.13 deprecation warnings inside Pygame's setup modules
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")

# =====================================================================
# PATH WRAPPER & CORE SUBSYSTEM INITIALIZATION
# =====================================================================
def resource_path(relative_path):
    """Get absolute path to resource, works for dev, PyInstaller, and Pygbag."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        # Target the absolute folder containing main.py
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Standardize forward slashes so paths don't break in browsers!
    return os.path.join(base_path, relative_path).replace("\\", "/")

# 🌟 WEB ACCELERATION BUFFER: Lower buffer processing overhead for canvas rendering
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
pygame.init()
pygame.mixer.init()

# Game Display Layout
SCREEN_WIDTH = 820
SCREEN_HEIGHT = 600
FPS = 60

# Colors (RGB format)
COLOR_BG = (15, 15, 25)
COLOR_PADDLE = (52, 152, 219)
COLOR_BALL = (236, 240, 241)
COLOR_POWERUP = (46, 204, 113)
COLOR_TEXT = (255, 255, 255)

# Tiered Brick Colors
COLORS_BRICKS = [
    (231, 76, 60),    # Row 0-1: Red
    (230, 126, 34),   # Row 2-3: Orange
    (241, 196, 15)    # Row 4: Yellow
]

# Set up the Screen, Clock, and Fonts
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Progressive Brick Breaker by Dennis Lee")
clock = pygame.time.Clock()

# Dynamic system text loaders
font = pygame.font.SysFont("NanumGothic.ttf", 24, bold=True)
large_font = pygame.font.SysFont("NanumGothic.ttf", 64, bold=True)

# =====================================================================
# AUDIO CONTROLLER & PLAYLIST ENGINE (FULLY CACHED ON STARTUP)
# =====================================================================
music_folder = resource_path("songs")

playlist_paths = []
cached_songs = {}        # 🌟 NEW: Holds pre-loaded Sound objects in RAM
shuffled_playlist = []   # Tracks the randomized queue order
current_track_index = 0
current_channel = None   
is_music_stopping_purposely = False

if os.path.exists(music_folder):
    playlist_paths = [
        os.path.join(music_folder, f) 
        for f in os.listdir(music_folder) 
        if f.lower().endswith(('.ogg'))
    ]
    

    # 🌟 NEW: Pre-cache ALL songs on startup to eliminate mid-game disk lag!
    print("⏳ Pre-loading soundtrack into memory...")
    for path in playlist_paths:
        try:
            filename = os.path.basename(path)
            cached_songs[path] = pygame.mixer.Sound(path)
            print(f"✅ Loaded: {filename}")
        except Exception as e:
            print(f"❌ Failed to pre-load {os.path.basename(path)}: {e}")

def reshuffle_playlist():
    """Creates a newly randomized copy of the playlist paths."""
    global shuffled_playlist
    if not playlist_paths:
        return
    shuffled_playlist = playlist_paths.copy()
    random.shuffle(shuffled_playlist)
    current_track_index = 0  # Reset index back to 0 whenever we shuffle
    print("🔀 Playlist shuffled and renewed!")

# Initialize the shuffle order on startup
reshuffle_playlist()

def play_track(index):
    """Plays a pre-cached soundtrack instantly out of RAM."""
    global current_track_index, shuffled_playlist, current_channel, is_music_stopping_purposely
    
    if not shuffled_playlist:
        reshuffle_playlist()
    if not shuffled_playlist:
        print("⚠️ Warning: No audio tracks available in the folder.")
        return

    if index >= len(shuffled_playlist) or index < 0:
        index = 0
        
    current_track_index = index
    track_path = shuffled_playlist[current_track_index]
    
    try:
        is_music_stopping_purposely = False
        
        # Force stop anything playing on our dedicated music channel
        if current_channel is not None:
            current_channel.stop()
            
        # 🌟 FIX: Pull the track from RAM instead of calling pygame.mixer.Sound(track_path)
        if track_path in cached_songs:
            audio_sound = cached_songs[track_path]
            current_channel = pygame.mixer.find_channel()
            if current_channel:
                current_channel.play(audio_sound)
                print(f"🎵 Now playing (Zero Lag): {os.path.basename(track_path)}")
        else:
            print(f"⚠️ Track missing from cache: {os.path.basename(track_path)}")
            next_track()
            
    except Exception as e:
        print(f"❌ Failed to play track {os.path.basename(track_path)}: {e}")
        next_track()

def next_track():
    """Advances cleanly to the next track in the queue."""
    global current_track_index, shuffled_playlist
    if shuffled_playlist:
        next_index = current_track_index + 1
        if next_index >= len(shuffled_playlist):
            reshuffle_playlist()
            next_index = 0
            
        play_track(next_index)

def check_music_status():
    """Monitors the dedicated channel status. Automatically transitions when a song finishes."""
    global current_channel, is_music_stopping_purposely
    if not is_music_stopping_purposely and current_channel is not None:
        # If the sound has finished playing naturally, jump to the next track
        if not current_channel.get_busy():
            next_track()

# Start the very first track automatically on startup
play_track(current_track_index)

# ===================================================================== #
# PROCEDURAL SYNTH SOUND GENERATION                                     #
# ===================================================================== #
def generate_synth_sound(freq_start, freq_end, duration_ms, type_wave="square"):
    sample_rate = 44100
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    buf = array.array('h', [0] * num_samples)
    for i in range(num_samples):
        t = float(i) / sample_rate
        current_freq = freq_start + (freq_end - freq_start) * (t / (duration_ms / 1000.0))
        if type_wave == "square":
            val = 16000 if math.sin(2.0 * math.pi * current_freq * t) > 0 else -16000
        else:
            val = int(16000 * math.sin(2.0 * math.pi * current_freq * t))
        if i > num_samples - 1000:
            val = int(val * ((num_samples - i) / 1000.0))
        buf[i] = val
    sound = pygame.mixer.Sound(buffer=buf)
    sound.set_volume(0.3)
    return sound

sound_paddle = generate_synth_sound(400, 600, 80, "sine")
sound_wall = generate_synth_sound(300, 300, 50, "sine")
sound_brick = generate_synth_sound(600, 200, 100, "square")
sound_powerup = generate_synth_sound(400, 1200, 250, "sine")
sound_level_up = generate_synth_sound(500, 1500, 400, "sine")

# ===================================================================== #
# GAME ENTITIES AND DYNAMIC VARIABLE POOLS                             #
# ===================================================================== #
PADDLE_BASE_WIDTH = 120
paddle_width = PADDLE_BASE_WIDTH
paddle_height = 15
paddle_speed = 800.0
paddle_x = float((SCREEN_WIDTH // 2) - (paddle_width // 2))
paddle_rect = pygame.Rect(int(paddle_x), SCREEN_HEIGHT - 40, paddle_width, paddle_height)

# =====================================================================
# INITIALIZE MASTER BALL LIST (REPLACES OLD SINGLE BALL VARIABLES)
# =====================================================================
ball_radius = 8 
ball_base_speed_x = 300.0
ball_base_speed_y = -360.0

# This list replaces ball_speed_x, ball_speed_y, ball_x, ball_y, and ball_rect
balls = []

def spawn_ball(x, y, vx, vy):
    """Helper function to cleanly inject a new ball into the game engine."""
    balls.append({
        "x": float(x),
        "y": float(y),
        "vx": float(vx),
        "vy": float(vy),
        "rect": pygame.Rect(int(x), int(y), ball_radius * 2, ball_radius * 2)
    })

# Spawn your very first starting ball right in the center of the screen
spawn_ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, ball_base_speed_x, ball_base_speed_y)

score = 0
lives = 5
current_level = 1
game_state = "PLAYING"
powerup_timer = 0
powerups = []
bricks = []

def generate_bricks():
    bricks.clear()
    brick_rows = 5
    brick_cols = 10
    brick_width = 70
    brick_height = 25
    brick_offset_x = 45
    brick_offset_y = 80
    brick_gap = 5
    for row in range(brick_rows):
        for col in range(brick_cols):
            x = brick_offset_x + col * (brick_width + brick_gap)
            y = brick_offset_y + row * (brick_height + brick_gap)
            if row == 0 or row == 1:
                color = COLORS_BRICKS[0]
                points = 30
            elif row == 2 or row == 3:
                color = COLORS_BRICKS[1]
                points = 20
            else:
                color = COLORS_BRICKS[2]
                points = 10
            bricks.append({
                "rect": pygame.Rect(x, y, brick_width, brick_height),
                "color": color,
                "points": points
            })
def reset_entire_game():
    global score, lives, current_level, game_state, ball_speed_x, ball_speed_y
    global paddle_width, paddle_x, paddle_rect, powerup_timer, ball_x, ball_y, ball_rect, bricks
    
    score = 0
    lives = 7
    current_level = 1
    game_state = "PLAYING"
    powerup_timer = 0
    powerups.clear()
    
    paddle_width = PADDLE_BASE_WIDTH
    paddle_x = float((SCREEN_WIDTH // 2) - (paddle_width // 2))
    paddle_rect = pygame.Rect(int(paddle_x), SCREEN_HEIGHT - 40, paddle_width, paddle_height)
    
    ball_x = float(SCREEN_WIDTH // 2)
    ball_y = float(SCREEN_HEIGHT // 2)
    ball_speed_x = ball_base_speed_x
    ball_speed_y = ball_base_speed_y
    ball_rect = pygame.Rect(int(ball_x), int(ball_y), ball_radius * 2, ball_radius * 2)
    
    generate_bricks()
    play_track(0)

# =====================================================================
# MAIN GAME EXECUTION THREAD (WEB COMPATIBLE & MULTI-BALL EQUIPPED)
# =====================================================================
async def main():
    # 🌟 UPDATED GLOBAL SCENARIO MATRIX
    global score, lives, current_level, game_state, balls
    global paddle_width, paddle_x, paddle_rect, powerup_timer
    global is_music_stopping_purposely 

    # Kick off the very first brick map generation before running loops
    generate_bricks()
    running = True

    while running:
        # Hard-lock delta time step to smooth out browser-based frame drops
        clock.tick(FPS)
        dt = 1.0 / FPS

        # Automatically monitors when a song finishes playing in RAM cache
        check_music_status()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if game_state == "GAMEOVER" and event.key == pygame.K_r:
                    # Reset game details completely
                    reset_entire_game() 
                    
                    # 🌟 MULTI-BALL RETRY CLEANUP: Clear any ghost arrays and spawn 1 ball
                    balls.clear()
                    spawn_ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, ball_base_speed_x, ball_base_speed_y)
                    
                    is_music_stopping_purposely = False
                    play_track(current_track_index)

        # CORE GAME ENGINE CALCULATION MATRIX
        if game_state == "PLAYING":
            # Powerup dynamic countdown timers
            if powerup_timer > 0:
                powerup_timer -= dt
                if powerup_timer <= 0:
                    center_x = paddle_rect.centerx
                    paddle_width = PADDLE_BASE_WIDTH
                    paddle_rect = pygame.Rect(center_x - paddle_width//2, paddle_rect.y, paddle_width, paddle_height)
                    paddle_x = float(paddle_rect.x) 

            # User Keyboard paddle checks
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] and paddle_rect.left > 0:
                paddle_x -= paddle_speed * dt
            if keys[pygame.K_RIGHT] and paddle_rect.right < SCREEN_WIDTH:
                paddle_x += paddle_speed * dt
            paddle_rect.x = int(paddle_x)

            # 🌟 MASTER MULTI-BALL CALCULATION LOOP
            for ball in balls[:]:
                # Apply vector movement updates purely using floating-point math
                ball["x"] += ball["vx"] * dt
                ball["y"] += ball["vy"] * dt
                ball["rect"].topleft = (int(ball["x"]), int(ball["y"]))

                # Wall Bounces
                if ball["x"] <= 0:
                    ball["x"] = 0.0
                    ball["vx"] = abs(ball["vx"])
                    sound_wall.play()
                elif ball["x"] + (ball_radius * 2) >= SCREEN_WIDTH:
                    ball["x"] = float(SCREEN_WIDTH - (ball_radius * 2))
                    ball["vx"] = -abs(ball["vx"])
                    sound_wall.play()

                if ball["y"] <= 0:
                    ball["y"] = 0.0
                    ball["vy"] = abs(ball["vy"])
                    sound_wall.play()

                # Bottom Out-Of-Bounds Drop Check
                if ball["y"] + (ball_radius * 2) >= SCREEN_HEIGHT:
                    balls.remove(ball)  # Delete this specific out-of-bounds ball
                    
                    # If NO balls are left anywhere on the canvas screen, drop a life!
                    if len(balls) == 0:
                        lives -= 1
                        if lives <= 0:
                            game_state = "GAMEOVER"
                            is_music_stopping_purposely = True
                            if current_channel is not None:
                                current_channel.stop()
                        else:
                            # Still have lives? Respawn exactly one starting center ball
                            spawn_ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, ball_base_speed_x, ball_base_speed_y)
                    continue # Escape calculations since this ball is fully deleted

                # Paddle Collision Logic
                if ball["rect"].colliderect(paddle_rect) and ball["vy"] > 0:
                    # Prevent standard bumper snapping/sticking loops
                    ball["y"] = float(paddle_rect.top - (ball_radius * 2))
                    sound_paddle.play()
                    
                    paddle_center = paddle_rect.x + (paddle_width / 2)
                    ball_center = ball["x"] + ball_radius
                    hit_position = (ball_center - paddle_center) / (paddle_width / 2)
                    
                    # Restrict max reflection factor to 0.75 (approx 45 degrees max)
                    hit_position = max(-0.75, min(0.75, hit_position))
                    
                    speed_multiplier = 1.0 + (current_level - 1) * 0.15
                    speed_total = math.hypot(ball_base_speed_x, ball_base_speed_y) * speed_multiplier
                    
                    ball["vx"] = hit_position * (480 * speed_multiplier)
                    
                    # Force healthy vertical exit velocity vectors
                    min_vertical_speed = speed_total * 0.5
                    calculated_speed_y = math.sqrt(max(10000, speed_total**2 - ball["vx"]**2))
                    ball["vy"] = -abs(max(min_vertical_speed, calculated_speed_y))

                # Brick Matrix Collisions
                for brick in bricks[:]:
                    b_rect = brick["rect"]
                    if ball["rect"].colliderect(b_rect):
                        sound_brick.play()
                        
                        overlap_left = ball["rect"].right - b_rect.left
                        overlap_right = b_rect.right - ball["rect"].left
                        overlap_top = ball["rect"].bottom - b_rect.top
                        overlap_bottom = b_rect.bottom - ball["rect"].top
                        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
                        
                        if min_overlap == overlap_left and ball["vx"] > 0:
                            ball["vx"] = -ball["vx"]
                        elif min_overlap == overlap_right and ball["vx"] < 0:
                            ball["vx"] = -ball["vx"]
                        elif min_overlap == overlap_top and ball["vy"] > 0:
                            ball["vy"] = -ball["vy"]
                        elif min_overlap == overlap_bottom and ball["vy"] < 0:
                            ball["vy"] = -ball["vy"]
                            
                        score += brick["points"]
                        
                        # 20% Chance drop capsule item
                        if random.random() < 0.20:
                            powerups.append(pygame.Rect(b_rect.centerx - 10, b_rect.centery, 20, 12))
                        bricks.remove(brick)
                        break # Process only one bounce mapping update calculation per frame tick

            # =============================================================
            # LEVEL ADVANCEMENT BLOCK
            # =============================================================
            if len(bricks) == 0:
                sound_level_up.play()
                current_level += 1
                lives += 5
                powerups.clear()
                
                # 🌟 MULTI-BALL LEVEL RESET: Wipe chaos array and cleanly spawn 1 track ball
                balls.clear()
                speed_multiplier = 1.0 + (current_level - 1) * 0.15
                spawn_ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, ball_base_speed_x * speed_multiplier, ball_base_speed_y * speed_multiplier)
                
                generate_bricks()
                paddle_x = float((SCREEN_WIDTH // 2) - (paddle_width // 2))
                paddle_rect.x = int(paddle_x)

            # =====================================================================
            # POWERUP UPDATES AND COLLECTION CHECKS
            # =====================================================================
            for p_up in powerups[:]:
                p_up.y += int(180 * dt)
                if p_up.colliderect(paddle_rect):
                    sound_powerup.play()
                    
                    # 🌟 POWERUP MULTI-BALL TRIGGER: Spawns 2 additional balls from your paddle!
                    speed_multiplier = 1.0 + (current_level - 1) * 0.15
                    spawn_ball(paddle_rect.centerx, paddle_rect.top - 20, -160 * speed_multiplier, -320 * speed_multiplier)
                    spawn_ball(paddle_rect.centerx, paddle_rect.top - 20, 160 * speed_multiplier, -320 * speed_multiplier)
                    
                    # Apply Paddle Widening side effect bonus
                    powerup_timer = 5.0
                    if paddle_width == PADDLE_BASE_WIDTH:
                        center_x = paddle_rect.centerx
                        paddle_width = PADDLE_BASE_WIDTH + 50
                        paddle_rect = pygame.Rect(center_x - paddle_width // 2, paddle_rect.y, paddle_width, paddle_height)
                        paddle_x = float(paddle_rect.x) 
                    powerups.remove(p_up)
                elif p_up.top > SCREEN_HEIGHT:
                    powerups.remove(p_up)

    # --- GRAPHICS & RENDERING ENGINE ---
        screen.fill(COLOR_BG)
        pygame.draw.rect(screen, COLOR_PADDLE, paddle_rect, border_radius=4)
        
        # 🌟 MULTI-BALL DRAWING HOOK: Draw every single active ball smoothly using floats
        for ball in balls:
            pygame.draw.circle(screen, COLOR_BALL, (int(ball["x"] + ball_radius), int(ball["y"] + ball_radius)), ball_radius)
            
        for brick in bricks:
            pygame.draw.rect(screen, brick["color"], brick["rect"], border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0), brick["rect"], 1)
        for p_up in powerups:
            pygame.draw.rect(screen, COLOR_POWERUP, p_up, border_radius=4)

        # =====================================================================
        # GRAPHICS RENDERING SYSTEM: HUD & GAME STATE OVERLAYS
        # =====================================================================
        # Text labels
        score_text = font.render(f"Score: {score}", True, COLOR_TEXT)
        level_text = font.render(f"Level: {current_level}", True, COLOR_TEXT)
        lives_text = font.render(f"Lives: {lives}", True, COLOR_TEXT)

        # Dynamically calculate positions using asset width to prevent overlapping text margins
        screen.blit(score_text, (25, 20))
        screen.blit(level_text, (SCREEN_WIDTH // 2 - level_text.get_width() // 2, 20))
        screen.blit(lives_text, (SCREEN_WIDTH - lives_text.get_width() - 25, 20))

        # Render active modification timer directly underneath the main layout HUD
        if powerup_timer > 0:
            timer_text = font.render(f"Bonus in progress...: {math.ceil(powerup_timer)} Second", True, COLOR_POWERUP)
            screen.blit(timer_text, (SCREEN_WIDTH // 2 - timer_text.get_width() // 2, 55))

        # Render Active Overlay Menus
        if game_state == "GAMEOVER":
            over_text = large_font.render("It's over man. Try again?", True, (231, 76, 60))
            restart_text = font.render("Then press 'R' ", True, COLOR_TEXT)
            
            # Perfect screen centering alignment matrix
            screen.blit(over_text, (SCREEN_WIDTH // 2 - over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

        # Push buffered frame configurations to active viewport surface
        pygame.display.flip()

        # 🌟 MANDATORY FOR WEB EXECUTION: This handles non-blocking window sleep.
        # Yields control back to the browser framework momentarily to process frames.
        await asyncio.sleep(0)

    # Engine teardown clean loop execution sequence
    pygame.quit()
    sys.exit()

# Run the execution wrapper cleanly if script is executed directly
if __name__ == "__main__":
    asyncio.run(main())