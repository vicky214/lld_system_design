# Strategy Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Define a family of algorithms, encapsulate each one, and make them interchangeable. Strategy lets the algorithm vary independently from clients that use it.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Hardcoding multiple pricing discount algorithms or payment routing strategies directly inside a controller leads to massive conditional blocks that must be modified every time marketing adds a new campaign.

### Real-World Industry Example:
E-Commerce Dynamic Pricing & Surge Pricing Strategy. Calculating ride fares in Uber (Standard vs Surge vs Peak Hour vs Corporate Discount) dynamically at runtime.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------------------+
|           PricingContext          |
+-----------------------------------+
| - strategy: PricingStrategy       |
+-----------------------------------+
| + setStrategy(strategy): void     |
| + calculateFare(dist, time): num  |
+-----------------------------------+
                  │ (delegates)
                  ▼
+-----------------------------------+
|          PricingStrategy          |
+-----------------------------------+
| + calculate(dist, time): number   |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|  StandardFare |   |   SurgeFare   |
+---------------+   +---------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Strategy Interface
export interface PricingStrategy {
  calculate(baseRate: number, distanceKm: number, durationMin: number): number;
}

// 2. Concrete Strategies
export class RegularPricingStrategy implements PricingStrategy {
  calculate(baseRate: number, distanceKm: number, durationMin: number): number {
    return baseRate + (distanceKm * 1.5) + (durationMin * 0.25);
  }
}

export class SurgePricingStrategy implements PricingStrategy {
  private multiplier: number;

  constructor(multiplier = 2.0) {
    this.multiplier = multiplier;
  }

  calculate(baseRate: number, distanceKm: number, durationMin: number): number {
    const raw = baseRate + (distanceKm * 1.5) + (durationMin * 0.25);
    return Math.round(raw * this.multiplier * 100) / 100;
  }
}

export class CorporateDiscountStrategy implements PricingStrategy {
  calculate(baseRate: number, distanceKm: number, durationMin: number): number {
    const raw = baseRate + (distanceKm * 1.2) + (durationMin * 0.15);
    return Math.round(raw * 0.85 * 100) / 100; // 15% corporate discount
  }
}

// 3. Context
export class RideFareCalculator {
  private strategy: PricingStrategy;

  constructor(strategy: PricingStrategy) {
    this.strategy = strategy;
  }

  setStrategy(strategy: PricingStrategy): void {
    this.strategy = strategy;
  }

  computeFare(distanceKm: number, durationMin: number): number {
    return this.strategy.calculate(5.0, distanceKm, durationMin);
  }
}

// --- Usage ---
const ride = new RideFareCalculator(new RegularPricingStrategy());
console.log("Regular Ride Fare:", ride.computeFare(10, 20)); // $25.00

// High demand detected -> Switch to surge dynamically
ride.setStrategy(new SurgePricingStrategy(2.5));
console.log("Surge Ride Fare:", ride.computeFare(10, 20)); // $62.50
```

---

## 5. Edge Cases & Failure Handling
- **Client Awareness Requirement**: Clients must understand how strategies differ in order to select the proper one at runtime.\n- **Strategy Statelessness**: Strategies should ideally be stateless pure functions to allow sharing instances across concurrent requests without race conditions.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you want to use different variants of an algorithm within an object and be able to switch from one algorithm to another during runtime.\n- When you have a lot of similar classes that only differ in the way they execute some behavior.\n- To isolate the business logic of an algorithm from the code that uses it.

### When NOT to Use / Anti-patterns:
- If you only have a couple of algorithms that rarely change (a simple function with an if-statement is simpler).
