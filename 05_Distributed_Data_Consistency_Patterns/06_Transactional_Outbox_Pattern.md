# Transactional Outbox Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Atomically commit business data and outgoing domain events within the same local database transaction into an 'outbox' table, guaranteeing zero event loss even if the message broker is temporarily offline.

---

## 2. Real-Life Industry Example
PayPal & Stripe payment webhook delivery engines (Writing payment record and webhook event to PostgreSQL in one local ACID commit, then an async worker relays events to Kafka/RabbitMQ).

---

## 3. Architecture & Flow Diagram
```
+-------------------------------------------------------------+
|                     PostgreSQL Database                     |
|  BEGIN TRANSACTION;                                         |
|    1. INSERT INTO orders VALUES (...);                      |
|    2. INSERT INTO outbox (topic, payload) VALUES (...);     |
|  COMMIT;                                                    |
+-------------------------------------------------------------+
                              |
                     Poller / CDC Reader
                              v
                +----------------------------+
                |    Outbox Relay Worker     |
                +----------------------------+
                              |
                      Reliable Publish
                              v
                +----------------------------+
                |   Kafka / RabbitMQ Broker  |
                +----------------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Transactional Outbox Pattern
 * Guaranteed dual-write atomicity without distributed 2PC transactions
 */

export interface OutboxRecord {
  id: string;
  topic: string;
  payload: string;
  status: 'PENDING' | 'SENT' | 'FAILED';
  createdAt: number;
}

export class TransactionalOrderService {
  private ordersTable = new Map<string, any>();
  private outboxTable: OutboxRecord[] = [];

  // Atomic database transaction simulation
  async createOrderAtomically(orderId: string, customerId: string, amount: number): Promise<void> {
    console.log(`[OrderService] Starting DB Transaction for Order ${orderId}...`);

    // 1. Write domain entity
    this.ordersTable.set(orderId, { orderId, customerId, amount, status: 'CREATED' });

    // 2. Write event to Outbox table within the SAME transaction boundary
    const outboxEntry: OutboxRecord = {
      id: `outbox-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
      topic: 'orders.v1.created',
      payload: JSON.stringify({ orderId, customerId, amount }),
      status: 'PENDING',
      createdAt: Date.now()
    };
    this.outboxTable.push(outboxEntry);

    console.log(`[OrderService] Transaction Committed: Order + Outbox record saved atomically.`);
  }

  getOutbox(): OutboxRecord[] {
    return this.outboxTable;
  }
}

// Background Relay Worker
export class OutboxRelayWorker {
  constructor(private orderService: TransactionalOrderService, private brokerPublisher: (topic: string, msg: string) => Promise<void>) {}

  async sweepAndPublish(): Promise<void> {
    const outbox = this.orderService.getOutbox();
    const pending = outbox.filter(o => o.status === 'PENDING');

    for (const record of pending) {
      try {
        console.log(`[OutboxRelay] Publishing message ${record.id} to broker topic ${record.topic}`);
        await this.brokerPublisher(record.topic, record.payload);
        record.status = 'SENT';
      } catch (err: any) {
        console.error(`[OutboxRelay] Failed to publish ${record.id}: ${err.message}. Will retry.`);
        record.status = 'FAILED';
      }
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **At-Least-Once Delivery to Broker**: If the worker publishes to Kafka and crashes before marking the outbox row as `SENT`, the next iteration will republish the same message. Downstream consumers MUST be idempotent.
2. **Outbox Polling Table Bloat**: Frequent table polling (`SELECT * FROM outbox WHERE status='PENDING'`) adds database read load. Mitigation: Use indexed status columns, batch queries with `SKIP LOCKED`, or switch to Transaction Log Tailing (CDC).
3. **Outbox Growth & Retention**: Sent messages will accumulate indefinitely. Set up a daily cron purge job for records where `status = 'SENT' AND createdAt < NOW() - INTERVAL '7 days'`.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Essential in distributed systems whenever a database mutation must reliably trigger an external message (Kafka, RabbitMQ, SQS) with zero message loss guarantee.

### When NOT to Use:
- When using native Change Data Capture (Debezium) or in systems where missing occasional events is tolerable (e.g. non-critical user telemetry analytics).
