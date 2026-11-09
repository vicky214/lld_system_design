# Flyweight Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Use sharing to support large numbers of fine-grained objects efficiently by separating intrinsic state (shared, immutable) from extrinsic state (unique, context-dependent).

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Rendering 1,000,000 forest trees in a 3D game or loading 500,000 formatted text characters in a word processor exhausts memory (e.g. allocating 2GB of RAM) if each object stores its own texture mesh, font metrics, and color palettes.

### Real-World Industry Example:
Rich Text Document Editor / Gaming Particle Engine. 1,000,000 character glyphs rendered in a document. The font family, size, weight, and vector outline (Intrinsic State) are shared, while character code and screen coordinates (Extrinsic State) are unique.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------------------------------------+
|                    FlyweightFactory                   |
+-------------------------------------------------------+
| - flyweights: Map<string, FontFlyweight>              |
+-------------------------------------------------------+
| + getFont(fontFamily, size, bold): FontFlyweight      |
+-------------------------------------------------------+
                           │ (Returns shared instance)
                           ▼
+-------------------------------------------------------+
|                     FontFlyweight                     | (Intrinsic State)
+-------------------------------------------------------+
| - fontFamily: string                                  |
| - size: number                                        |
| - isBold: boolean                                     |
| - vectorGlyphMesh: Buffer (Heavy: 500KB)              |
+-------------------------------------------------------+
| + render(char: string, x: number, y: number): void    | (Extrinsic)
+-------------------------------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Flyweight: Stores Intrinsic (Shared) Immutable State
export class CharacterFormatFlyweight {
  public readonly fontFamily: string;
  public readonly fontSize: number;
  public readonly isBold: boolean;
  public readonly colorHex: string;

  constructor(fontFamily: string, fontSize: number, isBold: boolean, colorHex: string) {
    this.fontFamily = fontFamily;
    this.fontSize = fontSize;
    this.isBold = isBold;
    this.colorHex = colorHex;
  }

  // Receives Extrinsic (Unique) State at runtime
  render(char: string, x: number, y: number): void {
    // In real engines, this invokes GPU draw calls
    // console.log(`Draw '${char}' at (${x},${y}) using ${this.fontFamily} ${this.fontSize}px ${this.colorHex}`);
  }
}

// 2. Flyweight Factory: Caches and reuses shared instances
export class FormatFlyweightFactory {
  private static pool = new Map<string, CharacterFormatFlyweight>();

  public static getFormat(fontFamily: string, fontSize: number, isBold: boolean, colorHex: string): CharacterFormatFlyweight {
    const key = `${fontFamily}_${fontSize}_${isBold}_${colorHex}`;
    let format = FormatFlyweightFactory.pool.get(key);

    if (!format) {
      format = new CharacterFormatFlyweight(fontFamily, fontSize, isBold, colorHex);
      FormatFlyweightFactory.pool.set(key, format);
    }

    return format;
  }

  public static getPoolSize(): number {
    return FormatFlyweightFactory.pool.size;
  }
}

// 3. Context Object: Stores Extrinsic State & Holds reference to Flyweight
export class CharacterGlyph {
  public char: string;
  public x: number;
  public y: number;
  public format: CharacterFormatFlyweight; // Reference to shared flyweight

  constructor(char: string, x: number, y: number, format: CharacterFormatFlyweight) {
    this.char = char;
    this.x = x;
    this.y = y;
    this.format = format;
  }

  draw(): void {
    this.format.render(this.char, this.x, this.y);
  }
}

// --- Usage Simulation ---
console.log("Simulating loading a 100,000-character document...");
const documentGlyphs: CharacterGlyph[] = [];

for (let i = 0; i < 100000; i++) {
  // Most text uses identical styles (e.g. Body text vs Heading)
  const isHeading = i % 500 === 0;
  const format = isHeading
    ? FormatFlyweightFactory.getFormat("Inter", 24, true, "#111827")
    : FormatFlyweightFactory.getFormat("Inter", 14, false, "#4B5563");

  documentGlyphs.push(new CharacterGlyph("A", i % 80, Math.floor(i / 80), format));
}

console.log(`✓ Total Character Glyphs allocated: ${documentGlyphs.length}`);
console.log(`✓ Unique Flyweight format objects in memory: ${FormatFlyweightFactory.getPoolSize()}`);
console.log(`Memory optimization: 100,000 items sharing only 2 format memory allocations!`);
```

---

## 5. Edge Cases & Failure Handling
- **Accidental Mutation of Intrinsic State**: Flyweights MUST be strictly immutable (using `readonly` / `Object.freeze`). If one client mutates a flyweight property, it inadvertently modifies millions of objects sharing that flyweight.\n- **CPU vs Memory Trade-off**: Flyweights save massive amounts of RAM, but computing and passing extrinsic parameters during every render loop incurs minor CPU cycles.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When your application needs to spawn millions of similar objects.\n- When RAM consumption is a critical bottleneck.\n- When duplicate state can be neatly separated into intrinsic (shared) and extrinsic (contextual) components.

### When NOT to Use / Anti-patterns:
- When memory is not a constraint or objects have unique properties that cannot be shared.
