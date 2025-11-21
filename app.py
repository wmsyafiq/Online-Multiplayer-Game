from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random
import math
import time
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretdefensegame'
socketio = SocketIO(app, cors_allowed_origins="*")

players = {}
enemies = []
bullets = []
enemy_bullets = []
powerups = []
particles = []
explosions = []

wave = 1
wave_enemies_spawned = 0
wave_enemies_to_spawn = 15
wave_complete = True
boss_alive = False
boss_defeated = False
enemy_id_counter = 0
powerup_id_counter = 0
formation_spawn_timer = 0
BOSS_WAVES = [5, 10, 15, 20, 25]

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def connect():
    sid = str(uuid.uuid4())[:8]
    players[sid] = {
        "x": 400, "y": 500, "lives": 3, "max_lives": 3, "score": 0, "kills": 0,
        "damage": 25, "fire_rate": 15, "fire_cooldown": 0, "speed": 6,
        "shield": 0, "rapid_fire": 0, "invulnerable": 0, "respawn_timer": 0,
        "triple_shot": False, "permanent_fire_rate": 0,
        "dead": False, "color": f"rgb({random.randint(100,255)},{random.randint(100,255)},{random.randint(100,255)})"
    }
    emit("init", {"sid": sid, "players": players, "enemies": enemies, "bullets": bullets,
                  "enemy_bullets": enemy_bullets, "powerups": powerups, "particles": particles,
                  "explosions": explosions, "wave": wave})
    emit("player_joined", {"sid": sid, "player": players[sid]}, broadcast=True, include_self=False)

@socketio.on("disconnect")
def disconnect():
    for sid in list(players.keys()):
        if sid not in [s.sid for s in socketio.server.manager.rooms['/']]:
            players.pop(sid, None)
            emit("player_disconnect", {"sid": sid}, broadcast=True)

@socketio.on("move")
def move(data):
    sid = data.get("sid")
    if sid in players and not players[sid]["dead"]:
        players[sid]["x"] = max(20, min(780, data["x"]))
        players[sid]["y"] = max(20, min(580, data["y"]))

@socketio.on("shoot")
def shoot(data):
    sid = data.get("sid")
    if sid in players:
        p = players[sid]
        if not p["dead"] and p["fire_cooldown"] <= 0:
            speed = 14
            
            if p["triple_shot"]:
                bullets.append({"owner": sid, "x": p["x"], "y": p["y"], "vx": 0, "vy": -speed, "damage": p["damage"]})
                bullets.append({"owner": sid, "x": p["x"] - 15, "y": p["y"], "vx": 0, "vy": -speed, "damage": p["damage"]})
                bullets.append({"owner": sid, "x": p["x"] + 15, "y": p["y"], "vx": 0, "vy": -speed, "damage": p["damage"]})
            else:
                bullets.append({"owner": sid, "x": p["x"], "y": p["y"], "vx": 0, "vy": -speed, "damage": p["damage"]})
            
            if p["rapid_fire"] > 0:
                bullets.append({"owner": sid, "x": p["x"] - 8, "y": p["y"], "vx": 0, "vy": -speed, "damage": p["damage"]})
                bullets.append({"owner": sid, "x": p["x"] + 8, "y": p["y"], "vx": 0, "vy": -speed, "damage": p["damage"]})
            
            actual_fire_rate = max(3, p["fire_rate"] - p["permanent_fire_rate"])
            p["fire_cooldown"] = actual_fire_rate

