import tkinter as tk
import math
import random
root = tk.Tk()
root.title("Midnight Mayhem")
canvas = tk.Canvas(root, width=1000, height=1000, bg="#550000")
canvas.pack()
# Obstacles: list of (x1, y1, x2, y2)
obstacles = [
    (0, 0, 300, 300),
    (700, 0, 1000, 300),
    (0, 700, 300, 1000),
    (700, 700, 1000, 1000),

]
player_radius = 30
player_x = 500
player_y = 900

enemies = []
# Bullets: [x, y, radius, vx, vy, homing, owner]
# owner: "player" or "enemy"
bullets = []
game_over = False
game_won = False
player_after_id = None
enemies_after_id = None
bullets_after_id = None
pressed_keys = set()
right_mouse_held = False
wave = 1
player_lives = 3

def spawn_wave():
    global enemies, wave
    enemies.clear()
    num_enemies = min(2 + wave, 10)
    speed = 6 + wave  # Enemies get faster each wave
    for i in range(num_enemies):
        # Random spawn at top or bottom, not too close to player
        if i % 2 == 0:
            x = random.randint(100, 900)
            y = random.choice([100, 200, 800, 900])
        else:
            x = random.choice([100, 900])
            y = random.randint(100, 900)
        angle = math.atan2(player_y - y, player_x - x)
        dx = math.cos(angle) * speed
        dy = math.sin(angle) * speed
        enemies.append([x, y, 24, dx, dy, 0])

def reset_game():
    global player_x, player_y, enemies, bullets, game_over, game_won, pressed_keys, right_mouse_held, wave, player_lives
    global player_after_id, enemies_after_id, bullets_after_id
    # Cancel previous loops if running
    if player_after_id is not None:
        root.after_cancel(player_after_id)
        player_after_id = None
    if enemies_after_id is not None:
        root.after_cancel(enemies_after_id)
        enemies_after_id = None
    if bullets_after_id is not None:
        root.after_cancel(bullets_after_id)
        bullets_after_id = None

    player_x = 500
    player_y = 900
    bullets.clear()
    game_over = False
    game_won = False
    pressed_keys.clear()
    right_mouse_held = False
    wave = 1
    player_lives = 3
    spawn_wave()
    draw()
    move_player()
    move_enemies()
    move_bullets()

def has_homing_bullet():
    return any(len(b) > 5 and b[5] for b in bullets if b[6] == "player")

