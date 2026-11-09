# Composite Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Compose objects into tree structures to represent part-whole hierarchies. Composite lets clients treat individual objects and compositions of objects uniformly.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
In e-commerce catalogs or organization hierarchies, orders can contain standalone individual items (a single book) or bundled packages (a gaming bundle containing a console, 2 games, and cables, where cables are themselves a sub-bundle). Writing separate logic to calculate pricing, shipping weights, or discounts for items vs bundles introduces nested branching spaghetti.

### Real-World Industry Example:
Multi-Level E-Commerce Bundle Pricing & Discount Rollup Engine. Calculates aggregate prices, stock validation, and promotional discounts across arbitrarily nested item hierarchies.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------+
                       |     CatalogComponent    | (Component)
                       +-------------------------+
                       | + getPrice(): number    |
                       | + getWeightKg(): number |
                       | + display(indent): void |
                       +-------------------------+
                                    ▲
                   ┌────────────────┴────────────────┐
                   │                                 │
        +--------------------+            +--------------------+
        |    SingleProduct   | (Leaf)     |     ProductBundle  | (Composite)
        +--------------------+            +--------------------+
        | - price: number    |            | - children: Comp[] |
        | - weightKg: number |            +--------------------+
        +--------------------+            | + add(component)   |
                                          | + getPrice(): sum  |
                                          +--------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Component Interface
export interface CatalogComponent {
  getName(): string;
  getPrice(): number;
  getWeightKg(): number;
  display(indent?: string): void;
}

// 2. Leaf Node: Single Standalone Product
export class ProductItem implements CatalogComponent {
  private name: string;
  private price: number;
  private weightKg: number;

  constructor(name: string, price: number, weightKg: number) {
    this.name = name;
    this.price = price;
    this.weightKg = weightKg;
  }

  getName(): string { return this.name; }
  getPrice(): number { return this.price; }
  getWeightKg(): number { return this.weightKg; }

  display(indent = ""): void {
    console.log(`${indent}📦 Item: ${this.name} | Price: $${this.price} | Weight: ${this.weightKg}kg`);
  }
}

// 3. Composite Node: Bundle containing Products and/or Sub-Bundles
export class ProductBundle implements CatalogComponent {
  private name: string;
  private discountPercentage: number;
  private children: CatalogComponent[] = [];

  constructor(name: string, discountPercentage = 0) {
    this.name = name;
    this.discountPercentage = discountPercentage;
  }

  add(component: CatalogComponent): void {
    this.children.push(component);
  }

  remove(component: CatalogComponent): void {
    const idx = this.children.indexOf(component);
    if (idx !== -1) this.children.splice(idx, 1);
  }

  getName(): string { return this.name; }

  getPrice(): number {
    const rawTotal = this.children.reduce((sum, item) => sum + item.getPrice(), 0);
    const discount = (rawTotal * this.discountPercentage) / 100;
    return Math.round((rawTotal - discount) * 100) / 100;
  }

  getWeightKg(): number {
    return this.children.reduce((sum, item) => sum + item.getWeightKg(), 0);
  }

  display(indent = ""): void {
    console.log(`${indent}📁 Bundle: ${this.name} (${this.discountPercentage}% Bundle Discount)`);
    for (const child of this.children) {
      child.display(indent + "   ");
    }
    console.log(`${indent}   ── Total Bundle Price: $${this.getPrice()} | Total Weight: ${this.getWeightKg()}kg`);
  }
}

// --- Usage ---
// Standalone Leaves
const consoleItem = new ProductItem("PlayStation 5", 499, 4.5);
const controller = new ProductItem("DualSense Controller", 69, 0.3);
const game1 = new ProductItem("God of War Ragnarok", 69, 0.1);
const game2 = new ProductItem("Spider-Man 2", 69, 0.1);

// Sub-Bundle: Games Duo Pack with 10% discount
const gamesDuo = new ProductBundle("Gamer 2-Pack Bundle", 10);
gamesDuo.add(game1);
gamesDuo.add(game2);

// Master Holiday Bundle: Console + Controller + Games Duo Pack with 15% discount
const megaHolidayBundle = new ProductBundle("Ultimate Holiday Console Bundle", 15);
megaHolidayBundle.add(consoleItem);
megaHolidayBundle.add(controller);
megaHolidayBundle.add(gamesDuo);

// Client interacts uniformly with composite as if it were a single item
megaHolidayBundle.display();
console.log(`\nTotal Cart Charge: $${megaHolidayBundle.getPrice()}`);
```

---

## 5. Edge Cases & Failure Handling
- **Recursive Tree Traversal Stack Overflow**: Unusually deep nesting (1,000+ levels) can trigger call stack exhaustion. Consider iterative breadth-first traversal for very deep trees.\n- **Circular Composition**: If bundle A adds bundle B, and bundle B accidentally adds bundle A, recursive pricing calculations will result in infinite loops. Solution: Maintain an ancestor set check in `.add()`.\n- **Leaf vs Composite Interface Discrepancies**: Leaves shouldn't expose `.add()` or `.remove()`. Following Interface Segregation Principle keeps Leaf clean.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you need to implement a tree-like object structure (DOM trees, menus, file systems, organizational units).\n- When you want the client code to treat both simple and complex elements uniformly.

### When NOT to Use / Anti-patterns:
- When components do not naturally share common methods and forcing an interface leads to empty/dummy method implementations on leaves.
