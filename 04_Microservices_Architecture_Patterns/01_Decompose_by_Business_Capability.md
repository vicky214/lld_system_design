# Decompose by Business Capability Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Decompose a large monolithic system into autonomous services structured around distinct business domains and business capabilities rather than technical layers.

---

## 2. Real-Life Industry Example
Amazon E-Commerce Architecture (Separating Order Management, Inventory Fulfillment, Billing, and Recommendation capabilities into independent services).

---

## 3. Architecture & Flow Diagram
```
Client / Frontend
       |
       v
+-------------------------------------------------------------+
|                     API Gateway Router                      |
+-------------------------------------------------------------+
       |                           |                          |
       v                           v                          v
+---------------+          +---------------+          +---------------+
| Order Service |          | Billing Svc   |          | Inventory Svc |
| (Orders, Cart)|          | (Invoices, Tx)|          | (Stock, SKU)  |
+---------------+          +---------------+          +---------------+
       |                           |                          |
       v                           v                          v
[ Order DB ]               [ Billing DB ]             [ Inventory DB ]
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Business Capability Decomposition Pattern
 * Independent Bounded Contexts with Domain Services and Message Contracts
 */

// 1. Order Capability Domain
export interface OrderPlacedEvent {
  orderId: string;
  customerId: string;
  items: Array<{ sku: string; quantity: number; unitPriceCents: number }>;
  totalAmountCents: number;
  timestamp: string;
}

export class OrderCapabilityService {
  constructor(private eventBus: EventBus) {}

  async createOrder(customerId: string, items: Array<{ sku: string; quantity: number; unitPriceCents: number }>): Promise<string> {
    const orderId = `ORD-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    const totalAmountCents = items.reduce((sum, item) => sum + item.quantity * item.unitPriceCents, 0);

    // Save to Order DB (omitted for brevity)
    console.log(`[OrderCapability] Order ${orderId} created for customer ${customerId}`);

    const event: OrderPlacedEvent = {
      orderId,
      customerId,
      items,
      totalAmountCents,
      timestamp: new Date().toISOString()
    };

    await this.eventBus.publish('order.placed', event);
    return orderId;
  }
}

// 2. Inventory Capability Domain
export class InventoryCapabilityService {
  private stockLevels = new Map<string, number>([
    ['SKU-LAPTOP-01', 50],
    ['SKU-MOUSE-02', 120]
  ]);

  constructor(private eventBus: EventBus) {
    this.subscribeEvents();
  }

  private subscribeEvents(): void {
    this.eventBus.subscribe('order.placed', async (payload: OrderPlacedEvent) => {
      await this.reserveInventory(payload.orderId, payload.items);
    });
  }

  async reserveInventory(orderId: string, items: Array<{ sku: string; quantity: number }>): Promise<boolean> {
    // Check all stock availability first (atomic reservation)
    for (const item of items) {
      const current = this.stockLevels.get(item.sku) || 0;
      if (current < item.quantity) {
        console.error(`[InventoryCapability] Stockout for SKU ${item.sku} on order ${orderId}`);
        await this.eventBus.publish('inventory.reservation_failed', { orderId, reason: `Insufficient stock for ${item.sku}` });
        return false;
      }
    }

    // Deduct stock
    for (const item of items) {
      const current = this.stockLevels.get(item.sku)!;
      this.stockLevels.set(item.sku, current - item.quantity);
    }

    console.log(`[InventoryCapability] Inventory successfully reserved for order ${orderId}`);
    await this.eventBus.publish('inventory.reserved', { orderId });
    return true;
  }
}

// 3. Billing Capability Domain
export class BillingCapabilityService {
  constructor(private eventBus: EventBus) {
    this.subscribeEvents();
  }

  private subscribeEvents(): void {
    this.eventBus.subscribe('inventory.reserved', async (payload: { orderId: string }) => {
      await this.chargeCustomer(payload.orderId);
    });
  }

  async chargeCustomer(orderId: string): Promise<void> {
    console.log(`[BillingCapability] Successfully charged payment method for order ${orderId}`);
    await this.eventBus.publish('billing.payment_captured', { orderId, transactionId: `TX-${Date.now()}` });
  }
}

// Lightweight in-memory broker contract for demonstration
export class EventBus {
  private listeners = new Map<string, Array<(payload: any) => Promise<void>>>();

  subscribe(topic: string, handler: (payload: any) => Promise<void>): void {
    if (!this.listeners.has(topic)) this.listeners.set(topic, []);
    this.listeners.get(topic)!.push(handler);
  }

  async publish(topic: string, payload: any): Promise<void> {
    const handlers = this.listeners.get(topic) || [];
    for (const handler of handlers) {
      await handler(payload);
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Cross-Capability Transaction Failures**: When one business domain succeeds (e.g. Order created) but another fails (e.g. Inventory unavailable), traditional ACID two-phase locks across services degrade availability. Mitigation: Use Saga Orchestration or Choreography with compensating undo actions.
2. **Data Duplication & Synchronization**: Shared concepts (e.g. Customer Name and Address) needed by both Order and Shipping. Mitigation: Event-driven replication with eventual consistency and bounded context domain models.
3. **Misaligned Domain Boundaries**: Slicing along technical layers (UI service, Database service) instead of business capabilities leads to 'distributed monolith' anti-pattern where every change requires synchronized deployment across all services.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Large, multi-team engineering organizations requiring autonomous deployments and fast product release velocity.
- Complex enterprise software where business capabilities evolve at different rates (e.g., Billing changes rarely, Catalog/Search changes daily).

### When NOT to Use:
- Early-stage startups where domain boundaries are still ambiguous and constantly shifting.
- Small engineering teams (1-5 devs) where operational overhead of multiple deployments and network RPC outweighs organizational benefits.
