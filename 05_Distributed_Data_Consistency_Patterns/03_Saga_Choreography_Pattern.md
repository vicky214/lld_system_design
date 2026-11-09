# Saga Choreography Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Coordinate distributed transactions across microservices through decentralized event publishing and subscribing where each service reacts to events and emits subsequent events without a central coordinator.

---

## 2. Real-Life Industry Example
Stripe Payment Lifecycle (PaymentAuthorized event triggers FraudService; FraudCleared event triggers TransferService; TransferFailed event triggers PaymentRefundService).

---

## 3. Architecture & Flow Diagram
```
[Order Service]       [Payment Service]       [Inventory Service]
       |                      |                         |
       |-- 1. OrderCreated -->|                         |
       |                      |-- 2. PaymentApproved -->|
       |                      |                         | (Stockout!)
       |                      |<-- 3. StockReservationFailed
       |<-- 4. PaymentRefunded-
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Saga Choreography Pattern
 * Decentralized event-driven state transitions with compensating events
 */

export interface Event<T = any> {
  id: string;
  name: string;
  payload: T;
}

export type EventBusListener = (event: Event) => Promise<void>;

export class ChoreographyEventBus {
  private listeners = new Map<string, EventBusListener[]>();

  subscribe(eventName: string, handler: EventBusListener): void {
    if (!this.listeners.has(eventName)) this.listeners.set(eventName, []);
    this.listeners.get(eventName)!.push(handler);
  }

  async emit(event: Event): Promise<void> {
    console.log(`[ChoreographyBus] Event Emitted: ${event.name} (ID: ${event.id})`);
    const handlers = this.listeners.get(event.name) || [];
    for (const handler of handlers) {
      await handler(event);
    }
  }
}

// 1. Order Service Choreographer
export class ChoreographedOrderService {
  constructor(private bus: ChoreographyEventBus) {
    this.bus.subscribe('PaymentFailed', async (evt) => {
      console.log(`[OrderService] Marking order ${evt.payload.orderId} as CANCELLED due to payment failure`);
    });
    this.bus.subscribe('InventoryReserved', async (evt) => {
      console.log(`[OrderService] Marking order ${evt.payload.orderId} as COMPLETED!`);
    });
  }

  async placeOrder(orderId: string, amount: number): Promise<void> {
    console.log(`[OrderService] Initiating order: ${orderId}`);
    await this.bus.emit({
      id: `evt-${Date.now()}`,
      name: 'OrderCreated',
      payload: { orderId, amount }
    });
  }
}

// 2. Payment Service Choreographer
export class ChoreographedPaymentService {
  constructor(private bus: ChoreographyEventBus) {
    this.bus.subscribe('OrderCreated', async (evt) => {
      await this.processPayment(evt.payload.orderId, evt.payload.amount);
    });
  }

  async processPayment(orderId: string, amount: number): Promise<void> {
    if (amount > 1000) {
      // Payment decline simulation
      console.warn(`[PaymentService] Card limit exceeded for order ${orderId}`);
      await this.bus.emit({
        id: `evt-pay-fail-${Date.now()}`,
        name: 'PaymentFailed',
        payload: { orderId, reason: 'INSUFFICIENT_FUNDS' }
      });
      return;
    }

    console.log(`[PaymentService] Payment approved for order ${orderId}`);
    await this.bus.emit({
      id: `evt-pay-ok-${Date.now()}`,
      name: 'PaymentApproved',
      payload: { orderId, amount }
    });
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Cyclic Event Loops**: If Service A listens to Event B, and emits Event C, which triggers Service B to emit Event B, an infinite storm occurs. Strict event hierarchy contracts and correlation IDs must be documented.
2. **Observability Complexity**: Tracking the end-to-end status of an order requires correlating distributed log messages across 5+ services without a single orchestrator state table. Distributed tracing (OpenTelemetry) is essential.
3. **Out-of-Order Events**: A network delay may cause `PaymentFailed` to arrive before `OrderCreated` is acknowledged.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Simple, loosely coupled workflows with 2-4 services where autonomous peer-to-peer reactions are natural and no central coordinator bottle-neck is desired.

### When NOT to Use:
- Complex business processes with 10+ steps or branching conditional logic where understanding workflow state requires reverse engineering multiple independent codebase listeners.
