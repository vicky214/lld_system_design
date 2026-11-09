import os

TARGET_DIR = "/home/vicky/Documents/Antigravity/lld/07_Caching_Concurrency_Patterns"
os.makedirs(TARGET_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Cache_Aside_Pattern.md",
        "title": "Cache-Aside (Lazy Loading) Pattern",
        "category": "Caching & Concurrency Patterns",
        "intent": "Load data on demand into cache only when requested (cache miss); on database updates, invalidate (delete) the cached entry to prevent stale read races.",
        "industry_example": "Facebook Memcached & Twitter Redis architecture (fetching user profile data from Redis; on cache miss, query MySQL and populate Redis with a TTL; on profile edit, delete Redis key).",
        "diagram": """
Client Read Request
        |
        v
+------------------+
| Check Cache (Key)|
+------------------+
     /          \\
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Cache Penetration**: Malicious users querying non-existent keys (e.g. `user:random-uuid-9999`) bypass the cache and hit the database directly. Mitigation: Cache empty results with short TTL (e.g. 60 seconds) or use a Bloom Filter.
2. **Cache Stampede on Expiration**: When a popular key expires, 10,000 concurrent requests miss simultaneously and overwhelm the DB. Mitigation: Mutual exclusion locking or early probabilistic recomputation (XFetch).
3. **Database Update vs Cache Deletion Race**: If DB update succeeds but Redis delete fails, the cache holds stale data until TTL expires. Use transactional outbox or retry queues for cache deletion.""",
        "tradeoffs": """### When to Use:
- Read-heavy workloads where data changes infrequently and temporary cache misses are acceptable.

### When NOT to Use:
- Strict real-time financial balances where zero staleness can be tolerated, or write-heavy systems where cached data is invalidated before it is ever read.""",
    },
    {
        "filename": "02_Write_Through_and_Write_Behind.md",
        "title": "Write-Through and Write-Behind (Write-Back) Pattern",
        "category": "Caching & Concurrency Patterns",
        "intent": "Maintain cache-database synchronization by making the cache the primary write target: Write-Through writes synchronously to cache and DB together; Write-Behind writes immediately to cache and asynchronously batches updates to the DB.",
        "industry_example": "Linux OS Page Cache (Write-Behind disk buffer) and Redis Enterprise / Hazelcast caching layers for high-frequency IoT sensor telemetry.",
        "diagram": """
[ Write-Through ]
Client ---> [ Cache ] --(Synchronous Write)--> [ Database ]

[ Write-Behind / Write-Back ]
Client ---> [ Cache ] (Immediate return < 2ms)
                 |
          (Async Queue / Buffer)
                 v
            [ Database ] (Batched writes every 5 seconds)
""",
        "code": """/**
 * Write-Behind (Write-Back) Caching Pattern
 * In-memory immediate write with asynchronous coalesced batch persistence
 */

export interface MetricEntry {
  deviceId: string;
  metric: string;
  value: number;
  timestamp: number;
}

export class WriteBehindBufferStore {
  private cache = new Map<string, number>();
  private dirtyQueue: MetricEntry[] = [];
  private flushTimer: any;

  constructor(private dbBatchWriter: (batch: MetricEntry[]) => Promise<void>) {
    // Background flush every 100ms
    this.flushTimer = setInterval(() => this.flushDirtyEntries(), 100);
  }

  // Ultra-fast write directly to in-memory cache
  writeMetric(deviceId: string, metric: string, value: number): void {
    const key = `${deviceId}:${metric}`;
    this.cache.set(key, value);

    // Enqueue for async database persistence
    this.dirtyQueue.push({ deviceId, metric, value, timestamp: Date.now() });
  }

  readMetric(deviceId: string, metric: string): number | undefined {
    return this.cache.get(`${deviceId}:${metric}`);
  }

  private async flushDirtyEntries(): Promise<void> {
    if (this.dirtyQueue.length === 0) return;

    const batch = [...this.dirtyQueue];
    this.dirtyQueue = []; // Drain queue

    try {
      console.log(`[WriteBehind] Flushing batch of ${batch.length} dirty updates to Database...`);
      await this.dbBatchWriter(batch);
    } catch (err: any) {
      console.error(`[WriteBehind CRITICAL] Failed to flush batch: ${err.message}. Re-queueing.`);
      this.dirtyQueue.unshift(...batch);
    }
  }

  destroy(): void {
    clearInterval(this.flushTimer);
  }
}
""",
        "edge_cases": """1. **Data Loss on Node Crash (Write-Behind)**: If the server crashes before dirty entries are flushed from memory to disk, queued writes are lost forever. Mitigation: Replicate cache nodes or back the write queue with persistent Redis AOF / Kafka.
2. **Write-Through Latency**: In Write-Through, write latency is the sum of both cache latency + database disk write latency.
3. **Queue Overflow**: If the database slows down, the in-memory dirty write queue grows unbounded until an Out-Of-Memory (OOM) crash occurs. Enforce bounded queue with backpressure.""",
        "tradeoffs": """### When to Use:
- Write-Behind: Ultra-high-write workloads (gaming leaderboards, IoT sensor telemetry, view counter increments) where throughput is king.
- Write-Through: Systems where reading back newly written data must guarantee immediate consistency without cache misses.

### When NOT to Use:
- Write-Behind: Financial ledger transactions where zero data loss on node failure is mandatory."""
    },
    {
        "filename": "03_Cache_Stampede_Prevention.md",
        "title": "Cache Stampede Prevention (SingleFlight / Mutex Lock) Pattern",
        "category": "Caching & Concurrency Patterns",
        "intent": "Prevent massive database overload when a heavily queried cache key expires by ensuring only one worker queries the database to recompute the value while all other concurrent requests wait or share the same in-flight promise.",
        "industry_example": "Go `singleflight` package used at Uber and Cloudflare, and Redis Mutex Locks used at Reddit during viral post traffic spikes.",
        "diagram": """
1,000 Concurrent Requests for 'Trending_Topic' (Expired Key)
                   |
                   v
    +------------------------------+
    |   SingleFlight Coordinator   |
    +------------------------------+
       /             |            \\
 (Request 1)   (Request 2..1000)
     |               |
     v               v
 Queries DB      Wait on Request 1's Promise
     |               |
     +-------+-------+
             v
 All 1,000 requests receive the result simultaneously!
 Database was queried exactly ONCE!
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Single Worker Failure Propagation**: If the leader query fails with an exception, all 1,000 waiting requests receive the exact same error. Ensure fast retry or fallback to stale cache.
2. **Distributed SingleFlight across Multi-Server Clusters**: SingleFlight in Node.js/Go protects a single pod. Across 50 Kubernetes pods, 50 queries still reach the database unless a distributed Redis mutex lock is used.
3. **Probabilistic Early Expiration (XFetch)**: Another powerful strategy: background recompute the cache slightly before it actually expires based on request probability: `delta * beta * log(rand())`.""",
        "tradeoffs": """### When to Use:
- Viral, hot cache keys (e.g. Breaking News headline, Homepage banner, World Cup live score) queried thousands of times per second.

### When NOT to Use:
- Uniformly distributed long-tail cache keys (e.g. searching archived order receipts from 2018) where concurrent misses on the exact same key are statistically improbable."""
    },
    {
        "filename": "04_Distributed_Lock_Redlock.md",
        "title": "Distributed Lock (Redlock) Pattern",
        "category": "Caching & Concurrency Patterns",
        "intent": "Coordinate mutual exclusion across a distributed multi-node cluster using consensus or multi-instance Redis locks with automatic heartbeat expiration and atomic release tokens.",
        "industry_example": "Redis Redlock algorithm and ZooKeeper / etcd distributed locks at Uber and Airbnb (preventing double-booking of hotel rooms or concurrent duplicate refund executions across microservice pods).",
        "diagram": """
Client Pod A                    Client Pod B
     |                               |
Acquire Lock 'room:304'         Acquire Lock 'room:304'
(UUID: A-123, TTL: 5000ms)      (UUID: B-456, TTL: 5000ms)
     |                               |
     v                               v
+------------------------------------+
|     Redis Cluster / Instances      |
|     SET key token NX PX 5000       |
+------------------------------------+
     |                               |
 (SUCCESS - Lock acquired)       (FAILED - Key exists)
     |                               |
 Critical Section Booking        Wait / Reject
     |
 Release via Atomic Lua Script
 (Only delete if token == A-123)
""",
        "code": """/**
 * Distributed Lock Pattern
 * Atomic acquisition with unique random token, heartbeat watchdog, and atomic Lua release
 */

export interface DistributedLockHandle {
  lockKey: string;
  token: string;
  release: () => Promise<boolean>;
}

export class DistributedLockManager {
  private store = new Map<string, { token: string; expiresAt: number }>();

  async acquireLock(lockKey: string, ttlMs: number = 5000): Promise<DistributedLockHandle | null> {
    const token = `token-${Math.random().toString(36).substr(2, 9)}`;
    const now = Date.now();

    // Check if key already locked and active
    const current = this.store.get(lockKey);
    if (current && current.expiresAt > now) {
      console.warn(`[Lock] Acquisition failed for '${lockKey}'. Already locked by token: ${current.token}`);
      return null;
    }

    // Atomic SET NX PX
    this.store.set(lockKey, { token, expiresAt: now + ttlMs });
    console.log(`[Lock] Acquired '${lockKey}' with token '${token}' for ${ttlMs}ms`);

    return {
      lockKey,
      token,
      release: async () => this.releaseLock(lockKey, token)
    };
  }

  // Atomic release: Only delete if the stored token matches our token!
  // In Redis, this MUST be executed as a Lua script:
  // if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end
  async releaseLock(lockKey: string, token: string): Promise<boolean> {
    const current = this.store.get(lockKey);
    if (!current) {
      console.warn(`[Lock] Release failed: Lock '${lockKey}' not found (possibly expired).`);
      return false;
    }

    if (current.token !== token) {
      console.error(`[Lock VIOLATION] Cannot release lock '${lockKey}': Token mismatch! Held by ${current.token}, attempted by ${token}`);
      return false;
    }

    this.store.delete(lockKey);
    console.log(`[Lock] Successfully released '${lockKey}'`);
    return true;
  }
}
""",
        "edge_cases": """1. **GC Pause / Process Freeze (Fencing Tokens)**: If a client acquires a lock for 5s, undergoes a 10s stop-the-world Garbage Collection pause, its lock expires. Another client acquires the lock, and both write concurrently! Solution: Martin Kleppmann's fencing tokens (monotonically incrementing integer checked by the storage layer).
2. **Redis Master-Replica Failover Loss**: Redis replication is asynchronous. If master crashes before replicating the lock key to replica, failover replica allows a second client to acquire the same lock.
3. **Missing Lock Renewal (Watchdog)**: If a long database transaction takes 7 seconds on a 5-second lock, the lock auto-expires midway. A background timer watchdog must refresh TTL every 2 seconds while active.""",
        "tradeoffs": """### When to Use:
- Non-idempotent operations where multiple servers might process the exact same resource concurrently (preventing double payouts or coupon redemption).

### When NOT to Use:
- High-frequency low-latency paths (> 100,000 ops/sec) where distributed locks create massive coordination bottlenecks. Use optimistic locking or partitioning instead."""
    },
    {
        "filename": "05_Optimistic_vs_Pessimistic_Locking.md",
        "title": "Optimistic vs Pessimistic Locking Pattern",
        "category": "Caching & Concurrency Patterns",
        "intent": "Prevent lost updates and dirty writes during concurrent database modifications: Optimistic locking checks record version during write without holding locks; Pessimistic locking locks the database record upfront using exclusive locks.",
        "industry_example": "E-Commerce Flash Sale / Ticket Booking (BookMyShow uses Pessimistic `SELECT FOR UPDATE` to lock seats for 10 minutes; GitHub PR reviews and Wikipedia edits use Optimistic version checking).",
        "diagram": """
[ Optimistic Locking (Low Contention) ]
Read Record (v=1)
Modify in Memory
UPDATE record SET balance = 150, version = 2 WHERE id = 101 AND version = 1;
-> If 0 rows updated, CONFLICT! Re-read and retry.

[ Pessimistic Locking (High Contention) ]
BEGIN TRANSACTION;
SELECT * FROM seats WHERE id = 42 FOR UPDATE;  <-- Row Locked for all others!
UPDATE seats SET status = 'BOOKED' WHERE id = 42;
COMMIT;                                        <-- Lock Released!
""",
        "code": """/**
 * Optimistic vs Pessimistic Concurrency Control
 * Comparison implementations with conflict detection and retry loops
 */

// 1. OPTIMISTIC LOCKING IMPLEMENTATION
export interface OptimisticProduct {
  id: string;
  name: string;
  stock: number;
  version: number; // Monotonic version counter
}

export class OptimisticInventoryService {
  private db = new Map<string, OptimisticProduct>([
    ['prod-1', { id: 'prod-1', name: 'iPhone 16 Pro', stock: 10, version: 1 }]
  ]);

  async purchaseWithRetry(productId: string, quantity: number, maxRetries = 3): Promise<boolean> {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      // 1. Read current state
      const product = this.db.get(productId);
      if (!product || product.stock < quantity) return false;

      const currentVersion = product.version;

      // 2. Perform business check
      const newStock = product.stock - quantity;

      // 3. Conditional Update: UPDATE products SET stock = newStock, version = version + 1 WHERE id = productId AND version = currentVersion
      const liveProduct = this.db.get(productId)!;
      if (liveProduct.version === currentVersion) {
        // Successful atomic compare-and-swap
        liveProduct.stock = newStock;
        liveProduct.version = currentVersion + 1;
        console.log(`[OptimisticLock] Success on attempt #${attempt}: Purchased ${quantity}. New stock: ${liveProduct.stock}, version: ${liveProduct.version}`);
        return true;
      }

      console.warn(`[OptimisticLock] Version conflict detected (Expected ${currentVersion}, found ${liveProduct.version}). Retrying attempt #${attempt + 1}...`);
      await new Promise(r => setTimeout(r, Math.random() * 50));
    }

    throw new Error('OptimisticLockConflictException: Max retries exceeded due to high write contention.');
  }
}

// 2. PESSIMISTIC LOCKING IMPLEMENTATION
export class PessimisticSeatReservationService {
  private lockedSeats = new Set<string>();

  async reserveSeatPessimistic(seatId: string, userId: string, action: () => Promise<void>): Promise<void> {
    // Emulates: SELECT * FROM seats WHERE id = ? FOR UPDATE;
    console.log(`[PessimisticLock] Acquiring exclusive database row lock for seat: ${seatId}`);
    
    if (this.lockedSeats.has(seatId)) {
      throw new Error(`PessimisticLockException: Seat ${seatId} is already locked by another active transaction.`);
    }

    this.lockedSeats.add(seatId);
    try {
      await action();
      console.log(`[PessimisticLock] Seat ${seatId} successfully booked for user ${userId}`);
    } finally {
      // COMMIT / ROLLBACK releases row lock
      this.lockedSeats.delete(seatId);
      console.log(`[PessimisticLock] Exclusive lock released for seat: ${seatId}`);
    }
  }
}
""",
        "edge_cases": """1. **Deadlocks in Pessimistic Locking**: Transaction 1 locks Seat A and waits for Seat B; Transaction 2 locks Seat B and waits for Seat A. Mitigation: Strict global lock ordering (always lock lower IDs first) and lock wait timeouts.
2. **Optimistic Starvation Under Flash Sales**: If 10,000 users try to buy 1 item at 12:00:00, optimistic locking causes 9,999 failures and massive retry storm CPU load. Under extreme contention, Pessimistic locking or queue serialization wins!
3. **Long Transaction Hold**: In Pessimistic locking, never make external third-party HTTP calls (e.g. calling Stripe) while holding an open database row lock.""",
        "tradeoffs": """### When to Use:
- Optimistic: Low-to-medium contention systems (document editing, user profiles, inventory with plentiful stock) where conflicts are rare.
- Pessimistic: High-contention limited resources (seat booking, flight reservations, flash sales) where conflict probability is very high.

### When NOT to Use:
- Pessimistic: High-throughput distributed microservices where holding row locks destroys database connection pool scalability."""
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
    print("[Caching & Concurrency] Successfully generated all 5 patterns.")
