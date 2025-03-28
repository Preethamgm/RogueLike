# Single-file Python Roguelike Game using PyGame

import pygame
import random
import math
from collections import deque
import pickle # For saving/loading
import os     # For checking if save file exists

# --- Constants ---
# Screen
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 32
FPS = 60

# Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GREY = (128, 128, 128)
COLOR_DARK_GREY = (50, 50, 50)
COLOR_PLAYER = (0, 128, 255)
COLOR_ENEMY_GOBLIN = (0, 150, 0)
COLOR_ENEMY_ORC = (200, 0, 0)
COLOR_ENEMY_ARCHER = (150, 150, 0) # Ranged
COLOR_WALL = (139, 69, 19) # Brown
COLOR_FLOOR = (105, 105, 105) # Dim Gray
COLOR_DOOR_CLOSED = (160, 82, 45) # Sienna
COLOR_DOOR_OPEN = (111, 78, 55) # Dark Sienna
COLOR_STAIRS = (255, 165, 0) # Orange
COLOR_HEALTH_POTION = (255, 0, 255) # Magenta
COLOR_WEAPON_SWORD = (192, 192, 192) # Silver
COLOR_KEY = (255, 215, 0) # Gold
COLOR_HEALTH_BAR = (0, 255, 0)
COLOR_HEALTH_BAR_BG = (255, 0, 0)
COLOR_DAMAGE_TEXT = (255, 100, 100)
COLOR_HUD_BG = (30, 30, 30)
COLOR_HUD_TEXT = (200, 200, 200)
COLOR_VICTORY = (0, 255, 0)
COLOR_GAME_OVER = (255, 0, 0)
COLOR_MENU_TITLE = (255, 255, 0)
COLOR_MENU_SELECTED = (255, 255, 255)
COLOR_MENU_NORMAL = (150, 150, 150)
COLOR_ORANGE = (255, 165, 0)


# Map Generation (BSP)
MAP_WIDTH = 80
MAP_HEIGHT = 60
BSP_MIN_LEAF_SIZE = 10
BSP_MAX_LEAF_SIZE = 20 # Controls density
ROOM_MIN_SIZE = 5
ROOM_MAX_PADDING = 2 # How much smaller room is than leaf

# Game Properties
PLAYER_START_HEALTH = 100
PLAYER_ATTACK = 10
PLAYER_INVENTORY_SIZE = 5
NUM_FLOORS = 3
SAVE_FILENAME = "savegame.dat"

# Enemy Properties
ENEMY_BASE_HEALTH = 20
ENEMY_BASE_ATTACK = 5
ENEMY_SIGHT_RADIUS = 8
ENEMY_ATTACK_RANGE = 1.5 # Tiles, covers adjacent including diagonals

# Items
HEALTH_POTION_AMOUNT = 40
SWORD_ATTACK_BONUS = 10

# Game States
STATE_MAIN_MENU = 'main_menu'
STATE_PLAYING = 'playing'
STATE_GAME_OVER = 'game_over'
STATE_VICTORY = 'victory'
STATE_LEVEL_TRANSITION = 'level_transition'

# Turn System
TURN_PLAYER = 'player'
TURN_ENEMY = 'enemy'

# --- Helper Functions ---