def get_flashlight_polygon():
    # Returns the list of points for the flashlight cone polygon
    mouse_x = canvas.winfo_pointerx() - canvas.winfo_rootx()
    mouse_y = canvas.winfo_pointery() - canvas.winfo_rooty()
    dx = mouse_x - player_x
    dy = mouse_y - player_y
    facing_angle = math.degrees(math.atan2(dy, dx))
    angle_step = 2
    cone_angle = 70
    cone_length = 2000
    points = [player_x, player_y]
    for a in range(-cone_angle//2, cone_angle//2+1, angle_step):
        ray_angle = math.radians(facing_angle + a)
        for dist in range(0, cone_length, 8):
            rx = player_x + math.cos(ray_angle) * dist
            ry = player_y + math.sin(ray_angle) * dist
            blocked = False
            # Only block by obstacles, not by enemies!
            for ox1, oy1, ox2, oy2 in obstacles:
                if ox1 <= rx <= ox2 and oy1 <= ry <= oy2:
                    blocked = True
                    break
            if blocked:
                break
        points.extend([rx, ry])
    return points

def point_in_flashlight(px, py, cone_points):
    # Use ray casting to check if point is inside the flashlight polygon
    n = len(cone_points) // 2
    inside = False
    xints = 0
    p1x, p1y = cone_points[0], cone_points[1]
    for i in range(n + 1):
        p2x, p2y = cone_points[(i % n) * 2], cone_points[(i % n) * 2 + 1]
        if min(p1y, p2y) < py <= max(p1y, p2y):
            if px <= max(p1x, p2x):
                if p1y != p2y:
                    xints = (py - p1y) * (p2x - p1x) / (p2y - p1y + 1e-9) + p1x
                if p1x == p2x or px <= xints:
                    inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def draw_flashlight():
    # 1. Draw a semi-transparent dark overlay everywhere
    canvas.create_rectangle(0, 0, 1000, 1000, fill="#222222", outline="")
    # 2. Draw the flashlight cone with the background color to "cut out" the darkness
    cone_points = get_flashlight_polygon()
    canvas.create_polygon(cone_points, fill="#550000", outline="")
    # 3. "Cut out" the player by overdrawing with the player color
    canvas.create_oval(
        player_x - player_radius, player_y - player_radius,
        player_x + player_radius, player_y + player_radius,
        fill="#cccccc", outline=""
    )

def draw():
    canvas.delete("all")
    # Draw goal
 
    canvas.create_oval(
        player_x - player_radius, player_y - player_radius,
        player_x + player_radius, player_y + player_radius,
        fill="#cccccc"
    )

    # Draw flashlight effect (cone and player cutout)
    cone_points = get_flashlight_polygon()
    draw_flashlight()

    # Draw enemies only if inside flashlight cone, always above the cone
    for ex, ey, er, _, _, _ in enemies:
        if point_in_flashlight(ex, ey, cone_points):
            canvas.create_oval(
                ex - er, ey - er, ex + er, ey + er,
                fill="#990000", outline="#cccccc", width=2
            )
    # Draw bullets only if inside flashlight cone
    for bx, by, br, _, _, _, owner in bullets:
        if point_in_flashlight(bx, by, cone_points):
            color = "#cccccc" if owner == "player" else "#ff2222"
            canvas.create_oval(
                bx - br, by - br, bx + br, by + br,
                fill=color, outline=color
            )

    # Draw obstacles (house outlines) OVER the flashlight
    for obs in obstacles:
        canvas.create_rectangle(*obs, outline="#8888ff", width=3)

    # Draw wave number and lives
    canvas.create_text(900, 40, text=f"Wave: {wave}", fill="white", font=("Arial", 24))
    canvas.create_text(900, 80, text=f"Lives: {player_lives}", fill="white", font=("Arial", 24))
    # Draw message if lost
    if game_over:
        canvas.create_text(500, 500, text="You have been Consumed!", fill="black", font=("Arial", 32))
    elif game_won:
        canvas.create_text(500, 500, text="You Escaped!", fill="white", font=("Arial", 32))


    dx = player_x 
    dy = player_y 
    return (dx*dx + dy*dy) <= (player_radius) ** 2

def on_key_press(event):
    if has_homing_bullet():
        return
    pressed_keys.add(event.keysym)
    if event.keysym == "space" and not (game_over or game_won):
        bullets.append([player_x, player_y - player_radius, 8, 0, -20, False, "player"])

def on_key_release(event):
    pressed_keys.discard(event.keysym)

def on_mouse_click(event):
    if has_homing_bullet():
        return
    if game_over or game_won:
        return
    # Left click: fast bullet toward mouse
    if event.num == 1:
        dx = event.x - player_x
        dy = event.y - player_y
        length = math.hypot(dx, dy)
        if length == 0:
            return
        speed = 20
        vx = dx / length * speed
        vy = dy / length * speed
        bullets.append([player_x, player_y, 8, vx, vy, False, "player"])

def on_right_click(event):
    global right_mouse_held
    if has_homing_bullet():
        return
    if game_over or game_won:
        return
    right_mouse_held = True
    dx = event.x - player_x
    dy = event.y - player_y
    length = math.hypot(dx, dy)
    if length == 0:
        return
    speed = 10  # Faster homing bullet
    vx = dx / length * speed
    vy = dy / length * speed
    bullets.append([player_x, player_y, 8, vx, vy, True, "player"])

def on_right_release(event):
    global right_mouse_held
    right_mouse_held = False
    mouse_x = event.x
    mouse_y = event.y
    for bullet in bullets:
        if len(bullet) > 5 and bullet[5] and bullet[6] == "player":  # If homing
            dx = mouse_x - bullet[0]
            dy = mouse_y - bullet[1]
            length = math.hypot(dx, dy)
            if length != 0:
                speed = 20  # Fast speed
                bullet[3] = dx / length * speed
                bullet[4] = dy / length * speed
            bullet[5] = False  # No longer homing

def move_player():
    global player_after_id, player_x, player_y, game_won, game_over
    if game_over or game_won:
        return
    dx = dy = 0
    speed = 10
    if 'Up' in pressed_keys:
        dy -= speed
    if 'Down' in pressed_keys:
        dy += speed
    if 'Left' in pressed_keys:
        dx -= speed
    if 'Right' in pressed_keys:
        dx += speed
    player_x += dx
    player_y += dy
 
    draw()
    player_after_id = root.after(20, move_player)

def move_enemies():
    global enemies_after_id, game_over, game_won
    if game_over or game_won:
        return
    for enemy in enemies:
        ex, ey, er, dx, dy, shoot_timer = enemy
        # Smart chase: move toward player
        vec_x = player_x - ex
        vec_y = player_y - ey
        dist = math.hypot(vec_x, vec_y)
        if dist > 0:
            speed = math.hypot(dx, dy)
            enemy[3] = vec_x / dist * speed
            enemy[4] = vec_y / dist * speed
        enemy[0] += enemy[3]
        enemy[1] += enemy[4]
        # Bounce off walls
        if enemy[0] - enemy[2] < 0 or enemy[0] + enemy[2] > 1000:
            enemy[3] *= -1
        if enemy[1] - enemy[2] < 0 or enemy[1] + enemy[2] > 1000:
            enemy[4] *= -1
        # Enemy shooting
        enemy[5] += 1
        if enemy[5] >= 40:
            shoot_at_player(enemy)
            enemy[5] = 0
    draw()
    enemies_after_id = canvas.after(40, move_enemies)

def shoot_at_player(enemy):
    ex, ey, er, _, _, _ = enemy
    dx = player_x - ex
    dy = player_y - ey
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    speed = 14
    vx = dx / dist * speed
    vy = dy / dist * speed
    bullets.append([ex, ey, 8, vx, vy, False, "enemy"])

def move_bullets():
    global bullets_after_id, game_over, wave, player_lives
    remove_bullets = []
    remove_enemies = []
    for i, bullet in enumerate(bullets):
        # Homing bullet logic (player only)
        if len(bullet) > 5 and bullet[5] and right_mouse_held and bullet[6] == "player":
            mouse_x = canvas.winfo_pointerx() - canvas.winfo_rootx()
            mouse_y = canvas.winfo_pointery() - canvas.winfo_rooty()
            dx = mouse_x - bullet[0]
            dy = mouse_y - bullet[1]
            length = math.hypot(dx, dy)
            if length != 0:
                speed = 10
                bullet[3] = dx / length * speed
                bullet[4] = dy / length * speed
        bullet[0] += bullet[3]
        bullet[1] += bullet[4]
        # Remove bullet if off screen
        if bullet[0] < 0 or bullet[0] > 1000 or bullet[1] < 0 or bullet[1] > 1000:
            remove_bullets.append(i)
            continue
        # Player bullet hits enemy
        if bullet[6] == "player":
            for j, enemy in enumerate(enemies):
                dx = bullet[0] - enemy[0]
                dy = bullet[1] - enemy[1]
                if (dx*dx + dy*dy) <= (bullet[2] + enemy[2]) ** 2:
                    remove_bullets.append(i)
                    remove_enemies.append(j)
        # Enemy bullet hits player
        elif bullet[6] == "enemy":
            dx = bullet[0] - player_x
            dy = bullet[1] - player_y
            if (dx*dx + dy*dy) <= (bullet[2] + player_radius) ** 2:
                remove_bullets.append(i)
                player_lives -= 1
                if player_lives <= 0:
                    game_over = True
                    draw()
                    root.after(1500, reset_game)
                    return
    for i in sorted(set(remove_bullets), reverse=True):
        del bullets[i]
    for j in sorted(set(remove_enemies), reverse=True):
        del enemies[j]
    draw()
    if not enemies and not game_over:
        wave += 1
        spawn_wave()
        move_enemies()
    bullets_after_id = canvas.after(30, move_bullets)

root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)
canvas.bind("<Button-1>", on_mouse_click)
canvas.bind("<Button-3>", on_right_click)
canvas.bind("<ButtonRelease-3>", on_right_release)
draw()
move_player()
move_enemies()
move_bullets()
root.mainloop()
# The game is a simple top-down shooter where the player must survive waves of enemies while avoiding obstacles.
# The player can shoot bullets towards the mouse cursor and can also fire homing bullets by holding the right mouse button.}