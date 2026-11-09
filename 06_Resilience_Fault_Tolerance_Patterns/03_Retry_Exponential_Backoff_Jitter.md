# Retry with Exponential Backoff and Full Jitter Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Transparently recover from transient network glitches by retrying failed idempotent requests with progressively doubling wait delays randomized with mathematical jitter to eliminate thundering herd synchronization.

---

## 2. Real-Life Industry Example
AWS SDK Architecture (Amazon DynamoDB & S3 client retry algorithms that prevent thousands of simultaneous clients from synchronizing retry spikes against recovering servers).

---

## 3. Architecture & Flow Diagram
```
Request 1 Failed
    |
Wait = min(Cap, Base * 2^0) = 100ms + Random Full Jitter [0..100ms]
    |
Retry 1 Failed
    |
Wait = min(Cap, Base * 2^1) = 200ms + Random Full Jitter [0..200ms]
    |
Retry 2 Failed
    |
Wait = min(Cap, Base * 2^2) = 400ms + Random Full Jitter [0..400ms]
    |
Retry 3 Succeeded!
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Exponential Backoff with Full Jitter Pattern
 * Idempotency check and decorrelated randomization
 */

export interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

export class RobustRetryEngine {
  constructor(private config: RetryConfig = { maxRetries: 3, baseDelayMs: 100, maxDelayMs: 2000 }) {}

  async executeWithRetry<T>(
    operationName: string,
    action: () => Promise<T>,
    isTransientError: (err: any) => boolean = () => true
  ): Promise<T> {
    let attempt = 0;

    while (true) {
      try {
        return await action();
      } catch (err: any) {
        attempt++;

        if (attempt > this.config.maxRetries || !isTransientError(err)) {
          console.error(`[RetryEngine] Operation '${operationName}' failed permanently after ${attempt} attempts: ${err.message}`);
          throw err;
        }

        // Calculate Exponential Backoff: min(maxDelay, baseDelay * 2^(attempt - 1))
        const exponentialDelay = Math.min(
          this.config.maxDelayMs,
          this.config.baseDelayMs * Math.pow(2, attempt - 1)
        );

        // Apply AWS Full Jitter: Uniform random between 0 and exponentialDelay
        const jitteredDelay = Math.floor(Math.random() * exponentialDelay);

        console.warn(`[RetryEngine] '${operationName}' failed (${err.message}). Retrying attempt ${attempt}/${this.config.maxRetries} after ${jitteredDelay}ms sleep...`);
        await new Promise(res => setTimeout(res, jitteredDelay));
      }
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Retrying Non-Idempotent Operations**: Retrying a `POST /charge-card` without an Idempotency-Key can charge the customer multiple times. NEVER retry non-idempotent writes without server-enforced idempotency keys!
2. **Amplifying Outages (Retry Storms)**: When a downstream database is already operating at 100% CPU, 5,000 clients retrying 3 times triples the traffic to 15,000 requests, driving the database into total collapse. Circuit breakers must gate retry policies.
3. **End-to-End Latency Breach**: Doubling delays can cause total execution time to exceed the upstream HTTP gateway timeout (e.g. 30 seconds), rendering the client retry wasted.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Handling transient network blips (DNS timeouts, TCP socket resets, HTTP 503 Service Unavailable, 429 Too Many Requests).

### When NOT to Use:
- Deterministic client errors (HTTP 400 Bad Request, 401 Unauthorized, 422 Unprocessable Entity) which will never succeed on retry.