def draw_text(surface, text, size, x, y, color, font_name=None, align="topleft"):
    """Draws text on a surface."""
    font = pygame.font.Font(font_name, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "center":
        text_rect.center = (x, y)
    elif align == "topright":
        text_rect.topright = (x, y)
    elif align == "midtop":
        text_rect.midtop = (x, y)
    else: # topleft
        text_rect.topleft = (x, y)
    surface.blit(text_surface, text_rect)
    return text_rect

def distance(x1, y1, x2, y2):
    """Calculates Euclidean distance."""
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def distance_grid(x1, y1, x2, y2):
    """Calculates Chebyshev distance (grid distance)."""
    return max(abs(x1 - x2), abs(y1 - y2))

# --- Classes ---

class Tile:
    """Represents a tile on the map."""
    def __init__(self, x, y, blocked, block_sight=None, tile_type='wall', explored=False):
        self.x = x
        self.y = y
        self.blocked = blocked
        self.block_sight = block_sight if block_sight is not None else blocked
        self.explored = explored # Now includes explored status for saving/loading
        self.type = tile_type # 'wall', 'floor', 'door_closed', 'door_open', 'stairs'

class GameMap:
    """Handles map generation, rendering, and pathfinding."""
    def __init__(self, width, height, dungeon_level=1):
        self.width = width
        self.height = height
        self.dungeon_level = dungeon_level # Store level for saving/loading context if needed
        self.tiles = self._initialize_tiles()
        self.rooms = []
        self.player_start_x = 0
        self.player_start_y = 0
        self.stairs_x = 0
        self.stairs_y = 0

    def _initialize_tiles(self):
        """Creates a map filled with walls."""
        tiles = [[Tile(x, y, True) for y in range(self.height)] for x in range(self.width)]
        return tiles

    def is_walkable(self, x, y):
        """Check if a tile is walkable."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        return not self.tiles[x][y].blocked

    def is_visible_tile(self, x, y):
        """ Placeholder for future Field of View calculation """
        if 0 <= x < self.width and 0 <= y < self.height:
            return True # Simplified FoV
        return False

    def create_room(self, rect):
        """Carves out a room within the given rectangle."""
        for x in range(rect.x + 1, rect.x + rect.w):
            for y in range(rect.y + 1, rect.y + rect.h):
                self.tiles[x][y].blocked = False
                self.tiles[x][y].block_sight = False
                self.tiles[x][y].type = 'floor'

    def create_h_tunnel(self, x1, x2, y):
        """Carves a horizontal tunnel."""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[x][y].blocked = False
            self.tiles[x][y].block_sight = False
            self.tiles[x][y].type = 'floor'
            self._try_place_door(x, y)


    def create_v_tunnel(self, y1, y2, x):
        """Carves a vertical tunnel."""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[x][y].blocked = False
            self.tiles[x][y].block_sight = False
            self.tiles[x][y].type = 'floor'
            self._try_place_door(x, y)

    def _try_place_door(self, x, y):
         """Place a door if the tunnel enters a room."""
         # Check neighbors to see if we are breaking into a potential room area
         # This logic is simplified and might place doors mid-corridor sometimes.
         # A better check would involve knowing room boundaries explicitly.
         neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
         wall_neighbors = 0
         floor_neighbors = 0
         for nx, ny in neighbors:
             if 0 <= nx < self.width and 0 <= ny < self.height:
                 if self.tiles[nx][ny].type == 'wall':
                     wall_neighbors += 1
                 elif self.tiles[nx][ny].type == 'floor':
                     floor_neighbors +=1

         # Heuristic: If carving a floor next to 2+ walls and 1+ floor, maybe it's an entrance
         if self.tiles[x][y].type == 'floor' and wall_neighbors >= 2 and floor_neighbors >= 1:
             # Check adjacent wall tiles and turn one into a door
             for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                check_x, check_y = x + dx, y + dy
                if 0 <= check_x < self.width and 0 <= check_y < self.height:
                     if self.tiles[check_x][check_y].type == 'wall':
                         # Ensure it connects to the floor we just carved
                         # And check if it's already a door to avoid duplicates
                         is_connected_to_floor = False
                         is_already_door = False
                         for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                             n_check_x, n_check_y = check_x + ddx, check_y + ddy
                             if n_check_x == x and n_check_y == y:
                                 is_connected_to_floor = True
                             if 0 <= n_check_x < self.width and 0 <= n_check_y < self.height:
                                if self.tiles[n_check_x][n_check_y].type in ['door_closed', 'door_open']:
                                    # Prevent doors right next to each other sometimes
                                    is_already_door = True # Simplified check

                         if is_connected_to_floor and not is_already_door and random.random() < 0.2: # Lower chance to place door
                            self.tiles[check_x][check_y] = Tile(check_x, check_y, True, True, 'door_closed')
                            break # Place only one door per tunnel step


    def generate_bsp(self):
        """Generates the map using Binary Space Partitioning."""
        self.rooms = []
        self._initialize_tiles() # Reset map

        root_leaf = BSPLeaf(0, 0, self.width, self.height)
        self.leafs = [root_leaf]

        did_split = True
        queue = [root_leaf]
        while queue:
            leaf = queue.pop(0)
            if leaf.split():
                queue.append(leaf.child_1)
                queue.append(leaf.child_2)

        root_leaf.create_rooms(self)

        # Place player in the center of the first room
        if self.rooms:
            first_room = self.rooms[0]
            self.player_start_x = first_room.centerx
            self.player_start_y = first_room.centery

            # Place stairs in the center of the last room
            last_room = self.rooms[-1]
            self.stairs_x = last_room.centerx
            self.stairs_y = last_room.centery
            self.tiles[self.stairs_x][self.stairs_y] = Tile(self.stairs_x, self.stairs_y, False, False, 'stairs')
        else:
            # Fallback if no rooms generated (shouldn't happen with BSP)
            self.player_start_x = self.width // 2
            self.player_start_y = self.height // 2


    def draw(self, surface, camera):
        """Draws the map."""
        cam_start_x = max(0, camera.map_view_x - 1)
        cam_start_y = max(0, camera.map_view_y - 1)
        cam_end_x = min(self.width, camera.map_view_x + camera.view_width // TILE_SIZE + 2)
        cam_end_y = min(self.height, camera.map_view_y + camera.view_height // TILE_SIZE + 2)

        for x in range(cam_start_x, cam_end_x):
             for y in range(cam_start_y, cam_end_y):
                tile = self.tiles[x][y]
                visible = self.is_visible_tile(x, y) # Simplified FoV
                if visible: # For now, all tiles are "visible" in concept
                    tile.explored = True # Mark as explored when "seen"
                    color = COLOR_FLOOR
                    if tile.type == 'wall':
                        color = COLOR_WALL
                    elif tile.type == 'door_closed':
                        color = COLOR_DOOR_CLOSED
                    elif tile.type == 'door_open':
                         color = COLOR_DOOR_OPEN
                    elif tile.type == 'stairs':
                        color = COLOR_STAIRS

                    wall_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(surface, color, camera.apply_rect(wall_rect))

                elif tile.explored: # Draw explored but not visible tiles in grey
                    color = COLOR_DARK_GREY if tile.type == 'floor' else COLOR_GREY
                    if tile.type == 'door_open': color = COLOR_DARK_GREY
                    if tile.type == 'stairs': color = COLOR_GREY # Show explored stairs

                    wall_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(surface, color, camera.apply_rect(wall_rect))


    def get_path(self, start_x, start_y, end_x, end_y):
        """Performs BFS to find a path."""
        if not self.is_walkable(start_x, start_y) or not self.is_walkable(end_x, end_y):
            return None

        queue = deque([(start_x, start_y, [])]) # x, y, path_list
        visited = set([(start_x, start_y)])

        while queue:
            x, y, path = queue.popleft()

            if x == end_x and y == end_y:
                return path

            # Check neighbors (including diagonals)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue

                    next_x, next_y = x + dx, y + dy

                    if (next_x, next_y) not in visited and self.is_walkable(next_x, next_y):
                        visited.add((next_x, next_y))
                        new_path = path + [(next_x, next_y)]
                        queue.append((next_x, next_y, new_path))

        return None # No path found

# --- BSP Tree Node ---
class BSPLeaf:
    """Node for the BSP tree."""
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.child_1 = None
        self.child_2 = None
        self.room = None
        self.connections = []

    def split(self):
        """Splits the leaf into two children."""
        if self.child_1 or self.child_2:
            return False

        split_horizontally = random.random() < 0.5
        if self.w > self.h and self.w / self.h >= 1.25:
            split_horizontally = True
        elif self.h > self.w and self.h / self.w >= 1.25:
            split_horizontally = False

        max_size = (self.h if split_horizontally else self.w) - BSP_MIN_LEAF_SIZE
        if max_size < BSP_MIN_LEAF_SIZE:
            return False

        split_pos = random.randint(BSP_MIN_LEAF_SIZE, max_size)

        if split_horizontally:
            self.child_1 = BSPLeaf(self.x, self.y, self.w, split_pos)
            self.child_2 = BSPLeaf(self.x, self.y + split_pos, self.w, self.h - split_pos)
        else:
            self.child_1 = BSPLeaf(self.x, self.y, split_pos, self.h)
            self.child_2 = BSPLeaf(self.x + split_pos, self.y, self.w - split_pos, self.h)

        return True

    def create_rooms(self, game_map):
        """Recursively creates rooms and connects them."""
        if self.child_1 or self.child_2:
            if self.child_1:
                self.child_1.create_rooms(game_map)
            if self.child_2:
                self.child_2.create_rooms(game_map)
            if self.child_1 and self.child_2:
                room1 = self.child_1.get_room()
                room2 = self.child_2.get_room()
                if room1 and room2:
                     self.connect_rooms(game_map, room1, room2)
        else:
            room_w = random.randint(ROOM_MIN_SIZE, max(ROOM_MIN_SIZE, self.w - ROOM_MAX_PADDING * 2))
            room_h = random.randint(ROOM_MIN_SIZE, max(ROOM_MIN_SIZE, self.h - ROOM_MAX_PADDING * 2))
            room_x = self.x + random.randint(ROOM_MAX_PADDING, max(ROOM_MAX_PADDING, self.w - room_w - ROOM_MAX_PADDING))
            room_y = self.y + random.randint(ROOM_MAX_PADDING, max(ROOM_MAX_PADDING, self.h - room_h - ROOM_MAX_PADDING))

            # Ensure room dimensions are positive
            if room_w < 1 or room_h < 1: return

            self.room = pygame.Rect(room_x, room_y, room_w, room_h)
            game_map.create_room(self.room)
            game_map.rooms.append(self.room)

    def get_room(self):
        """Finds a room in this leaf or its children."""
        if self.room:
            return self.room
        else:
            room1, room2 = None, None
            if self.child_1: room1 = self.child_1.get_room()
            if self.child_2: room2 = self.child_2.get_room()

            if room1 and room2: return random.choice([room1, room2])
            elif room1: return room1
            elif room2: return room2
            else: return None

    def connect_rooms(self, game_map, room1, room2):
        """Connects two rooms with a corridor."""
        center1_x, center1_y = room1.centerx, room1.centery
        center2_x, center2_y = room2.centerx, room2.centery

        if random.random() < 0.5:
            game_map.create_h_tunnel(center1_x, center2_x, center1_y)
            game_map.create_v_tunnel(center1_y, center2_y, center2_x)
        else:
            game_map.create_v_tunnel(center1_y, center2_y, center1_x)
            game_map.create_h_tunnel(center1_x, center2_x, center2_y)


# --- Entities ---
class Entity:
    """Base class for player and enemies."""
    def __init__(self, x, y, char, color, name, health=100, attack=5, blocks=True):
        self.x = x
        self.y = y
        self.char = char # Character representation (unused with rects)
        self.color = color
        self.name = name
        self.max_health = health
        self.health = health
        self.attack_power = attack
        self.blocks = blocks # Does this entity block movement?

    def move(self, dx, dy, game_map, entities, game): # Added game ref
        """Moves the entity by dx, dy if possible."""
        target_x = self.x + dx
        target_y = self.y + dy

        # Check map boundaries and walkability
        if not game_map.is_walkable(target_x, target_y):
            if 0 <= target_x < game_map.width and 0 <= target_y < game_map.height:
                 tile = game_map.tiles[target_x][target_y]
                 if tile.type == 'door_closed':
                     if isinstance(self, Player) and self.keys > 0:
                         self.use_key(target_x, target_y, game_map, game) # Pass game ref
                         return True # Action taken (opening door)
                     else:
                        if isinstance(self, Player): game.add_message("The door is locked. Find a key!", COLOR_WHITE)
                        return False
            return False

        # Check for blocking entities
        target_entity = get_blocking_entity_at(entities, target_x, target_y)
        if target_entity and target_entity != self:
            if isinstance(self, Player) and isinstance(target_entity, Enemy):
                self.attack(target_entity, game)
                return True # Attacking takes the turn
            elif isinstance(self, Enemy) and isinstance(target_entity, Player):
                self.attack(target_entity, game)
                return True
            else:
                 return False

        # Move the entity
        self.x = target_x
        self.y = target_y
        return True # Movement successful

    def take_damage(self, amount, game):
        """Handles taking damage."""
        self.health -= amount
        game.add_floating_text(str(amount), self.x, self.y, COLOR_DAMAGE_TEXT)
        if self.health <= 0:
            self.die(game)

    def attack(self, target, game):
        """Attacks another entity."""
        damage = self.attack_power
        game.add_message(f"{self.name} attacks {target.name} for {damage} damage!", COLOR_WHITE if isinstance(self, Player) else COLOR_ENEMY_ORC)
        target.take_damage(damage, game)

    def die(self, game):
        """Handles entity death."""
        game.add_message(f"{self.name} dies!", COLOR_ORANGE if isinstance(self, Enemy) else COLOR_GAME_OVER)
        self.blocks = False
        self.color = COLOR_DARK_GREY
        self.name = f"remains of {self.name}"
        # In a real game, might remove from entity list or change state further

    def heal(self, amount):
        """Heals the entity."""
        heal_amount = min(amount, self.max_health - self.health) # Can't heal over max
        self.health += heal_amount
        return heal_amount # Return how much was actually healed

    def draw(self, surface, camera):
        """Draws the entity."""
        entity_rect = pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(surface, self.color, camera.apply_rect(entity_rect))

        # Draw health bar
        if self.health < self.max_health and self.health > 0:
            bar_width = TILE_SIZE * (self.health / self.max_health)
            # Position bar slightly above the entity
            bar_y = self.y * TILE_SIZE - 6
            bg_rect = pygame.Rect(self.x * TILE_SIZE, bar_y, TILE_SIZE, 5)
            hp_rect = pygame.Rect(self.x * TILE_SIZE, bar_y, bar_width, 5)
            pygame.draw.rect(surface, COLOR_HEALTH_BAR_BG, camera.apply_rect(bg_rect))
            pygame.draw.rect(surface, COLOR_HEALTH_BAR, camera.apply_rect(hp_rect))

# --- Player ---
class Player(Entity):
    """The player character."""
    def __init__(self, x, y):
        super().__init__(x, y, '@', COLOR_PLAYER, "Player", health=PLAYER_START_HEALTH, attack=PLAYER_ATTACK)
        self.inventory = []
        self.keys = 0
        self.current_weapon = None # Track equipped weapon

    def pick_up_item(self, items, game):
        """Picks up an item at the player's location."""
        item_found = get_item_at(items, self.x, self.y)

        if item_found:
            if item_found.name == 'Key':
                 self.keys += 1
                 items.remove(item_found)
                 game.add_message(f"You picked up a {item_found.name}!", COLOR_KEY)
                 return True
            elif len(self.inventory) < PLAYER_INVENTORY_SIZE:
                self.inventory.append(item_found)
                items.remove(item_found)
                game.add_message(f"You picked up a {item_found.name}!", item_found.color)
                if isinstance(item_found, Weapon):
                    # Auto-equip if no weapon or if new weapon is better (simple check)
                    if self.current_weapon is None or item_found.attack_bonus > self.current_weapon.attack_bonus:
                        self.equip_weapon(item_found, game)
                return True
            else:
                game.add_message("Your inventory is full.", COLOR_GREY)
                return False
        else:
            game.add_message("There is nothing here to pick up.", COLOR_GREY)
            return False

    def use_item(self, item_index, game):
        """Uses an item from the inventory."""
        if 0 <= item_index < len(self.inventory):
            item = self.inventory[item_index]
            used = False
            if isinstance(item, HealthPotion):
                healed_amount = self.heal(item.amount)
                if healed_amount > 0:
                    game.add_message(f"You used a {item.name}, healing {healed_amount} HP.", COLOR_HEALTH_POTION)
                    used = True
                else:
                    game.add_message("You are already at full health.", COLOR_GREY)
                    return False # Didn't actually use it
            elif isinstance(item, Weapon):
                 self.equip_weapon(item, game)
                 # Equipping isn't 'using' in the consumable sense
                 return True # Action taken (equipped)

            if used:
                 self.inventory.pop(item_index)
            return True
        else:
            # game.add_message("Invalid item selection.", COLOR_GREY) # Already handled by index check
            return False

    def equip_weapon(self, weapon, game):
        """Equips a weapon, updating attack power."""
        # If already holding a weapon, potentially unequip it first (or swap)
        # For simplicity, we just replace. Item remains in inventory.
        if weapon in self.inventory:
            # Remove previous weapon bonus if one was equipped
            if self.current_weapon:
                 self.attack_power -= self.current_weapon.attack_bonus

            self.current_weapon = weapon
            self.attack_power = PLAYER_ATTACK + weapon.attack_bonus # Base + new bonus
            game.add_message(f"You equipped the {weapon.name} (+{weapon.attack_bonus} attack).", COLOR_WEAPON_SWORD)
        else:
            game.add_message("Cannot equip item not in inventory.", COLOR_GREY)


    def use_key(self, door_x, door_y, game_map, game):
        """Uses a key to open a door."""
        if self.keys > 0:
            tile = game_map.tiles[door_x][door_y]
            if tile.type == 'door_closed':
                tile.type = 'door_open'
                tile.blocked = False
                tile.block_sight = False
                self.keys -= 1
                game.add_message("You unlocked the door.", COLOR_KEY)
                return True
            else: # Trying to use key on not-a-closed-door
                 return False
        else:
            # Handled in move method
            # game.add_message("You need a key to open this door.", COLOR_WHITE)
            return False


# --- Enemies ---
class Enemy(Entity):
    """Base class for enemies."""
    def __init__(self, x, y, char, color, name, health, attack, sight_radius=ENEMY_SIGHT_RADIUS, attack_range=ENEMY_ATTACK_RANGE):
        super().__init__(x, y, char, color, name, health=health, attack=attack)
        self.sight_radius = sight_radius
        self.attack_range = attack_range
        self.current_path = None
        self.state = 'idle' # 'idle', 'chasing', 'attacking'

    def take_turn(self, player, game_map, entities, game):
        """Enemy AI logic."""
        dist_to_player = distance_grid(self.x, self.y, player.x, player.y)

        # Basic visibility: Check distance and if player is on an explored tile (simplistic FoV)
        player_tile_visible_ish = game_map.tiles[player.x][player.y].explored

        if dist_to_player <= self.sight_radius and player_tile_visible_ish:
            if dist_to_player <= self.attack_range:
                # Attempt to attack (move function handles attack if target is player)
                dx = player.x - self.x
                dy = player.y - self.y
                # Normalize dx/dy for movement attempt
                norm_dx = 0 if dx == 0 else int(dx / abs(dx))
                norm_dy = 0 if dy == 0 else int(dy / abs(dy))

                if self.move(norm_dx, norm_dy, game_map, entities, game):
                    self.state = 'attacking'
                    self.current_path = None
                else:
                     # If attack move failed (e.g., player moved away), try pathfinding
                     if dist_to_player > 1.5: # Not adjacent
                          self.move_towards(player.x, player.y, game_map, entities, game)
                     self.state = 'chasing'
            else:
                self.state = 'chasing'
                self.move_towards(player.x, player.y, game_map, entities, game)
        else:
            self.state = 'idle'
            self.current_path = None
            # Optional: Random wandering
            # if random.random() < 0.1:
            #     dx, dy = random.choice([(0,1), (0,-1), (1,0), (-1,0)])
            #     self.move(dx, dy, game_map, entities, game)

    def move_towards(self, target_x, target_y, game_map, entities, game):
        """Moves the enemy towards the target using BFS path."""
        if not self.current_path:
            path = game_map.get_path(self.x, self.y, target_x, target_y)
            if path:
                self.current_path = path

        if self.current_path:
            try:
                next_x, next_y = self.current_path.pop(0)
                dx = next_x - self.x
                dy = next_y - self.y
                if not self.move(dx, dy, game_map, entities, game):
                     self.current_path = None # Path blocked, recalculate next turn
                if not self.current_path:
                     self.current_path = None
            except IndexError:
                self.current_path = None

class Goblin(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 'g', COLOR_ENEMY_GOBLIN, "Goblin",
                         health=ENEMY_BASE_HEALTH, attack=ENEMY_BASE_ATTACK)

class Orc(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 'O', COLOR_ENEMY_ORC, "Orc",
                         health=ENEMY_BASE_HEALTH * 2, attack=ENEMY_BASE_ATTACK + 2, sight_radius=ENEMY_SIGHT_RADIUS -1)

# --- Items ---
class Item:
    """Base class for items."""
    def __init__(self, x, y, char, color, name):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name

    def draw(self, surface, camera):
        item_rect = pygame.Rect(self.x * TILE_SIZE + TILE_SIZE // 4,
                                 self.y * TILE_SIZE + TILE_SIZE // 4,
                                 TILE_SIZE // 2, TILE_SIZE // 2)
        pygame.draw.rect(surface, self.color, camera.apply_rect(item_rect))

class HealthPotion(Item):
    def __init__(self, x, y):
        super().__init__(x, y, '!', COLOR_HEALTH_POTION, "Health Potion")
        self.amount = HEALTH_POTION_AMOUNT

class Weapon(Item):
    def __init__(self, x, y, name="Sword", attack_bonus=SWORD_ATTACK_BONUS):
        super().__init__(x, y, '/', COLOR_WEAPON_SWORD, name)
        self.attack_bonus = attack_bonus

class Key(Item):
    def __init__(self, x, y):
        super().__init__(x, y, 'k', COLOR_KEY, "Key")


# --- Utility Classes ---

class Camera:
    """Handles scrolling the map."""
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.map_width_pixels = 0
        self.map_height_pixels = 0
        self.view_width = SCREEN_WIDTH
        self.view_height = SCREEN_HEIGHT - HUD_HEIGHT

        self.map_view_x = 0
        self.map_view_y = 0

    def set_map_size(self, map_width, map_height):
        self.map_width_pixels = map_width * TILE_SIZE
        self.map_height_pixels = map_height * TILE_SIZE

    def apply(self, entity):
        """Adjusts entity coordinates based on camera position."""
        return entity.rect.move(self.camera.topleft) # Assumes entity has a rect

    def apply_rect(self, rect):
        """Adjusts rectangle coordinates based on camera position."""
        return rect.move(self.camera.topleft)

    def update(self, target):
        """Updates the camera position to follow the target entity."""
        if not target: return # Don't update if target is None

        target_x_pixel = target.x * TILE_SIZE
        target_y_pixel = target.y * TILE_SIZE

        x = -target_x_pixel + int(self.view_width / 2)
        y = -target_y_pixel + int(self.view_height / 2)

        # Clamp camera
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.map_width_pixels - self.view_width), x)
        y = max(-(self.map_height_pixels - self.view_height), y)

        self.camera = pygame.Rect(x, y, self.width, self.height)

        # Update map view boundaries (approximate)
        self.map_view_x = -x // TILE_SIZE
        self.map_view_y = -y // TILE_SIZE