def spawn_formation(wave_num, formation_type):
    global enemy_id_counter
    
    if formation_type == "v_formation":
        for i in range(5):
            enemy_id_counter += 1
            x = 400 + (i - 2) * 80
            y = -50 - i * 40
            enemies.append({
                "id": enemy_id_counter, "x": x, "y": y, "health": 40 + wave_num*8,
                "max_health": 40 + wave_num*8, "type": "grunt", "speed": 2.0, "damage": 20,
                "attack_cooldown": random.randint(0, 60), "size": 25, "score": 15,
                "shoot_rate": 70, "pattern": "formation_v", "pattern_time": 0,
                "formation_offset": i
            })
    
    elif formation_type == "line":
        for i in range(6):
            enemy_id_counter += 1
            x = 150 + i * 100
            y = -50
            enemies.append({
                "id": enemy_id_counter, "x": x, "y": y, "health": 35 + wave_num*7,
                "max_health": 35 + wave_num*7, "type": "fast", "speed": 2.5, "damage": 18,
                "attack_cooldown": random.randint(0, 80), "size": 20, "score": 18,
                "shoot_rate": 60, "pattern": "formation_line", "pattern_time": 0,
                "formation_offset": i
            })
    
    elif formation_type == "circle":
        for i in range(8):
            enemy_id_counter += 1
            angle = (i / 8) * 2 * math.pi
            x = 400 + math.cos(angle) * 150
            y = 100
            enemies.append({
                "id": enemy_id_counter, "x": x, "y": y, "health": 45 + wave_num*9,
                "max_health": 45 + wave_num*9, "type": "shooter", "speed": 1.5, "damage": 22,
                "attack_cooldown": random.randint(0, 50), "size": 22, "score": 25,
                "shoot_rate": 50, "pattern": "formation_circle", "pattern_time": 0,
                "formation_offset": i
            })
    
    elif formation_type == "diamond":
        positions = [(400, -50), (350, 0), (450, 0), (300, 50), (400, 50), (500, 50), (350, 100), (450, 100)]
        for i, (x, y) in enumerate(positions):
            enemy_id_counter += 1
            enemies.append({
                "id": enemy_id_counter, "x": x, "y": y, "health": 50 + wave_num*10,
                "max_health": 50 + wave_num*10, "type": "tank", "speed": 1.2, "damage": 25,
                "attack_cooldown": random.randint(0, 70), "size": 28, "score": 30,
                "shoot_rate": 65, "pattern": "formation_diamond", "pattern_time": 0,
                "formation_offset": i
            })

def spawn_boss(wave_num):
    global enemy_id_counter
    enemy_id_counter += 1
    boss_type = random.choice(["mega", "swarm", "tank"])
    enemies.append({
        "id": enemy_id_counter, "x": 400, "y": 80, "health": 1500 + wave_num * 300,
        "max_health": 1500 + wave_num * 300, "type": "boss", "boss_type": boss_type,
        "speed": 0, "damage": 50, "attack_cooldown": 0, "size": 60, "score": 2000,
        "pattern": "boss_hover", "pattern_time": 0, "hover_x": 400,
        "spawn_cooldown": 0, "bullet_pattern_cooldown": 0
    })

def spawn_powerup(x, y):
    global powerup_id_counter
    powerup_id_counter += 1
    
    rand = random.random()
    if rand < 0.03:
        powerup_type = "triple_shot"
    elif rand < 0.06:
        powerup_type = "perm_fire_rate"
    else:
        powerup_type = random.choices(
            ["health", "damage", "rapid_fire", "shield", "nuke", "extra_life", "speed"],
            weights=[30, 20, 20, 15, 5, 5, 5]
        )[0]
    
    powerups.append({"id": powerup_id_counter, "x": x, "y": y, "type": powerup_type, "vy": 2.5})

