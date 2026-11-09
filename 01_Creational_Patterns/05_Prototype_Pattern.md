# Prototype Pattern

## Category: Creational Pattern

---

## 1. Core Intent & Definition
Specify the kinds of objects to create using a prototypical instance, and create new objects by copying this prototype rather than through expensive initialization.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Instantiating complex domain objects from scratch involves expensive database reads, network lookups, and parsing operations. If 1,000 similar objects are needed, repeating this pipeline exhausts CPU and increases latency.

### Real-World Industry Example:
Game Entity Spawning / Document Template Generator. In a real-time multiplayer combat simulation, spawning 500 enemy NPC soldiers with identical mesh physics, armor, weapon stats, and behavior trees from disk is too slow. A base prototype is loaded once into memory and cloned with unique IDs and coordinates.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------------------+
|             Prototype             |
+-----------------------------------+
| + clone(): Prototype              |
+-----------------------------------+
                  ▲
                  │
+-----------------------------------+
|           EnemySoldier            |
+-----------------------------------+
| - weaponStats: object             |
| - health: number                  |
| - position: { x, y }              |
+-----------------------------------+
| + clone(): EnemySoldier           |
+-----------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface Clonable<T> {
  clone(): T;
}

export interface WeaponLoadout {
  primary: string;
  damage: number;
  ammoCapacity: number;
}

export class EnemyNpc implements Clonable<EnemyNpc> {
  public id: string;
  public rank: string;
  public health: number;
  public position: { x: number; y: number };
  public loadout: WeaponLoadout;

  constructor(
    id: string,
    rank: string,
    health: number,
    position: { x: number; y: number },
    loadout: WeaponLoadout
  ) {
    this.id = id;
    this.rank = rank;
    this.health = health;
    this.position = position;
    this.loadout = loadout;
  }

  /**
   * Deep Copy Clone implementation.
   * Ensures mutable nested objects (loadout, position) do not share references.
   */
  public clone(): EnemyNpc {
    return new EnemyNpc(
      `npc-${crypto.randomUUID().slice(0, 8)}`,
      this.rank,
      this.health,
      { ...this.position },
      { ...this.loadout }
    );
  }
}

// Prototype Registry
export class PrototypeRegistry {
  private prototypes = new Map<string, Clonable<any>>();

  register(name: string, prototype: Clonable<any>): void {
    this.prototypes.set(name, prototype);
  }

  create(name: string): any {
    const proto = this.prototypes.get(name);
    if (!proto) {
      throw new Error(`Prototype with key "${name}" not found in registry.`);
    }
    return proto.clone();
  }
}

// --- Usage ---
const registry = new PrototypeRegistry();

// Initialize expensive template once
const eliteSniperPrototype = new EnemyNpc(
  "base-sniper",
  "ELITE",
  100,
  { x: 0, y: 0 },
  { primary: "Barrett .50", damage: 150, ammoCapacity: 5 }
);
registry.register("ELITE_SNIPER", eliteSniperPrototype);

// Instant cheap clones during gameplay
const spawnedSniper1 = registry.create("ELITE_SNIPER");
spawnedSniper1.position.x = 250;

const spawnedSniper2 = registry.create("ELITE_SNIPER");
spawnedSniper2.position.x = 420;

console.log("Clone 1 ID:", spawnedSniper1.id, "Pos:", spawnedSniper1.position);
console.log("Clone 2 ID:", spawnedSniper2.id, "Pos:", spawnedSniper2.position);
```

---

## 5. Edge Cases & Failure Handling
- **Shallow vs Deep Copy**: A shallow copy only duplicates top-level primitives. Modifying a nested object (e.g. `clone.loadout.damage = 999`) will corrupt the original prototype if deep cloning is omitted.\n- **Circular References**: Objects containing circular pointer graphs cause infinite recursion during naive recursive serialization cloning.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When object creation is computationally or I/O expensive.\n- When your code shouldn't depend on the concrete classes of objects you need to copy.\n- When avoiding inheritance subclasses that differ only in initial variable states.

### When NOT to Use / Anti-patterns:
- Cloning complex objects with circular references or external socket/file handles that cannot be cloned safely.
