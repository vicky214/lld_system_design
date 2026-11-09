# Cache-Aside (Lazy Loading) Pattern

## 1. Classification & Intent
- **Pattern Category:** Caching & Concurrency Patterns
- **Core Intent:** Load data on demand into cache only when requested (cache miss); on database updates, invalidate (delete) the cached entry to prevent stale read races.

---

## 2. Real-Life Industry Example
Facebook Memcached & Twitter Redis architecture (fetching user profile data from Redis; on cache miss, query MySQL and populate Redis with a TTL; on profile edit, delete Redis key).

---

## 3. Architecture & Flow Diagram
```
Client Read Request
        |
        v
+------------------+
| Check Cache (Key)|
+------------------+
     /          \
 (Hit)          (Miss)
   v               v
Return Data   +--------------------+
              | Query Database     |
              +--------------------+
                       |
              Write to Cache (TTL)
                       |
                       v
                  Return Data
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Cache-Aside Pattern
 * On-demand read loading with explicit cache invalidation on write
 */

export interface CacheStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string, ttlSeconds: number): Promise<void>;
  del(key: string): Promise<void>;
}

export interface UserRecord {
  id: string;
  name: string;
  email: string;
  bio: string;
}

export class CacheAsideUserService {
  constructor(
    private cache: CacheStore,
    private database: Map<string, UserRecord> // Simulated DB
  ) {}

  async getUser(userId: string): Promise<UserRecord | null> {
    const cacheKey = `user:${userId}`;

    // 1. Try reading from Cache first
    const cachedJson = await this.cache.get(cacheKey);
    if (cachedJson) {
      console.log(`[CacheAside] Cache HIT for key: ${cacheKey}`);
      return JSON.parse(cachedJson);
    }

    // 2. Cache MISS -> Read from primary Database
    console.log(`[CacheAside] Cache MISS for key: ${cacheKey}. Querying DB...`);
    const dbRecord = this.database.get(userId) || null;

    if (dbRecord) {
      // 3. Populate Cache with a safe Time-to-Live (TTL)
      await this.cache.set(cacheKey, JSON.stringify(dbRecord), 300); // 5 min TTL
    }

    return dbRecord;
  }

  async updateUser(userId: string, updates: Partial<UserRecord>): Promise<void> {
    const cacheKey = `user:${userId}`;

    // 1. Update Database first
    const existing = this.database.get(userId);
    if (!existing) throw new Error(`User ${userId} not found`);
    const updated = { ...existing, ...updates };
    this.database.set(userId, updated);

    // 2. INVALIDATE (DELETE) cache key instead of updating it
    // Why delete instead of set? Deleting avoids race conditions where two concurrent writes
    // update cache and DB in reverse order!
    await this.cache.del(cacheKey);
    console.log(`[CacheAside] DB updated & cache key ${cacheKey} invalidated successfully.`);
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Cache Penetration**: Malicious users querying non-existent keys (e.g. `user:random-uuid-9999`) bypass the cache and hit the database directly. Mitigation: Cache empty results with short TTL (e.g. 60 seconds) or use a Bloom Filter.
2. **Cache Stampede on Expiration**: When a popular key expires, 10,000 concurrent requests miss simultaneously and overwhelm the DB. Mitigation: Mutual exclusion locking or early probabilistic recomputation (XFetch).
3. **Database Update vs Cache Deletion Race**: If DB update succeeds but Redis delete fails, the cache holds stale data until TTL expires. Use transactional outbox or retry queues for cache deletion.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Read-heavy workloads where data changes infrequently and temporary cache misses are acceptable.

### When NOT to Use:
- Strict real-time financial balances where zero staleness can be tolerated, or write-heavy systems where cached data is invalidated before it is ever read.