def create_explosion(x, y, size="normal"):
    sizes = {"small": 20, "normal": 40, "large": 80, "huge": 150}
    radius = sizes.get(size, 40)
    explosions.append({"x": x, "y": y, "radius": radius, "max_radius": radius, "life": 20})
    particle_count = {"small": 15, "normal": 30, "large": 60, "huge": 100}[size]
    for _ in range(particle_count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        particles.append({
            "x": x, "y": y, "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed,
            "life": random.randint(20, 50), "size": random.randint(2, 6)
        })

def shoot_bullet_pattern(enemy, pattern_type):
    if pattern_type == "spiral":
        for i in range(8):
            angle = (i / 8) * 2 * math.pi + enemy["pattern_time"] * 0.1
            enemy_bullets.append({
                "x": enemy["x"], "y": enemy["y"],
                "vx": math.cos(angle) * 4, "vy": math.sin(angle) * 4,
                "damage": enemy["damage"]
            })
    
    elif pattern_type == "wave":
        for i in range(-3, 4):
            angle = math.pi/2 + i * 0.2
            enemy_bullets.append({
                "x": enemy["x"], "y": enemy["y"],
                "vx": math.cos(angle) * 4.5, "vy": math.sin(angle) * 4.5,
                "damage": enemy["damage"]
            })
    
    elif pattern_type == "cross":
        for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
            enemy_bullets.append({
                "x": enemy["x"], "y": enemy["y"],
                "vx": math.cos(angle) * 5, "vy": math.sin(angle) * 5,
                "damage": enemy["damage"]
            })
    
    elif pattern_type == "ring":
        for i in range(12):
            angle = (i / 12) * 2 * math.pi
            enemy_bullets.append({
                "x": enemy["x"], "y": enemy["y"],
                "vx": math.cos(angle) * 3.5, "vy": math.sin(angle) * 3.5,
                "damage": enemy["damage"]
            })

def game_loop():
    global wave, wave_enemies_spawned, wave_enemies_to_spawn, wave_complete, boss_alive, boss_defeated
    global enemies, bullets, enemy_bullets, powerups, particles, explosions, formation_spawn_timer
    
    frame = 0
    while True:
        time.sleep(0.033)
        frame += 1
        
        if wave_complete and len(enemies) == 0:
            wave_complete = False
            wave_enemies_spawned = 0
            boss_defeated = False
            if wave in BOSS_WAVES:
                boss_alive = False
                wave_enemies_to_spawn = 0
            else:
                wave_enemies_to_spawn = 4
                formation_spawn_timer = 0
        
        if not wave_complete:
            if wave in BOSS_WAVES:
                if not boss_alive:
                    spawn_boss(wave)
                    boss_alive = True
                elif len(enemies) == 0 and boss_defeated:
                    wave += 1
                    wave_complete = True
            else:
                if wave_enemies_spawned < wave_enemies_to_spawn:
                    formation_spawn_timer += 1
                    if formation_spawn_timer >= 120:
                        formation_type = random.choice(["v_formation", "line", "circle", "diamond"])
                        spawn_formation(wave, formation_type)
                        wave_enemies_spawned += 1
                        formation_spawn_timer = 0
                elif len(enemies) == 0:
                    wave += 1
                    wave_complete = True
        
        for p in players.values():
            if p["fire_cooldown"] > 0:
                p["fire_cooldown"] -= 1
            if p["rapid_fire"] > 0:
                p["rapid_fire"] -= 1
            if p["shield"] > 0:
                p["shield"] -= 1
            if p["invulnerable"] > 0:
                p["invulnerable"] -= 1
            if p["dead"] and p["respawn_timer"] > 0:
                p["respawn_timer"] -= 1
                if p["respawn_timer"] == 0 and p["lives"] > 0:
                    p["dead"] = False
                    p["x"] = 400
                    p["y"] = 500
                    p["invulnerable"] = 120
        
        for b in bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["y"] < -10 or b["x"] < -10 or b["x"] > 810:
                bullets.remove(b)
        
        for eb in enemy_bullets[:]:
            eb["x"] += eb["vx"]
            eb["y"] += eb["vy"]
            if eb["y"] > 610 or eb["x"] < -10 or eb["x"] > 810 or eb["y"] < -10:
                enemy_bullets.remove(eb)
        
        for e in enemies[:]:
            e["pattern_time"] += 1
            
            if e["type"] == "boss":
                e["hover_x"] += math.sin(frame * 0.03) * 3
                e["x"] = max(100, min(700, e["hover_x"]))
                e["y"] = 80 + math.sin(frame * 0.05) * 10
                
                e["bullet_pattern_cooldown"] -= 1
                if e["bullet_pattern_cooldown"] <= 0:
                    pattern = random.choice(["spiral", "wave", "cross", "ring"])
                    shoot_bullet_pattern(e, pattern)
                    e["bullet_pattern_cooldown"] = 80
                
                e["spawn_cooldown"] -= 1
                if e["spawn_cooldown"] <= 0 and e["boss_type"] == "swarm":
                    formation_type = random.choice(["v_formation", "line"])
                    spawn_formation(wave, formation_type)
                    e["spawn_cooldown"] = 200
            
            else:
                if "formation" in e["pattern"]:
                    if e["pattern"] == "formation_v":
                        e["y"] += e["speed"]
                        e["x"] += math.sin(e["pattern_time"] * 0.05) * 2
                    elif e["pattern"] == "formation_line":
                        e["y"] += e["speed"]
                        e["x"] += math.sin(e["pattern_time"] * 0.08 + e["formation_offset"]) * 3
                    elif e["pattern"] == "formation_circle":
                        angle = (e["formation_offset"] / 8) * 2 * math.pi + e["pattern_time"] * 0.02
                        e["x"] = 400 + math.cos(angle) * 150
                        e["y"] = 150 + math.sin(angle) * 80
                    elif e["pattern"] == "formation_diamond":
                        e["y"] += e["speed"] * 0.5
                        e["x"] += math.cos(e["pattern_time"] * 0.06 + e["formation_offset"]) * 2
                
                e["attack_cooldown"] -= 1
                if e["attack_cooldown"] <= 0 and e["y"] > 50 and e["y"] < 500:
                    if players and random.random() < 0.7:
                        alive_players = [p for p in players.values() if not p["dead"]]
                        if alive_players:
                            target = random.choice(alive_players)
                            dx = target["x"] - e["x"]
                            dy = target["y"] - e["y"]
                            dist = math.hypot(dx, dy)
                            if dist > 0:
                                enemy_bullets.append({
                                    "x": e["x"], "y": e["y"],
                                    "vx": (dx/dist) * 5, "vy": (dy/dist) * 5,
                                    "damage": e["damage"]
                                })
                    else:
                        enemy_bullets.append({
                            "x": e["x"], "y": e["y"],
                            "vx": 0, "vy": 5,
                            "damage": e["damage"]
                        })
                    e["attack_cooldown"] = e["shoot_rate"]
                
                if e["y"] > 650:
                    enemies.remove(e)
        
        for b in bullets[:]:
            for e in enemies[:]:
                dist = math.hypot(b["x"] - e["x"], b["y"] - e["y"])
                if dist < e["size"]:
                    e["health"] -= b["damage"]
                    if b in bullets:
                        bullets.remove(b)
                    
                    if e["health"] <= 0:
                        if e["type"] == "boss":
                            create_explosion(e["x"], e["y"], "huge")
                            for _ in range(12):
                                spawn_powerup(e["x"] + random.randint(-50, 50), e["y"] + random.randint(-30, 30))
                            boss_defeated = True
                        else:
                            create_explosion(e["x"], e["y"], "normal")
                            if random.random() < 0.40:
                                spawn_powerup(e["x"], e["y"])
                        
                        if b["owner"] in players:
                            players[b["owner"]]["score"] += e["score"]
                            players[b["owner"]]["kills"] += 1
                        
                        if e in enemies:
                            enemies.remove(e)
                    break
        
        for eb in enemy_bullets[:]:
            for sid, p in players.items():
                if not p["dead"]:
                    dist = math.hypot(eb["x"] - p["x"], eb["y"] - p["y"])
                    if dist < 20:
                        if p["shield"] <= 0 and p["invulnerable"] <= 0:
                            p["lives"] -= 1
                            create_explosion(p["x"], p["y"], "small")
                            if p["lives"] <= 0:
                                p["dead"] = True
                                p["lives"] = 3
                                p["respawn_timer"] = 180
                                create_explosion(p["x"], p["y"], "large")
                            else:
                                p["invulnerable"] = 60
                        if eb in enemy_bullets:
                            enemy_bullets.remove(eb)
                        break
        
        for pu in powerups[:]:
            pu["y"] += pu["vy"]
            
            for sid, p in players.items():
                if not p["dead"]:
                    dist = math.hypot(pu["x"] - p["x"], pu["y"] - p["y"])
                    if dist < 25:
                        if pu["type"] == "health":
                            p["lives"] = min(p["max_lives"], p["lives"] + 1)
                        elif pu["type"] == "damage":
                            p["damage"] += 5
                        elif pu["type"] == "rapid_fire":
                            p["rapid_fire"] = 400
                        elif pu["type"] == "shield":
                            p["shield"] = 250
                        elif pu["type"] == "nuke":
                            for e in enemies[:]:
                                if e["type"] != "boss":
                                    create_explosion(e["x"], e["y"], "large")
                                    p["score"] += e["score"]
                                    p["kills"] += 1
                                    enemies.remove(e)
                            create_explosion(400, 300, "huge")
                        elif pu["type"] == "extra_life":
                            p["max_lives"] += 1
                            p["lives"] = min(p["max_lives"], p["lives"] + 1)
                        elif pu["type"] == "speed":
                            p["speed"] = min(10, p["speed"] + 1)
                        elif pu["type"] == "triple_shot":
                            p["triple_shot"] = True
                        elif pu["type"] == "perm_fire_rate":
                            p["permanent_fire_rate"] += 3
                        
                        powerups.remove(pu)
                        break
            
            if pu["y"] > 620:
                powerups.remove(pu)
        
        for part in particles[:]:
            part["x"] += part["vx"]
            part["y"] += part["vy"]
            part["vy"] += 0.15
            part["life"] -= 1
            if part["life"] <= 0:
                particles.remove(part)
        
        for exp in explosions[:]:
            exp["life"] -= 1
            exp["radius"] = exp["max_radius"] * (exp["life"] / 20)
            if exp["life"] <= 0:
                explosions.remove(exp)
        
        socketio.emit("update_game", {
            "players": players, "enemies": enemies, "bullets": bullets,
            "enemy_bullets": enemy_bullets, "powerups": powerups,
            "particles": particles, "explosions": explosions, "wave": wave
        })

if __name__ == "__main__":
    import threading
    threading.Thread(target=game_loop, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=3000, debug=False)