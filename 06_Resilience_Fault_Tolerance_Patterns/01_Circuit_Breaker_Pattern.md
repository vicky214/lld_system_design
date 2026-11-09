# Circuit Breaker Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Prevent cascading failures in distributed systems by stopping repeated calls to a failing remote dependency once an error threshold is reached, failing fast and allowing the downstream service time to recover.

---

## 2. Real-Life Industry Example
Netflix Hystrix / Resilience4j protecting video streaming microservices when recommendation recommendation algorithms or third-party DRM servers crash.

---

## 3. Architecture & Flow Diagram
```
+-------------------------+
           |         CLOSED          |  (Normal operation, calls pass through)
           +-------------------------+
                 |             ^
   Failures >    |             | Success threshold reached
   Threshold     v             |
           +-------------------------+
           |          OPEN           |  (Fail fast, reject all calls immediately)
           +-------------------------+
                 |
   Reset timeout |
   expires       v
           +-------------------------+
           |        HALF-OPEN        |  (Test limited canary requests)
           +-------------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Circuit Breaker Pattern
 * Finite State Machine (CLOSED, OPEN, HALF_OPEN) with failure window and recovery probe
 */

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export interface CircuitBreakerOptions {
  failureThreshold: number;       // Consecutive failures before opening
  resetTimeoutMs: number;         // Time to wait before testing recovery
  successThresholdHalfOpen: number; // Successes in half-open before closing
}

export class CircuitBreaker {
  private state: CircuitState = 'CLOSED';
  private failureCount: number = 0;
  private successCountHalfOpen: number = 0;
  private nextAttemptTimestamp: number = 0;

  constructor(private options: CircuitBreakerOptions = { failureThreshold: 3, resetTimeoutMs: 5000, successThresholdHalfOpen: 2 }) {}

  getState(): CircuitState {
    return this.state;
  }

  async execute<T>(action: () => Promise<T>, fallback?: () => Promise<T>): Promise<T> {
    const now = Date.now();

    // 1. Check if OPEN state has expired -> Transition to HALF_OPEN
    if (this.state === 'OPEN') {
      if (now >= this.nextAttemptTimestamp) {
        console.log('[CircuitBreaker] Reset timeout elapsed -> Transitioning OPEN to HALF_OPEN');
        this.state = 'HALF_OPEN';
        this.successCountHalfOpen = 0;
      } else {
        console.warn('[CircuitBreaker] Circuit is OPEN! Fast-failing request without network call.');
        if (fallback) return await fallback();
        throw new Error('CircuitBreakerOpenException: Service temporarily unavailable');
      }
    }

    try {
      const result = await action();
      this.onSuccess();
      return result;
    } catch (err: any) {
      this.onFailure();
      if (fallback) {
        console.log('[CircuitBreaker] Primary action failed, returning fallback value.');
        return await fallback();
      }
      throw err;
    }
  }

  private onSuccess(): void {
    if (this.state === 'HALF_OPEN') {
      this.successCountHalfOpen++;
      if (this.successCountHalfOpen >= this.options.successThresholdHalfOpen) {
        console.log('[CircuitBreaker] Recovery confirmed! Transitioning HALF_OPEN to CLOSED.');
        this.state = 'CLOSED';
        this.failureCount = 0;
      }
    } else if (this.state === 'CLOSED') {
      this.failureCount = 0;
    }
  }

  private onFailure(): void {
    if (this.state === 'HALF_OPEN') {
      console.warn('[CircuitBreaker] Canary probe failed in HALF_OPEN! Re-opening circuit immediately.');
      this.state = 'OPEN';
      this.nextAttemptTimestamp = Date.now() + this.options.resetTimeoutMs;
    } else if (this.state === 'CLOSED') {
      this.failureCount++;
      console.warn(`[CircuitBreaker] Failure recorded (${this.failureCount}/${this.options.failureThreshold})`);
      if (this.failureCount >= this.options.failureThreshold) {
        console.error('[CircuitBreaker] Failure threshold exceeded! Tripping circuit to OPEN.');
        this.state = 'OPEN';
        this.nextAttemptTimestamp = Date.now() + this.options.resetTimeoutMs;
      }
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Distinguishing Client vs Server Errors**: HTTP 400 Bad Request or 404 Not Found represent client errors and should NOT trip the circuit breaker. Only count 5xx Server Errors or TCP Timeouts.
2. **Thundering Herd on Half-Open**: When 1,000 requests arrive at the exact millisecond the reset timeout expires, only 1 or 2 canary requests should be allowed through in HALF_OPEN; the remaining 998 must be rejected.
3. **Flapping Circuits**: A service that recovers for 1 second then crashes repeatedly causes the circuit to flap rapidly between Open and Closed. Mitigation: Exponential backoff on reset timeouts (5s -> 10s -> 30s).

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Calling external third-party APIs (Stripe, Twilio, Sendgrid) or inter-service RPC where network blips and latency spikes can tie up thread pools.

### When NOT to Use:
- Accessing local in-memory caches or critical local database transactions where immediate error throwing with local transaction rollbacks is required.
