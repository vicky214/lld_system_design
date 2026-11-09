# Bridge Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Decouple an abstraction from its implementation so that the two can vary independently, avoiding a Cartesian product explosion of subclasses.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
If you have 3 payment client platforms (Web, Mobile App, POS Terminal) and 3 payment providers (Stripe, PayPal, Adyen), traditional inheritance forces you to create 9 subclasses (`WebStripePayment`, `WebPayPalPayment`, `MobileStripePayment`, etc.). Adding 1 new provider requires creating subclasses for every single platform.

### Real-World Industry Example:
Cross-Platform Payment Architecture. Decoupling Checkout Presentation Abstractions (SubscriptionCheckout, OneTimeCheckout) from Payment Processing Implementations (StripeGateway, AdyenGateway).

---

## 3. Architecture & Visual Flow Diagram
```
Abstraction Layer                     Implementation Layer
      +-----------------------+              +-----------------------+
      |       Checkout        | ───────────► |    PaymentGateway     | (Implementor)
      +-----------------------+ (has-a)      +-----------------------+
      | + processCheckout()   |              | + authorizePayment()  |
      +-----------------------+              +-----------------------+
                  ▲                                      ▲
         ┌────────┴────────┐                    ┌────────┴────────┐
         │                 │                    │                 │
+-----------------+ +---------------+  +-----------------+ +---------------+
| OneTimeCheckout | | SubscrCheckout|  |  StripeGateway  | |  AdyenGateway |
+-----------------+ +---------------+  +-----------------+ +---------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Implementation Interface
export interface PaymentGatewayImplementor {
  authorize(amount: number, token: string): Promise<{ authCode: string; success: boolean }>;
  capture(authCode: string, amount: number): Promise<boolean>;
}

// 2. Concrete Implementations
export class StripeGatewayImplementor implements PaymentGatewayImplementor {
  async authorize(amount: number, token: string) {
    console.log(`[Stripe] Authorized $${amount} with customer token ${token}`);
    return { authCode: `stripe_auth_${Date.now()}`, success: true };
  }
  async capture(authCode: string, amount: number) {
    console.log(`[Stripe] Captured $${amount} against auth ${authCode}`);
    return true;
  }
}

export class AdyenGatewayImplementor implements PaymentGatewayImplementor {
  async authorize(amount: number, token: string) {
    console.log(`[Adyen] Authorized $${amount} via 3DSecure session ${token}`);
    return { authCode: `adyen_auth_${Date.now()}`, success: true };
  }
  async capture(authCode: string, amount: number) {
    console.log(`[Adyen] Captured $${amount} against auth ${authCode}`);
    return true;
  }
}

// 3. Abstraction
export abstract class CheckoutAbstraction {
  protected gateway: PaymentGatewayImplementor;

  constructor(gateway: PaymentGatewayImplementor) {
    this.gateway = gateway;
  }

  public setGateway(gateway: PaymentGatewayImplementor): void {
    this.gateway = gateway;
  }

  abstract execute(amount: number, token: string): Promise<boolean>;
}

// 4. Refined Abstractions
export class OneTimeCheckout extends CheckoutAbstraction {
  async execute(amount: number, token: string): Promise<boolean> {
    console.log(`[Checkout] Processing Standard One-Time Checkout of $${amount}`);
    const auth = await this.gateway.authorize(amount, token);
    if (!auth.success) return false;
    return this.gateway.capture(auth.authCode, amount);
  }
}

export class SubscriptionCheckout extends CheckoutAbstraction {
  private recurrencePeriodDays: number;

  constructor(gateway: PaymentGatewayImplementor, recurrencePeriodDays = 30) {
    super(gateway);
    this.recurrencePeriodDays = recurrencePeriodDays;
  }

  async execute(amount: number, token: string): Promise<boolean> {
    console.log(`[Checkout] Setting up ${this.recurrencePeriodDays}-day recurring subscription of $${amount}`);
    const auth = await this.gateway.authorize(amount, token);
    return auth.success;
  }
}

// --- Usage ---
const stripe = new StripeGatewayImplementor();
const adyen = new AdyenGatewayImplementor();

// Seamlessly combine any checkout abstraction with any gateway implementation
const instantOrder = new OneTimeCheckout(stripe);
instantOrder.execute(99, "tok_123");

const monthlySub = new SubscriptionCheckout(adyen, 30);
monthlySub.execute(29, "tok_456");
```

---

## 5. Edge Cases & Failure Handling
- **Mismatched Feature Sets**: If Stripe supports instant refunds but Adyen requires batch settlements, the implementor interface must gracefully handle optional capabilities without throwing unexpected errors.\n- **Runtime Hot-Swapping**: Switching the gateway implementation mid-transaction requires state validation to prevent orphaned authorizations.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you want to divide and organize a monolithic class that has multiple variants of some functionality (e.g. cross-platform GUI engines, multi-cloud storage).\n- When you need to be able to switch implementations at runtime.\n- To prevent an exponential explosion of inheritance classes ($M \times N$ classes reduced to $M + N$).

### When NOT to Use / Anti-patterns:
- When your domain has only one concrete platform and implementation (introduces unnecessary indirection).
