import pygame
import sys
import random

pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("my moba game")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 40)

# Player and enemy settings
PLAYER_SIZE = 40
PLAYER_SPEED = 5
PLAYER_MAX_HEALTH = 100

ENEMY_SIZE = 30
ENEMY_SPEED = 2
ENEMY_MAX_HEALTH = 30
ENEMY_SPAWN_INTERVAL = 2000  # milliseconds

attack_range = 60  # Ability effect radius

# Ability definitions
ABILITY_KEYS = {
    pygame.K_q: {"name": "Q", "damage": 20, "cooldown": 1500, "color": (255, 255, 255)},  # Sword spin white
    pygame.K_w: {"name": "W", "damage": 20, "cooldown": 1500, "color": (0, 255, 0)},      # Green AoE
    pygame.K_e: {"name": "E", "damage": 25, "cooldown": 2000, "color": (0, 0, 255)},      # Blue projectile
    pygame.K_r: {"name": "R", "damage": 40, "cooldown": 5000, "color": (255, 255, 0)},    # Yellow AoE
}

color_options = [
    (0, 128, 255),  # Blue
    (255, 50, 50),  # Red
    (50, 255, 50),  # Green
    (255, 255, 0),  # Yellow
    (255, 0, 255)   # Purple
]

selected_color_index = 0

class Entity:
    def __init__(self, x, y, size, color, health):
        self.pos = pygame.Vector2(x, y)
        self.size = size
        self.color = color
        self.health = health
        self.max_health = health
        self.hit_flash_duration = 100  # ms
        self.hit_flash_timer = 0

    def draw_health_bar(self):
        bar_width = self.size
        bar_height = 6
        health_ratio = max(self.health, 0) / self.max_health
        health_bar_rect = pygame.Rect(self.pos.x, self.pos.y - 10, bar_width, bar_height)
        pygame.draw.rect(screen, (255, 0, 0), health_bar_rect)  # Red background
        pygame.draw.rect(screen, (0, 255, 0), (self.pos.x, self.pos.y - 10, bar_width * health_ratio, bar_height))

    def draw(self):
        if pygame.time.get_ticks() - self.hit_flash_timer < self.hit_flash_duration:
            color = (255, 255, 255)
        else:
            color = self.color
        pygame.draw.rect(screen, color, (self.pos.x, self.pos.y, self.size, self.size))
        self.draw_health_bar()

    def take_damage(self, amount):
        self.health -= amount
        self.hit_flash_timer = pygame.time.get_ticks()

class Player(Entity):
    def __init__(self, x, y, size, color, health, speed):
        super().__init__(x, y, size, color, health)
        self.speed = speed

    def move_towards(self, target_pos):
        direction = target_pos - self.pos
        if direction.length() > self.speed:
            direction = direction.normalize()
            self.pos += direction * self.speed
            return False
        else:
            self.pos = target_pos
            return True

class Enemy(Entity):
    def __init__(self, x, y, size, color, health, speed):
        super().__init__(x, y, size, color, health)
        self.speed = speed

    def move_towards(self, target_pos):
        direction = target_pos - self.pos
        if direction.length() != 0:
            direction = direction.normalize()
            self.pos += direction * self.speed

class AttackEffect:
    def __init__(self, pos, color):
        self.pos = pos
        self.color = color
        self.start_time = pygame.time.get_ticks()
        self.duration = 300  # ms

    def draw(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed < self.duration:
            alpha = 255 * (1 - elapsed / self.duration)
            surface = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*self.color, int(alpha)), (50, 50), 40)
            screen.blit(surface, (self.pos.x - 50, self.pos.y - 50))
            return True
        return False

class Projectile:
    def __init__(self, start_pos, target_pos, color, damage, speed=10, radius=8):
        self.pos = pygame.Vector2(start_pos)
        direction = target_pos - start_pos
        self.direction = direction.normalize() if direction.length() != 0 else pygame.Vector2(1, 0)
        self.color = color
        self.damage = damage
        self.speed = speed
        self.radius = radius
        self.active = True

    def update(self):
        self.pos += self.direction * self.speed
        if self.pos.x < 0 or self.pos.x > WIDTH or self.pos.y < 0 or self.pos.y > HEIGHT:
            self.active = False

    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)

    def check_collision(self, enemies):
        for enemy in enemies[:]:
            enemy_center = enemy.pos + pygame.Vector2(enemy.size/2, enemy.size/2)
            if self.pos.distance_to(enemy_center) <= self.radius + enemy.size/2:
                enemy.take_damage(self.damage)
                if enemy.health <= 0:
                    enemies.remove(enemy)
                self.active = False
                break

