# Cache Stampede Prevention (SingleFlight / Mutex Lock) Pattern

## 1. Classification & Intent
- **Pattern Category:** Caching & Concurrency Patterns
- **Core Intent:** Prevent massive database overload when a heavily queried cache key expires by ensuring only one worker queries the database to recompute the value while all other concurrent requests wait or share the same in-flight promise.

---

## 2. Real-Life Industry Example
Go `singleflight` package used at Uber and Cloudflare, and Redis Mutex Locks used at Reddit during viral post traffic spikes.

---

## 3. Architecture & Flow Diagram
```
1,000 Concurrent Requests for 'Trending_Topic' (Expired Key)
                   |
                   v
    +------------------------------+
    |   SingleFlight Coordinator   |
    +------------------------------+
       /             |            \
 (Request 1)   (Request 2..1000)
     |               |
     v               v
 Queries DB      Wait on Request 1's Promise
     |               |
     +-------+-------+
             v
 All 1,000 requests receive the result simultaneously!
 Database was queried exactly ONCE!
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * SingleFlight / Mutex Cache Stampede Prevention Pattern
 * Deduplicates in-flight compute promises across concurrent callers
 */

export class SingleFlightCoordinator {
  private inFlightCalls = new Map<string, Promise<any>>();

  async do<T>(key: string, fn: () => Promise<T>): Promise<T> {
    // If a call for this key is ALREADY running, reuse its active Promise!
    const existing = this.inFlightCalls.get(key);
    if (existing) {
      console.log(`[SingleFlight] Key '${key}' is already being computed. Joining in-flight execution!`);
      return await existing;
    }

    console.log(`[SingleFlight] Key '${key}' initiated leader execution.`);
    const promise = fn()
      .then(res => {
        this.inFlightCalls.delete(key);
        return res;
      })
      .catch(err => {
        this.inFlightCalls.delete(key);
        throw err;
      });

    this.inFlightCalls.set(key, promise);
    return await promise;
  }
}

// Practical usage in Cached Data Fetcher
export class StampedeProtectedCache {
  private coordinator = new SingleFlightCoordinator();
  private cache = new Map<string, { value: string; expiresAt: number }>();

  async getOrCompute(key: string, ttlMs: number, computeFn: () => Promise<string>): Promise<string> {
    const item = this.cache.get(key);
    if (item && Date.now() < item.expiresAt) {
      return item.value;
    }

    // Wrap the database query inside SingleFlight!
    return await this.coordinator.do(key, async () => {
      // Double-check cache inside lock in case another worker just finished it
      const freshItem = this.cache.get(key);
      if (freshItem && Date.now() < freshItem.expiresAt) {
        return freshItem.value;
      }

      console.log(`[DB] Executing heavy query for key: ${key}`);
      const computedValue = await computeFn();
      this.cache.set(key, { value: computedValue, expiresAt: Date.now() + ttlMs });
      return computedValue;
    });
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Single Worker Failure Propagation**: If the leader query fails with an exception, all 1,000 waiting requests receive the exact same error. Ensure fast retry or fallback to stale cache.
2. **Distributed SingleFlight across Multi-Server Clusters**: SingleFlight in Node.js/Go protects a single pod. Across 50 Kubernetes pods, 50 queries still reach the database unless a distributed Redis mutex lock is used.
3. **Probabilistic Early Expiration (XFetch)**: Another powerful strategy: background recompute the cache slightly before it actually expires based on request probability: `delta * beta * log(rand())`.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Viral, hot cache keys (e.g. Breaking News headline, Homepage banner, World Cup live score) queried thousands of times per second.

### When NOT to Use:
- Uniformly distributed long-tail cache keys (e.g. searching archived order receipts from 2018) where concurrent misses on the exact same key are statistically improbable.
