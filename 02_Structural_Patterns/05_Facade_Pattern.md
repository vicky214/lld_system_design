# Facade Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Provide a unified interface to a set of interfaces in a subsystem. Facade defines a higher-level interface that makes the subsystem easier to use.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Complex enterprise backends consist of dozens of decoupled subsystems (Inventory, Payment Gateways, Fraud Detection, Shipping Courier APIs, SMS/Email Notifications). Forcing client code or web controllers to orchestrate all these subsystems manually leads to massive code duplication and tight coupling.

### Real-World Industry Example:
E-Commerce Checkout Facade. An online store coordinates 5 distinct microservice calls to complete an order. The CheckoutFacade exposes a single `.placeOrder()` method that orchestrates the entire workflow.

---

## 3. Architecture & Visual Flow Diagram
```
[ Web App / Mobile Client ]
                   │
                   ▼
       +-----------------------+
       |     CheckoutFacade    | (Facade)
       +-----------------------+
       | + placeOrder(): res   |
       +-----------------------+
                   │
       ┌───────────┼───────────┬───────────┐
       ▼           ▼           ▼           ▼
  [Inventory]  [Payment]   [Shipping]  [NotifService]
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface OrderRequest {
  userId: string;
  items: Array<{ sku: string; quantity: number; price: number }>;
  paymentToken: string;
  shippingAddress: string;
}

export interface OrderConfirmation {
  orderId: string;
  totalAmount: number;
  trackingNumber: string;
  status: "PLACED" | "FAILED";
}

// --- Complex Subsystems ---
export class InventorySubsystem {
  async reserveStock(items: Array<{ sku: string; quantity: number }>): Promise<boolean> {
    console.log(`[Inventory] Reserved stock for ${items.length} items`);
    return true;
  }
}

export class PaymentSubsystem {
  async processPayment(amount: number, token: string): Promise<{ txnId: string; success: boolean }> {
    console.log(`[Payment] Charged $${amount} via payment token ${token}`);
    return { txnId: `TXN-${Date.now()}`, success: true };
  }
}

export class ShippingSubsystem {
  async createShipmentLabel(address: string, itemsCount: number): Promise<string> {
    console.log(`[Shipping] Created courier dispatch label for ${address}`);
    return `TRACK-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
  }
}

export class NotificationSubsystem {
  async sendOrderConfirmation(userId: string, orderId: string, tracking: string): Promise<void> {
    console.log(`[Notifications] Sent SMS/Email confirmation for order ${orderId} to user ${userId}`);
  }
}

// --- The Facade ---
export class OrderPlacementFacade {
  private inventory: InventorySubsystem;
  private payment: PaymentSubsystem;
  private shipping: ShippingSubsystem;
  private notifications: NotificationSubsystem;

  constructor() {
    this.inventory = new InventorySubsystem();
    this.payment = new PaymentSubsystem();
    this.shipping = new ShippingSubsystem();
    this.notifications = new NotificationSubsystem();
  }

  /**
   * Unified, simplified entrypoint for client applications.
   */
  public async placeOrder(request: OrderRequest): Promise<OrderConfirmation> {
    console.log(`[Facade] Starting orchestrated order placement for user ${request.userId}...`);

    // 1. Calculate total
    const totalAmount = request.items.reduce((sum, item) => sum + item.price * item.quantity, 0);

    // 2. Reserve stock
    const stockReserved = await this.inventory.reserveStock(request.items);
    if (!stockReserved) throw new Error("Inventory reservation failed.");

    // 3. Process payment
    const paymentResult = await this.payment.processPayment(totalAmount, request.paymentToken);
    if (!paymentResult.success) throw new Error("Payment processing declined.");

    // 4. Arrange courier logistics
    const trackingNumber = await this.shipping.createShipmentLabel(request.shippingAddress, request.items.length);

    // 5. Notify customer
    const orderId = `ORD-${Date.now()}`;
    await this.notifications.sendOrderConfirmation(request.userId, orderId, trackingNumber);

    console.log(`[Facade] Order ${orderId} successfully completed!`);

    return {
      orderId,
      totalAmount,
      trackingNumber,
      status: "PLACED",
    };
  }
}

// --- Client Usage ---
const facade = new OrderPlacementFacade();
facade.placeOrder({
  userId: "usr_9918",
  items: [{ sku: "MACBOOK_PRO", quantity: 1, price: 1999 }],
  paymentToken: "tok_visa_valid",
  shippingAddress: "742 Evergreen Terrace",
});
```

---

## 5. Edge Cases & Failure Handling
- **God Object Anti-Pattern**: A Facade can easily turn into an unmanageable 'God Object' if developers cram unrelated system methods into it. Keep facades focused on cohesive workflows.\n- **Subsystem Bypassing**: Facade provides a convenient simplified interface, but clients should still be allowed to access low-level subsystems directly if they require specialized fine-grained control.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you need to provide a simple, high-level interface to a complex subsystem.\n- When structuring subsystems into layers — use facades to define entry points to each subsystem level.\n- Decoupling client applications from intricate implementation details of multiple third-party libraries.

### When NOT to Use / Anti-patterns:
- When client applications genuinely need fine-grained, low-level configuration of every subsystem parameter.
