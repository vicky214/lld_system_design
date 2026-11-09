# Write-Through and Write-Behind (Write-Back) Pattern

## 1. Classification & Intent
- **Pattern Category:** Caching & Concurrency Patterns
- **Core Intent:** Maintain cache-database synchronization by making the cache the primary write target: Write-Through writes synchronously to cache and DB together; Write-Behind writes immediately to cache and asynchronously batches updates to the DB.

---

## 2. Real-Life Industry Example
Linux OS Page Cache (Write-Behind disk buffer) and Redis Enterprise / Hazelcast caching layers for high-frequency IoT sensor telemetry.

---

## 3. Architecture & Flow Diagram
```
[ Write-Through ]
Client ---> [ Cache ] --(Synchronous Write)--> [ Database ]

[ Write-Behind / Write-Back ]
Client ---> [ Cache ] (Immediate return < 2ms)
                 |
          (Async Queue / Buffer)
                 v
            [ Database ] (Batched writes every 5 seconds)
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Data Loss on Node Crash (Write-Behind)**: If the server crashes before dirty entries are flushed from memory to disk, queued writes are lost forever. Mitigation: Replicate cache nodes or back the write queue with persistent Redis AOF / Kafka.
2. **Write-Through Latency**: In Write-Through, write latency is the sum of both cache latency + database disk write latency.
3. **Queue Overflow**: If the database slows down, the in-memory dirty write queue grows unbounded until an Out-Of-Memory (OOM) crash occurs. Enforce bounded queue with backpressure.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Write-Behind: Ultra-high-write workloads (gaming leaderboards, IoT sensor telemetry, view counter increments) where throughput is king.
- Write-Through: Systems where reading back newly written data must guarantee immediate consistency without cache misses.

### When NOT to Use:
- Write-Behind: Financial ledger transactions where zero data loss on node failure is mandatory.