class SwordSpin:
    def __init__(self, player, damage, duration=500, radius=70):
        self.player = player
        self.damage = damage
        self.radius = radius
        self.start_time = pygame.time.get_ticks()
        self.duration = duration
        self.active = True
        self.angle = 0
        self.damaged_enemies = set()

    def update(self, enemies):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed > self.duration:
            self.active = False
            return

        self.angle = (self.angle + 15) % 360

        player_center = self.player.pos + pygame.Vector2(self.player.size/2, self.player.size/2)
        for enemy in enemies[:]:
            if enemy in self.damaged_enemies:
                continue
            enemy_center = enemy.pos + pygame.Vector2(enemy.size/2, enemy.size/2)
            if player_center.distance_to(enemy_center) <= self.radius:
                enemy.take_damage(self.damage)
                self.damaged_enemies.add(enemy)
                if enemy.health <= 0:
                    enemies.remove(enemy)

    def draw(self):
        player_center = self.player.pos + pygame.Vector2(self.player.size/2, self.player.size/2)
        length = self.radius
        end_pos = player_center + pygame.Vector2(length, 0).rotate(self.angle)
        pygame.draw.line(screen, (255, 255, 255), player_center, end_pos, 5)

class EnemyAttackEffect:
    def __init__(self, enemy):
        self.enemy = enemy
        self.start_time = pygame.time.get_ticks()
        self.duration = 300  # ms

    def draw(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed < self.duration:
            # Draw a red swinging "hit" rectangle next to enemy to show attack
            attack_rect = pygame.Rect(
                self.enemy.pos.x + self.enemy.size,  # right side of enemy
                self.enemy.pos.y + self.enemy.size // 4,
                15,
                self.enemy.size // 2
            )
            alpha = 255 * (1 - elapsed / self.duration)
            surf = pygame.Surface((attack_rect.width, attack_rect.height), pygame.SRCALPHA)
            surf.fill((255, 0, 0, int(alpha)))
            screen.blit(surf, (attack_rect.x, attack_rect.y))
            return True
        return False

def draw_start_screen():
    screen.fill((20, 20, 20))
    title = font.render("Choose Your Character Color", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    for i, color in enumerate(color_options):
        rect = pygame.Rect(150 + i*120, HEIGHT//2 - 50, 80, 80)
        pygame.draw.rect(screen, color, rect)
        if i == selected_color_index:
            pygame.draw.rect(screen, (255, 255, 255), rect, 5)

    instruction = font.render("Use LEFT/RIGHT arrows to select, ENTER to start", True, (200, 200, 200))
    screen.blit(instruction, (WIDTH//2 - instruction.get_width()//2, HEIGHT - 100))

def game_over_screen():
    screen.fill((30, 0, 0))
    game_over_text = font.render("Game Over! Press ESC to Quit.", True, (255, 255, 255))
    screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//2 - 20))
    pygame.display.flip()

def draw_ability_bar(last_ability_use, current_time):
    bar_height = 80
    bar_y = HEIGHT - bar_height
    ability_width = WIDTH // 4

    for i, key in enumerate([pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r]):
        x = i * ability_width
        rect = pygame.Rect(x, bar_y, ability_width, bar_height)

        pygame.draw.rect(screen, (50, 50, 50), rect)

        label = font.render(ABILITY_KEYS[key]["name"], True, (255, 255, 255))
        label_pos = label.get_rect(center=(x + ability_width // 2, bar_y + bar_height // 3))
        screen.blit(label, label_pos)

        cooldown = ABILITY_KEYS[key]["cooldown"]
        elapsed = current_time - last_ability_use.get(key, 0)
        cooldown_left = max(0, cooldown - elapsed)

        if cooldown_left > 0:
            s = pygame.Surface((ability_width, bar_height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            screen.blit(s, (x, bar_y))

            seconds_left = int(cooldown_left / 1000) + 1
            cd_text = font.render(str(seconds_left), True, (255, 255, 255))
            cd_pos = cd_text.get_rect(center=(x + ability_width // 2, bar_y + 2*bar_height // 3))
            screen.blit(cd_text, cd_pos)

def main():
    global selected_color_index

    in_start_screen = True
    while in_start_screen:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    selected_color_index = (selected_color_index + 1) % len(color_options)
                elif event.key == pygame.K_LEFT:
                    selected_color_index = (selected_color_index - 1) % len(color_options)
                elif event.key == pygame.K_RETURN:
                    in_start_screen = False

        draw_start_screen()
        pygame.display.flip()

    player = Player(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, color_options[selected_color_index], PLAYER_MAX_HEALTH, PLAYER_SPEED)
    enemies = []
    enemy_spawn_event = pygame.USEREVENT + 1
    pygame.time.set_timer(enemy_spawn_event, ENEMY_SPAWN_INTERVAL)

    attack_effects = []
    projectiles = []
    sword_spins = []
    enemy_attack_effects = []
    last_ability_use = {key: 0 for key in ABILITY_KEYS}
    player_target_pos = None

    running = True
    game_over = False

    while running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == enemy_spawn_event and not game_over:
                spawn_side = random.choice(['top', 'bottom', 'left', 'right'])
                if spawn_side == 'top':
                    x = random.randint(0, WIDTH - ENEMY_SIZE)
                    y = -ENEMY_SIZE
                elif spawn_side == 'bottom':
                    x = random.randint(0, WIDTH - ENEMY_SIZE)
                    y = HEIGHT + ENEMY_SIZE
                elif spawn_side == 'left':
                    x = -ENEMY_SIZE
                    y = random.randint(0, HEIGHT - ENEMY_SIZE)
                else:
                    x = WIDTH + ENEMY_SIZE
                    y = random.randint(0, HEIGHT - ENEMY_SIZE)
                enemies.append(Enemy(x, y, ENEMY_SIZE, (200, 50, 50), ENEMY_MAX_HEALTH, ENEMY_SPEED))

            if event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1:
                    player_target_pos = pygame.Vector2(event.pos)

            if event.type == pygame.KEYDOWN and not game_over:
                if event.key in ABILITY_KEYS:
                    if current_time - last_ability_use[event.key] >= ABILITY_KEYS[event.key]["cooldown"]:
                        last_ability_use[event.key] = current_time

                        if event.key == pygame.K_q:
                            sword_spins.append(SwordSpin(player, ABILITY_KEYS[event.key]["damage"]))
                        elif event.key == pygame.K_e:
                            mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
                            projectiles.append(Projectile(player.pos + pygame.Vector2(player.size/2, player.size/2), mouse_pos, ABILITY_KEYS[event.key]["color"], ABILITY_KEYS[event.key]["damage"]))
                        else:
                            mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
                            attack_effects.append(AttackEffect(mouse_pos, ABILITY_KEYS[event.key]["color"]))
                            for enemy in enemies[:]:
                                enemy_center = enemy.pos + pygame.Vector2(enemy.size/2, enemy.size/2)
                                if mouse_pos.distance_to(enemy_center) <= attack_range:
                                    enemy.take_damage(ABILITY_KEYS[event.key]["damage"])
                                    if enemy.health <= 0:
                                        enemies.remove(enemy)

        if player_target_pos:
            reached = player.move_towards(player_target_pos)
            if reached:
                player_target_pos = None

        if not game_over:
            for enemy in enemies:
                enemy.move_towards(player.pos)

            # Enemies attack effect when near but not colliding
            player_center = player.pos + pygame.Vector2(player.size/2, player.size/2)
            for enemy in enemies:
                enemy_center = enemy.pos + pygame.Vector2(enemy.size/2, enemy.size/2)
                dist = enemy_center.distance_to(player_center)
                # Attack if within range but not colliding
                if attack_range < dist < attack_range + 20:
                    # Avoid too many effects by some cooldown or just append (simple version)
                    enemy_attack_effects.append(EnemyAttackEffect(enemy))

            # Player-enemy collision: no health loss, no auto spin
            # You can add something here if needed

            if player.health <= 0:
                game_over = True

        screen.fill((30, 30, 30))

        # Inside the game loop, after enemies move:



        if not game_over:
            player.draw()
            for enemy in enemies:
                enemy.draw()

            for effect in attack_effects[:]:
                if not effect.draw():
                    attack_effects.remove(effect)

            for proj in projectiles[:]:
                proj.update()
                proj.check_collision(enemies)
                if not proj.active:
                    projectiles.remove(proj)
                else:
                    proj.draw()

            for spin in sword_spins[:]:
                spin.update(enemies)
                if not spin.active:
                    sword_spins.remove(spin)
                else:
                    spin.draw()

            for effect in enemy_attack_effects[:]:
                if not effect.draw():
                    enemy_attack_effects.remove(effect)

            draw_ability_bar(last_ability_use, current_time)

        else:
            game_over_screen()
            if keys[pygame.K_ESCAPE]:
                running = False

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
