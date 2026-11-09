import os

TARGET_DIR = "/home/vicky/Documents/Antigravity/lld/06_Resilience_Fault_Tolerance_Patterns"
os.makedirs(TARGET_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Circuit_Breaker_Pattern.md",
        "title": "Circuit Breaker Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Prevent cascading failures in distributed systems by stopping repeated calls to a failing remote dependency once an error threshold is reached, failing fast and allowing the downstream service time to recover.",
        "industry_example": "Netflix Hystrix / Resilience4j protecting video streaming microservices when recommendation recommendation algorithms or third-party DRM servers crash.",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Distinguishing Client vs Server Errors**: HTTP 400 Bad Request or 404 Not Found represent client errors and should NOT trip the circuit breaker. Only count 5xx Server Errors or TCP Timeouts.
2. **Thundering Herd on Half-Open**: When 1,000 requests arrive at the exact millisecond the reset timeout expires, only 1 or 2 canary requests should be allowed through in HALF_OPEN; the remaining 998 must be rejected.
3. **Flapping Circuits**: A service that recovers for 1 second then crashes repeatedly causes the circuit to flap rapidly between Open and Closed. Mitigation: Exponential backoff on reset timeouts (5s -> 10s -> 30s).""",
        "tradeoffs": """### When to Use:
- Calling external third-party APIs (Stripe, Twilio, Sendgrid) or inter-service RPC where network blips and latency spikes can tie up thread pools.

### When NOT to Use:
- Accessing local in-memory caches or critical local database transactions where immediate error throwing with local transaction rollbacks is required."""
    },
    {
        "filename": "02_Bulkhead_Pattern.md",
        "title": "Bulkhead Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Isolate critical resources (thread pools, connection pools, memory partitions) into segregated compartments so that a failure or slowdown in one component cannot exhaust the entire system's capacity.",
        "industry_example": "Shipbuilding watertight bulkheads; Netflix and Uber segregating thread pools for critical payment checkouts vs slow, non-critical recommendation algorithms.",
        "diagram": """
                       Incoming Traffic
                              |
                 +------------+------------+
                 |                         |
                 v                         v
       [ Critical Pool ]           [ Non-Critical Pool ]
     (Checkout: 50 Threads)       (Recommendations: 10 Threads)
                 |                         |
                 v                         v
          Stripe Payment             AI Vector Search
                 |                         |
             (Smooth)              (Hung / Slow 10s)
                                           |
                                  Max 10 threads blocked!
                           Checkout pool remains 100% available!
""",
        "code": """/**
 * Bulkhead Isolation Pattern
 * Concurrency Semaphore Bulkhead with segregated execution quotas
 */

export class BulkheadCompartment {
  private activeCount: number = 0;
  private queue: Array<() => void> = [];

  constructor(
    public readonly name: string,
    private readonly maxConcurrent: number,
    private readonly maxQueue: number
  ) {}

  async execute<T>(task: () => Promise<T>): Promise<T> {
    if (this.activeCount < this.maxConcurrent) {
      this.activeCount++;
      try {
        return await task();
      } finally {
        this.release();
      }
    }

    if (this.queue.length >= this.maxQueue) {
      throw new Error(`BulkheadRejectedException: Compartment '${this.name}' capacity saturated (${this.activeCount} active, ${this.queue.length} queued).`);
    }

    // Wait in queue
    return new Promise<T>((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const res = await task();
          resolve(res);
        } catch (err) {
          reject(err);
        } finally {
          this.release();
        }
      });
    });
  }

  private release(): void {
    if (this.queue.length > 0) {
      const nextTask = this.queue.shift()!;
      nextTask();
    } else {
      this.activeCount--;
    }
  }

  getMetrics() {
    return { name: this.name, active: this.activeCount, queued: this.queue.length };
  }
}
""",
        "edge_cases": """1. **Resource Underutilization**: If non-critical traffic is zero, allocating 50 dedicated threads to checkout might leave idle hardware unharvested. Modern implementations use dynamic autoscaling semaphores.
2. **Downstream Cascading Resource Exhaustion**: Even if Service A isolates its thread pools, if both pools hit the same database connection pool, the bulkhead fails at the database tier. Bulkheads must be applied at all layers (threads, DB connections, memory).""",
        "tradeoffs": """### When to Use:
- Multi-tenant platforms or microservices hosting both high-priority core operations (e.g. login, payment) and high-latency, low-priority operations (e.g. analytics exports, batch PDF rendering).

