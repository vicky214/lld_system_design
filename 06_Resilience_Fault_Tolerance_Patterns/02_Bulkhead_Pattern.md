# Bulkhead Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Isolate critical resources (thread pools, connection pools, memory partitions) into segregated compartments so that a failure or slowdown in one component cannot exhaust the entire system's capacity.

---

## 2. Real-Life Industry Example
Shipbuilding watertight bulkheads; Netflix and Uber segregating thread pools for critical payment checkouts vs slow, non-critical recommendation algorithms.

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Resource Underutilization**: If non-critical traffic is zero, allocating 50 dedicated threads to checkout might leave idle hardware unharvested. Modern implementations use dynamic autoscaling semaphores.
2. **Downstream Cascading Resource Exhaustion**: Even if Service A isolates its thread pools, if both pools hit the same database connection pool, the bulkhead fails at the database tier. Bulkheads must be applied at all layers (threads, DB connections, memory).

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Multi-tenant platforms or microservices hosting both high-priority core operations (e.g. login, payment) and high-latency, low-priority operations (e.g. analytics exports, batch PDF rendering).

### When NOT to Use:
- Uniform low-latency microservices with homogenous workloads where simple global connection pooling is more resource efficient.