class FloatingText:
    """Displays temporary text that floats up and fades."""
    def __init__(self, text, x, y, color, duration=FPS):
        self.text = text
        self.x = x # Tile coordinates
        self.y = y # Tile coordinates
        self.color = color
        self.duration = duration
        self.timer = duration
        self.offset_y = 0

    def update(self):
        self.timer -= 1
        self.offset_y -= 0.5 # Float upwards

    def draw(self, surface, camera, font_size=20):
        if self.timer > 0:
            pixel_x = self.x * TILE_SIZE + TILE_SIZE // 2
            pixel_y = self.y * TILE_SIZE + TILE_SIZE // 2 + int(self.offset_y)
            # Apply camera offset manually for floating text
            draw_text(surface, self.text, font_size,
                      pixel_x + camera.camera.x, pixel_y + camera.camera.y,
                      self.color, align="center")


# --- Game Class ---
HUD_HEIGHT = 120 # Increased HUD height slightly
MESSAGE_LOG_MAX = 6

class Game:
    """Main game class."""
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(200, 75) # Enable key repeat
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Simple Pygame Roguelike")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)

        self.game_state = STATE_MAIN_MENU
        self.current_floor = 1
        self.player = None
        self.game_map = None
        self.entities = []
        self.items = []
        self.camera = Camera(MAP_WIDTH * TILE_SIZE, MAP_HEIGHT * TILE_SIZE)
        self.floating_texts = []
        self.message_log = []
        self.player_turn = True

        # Menu state
        self.menu_options = ["New Game", "Load Game", "Quit"]
        self.selected_option = 0
        self.save_exists = os.path.exists(SAVE_FILENAME)


    def reset_game_vars(self):
        """Resets variables for a new game or floor."""
        self.current_floor = 1
        self.player = None
        self.game_map = None
        self.entities = []
        self.items = []
        self.floating_texts = []
        self.message_log = []
        self.player_turn = True

    def new_game(self):
        """Starts a new game."""
        self.reset_game_vars()
        self.setup_floor()
        self.game_state = STATE_PLAYING
        self.add_message("Welcome to the Dungeon!", COLOR_WHITE)
        self.add_message("Use WASD/Arrows to move, G to get items, 1-5 to use.", COLOR_GREY)
        self.add_message("Press P to Save, ESC to return to Menu.", COLOR_GREY)


    def next_floor(self):
        """Progresses to the next floor."""
        self.current_floor += 1
        if self.current_floor > NUM_FLOORS:
            self.game_state = STATE_VICTORY
        else:
            self.game_state = STATE_LEVEL_TRANSITION
            self.add_message(f"You descend to floor {self.current_floor}...", COLOR_STAIRS)
            pygame.time.wait(500) # Short delay
            # Clear volatile data before setting up next floor
            self.floating_texts = []
            # Keep player object, items in inventory, keys etc.
            # Reset map, non-player entities, items on ground
            self.entities = [self.player] # Keep only player
            self.items = []
            self.setup_floor() # This places player, spawns new enemies/items
            self.game_state = STATE_PLAYING


    def setup_floor(self):
        """Sets up entities and map for the current floor."""
        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT, self.current_floor)
        self.game_map.generate_bsp()
        self.camera.set_map_size(self.game_map.width, self.game_map.height)

        if not self.player:
            self.player = Player(self.game_map.player_start_x, self.game_map.player_start_y)
        else:
             self.player.x = self.game_map.player_start_x
             self.player.y = self.game_map.player_start_y
             # Ensure player is the first entity for drawing/update order if needed
             if self.player not in self.entities:
                 self.entities.insert(0, self.player)

        # Ensure player is in entities list (might have been cleared on next_floor)
        if self.player not in self.entities:
             self.entities.insert(0, self.player)

        self.spawn_entities()
        self.spawn_items()
        self.player_turn = True
        self.camera.update(self.player) # Initial camera position


    def spawn_entities(self):
        """Spawns enemies."""
        num_enemies = self.current_floor * 3 + random.randint(0, 2)

        for _ in range(num_enemies):
            room = random.choice(self.game_map.rooms) if self.game_map.rooms else None
            if not room: continue # Skip if no rooms

            x = random.randint(room.x + 1, room.x + room.w - 1)
            y = random.randint(room.y + 1, room.y + room.h - 1)

            if not get_blocking_entity_at(self.entities, x, y):
                if random.random() < 0.7:
                    enemy = Goblin(x, y)
                else:
                    enemy = Orc(x, y)

                enemy.max_health += self.current_floor * 2
                enemy.health = enemy.max_health
                enemy.attack_power += self.current_floor // 2

                self.entities.append(enemy)

    def spawn_items(self):
        """Spawns items."""
        num_items = self.current_floor * 1 + random.randint(1, 3)

        for _ in range(num_items):
             room = random.choice(self.game_map.rooms) if self.game_map.rooms else None
             if not room: continue

             x = random.randint(room.x + 1, room.x + room.w - 1)
             y = random.randint(room.y + 1, room.y + room.h - 1)

             if not get_blocking_entity_at(self.entities, x, y) and not get_item_at(self.items, x, y):
                 item_chance = random.random()
                 if item_chance < 0.55:
                     item = HealthPotion(x, y)
                 elif item_chance < 0.80:
                      item = Weapon(x, y)
                 elif item_chance < 0.95:
                      item = Key(x, y)
                 # else: 5% nothing spawned here

                 if 'item' in locals(): # Check if item was created
                    self.items.append(item)
                    del item # clean up local var

    def add_message(self, text, color=COLOR_WHITE):
        """Adds a message to the game log."""
        self.message_log.insert(0, (text, color))
        if len(self.message_log) > MESSAGE_LOG_MAX:
            self.message_log.pop()

    def add_floating_text(self, text, x, y, color):
        """Adds floating text effect."""
        self.floating_texts.append(FloatingText(text, x, y, color))


    def run(self):
        """Main game loop."""
        running = True
        while running:
            # Event handling depends on state
            running = self.events()

            # Updates depend on state
            if self.game_state == STATE_PLAYING:
                self.update()
            elif self.game_state == STATE_LEVEL_TRANSITION:
                # Usually handled synchronously within next_floor, but could have animation here
                pass

            # Rendering depends on state
            self.render()

            self.clock.tick(FPS)

        pygame.quit()


    def events(self):
        """Handles input and events based on game state. Returns False if quit."""
        player_action_taken = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False # Signal to exit main loop

            # --- Global Keys (Work in most states) ---
            if event.type == pygame.KEYDOWN:
                 if event.key == pygame.K_ESCAPE:
                    if self.game_state == STATE_PLAYING:
                        # Go back to main menu (lose progress unless saved)
                        self.game_state = STATE_MAIN_MENU
                        # Refresh save status in case user saved then escaped
                        self.save_exists = os.path.exists(SAVE_FILENAME)
                    elif self.game_state in [STATE_GAME_OVER, STATE_VICTORY]:
                         return False # Quit from end screens
                    elif self.game_state == STATE_MAIN_MENU:
                         # Allow ESC to quit from main menu as well
                         if self.selected_option == self.menu_options.index("Quit"):
                             return False
                         else: # Or select Quit option
                             self.selected_option = self.menu_options.index("Quit")


            # --- State-Specific Input ---
            if self.game_state == STATE_MAIN_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.selected_option = (self.selected_option - 1) % len(self.menu_options)
                    elif event.key == pygame.K_DOWN:
                        self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                    elif event.key == pygame.K_RETURN:
                        selected_action = self.menu_options[self.selected_option]
                        if selected_action == "New Game":
                            self.new_game()
                        elif selected_action == "Load Game":
                            if self.save_exists:
                                self.load_game()
                            else:
                                print("DEBUG: No save file found.") # Add feedback later
                        elif selected_action == "Quit":
                            return False # Quit

            elif self.game_state == STATE_PLAYING:
                if self.player_turn:
                    if event.type == pygame.KEYDOWN:
                        dx, dy = 0, 0
                        action_key = None

                        if event.key == pygame.K_UP or event.key == pygame.K_w: dy = -1
                        elif event.key == pygame.K_DOWN or event.key == pygame.K_s: dy = 1
                        elif event.key == pygame.K_LEFT or event.key == pygame.K_a: dx = -1
                        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d: dx = 1
                        elif event.key == pygame.K_g: action_key = 'get'
                        elif event.key == pygame.K_SPACE: action_key = 'wait'
                        elif event.key == pygame.K_p: action_key = 'save' # Save key
                        elif pygame.K_1 <= event.key <= pygame.K_5:
                             action_key = 'use_item'
                             item_index = event.key - pygame.K_1

                        # Process action
                        if dx != 0 or dy != 0:
                            if self.player.move(dx, dy, self.game_map, self.entities, self):
                                 player_action_taken = True
                        elif action_key == 'get':
                             if self.player.pick_up_item(self.items, self):
                                  player_action_taken = True
                        elif action_key == 'wait':
                             player_action_taken = True
                        elif action_key == 'save':
                             self.save_game()
                             # Saving does NOT take a turn
                        elif action_key == 'use_item':
                             if self.player.use_item(item_index, self):
                                  player_action_taken = True

                        # Check for stairs after move/action
                        if player_action_taken and self.player.x == self.game_map.stairs_x and self.player.y == self.game_map.stairs_y:
                            self.next_floor()
                            # next_floor changes state, stops further processing this turn


                # If player took an action, switch to enemy turn
                if player_action_taken and self.game_state == STATE_PLAYING: # Check state hasn't changed
                    self.player_turn = False


            elif self.game_state in [STATE_GAME_OVER, STATE_VICTORY]:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.game_state = STATE_MAIN_MENU # Go back to menu after game end
                        self.save_exists = os.path.exists(SAVE_FILENAME) # Update save status
                    # ESC handling is now global

        return True # Continue running


    def update(self):
        """Updates game logic (only called when STATE_PLAYING)."""
        if not self.player: return # Should not happen in PLAYING state, but safety check

        if self.player.health <= 0:
            self.game_state = STATE_GAME_OVER
            return

        # Enemy turns
        if not self.player_turn:
            active_enemies = [e for e in self.entities if isinstance(e, Enemy) and e.health > 0]
            for enemy in active_enemies:
                 if self.player.health > 0: # Check again in case player died from last enemy
                    enemy.take_turn(self.player, self.game_map, self.entities, self)

            # Check if player died during enemy turns
            if self.player.health <= 0:
                 self.game_state = STATE_GAME_OVER
                 return

            # Switch back to player turn
            self.player_turn = True

        # Update camera (follows player)
        self.camera.update(self.player)

        # Update floating texts
        self.floating_texts = [t for t in self.floating_texts if t.timer > 0]
        for text in self.floating_texts:
             text.update()

        # Update entities (animations, effects - none currently)
        # for entity in self.entities: entity.update()


    def render(self):
        """Draws everything based on the current game state."""
        self.screen.fill(COLOR_BLACK)

        if self.game_state == STATE_MAIN_MENU:
            self.render_main_menu()
        elif self.game_state in [STATE_PLAYING, STATE_LEVEL_TRANSITION, STATE_GAME_OVER, STATE_VICTORY]:
            # Render the game world (map, items, entities)
            if self.game_map and self.player: # Ensure map and player exist
                self.game_map.draw(self.screen, self.camera)
                for item in self.items:
                    if self.game_map.tiles[item.x][item.y].explored: # Draw explored items
                        item.draw(self.screen, self.camera)
                for entity in sorted(self.entities, key=lambda e: 1 if isinstance(e, Player) else 0):
                    if self.game_map.tiles[entity.x][entity.y].explored: # Draw explored entities
                         entity.draw(self.screen, self.camera)
                for text in self.floating_texts:
                    text.draw(self.screen, self.camera)

                # Draw HUD on top
                self.draw_hud()

            # Render overlays for game end states
            if self.game_state == STATE_GAME_OVER:
                self.render_game_over_screen()
            elif self.game_state == STATE_VICTORY:
                 self.render_victory_screen()
            elif self.game_state == STATE_LEVEL_TRANSITION:
                 # Could draw a "Descending..." message overlay here
                 pass

        pygame.display.flip()


    def render_main_menu(self):
        """Draws the main menu screen."""
        title_y = SCREEN_HEIGHT // 4
        draw_text(self.screen, "PYTHON ROGUELIKE", 64, SCREEN_WIDTH // 2, title_y, COLOR_MENU_TITLE, align="center")

        menu_start_y = SCREEN_HEIGHT // 2
        option_height = 50
        for i, option in enumerate(self.menu_options):
            y = menu_start_y + i * option_height
            color = COLOR_MENU_SELECTED if i == self.selected_option else COLOR_MENU_NORMAL
            # Grey out Load Game if no save exists
            if option == "Load Game" and not self.save_exists:
                 color = COLOR_DARK_GREY

            draw_text(self.screen, option, 48, SCREEN_WIDTH // 2, y, color, align="center")

    def render_game_over_screen(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, "GAME OVER", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, COLOR_GAME_OVER, align="center")
        draw_text(self.screen, "Press ENTER for Menu or ESC to quit", 32, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50, COLOR_WHITE, align="center")

    def render_victory_screen(self):
         overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
         overlay.fill((0, 0, 0, 180))
         self.screen.blit(overlay, (0, 0))
         draw_text(self.screen, "VICTORY!", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, COLOR_VICTORY, align="center")
         draw_text(self.screen, "You cleared the dungeon!", 32, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20, COLOR_WHITE, align="center")
         draw_text(self.screen, "Press ENTER for Menu or ESC to quit", 32, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70, COLOR_WHITE, align="center")

    def draw_hud(self):
        """Draws the Heads-Up Display."""
        if not self.player: return # Can't draw HUD without player

        hud_panel = pygame.Rect(0, SCREEN_HEIGHT - HUD_HEIGHT, SCREEN_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_HUD_BG, hud_panel)

        # --- Column 1: Player Stats ---
        col1_x = 15
        draw_text(self.screen, f"HP: {self.player.health}/{self.player.max_health}", 24, col1_x, SCREEN_HEIGHT - HUD_HEIGHT + 5, COLOR_WHITE)
        draw_text(self.screen, f"ATK: {self.player.attack_power}", 24, col1_x, SCREEN_HEIGHT - HUD_HEIGHT + 30, COLOR_WHITE)
        draw_text(self.screen, f"Keys: {self.player.keys}", 24, col1_x, SCREEN_HEIGHT - HUD_HEIGHT + 55, COLOR_KEY)
        draw_text(self.screen, f"Floor: {self.current_floor}/{NUM_FLOORS}", 24, col1_x, SCREEN_HEIGHT - HUD_HEIGHT + 80, COLOR_WHITE)


        # --- Column 2: Inventory ---
        col2_x = 200
        inv_y = SCREEN_HEIGHT - HUD_HEIGHT + 5
        draw_text(self.screen, "Inventory (1-5 to use):", 22, col2_x, inv_y, COLOR_HUD_TEXT)
        for i, item in enumerate(self.player.inventory):
             item_text = f"{i+1}. {item.name}"
             item_text += f" (+{item.attack_bonus})" if isinstance(item, Weapon) else ""
             color = item.color
             if isinstance(item, Weapon) and item == self.player.current_weapon:
                  color = COLOR_WHITE # Highlight equipped weapon
             draw_text(self.screen, item_text, 20, col2_x + 10, inv_y + 25 + i * 18, color)

        # --- Column 3: Message Log ---
        col3_x = 500 # Shifted right
        log_y = SCREEN_HEIGHT - HUD_HEIGHT + 5
        draw_text(self.screen, "Log:", 22, col3_x, log_y, COLOR_HUD_TEXT)
        for i, (msg, color) in enumerate(self.message_log):
             draw_text(self.screen, msg, 18, col3_x + 5, log_y + 25 + i * 17, color)


        # --- Turn Indicator (Top Right of HUD) ---
        turn_text = "Player Turn" if self.player_turn else "Enemy Turn"
        turn_color = COLOR_PLAYER if self.player_turn else COLOR_ENEMY_ORC
        draw_text(self.screen, turn_text, 24, SCREEN_WIDTH - 15, SCREEN_HEIGHT - HUD_HEIGHT + 5, turn_color, align="topright")


    def save_game(self):
        """Saves the current game state to a file."""
        # Consolidate all necessary data into a dictionary
        save_data = {
            'current_floor': self.current_floor,
            'player': self.player, # Pickles the player object directly
            'entities': [e for e in self.entities if e != self.player], # Save non-player entities
            'items': self.items, # Items on the ground
            'game_map': { # Save relevant map data, not the whole object easily
                 'width': self.game_map.width,
                 'height': self.game_map.height,
                 'tiles': self.game_map.tiles, # This saves the 2D list of Tile objects
                 'stairs_x': self.game_map.stairs_x,
                 'stairs_y': self.game_map.stairs_y,
                 'rooms': self.game_map.rooms # Optional, but helps if needed later
            },
            'message_log': self.message_log,
            'player_turn': self.player_turn,
            # Add other necessary states here
        }
        try:
            with open(SAVE_FILENAME, 'wb') as f:
                pickle.dump(save_data, f, pickle.HIGHEST_PROTOCOL)
            self.add_message("Game Saved!", COLOR_WHITE)
            self.save_exists = True # Update menu flag
            print("DEBUG: Game Saved Successfully.")
        except Exception as e:
            self.add_message("Error saving game!", COLOR_RED)
            print(f"Error saving game: {e}")

    def load_game(self):
        """Loads the game state from a file."""
        if not os.path.exists(SAVE_FILENAME):
            self.add_message("No save file found!", COLOR_RED)
            self.game_state = STATE_MAIN_MENU # Go back to menu
            return

        try:
            with open(SAVE_FILENAME, 'rb') as f:
                save_data = pickle.load(f)

            # Restore game state from the dictionary
            self.current_floor = save_data['current_floor']
            self.player = save_data['player']
            loaded_entities = save_data['entities']
            self.items = save_data['items']
            self.message_log = save_data['message_log']
            self.player_turn = save_data['player_turn']

            # Reconstruct GameMap
            map_data = save_data['game_map']
            self.game_map = GameMap(map_data['width'], map_data['height'], self.current_floor)
            self.game_map.tiles = map_data['tiles']
            self.game_map.stairs_x = map_data['stairs_x']
            self.game_map.stairs_y = map_data['stairs_y']
            self.game_map.rooms = map_data['rooms'] # Restore rooms list

            # Combine player and loaded entities
            self.entities = [self.player] + loaded_entities

            # Re-setup camera based on loaded map/player
            self.camera.set_map_size(self.game_map.width, self.game_map.height)
            self.camera.update(self.player)

            # Clear transient data
            self.floating_texts = []

            self.game_state = STATE_PLAYING
            self.add_message("Game Loaded!", COLOR_WHITE)
            print("DEBUG: Game Loaded Successfully.")

        except Exception as e:
            self.add_message("Error loading game!", COLOR_RED)
            print(f"Error loading game: {e}")
            # If loading fails, return to main menu safely
            self.reset_game_vars() # Clear potentially corrupted state
            self.game_state = STATE_MAIN_MENU
            self.save_exists = os.path.exists(SAVE_FILENAME) # Re-check save status


# --- Global Helper Functions ---

def get_blocking_entity_at(entities, x, y):
    """Finds a blocking entity at a given location."""
    for entity in entities:
        if entity.blocks and entity.x == x and entity.y == y and entity.health > 0:
            return entity
    return None

def get_item_at(items, x, y):
    """Finds an item at a given location."""
    for item in items:
        if item.x == x and item.y == y:
            return item
    return None

# --- Main Execution ---
if __name__ == '__main__':
    # Ensure Pygame fonts are initialized
    pygame.font.init()
    game = Game()
    game.run()
