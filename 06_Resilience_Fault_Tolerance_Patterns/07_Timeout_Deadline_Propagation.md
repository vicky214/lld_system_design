# Timeout and Deadline Propagation Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Propagate a client's maximum allowable execution deadline across all downstream microservice calls so that subsequent services terminate work immediately if the upstream caller has already timed out.

---

## 2. Real-Life Industry Example
gRPC Deadline Propagation & Google Internal RPC Framework (Stubby) where every RPC request carries a deadline timestamp; if a backend query takes 5 seconds when the user set a 2-second timeout, all downstream queries abort immediately.

---

## 3. Architecture & Flow Diagram
```
Client (Sets Deadline: 1000ms)
       |
       |-- 1. Call Gateway (100ms elapsed, Remaining: 900ms)
       v
API Gateway
       |
       |-- 2. Call Order Service (300ms elapsed, Remaining: 600ms)
       v
Order Service
       |
       |-- 3. Call Payment Svc (Takes 800ms)
       |
   [ Deadline Exceeded! Remaining: -200ms ]
       |
       +--> Instantly ABORT downstream database query!
            Do not waste compute on an abandoned request!
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Distributed Deadline Propagation Pattern
 * Context deadline tracking across cascading asynchronous service calls
 */

export class ExecutionContext {
  constructor(public readonly deadlineTimestamp: number) {}

  static withTimeout(timeoutMs: number): ExecutionContext {
    return new ExecutionContext(Date.now() + timeoutMs);
  }

  getRemainingMs(): number {
    return Math.max(0, this.deadlineTimestamp - Date.now());
  }

  isExpired(): boolean {
    return Date.now() >= this.deadlineTimestamp;
  }

  throwIfExpired(stepName: string): void {
    if (this.isExpired()) {
      throw new Error(`DeadlineExceededException: Step '${stepName}' aborted. Execution time exceeded caller deadline.`);
    }
  }
}

export class CascadingServiceCall {
  async processUserCheckout(ctx: ExecutionContext): Promise<string> {
    console.log(`[OrderService] Starting checkout. Remaining budget: ${ctx.getRemainingMs()}ms`);
    ctx.throwIfExpired('OrderService:Init');

    // Step 1: Query inventory (Fast: 50ms)
    await new Promise(res => setTimeout(res, 50));
    ctx.throwIfExpired('InventoryCheck');

    // Step 2: Call Fraud Detection (Slow: 600ms)
    console.log(`[OrderService] Calling Fraud Service. Remaining budget: ${ctx.getRemainingMs()}ms`);
    await new Promise(res => setTimeout(res, 600));
    ctx.throwIfExpired('FraudDetection');

    // Step 3: Call Payment Gateway
    console.log(`[OrderService] Calling Payment Gateway. Remaining budget: ${ctx.getRemainingMs()}ms`);
    // If deadline was 500ms, step 2 will throw before step 3 even touches the payment API!

    return 'ORDER_PROCESSED';
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Clock Skew Across Distributed Nodes**: If server clocks differ by 500ms via NTP drift, absolute deadline timestamps will be miscalculated. Solution: Propagate relative remaining time duration (e.g. `X-Remaining-Time-Ms: 850`) instead of absolute wall clock time.
2. **Partial Write Cancellation**: If an operation is aborted midway due to deadline expiry, ensure incomplete database records are rolled back or cleaned up to avoid orphaned records.
3. **Database Connection Leaks**: When canceling a call due to deadline expiry, ensure the underlying TCP socket or HTTP/2 stream is formally cancelled via `AbortController`.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Multi-tier microservices with deep call trees (Service A -> B -> C -> D) to prevent wasted CPU, memory, and database locks on abandoned requests.

### When NOT to Use:
- Asynchronous fire-and-forget background jobs that are meant to run to completion regardless of user browser disconnection.
