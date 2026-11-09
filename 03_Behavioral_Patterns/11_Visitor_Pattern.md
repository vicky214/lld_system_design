# Visitor Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Represent an operation to be performed on the elements of an object structure. Visitor lets you define a new operation without changing the classes of the elements on which it operates.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
You have a complex object structure (e.g. Products in a cart: Groceries, Electronics, Liquor). Every time finance wants to calculate sales tax, or shipping wants to compute export customs duties, you must modify every single product class (`Grocery.computeTax()`, `Electronics.computeTax()`), cluttering domain models with unrelated concerns.

### Real-World Industry Example:
Multi-Category E-Commerce Tax and Export Regulatory Compliance Visitor. Adds new operational passes (US Sales Tax, EU VAT, Hazardous Materials Shipping Audit) without modifying core product classes.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------------------+
|              Element              |
+-----------------------------------+
| + accept(visitor: Visitor): void  |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|   FoodItem    |   | ElectronicItem|
+---------------+   +---------------+
| + accept(v)   |   | + accept(v)   |
+---------------+   +---------------+
        │                   │
        └─────────┬─────────┘
                  ▼ (calls back)
+-----------------------------------+
|              Visitor              |
+-----------------------------------+
| + visitFood(item): void           |
| + visitElectronic(item): void     |
+-----------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Visitor Interface
export interface CartVisitor {
  visitFood(item: FoodProduct): void;
  visitElectronic(item: ElectronicProduct): void;
}

// 2. Element Interface
export interface CartItem {
  accept(visitor: CartVisitor): void;
  getPrice(): number;
  getName(): string;
}

// 3. Concrete Elements
export class FoodProduct implements CartItem {
  private name: string;
  private price: number;
  public isOrganic: boolean;

  constructor(name: string, price: number, isOrganic = false) {
    this.name = name;
    this.price = price;
    this.isOrganic = isOrganic;
  }

  getName() { return this.name; }
  getPrice() { return this.price; }

  // Double Dispatch
  accept(visitor: CartVisitor): void {
    visitor.visitFood(this);
  }
}

export class ElectronicProduct implements CartItem {
  private name: string;
  private price: number;
  public batteryWattHours: number;

  constructor(name: string, price: number, batteryWattHours: number) {
    this.name = name;
    this.price = price;
    this.batteryWattHours = batteryWattHours;
  }

  getName() { return this.name; }
  getPrice() { return this.price; }

  accept(visitor: CartVisitor): void {
    visitor.visitElectronic(this);
  }
}

// 4. Concrete Visitors
export class SalesTaxVisitor implements CartVisitor {
  public totalTax = 0;

  visitFood(item: FoodProduct): void {
    // Groceries are tax-exempt (0% tax)
    console.log(`[Tax Visitor] Food item "${item.getName()}" is tax exempt ($0 tax).`);
  }

  visitElectronic(item: ElectronicProduct): void {
    // Electronics have 18% standard VAT
    const tax = Math.round(item.getPrice() * 0.18 * 100) / 100;
    this.totalTax += tax;
    console.log(`[Tax Visitor] Electronic "${item.getName()}" 18% tax: $${tax}`);
  }
}

export class DangerousGoodsShippingVisitor implements CartVisitor {
  public requiresHazmatDeclaration = false;

  visitFood(item: FoodProduct): void {
    // Food is non-hazardous
  }

  visitElectronic(item: ElectronicProduct): void {
    if (item.batteryWattHours > 100) {
      console.log(`[Shipping Visitor] ALERT: "${item.getName()}" exceeds 100Wh battery limit! Requires Hazmat handling.`);
      this.requiresHazmatDeclaration = true;
    }
  }
}

// --- Usage ---
const cart: CartItem[] = [
  new FoodProduct("Organic Apples", 15, true),
  new ElectronicProduct("Gaming Laptop", 1800, 99),
  new ElectronicProduct("Drone High-Capacity Battery Pack", 350, 160),
];

// Run Tax pass
const taxCalculator = new SalesTaxVisitor();
for (const item of cart) {
  item.accept(taxCalculator);
}
console.log(`Total Sales Tax to Remit: $${taxCalculator.totalTax}\n`);

// Run Hazardous Goods Shipping pass without altering item classes
const shippingAudit = new DangerousGoodsShippingVisitor();
for (const item of cart) {
  item.accept(shippingAudit);
}
console.log("Cart Requires Hazmat Handling?", shippingAudit.requiresHazmatDeclaration);
```

---

## 5. Edge Cases & Failure Handling
- **Adding New Concrete Elements**: If you add a new element class (e.g. `LiquorProduct`), you MUST add a `visitLiquor()` method to the `CartVisitor` interface and update every single existing concrete visitor.\n- **Access to Private Encapsulation**: Visitors often need deep access to internal element state, which might tempt developers to make private fields public.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you need to perform an operation on all elements of a complex object structure (such as an AST or shopping cart).\n- When you want to clean up the business logic of auxiliary behaviors from the primary classes.\n- When the element hierarchy rarely changes, but you frequently add new operations over them.

### When NOT to Use / Anti-patterns:
- When the element class hierarchy changes frequently (adding an element forces refactoring all visitors).