### When NOT to Use:
- Uniform low-latency microservices with homogenous workloads where simple global connection pooling is more resource efficient."""
    },
    {
        "filename": "03_Retry_Exponential_Backoff_Jitter.md",
        "title": "Retry with Exponential Backoff and Full Jitter Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Transparently recover from transient network glitches by retrying failed idempotent requests with progressively doubling wait delays randomized with mathematical jitter to eliminate thundering herd synchronization.",
        "industry_example": "AWS SDK Architecture (Amazon DynamoDB & S3 client retry algorithms that prevent thousands of simultaneous clients from synchronizing retry spikes against recovering servers).",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Retrying Non-Idempotent Operations**: Retrying a `POST /charge-card` without an Idempotency-Key can charge the customer multiple times. NEVER retry non-idempotent writes without server-enforced idempotency keys!
2. **Amplifying Outages (Retry Storms)**: When a downstream database is already operating at 100% CPU, 5,000 clients retrying 3 times triples the traffic to 15,000 requests, driving the database into total collapse. Circuit breakers must gate retry policies.
3. **End-to-End Latency Breach**: Doubling delays can cause total execution time to exceed the upstream HTTP gateway timeout (e.g. 30 seconds), rendering the client retry wasted.""",
        "tradeoffs": """### When to Use:
- Handling transient network blips (DNS timeouts, TCP socket resets, HTTP 503 Service Unavailable, 429 Too Many Requests).

### When NOT to Use:
- Deterministic client errors (HTTP 400 Bad Request, 401 Unauthorized, 422 Unprocessable Entity) which will never succeed on retry."""
    },
    {
        "filename": "04_Rate_Limiting_Throttling.md",
        "title": "Rate Limiting and Throttling Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Control the rate of traffic sent or received by an API to protect services from abuse, denial-of-service (DoS) attacks, resource exhaustion, and ensure fair resource allocation across tenants.",
        "industry_example": "Stripe, GitHub, and Cloudflare API rate limiters (e.g. 5,000 requests per hour for authenticated accounts, 60 requests per minute for unauthenticated IPs).",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Distributed State Race Conditions**: In a cluster of 20 API servers, checking and decrementing token counters in Redis can suffer from check-then-act concurrency race conditions. Mitigation: Execute token updates via atomic Redis Lua scripts.
2. **Fixed Window Edge Spike**: If 100 requests are allowed per minute, a client sending 100 requests at 11:59:59 and another 100 at 12:00:01 pushes 200 requests in 2 seconds. Mitigation: Use Sliding Window Log or Token Bucket.
3. **VIP / Tiered Quota Bypass**: Internal admin jobs or critical payment webhooks should not be throttled alongside generic unauthenticated web visitors.""",
        "tradeoffs": """### When to Use:
- Public APIs, multi-tenant SaaS backends, and login endpoints susceptible to credential stuffing or DDoS attacks.

### When NOT to Use:
- Low-latency internal microservice communication within the same private VPC where network overhead of rate limit checks adds latency without threat exposure."""
    },
    {
        "filename": "05_Dead_Letter_Queue_DLQ.md",
        "title": "Dead-Letter Queue (DLQ) Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Route unprocessable, poison-pill messages that repeatedly fail consumer processing into a dedicated quarantine queue for offline inspection, diagnostics, and replay without blocking main message processing.",
        "industry_example": "AWS SQS DLQ, Apache Kafka dead-letter topics at Uber and Shopify (isolating corrupted JSON payloads or deleted account references so normal transactions continue uninterrupted).",
        "diagram": """
   +----------------------+
   |  Main Message Queue  |
   +----------------------+
              |
      Consume message
              v
   +----------------------+
   |   Consumer Worker    | ==(3 Failures)==> [ Move to DLQ ]
   +----------------------+                          |
              |                                      v
     (Successful msgs)                     +--------------------+
              v                            | Dead-Letter Queue  |
       Database Commit                     +--------------------+
                                                     |
                                            Admin Triage / Replay
""",
        "code": """/**
 * Dead-Letter Queue Pattern
 * Poison-pill isolation with error metadata envelope and redrive management
 */

export interface PoisonEnvelope<T = any> {
  originalMessageId: string;
  originalTopic: string;
  payload: T;
  retryCount: number;
  failureReason: string;
  failedAt: string;
}

export class DeadLetterQueueManager<T> {
  private dlqStorage: PoisonEnvelope<T>[] = [];

  constructor(private maxRetries: number = 3) {}

  async processWithDlq(
    topic: string,
    messageId: string,
    payload: T,
    processor: (payload: T) => Promise<void>
  ): Promise<boolean> {
    let retries = 0;
    let lastError: any;

    while (retries < this.maxRetries) {
      try {
        await processor(payload);
        return true; // Success
      } catch (err: any) {
        retries++;
        lastError = err;
        console.warn(`[QueueWorker] Message ${messageId} processing attempt ${retries}/${this.maxRetries} failed: ${err.message}`);
      }
    }

    // Max retries exceeded -> Route to Dead-Letter Queue
    console.error(`[DLQ] Quarantining poison message ${messageId} to Dead-Letter Queue.`);
    this.dlqStorage.push({
      originalMessageId: messageId,
      originalTopic: topic,
      payload,
      retryCount: retries,
      failureReason: lastError?.message || 'Unknown error',
      failedAt: new Date().toISOString()
    });

    return false;
  }

  getDlqMessages(): PoisonEnvelope<T>[] {
    return [...this.dlqStorage];
  }

  // Administrative Redrive / Replay back to primary queue
  async redrive(messageId: string, reprocessFn: (payload: T) => Promise<void>): Promise<boolean> {
    const idx = this.dlqStorage.findIndex(m => m.originalMessageId === messageId);
    if (idx === -1) return false;

    const envelope = this.dlqStorage[idx];
    console.log(`[DLQ Redrive] Attempting administrative replay for message ${messageId}...`);

    try {
      await reprocessFn(envelope.payload);
      this.dlqStorage.splice(idx, 1); // Removed from DLQ upon successful fix
      console.log(`[DLQ Redrive] Message ${messageId} replayed and removed from DLQ.`);
      return true;
    } catch (err: any) {
      console.error(`[DLQ Redrive] Replay failed: ${err.message}`);
      return false;
    }
  }
}
""",
        "edge_cases": """1. **DLQ Silent Accumulation**: If a software bug causes 100% of messages to route to the DLQ, and no alerts are configured, thousands of orders silently fail unnoticed. Set up CloudWatch / Datadog alerts on `DLQ.Depth > 0`.
2. **Redrive Storms**: Replaying 50,000 backlogged DLQ messages simultaneously after deploying a bugfix can overwhelm downstream databases. Use throttled batch redrive.
3. **Message Expiry in DLQ**: Cloud SQS DLQs have default message retention limits (e.g. 14 days). If unaddressed within 14 days, poison messages are deleted permanently.""",
        "tradeoffs": """### When to Use:
- All mission-critical asynchronous message queues to prevent single corrupted messages from halting an entire consumer group partition.

### When NOT to Use:
- Synchronous HTTP request-response APIs (use standard HTTP 4xx/5xx responses and client logs instead)."""
    },
    {
        "filename": "06_Fallback_Graceful_Degradation.md",
        "title": "Fallback and Graceful Degradation Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Maintain core system availability during partial outages by switching to fallback strategies (stale caches, default static content, or disabled secondary features) instead of displaying an error page.",
        "industry_example": "Amazon Product Page & Netflix Home Screen (If the AI personalized recommendations engine is down, Amazon falls back to hardcoded Top 10 Best Sellers; if user bookmark sync fails, Netflix plays video without showing bookmarks).",
        "diagram": """
Client Requests Home Page
           |
           v
+------------------------------------+
| Personalization Service Available? |
+------------------------------------+
         /                  \\
   (Yes)/                    \\(No / Timeout 200ms)
       v                      v
[ Live AI Custom Rows ]  [ Fallback Static Top 10 Bestsellers ]
       \\                      /
        v                    v
+------------------------------------+
| Client Receives Functional Webpage |
|      (No 500 Server Error)         |
+------------------------------------+
""",
        "code": """/**
 * Fallback & Graceful Degradation Pattern
 * Multi-tiered fallback hierarchy (Live -> Local Stale Cache -> Static Default)
 */

export interface ProductSummary {
  id: string;
  title: string;
  price: number;
  source: 'LIVE_SERVICE' | 'STALE_CACHE' | 'STATIC_FALLBACK';
}

export class GracefulRecommendationService {
  private staleCache = new Map<string, ProductSummary[]>();

  async getRecommendations(userId: string): Promise<ProductSummary[]> {
    try {
      // 1. Primary: Attempt live personalized microservice call with strict 300ms timeout
      const liveData = await this.fetchLiveWithTimeout(userId, 300);
      
      // Update stale cache for future resilience
      this.staleCache.set(userId, liveData);
      return liveData;
    } catch (err: any) {
      console.warn(`[FallbackService] Primary call failed (${err.message}). Degrading to Level 2: Stale Cache.`);

      // 2. Secondary Fallback: Serve stale personalized cache if available
      const cached = this.staleCache.get(userId);
      if (cached && cached.length > 0) {
        return cached.map(item => ({ ...item, source: 'STALE_CACHE' }));
      }

      // 3. Tertiary Fallback: Hardcoded static default catalog
      console.warn('[FallbackService] Stale cache missed. Degrading to Level 3: Static Default Catalog.');
      return this.getStaticFallbackCatalog();
    }
  }

  private async fetchLiveWithTimeout(userId: string, timeoutMs: number): Promise<ProductSummary[]> {
    // Simulating remote service timeout failure
    throw new Error('AI Personalization cluster timeout (> 300ms)');
  }

  private getStaticFallbackCatalog(): ProductSummary[] {
    return [
      { id: 'prod-01', title: 'Top Seller: Wireless Headphones', price: 99.99, source: 'STATIC_FALLBACK' },
      { id: 'prod-02', title: 'Top Seller: Ergonomic Keyboard', price: 129.99, source: 'STATIC_FALLBACK' }
    ];
  }
}
""",
        "edge_cases": """1. **Fallback Masquerading as Normal Operation**: If a fallback is too seamless, engineers might not notice the primary service has been offline for 3 days. Always emit telemetry metrics whenever a fallback path executes.
2. **Financial / Transactional Fallbacks**: NEVER provide optimistic fallbacks for payments or money transfers. If payment verification fails, fail explicitly rather than guessing approval.
3. **Stale Cache Expiry Threshold**: Serving cached data that is 10 minutes old is great; serving cached bank balances that are 3 days old is dangerous. Enforce maximum tolerable staleness.""",
        "tradeoffs": """### When to Use:
- Customer-facing interfaces (browsing, search, recommendation, home feed) where showing slightly stale or generic data is vastly superior to displaying an error.

### When NOT to Use:
- Cryptographic verification, money disbursement, medical dosing, or operations where incorrect data causes severe harm."""
    },
    {
        "filename": "07_Timeout_Deadline_Propagation.md",
        "title": "Timeout and Deadline Propagation Pattern",
        "category": "Resilience & Fault Tolerance Patterns",
        "intent": "Propagate a client's maximum allowable execution deadline across all downstream microservice calls so that subsequent services terminate work immediately if the upstream caller has already timed out.",
        "industry_example": "gRPC Deadline Propagation & Google Internal RPC Framework (Stubby) where every RPC request carries a deadline timestamp; if a backend query takes 5 seconds when the user set a 2-second timeout, all downstream queries abort immediately.",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Clock Skew Across Distributed Nodes**: If server clocks differ by 500ms via NTP drift, absolute deadline timestamps will be miscalculated. Solution: Propagate relative remaining time duration (e.g. `X-Remaining-Time-Ms: 850`) instead of absolute wall clock time.
2. **Partial Write Cancellation**: If an operation is aborted midway due to deadline expiry, ensure incomplete database records are rolled back or cleaned up to avoid orphaned records.
3. **Database Connection Leaks**: When canceling a call due to deadline expiry, ensure the underlying TCP socket or HTTP/2 stream is formally cancelled via `AbortController`.""",
        "tradeoffs": """### When to Use:
- Multi-tier microservices with deep call trees (Service A -> B -> C -> D) to prevent wasted CPU, memory, and database locks on abandoned requests.

### When NOT to Use:
- Asynchronous fire-and-forget background jobs that are meant to run to completion regardless of user browser disconnection."""
    }
]

def generate():
    for p in patterns:
        filepath = os.path.join(TARGET_DIR, p["filename"])
        content = f"""# {p['title']}

## 1. Classification & Intent
- **Pattern Category:** {p['category']}
- **Core Intent:** {p['intent']}

---

## 2. Real-Life Industry Example
{p['industry_example']}

---

## 3. Architecture & Flow Diagram
```
{p['diagram'].strip()}
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
{p['code'].strip()}
```

---

## 5. Edge Cases & Failure Scenarios
{p['edge_cases'].strip()}

---

## 6. Trade-offs: When to Use vs When NOT to Use
{p['tradeoffs'].strip()}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[Generated] {p['filename']}")

if __name__ == "__main__":
    generate()
    print("[Resilience] Successfully generated all 7 patterns.")
