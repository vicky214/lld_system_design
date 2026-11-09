# State Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Allow an object to alter its behavior when its internal state changes. The object will appear to change its class.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Managing state machines with giant `switch (state)` statements across dozens of methods makes code brittle. Adding a new state requires editing every single switch block, violating the Open/Closed Principle.

### Real-World Industry Example:
E-Commerce Order State Lifecycle (`PENDING` $\rightarrow$ `PAID` $\rightarrow$ `SHIPPED` $\rightarrow$ `DELIVERED`). An order behaves differently depending on whether it has been paid, shipped, or cancelled.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------------------+
|               Order               | (Context)
+-----------------------------------+
| - state: OrderState               |
+-----------------------------------+
| + setState(state): void           |
| + pay(): void                     |
| + ship(): void                    |
| + cancel(): void                  |
+-----------------------------------+
                  │ (delegates)
                  ▼
+-----------------------------------+
|             OrderState            | (State Interface)
+-----------------------------------+
| + pay(order): void                |
| + ship(order): void               |
| + cancel(order): void             |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|  PendingState |   |   PaidState   |
+---------------+   +---------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface OrderState {
  pay(order: OrderContext): void;
  ship(order: OrderContext): void;
  cancel(order: OrderContext): void;
  getName(): string;
}

export class OrderContext {
  private state: OrderState;

  constructor() {
    this.state = new PendingState(); // Initial state
  }

  public setState(state: OrderState): void {
    console.log(`[Order] State transitioning: ${this.state.getName()} -> ${state.getName()}`);
    this.state = state;
  }

  public pay(): void { this.state.pay(this); }
  public ship(): void { this.state.ship(this); }
  public cancel(): void { this.state.cancel(this); }
}

// --- Concrete States ---
export class PendingState implements OrderState {
  getName() { return "PENDING"; }

  pay(order: OrderContext): void {
    console.log("✓ Payment authorized. Transitioning order to PAID.");
    order.setState(new PaidState());
  }

  ship(): void {
    console.log("❌ Cannot ship an unpaid order.");
  }

  cancel(order: OrderContext): void {
    console.log("✓ Order cancelled.");
    order.setState(new CancelledState());
  }
}

export class PaidState implements OrderState {
  getName() { return "PAID"; }

  pay(): void {
    console.log("❌ Order is already paid.");
  }

  ship(order: OrderContext): void {
    console.log("✓ Order dispatched with courier tracking. Transitioning to SHIPPED.");
    order.setState(new ShippedState());
  }

  cancel(): void {
    console.log("❌ Cannot cancel directly. Initiate refund flow first.");
  }
}

export class ShippedState implements OrderState {
  getName() { return "SHIPPED"; }

  pay(): void { console.log("❌ Already paid and shipped."); }
  ship(): void { console.log("❌ Already in transit."); }
  cancel(): void { console.log("❌ Cannot cancel items already in transit."); }
}

export class CancelledState implements OrderState {
  getName() { return "CANCELLED"; }
  pay(): void { console.log("❌ Cannot pay for a cancelled order."); }
  ship(): void { console.log("❌ Cannot ship a cancelled order."); }
  cancel(): void { console.log("❌ Order is already cancelled."); }
}

// --- Usage ---
const order = new OrderContext();
order.ship();   // Blocked
order.pay();    // Transitions to PAID
order.cancel(); // Blocked by business rules
order.ship();   // Transitions to SHIPPED
```

---

## 5. Edge Cases & Failure Handling
- **State Explosion**: Systems with hundreds of intermediate sub-states can produce an overwhelming number of classes. Combine with Hierarchical State Machines (Statecharts) if complexity grows too large.\n- **Persistence & Serialization**: In distributed web apps, order state is stored in a database (e.g. `status = 'PAID'`). The Context must rehydrate the appropriate concrete State class based on database records upon request arrival.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When an object behaves differently depending on its current state.\n- When you have massive conditionals (`if/else` or `switch`) spanning multiple methods based on an object's state.\n- Workflow engines, document review pipelines, game character animations.

### When NOT to Use / Anti-patterns:
- When an object has only 2 simple states that rarely change behavior.
