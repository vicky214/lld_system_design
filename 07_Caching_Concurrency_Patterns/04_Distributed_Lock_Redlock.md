# Distributed Lock (Redlock) Pattern

## 1. Classification & Intent
- **Pattern Category:** Caching & Concurrency Patterns
- **Core Intent:** Coordinate mutual exclusion across a distributed multi-node cluster using consensus or multi-instance Redis locks with automatic heartbeat expiration and atomic release tokens.

---

## 2. Real-Life Industry Example
Redis Redlock algorithm and ZooKeeper / etcd distributed locks at Uber and Airbnb (preventing double-booking of hotel rooms or concurrent duplicate refund executions across microservice pods).

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **GC Pause / Process Freeze (Fencing Tokens)**: If a client acquires a lock for 5s, undergoes a 10s stop-the-world Garbage Collection pause, its lock expires. Another client acquires the lock, and both write concurrently! Solution: Martin Kleppmann's fencing tokens (monotonically incrementing integer checked by the storage layer).
2. **Redis Master-Replica Failover Loss**: Redis replication is asynchronous. If master crashes before replicating the lock key to replica, failover replica allows a second client to acquire the same lock.
3. **Missing Lock Renewal (Watchdog)**: If a long database transaction takes 7 seconds on a 5-second lock, the lock auto-expires midway. A background timer watchdog must refresh TTL every 2 seconds while active.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Non-idempotent operations where multiple servers might process the exact same resource concurrently (preventing double payouts or coupon redemption).

### When NOT to Use:
- High-frequency low-latency paths (> 100,000 ops/sec) where distributed locks create massive coordination bottlenecks. Use optimistic locking or partitioning instead.
