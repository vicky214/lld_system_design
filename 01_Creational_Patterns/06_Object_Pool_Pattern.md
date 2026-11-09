# Object Pool Pattern

## Category: Creational Pattern

---

## 1. Core Intent & Definition
Manage the reuse of a pool of pre-allocated, expensive-to-create objects rather than continuously allocating and destroying them, minimizing Garbage Collection (GC) pressure and socket exhaustion.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Continuously creating and tearing down high-overhead resources (TCP sockets, database connections, SSL handshake sessions) causes severe CPU spikes, memory fragmentation, and frequent Garbage Collection pauses that degrade real-time performance.

### Real-World Industry Example:
Database / Network Connection Pool. An API handling 10,000 requests per second leases pre-warmed connection instances from an active pool, executes queries, and returns connections to the pool for reuse.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------------------------------------+
|                       ObjectPool                      |
+-------------------------------------------------------+
| - available: Resource[]                               |
| - inUse: Map<string, Resource>                        |
| - maxCapacity: number                                 |
+-------------------------------------------------------+
| + acquire(timeoutMs): Promise<Resource>               |
| + release(resource): void                             |
+-------------------------------------------------------+
           ▲                             │
           │ (Returns resource)          │ (Leases resource)
           │                             ▼
    [ Client Request ] ◄─────── [ Active Resource ]
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface PoolableResource {
  id: string;
  isValid(): boolean;
  reset(): void;
}

export class MockDbConnection implements PoolableResource {
  public id: string;
  private isAlive = true;

  constructor(id: string) {
    this.id = id;
  }

  isValid(): boolean {
    return this.isAlive;
  }

  reset(): void {
    // Reset transaction state, session variables, etc.
  }

  close(): void {
    this.isAlive = false;
  }
}

export class ObjectPool<T extends PoolableResource> {
  private available: T[] = [];
  private inUse = new Set<T>();
  private maxCapacity: number;
  private factoryFn: () => T;
  private waitingQueue: Array<(resource: T) => void> = [];

  constructor(factoryFn: () => T, minSize = 2, maxCapacity = 10) {
    this.factoryFn = factoryFn;
    this.maxCapacity = maxCapacity;

    // Pre-warm minimum pool
    for (let i = 0; i < minSize; i++) {
      this.available.push(this.factoryFn());
    }
  }

  public async acquire(timeoutMs = 3000): Promise<T> {
    // 1. Reuse existing available resource if valid
    while (this.available.length > 0) {
      const resource = this.available.pop()!;
      if (resource.isValid()) {
        this.inUse.add(resource);
        return resource;
      }
    }

    // 2. Expand pool if under max capacity
    if (this.inUse.size < this.maxCapacity) {
      const newResource = this.factoryFn();
      this.inUse.add(newResource);
      return newResource;
    }

    // 3. Queue request if capacity reached
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        const index = this.waitingQueue.indexOf(resolve);
        if (index !== -1) {
          this.waitingQueue.splice(index, 1);
          reject(new Error("Connection pool acquisition timeout: Pool exhausted."));
        }
      }, timeoutMs);

      this.waitingQueue.push((resource: T) => {
        clearTimeout(timer);
        this.inUse.add(resource);
        resolve(resource);
      });
    });
  }

  public release(resource: T): void {
    if (!this.inUse.has(resource)) return;
    this.inUse.delete(resource);

    if (resource.isValid()) {
      resource.reset();

      if (this.waitingQueue.length > 0) {
        const nextCaller = this.waitingQueue.shift()!;
        nextCaller(resource);
      } else {
        this.available.push(resource);
      }
    }
  }

  public getStats() {
    return {
      available: this.available.length,
      inUse: this.inUse.size,
      queuedRequests: this.waitingQueue.length,
    };
  }
}

// --- Usage ---
let connCounter = 1;
const pool = new ObjectPool(() => new MockDbConnection(`conn-${connCounter++}`), 2, 5);

async function executeQuery() {
  const conn = await pool.acquire();
  try {
    console.log(`[Worker] Leased connection ${conn.id}`);
    await new Promise((r) => setTimeout(r, 40));
  } finally {
    pool.release(conn);
    console.log(`[Worker] Returned connection ${conn.id}`);
  }
}

executeQuery();
executeQuery();
```

---

## 5. Edge Cases & Failure Handling
- **Resource Leaks (Forgotten Releases)**: If a client throws an unhandled error and fails to execute `pool.release()`, the resource is leaked, eventually starving the pool. Always wrap acquire/release in `try ... finally` blocks.\n- **Dirty State Leakage**: When resources are returned, uncommitted database transactions or lingering socket buffers must be reset (`resource.reset()`) to avoid cross-request data leaks.\n- **Stale Resource Detection**: Network connections can silently drop behind firewalls. The pool must perform periodic health checks (`isValid()`) before leasing.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When object creation cost is high and rate of instantiation/destruction is extreme.\n- Managing finite external connections (DB sockets, TCP channels, audio/render buffers).

### When NOT to Use / Anti-patterns:
- For lightweight objects with low creation overhead (creating a pool for simple POJOs increases memory overhead and GC burden).
