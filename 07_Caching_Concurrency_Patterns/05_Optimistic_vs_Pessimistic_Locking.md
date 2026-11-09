# Optimistic vs Pessimistic Locking Pattern

## 1. Classification & Intent
- **Pattern Category:** Caching & Concurrency Patterns
- **Core Intent:** Prevent lost updates and dirty writes during concurrent database modifications: Optimistic locking checks record version during write without holding locks; Pessimistic locking locks the database record upfront using exclusive locks.

---

## 2. Real-Life Industry Example
E-Commerce Flash Sale / Ticket Booking (BookMyShow uses Pessimistic `SELECT FOR UPDATE` to lock seats for 10 minutes; GitHub PR reviews and Wikipedia edits use Optimistic version checking).

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Deadlocks in Pessimistic Locking**: Transaction 1 locks Seat A and waits for Seat B; Transaction 2 locks Seat B and waits for Seat A. Mitigation: Strict global lock ordering (always lock lower IDs first) and lock wait timeouts.
2. **Optimistic Starvation Under Flash Sales**: If 10,000 users try to buy 1 item at 12:00:00, optimistic locking causes 9,999 failures and massive retry storm CPU load. Under extreme contention, Pessimistic locking or queue serialization wins!
3. **Long Transaction Hold**: In Pessimistic locking, never make external third-party HTTP calls (e.g. calling Stripe) while holding an open database row lock.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Optimistic: Low-to-medium contention systems (document editing, user profiles, inventory with plentiful stock) where conflicts are rare.
- Pessimistic: High-contention limited resources (seat booking, flight reservations, flash sales) where conflict probability is very high.

### When NOT to Use:
- Pessimistic: High-throughput distributed microservices where holding row locks destroys database connection pool scalability.
