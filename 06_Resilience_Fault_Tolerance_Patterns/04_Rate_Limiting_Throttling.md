# Rate Limiting and Throttling Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Control the rate of traffic sent or received by an API to protect services from abuse, denial-of-service (DoS) attacks, resource exhaustion, and ensure fair resource allocation across tenants.

---

## 2. Real-Life Industry Example
Stripe, GitHub, and Cloudflare API rate limiters (e.g. 5,000 requests per hour for authenticated accounts, 60 requests per minute for unauthenticated IPs).

---

## 3. Architecture & Flow Diagram
```
Client Request
      |
      v
+------------------------------------+
|    Token Bucket / Sliding Window   |
|   Current Tokens: 4 / 10           |
+------------------------------------+
      |
      |-- (Tokens Available) -> Deduct 1 token -> Allow to Backend API
      |
      +-- (Tokens Empty)     -> Reject with HTTP 429 Too Many Requests
                                (Include headers: Retry-After, X-RateLimit-Reset)
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Token Bucket Rate Limiting Pattern
 * High-performance burstable rate limiter with millisecond continuous token replenishment
 */

export interface RateLimitResult {
  allowed: boolean;
  remainingTokens: number;
  retryAfterSeconds: number;
}

export class TokenBucketLimiter {
  private tokens: number;
  private lastRefillTimestamp: number;

  constructor(
    public readonly capacity: number,       // Max burst capacity
    public readonly refillRatePerSecond: number // Token generation velocity
  ) {
    this.tokens = capacity;
    this.lastRefillTimestamp = Date.now();
  }

  tryConsume(cost: number = 1): RateLimitResult {
    this.refill();

    if (this.tokens >= cost) {
      this.tokens -= cost;
      return {
        allowed: true,
        remainingTokens: Math.floor(this.tokens),
        retryAfterSeconds: 0
      };
    }

    const missingTokens = cost - this.tokens;
    const retryAfter = Math.ceil(missingTokens / this.refillRatePerSecond);

    return {
      allowed: false,
      remainingTokens: Math.floor(this.tokens),
      retryAfterSeconds: retryAfter
    };
  }

  private refill(): void {
    const now = Date.now();
    const elapsedSeconds = (now - this.lastRefillTimestamp) / 1000;
    const tokensToAdd = elapsedSeconds * this.refillRatePerSecond;

    if (tokensToAdd > 0) {
      this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
      this.lastRefillTimestamp = now;
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Distributed State Race Conditions**: In a cluster of 20 API servers, checking and decrementing token counters in Redis can suffer from check-then-act concurrency race conditions. Mitigation: Execute token updates via atomic Redis Lua scripts.
2. **Fixed Window Edge Spike**: If 100 requests are allowed per minute, a client sending 100 requests at 11:59:59 and another 100 at 12:00:01 pushes 200 requests in 2 seconds. Mitigation: Use Sliding Window Log or Token Bucket.
3. **VIP / Tiered Quota Bypass**: Internal admin jobs or critical payment webhooks should not be throttled alongside generic unauthenticated web visitors.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Public APIs, multi-tenant SaaS backends, and login endpoints susceptible to credential stuffing or DDoS attacks.

### When NOT to Use:
- Low-latency internal microservice communication within the same private VPC where network overhead of rate limit checks adds latency without threat exposure.
