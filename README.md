# 🗡️ Python Roguelike

A **turn-based, procedurally generated roguelike game** built entirely in **Python** using **PyGame** — all in a single `.py` file!

Inspired by classics like *The Binding of Isaac*, *NetHack*, and *Rogue*, this project showcases procedural level design, enemy AI, inventory management, turn-based combat, and a fully playable game loop — with save/load support and victory conditions.

## 🎮 Features

- 🔁 **Procedural Dungeon Generation** using Binary Space Partitioning (BSP)
- 👾 **Multiple Enemy Types** with pathfinding AI (Goblins, Orcs, etc.)
- ⚔️ **Turn-Based Combat System** (Player vs. AI)
- 🧠 **Enemy State Behavior** (idle, chase, attack)
- 🧭 **Camera System** with smooth scrolling
- 🗝️ **Items & Inventory**
  - Health Potions (heal HP)
  - Weapons (boost attack)
  - Keys (unlock doors)
- 📦 **Save/Load System** using `pickle`
- 📈 **Difficulty Scaling** across multiple floors
- 💬 **Floating Damage Text + Message Log**
- 🎨 **ASCII-style Graphics** with HUD and health bars
- 🏆 **Victory & Game Over Screens**
- 🧪 **Fully Playable Game Loop** with menu, transitions, and restart

---



---

## 🚀 Getting Started

### Requirements

- Python 3.8+
- `pygame` library

### Installation

1. Clone this repo or download `game.py`
2. Install PyGame if you don’t have it:

```bash
pip install pygame
```

3. Run the game:

```bash
python game.py
```

---

## 🕹️ Controls

| Key         | Action                      |
|-------------|-----------------------------|
| `WASD` / Arrows | Move player             |
| `G`         | Pick up item                |
| `1`–`5`     | Use inventory item          |
| `Space`     | Wait / skip turn            |
| `P`         | Save game                   |
| `ESC`       | Main menu / Quit            |
| `Enter`     | Confirm selection (Menu)    |

---

## 📁 Save System

The game auto-saves when you press `P`. The save file is stored as:

```
savegame.dat
```

You can load the game from the main menu if the file exists.

---

## 🧠 Design Notes

- All logic is implemented in a **single `.py` file** for simplicity and portability.
- Procedural maps are generated via **Binary Space Partitioning** (BSP), creating unique dungeon layouts each run.
- The game uses a **turn system** (Player → Enemies → Player), with each action taking one turn.
- Pathfinding is implemented via **Breadth-First Search (BFS)** for enemy navigation.
- Designed with future extensions in mind: ranged enemies, FOV, status effects, mini-map, etc.

---

## 📦 File Structure

```
game.py          # The complete roguelike game (single-file)
savegame.dat     # Save file (created after pressing 'P')
```

---

## 💡 Future Ideas (Optional Enhancements)

- Field of View (FOV) / Fog of War
- Ranged enemies / special attacks
- Sound effects and background music
- Minimap
- Quest system or boss fights
- Visual polish with sprite assets
- Persistent stats / high scores

---

## 👨‍💻 Author

Built with ❤️ and `pygame` by Preetham  
→ Want to show off your version? Fork it, add features, and drop a PR or screenshot!

---
