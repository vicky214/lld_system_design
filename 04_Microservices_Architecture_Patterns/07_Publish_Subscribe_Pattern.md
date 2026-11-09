# Publish-Subscribe (Pub/Sub) Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Enable asynchronous, loosely coupled communication where message producers (publishers) broadcast events to topics without knowing which or how many consumers (subscribers) will receive them.

---

## 2. Real-Life Industry Example
Apache Kafka or RabbitMQ at LinkedIn & Uber (publishing 'RiderRequested' or 'ConnectionAccepted' consumed concurrently by Notification, Billing, Driver Search, and ML Data Pipelines).

---

## 3. Architecture & Flow Diagram
```
+-------------------+
                       |    Publisher      |
                       |  (Order Service)  |
                       +-------------------+
                                 |
                          publish('OrderCreated')
                                 v
               +-----------------------------------+
               |       Message Broker / Kafka      |
               |       Topic: 'orders.v1'          |
               +-----------------------------------+
                     /           |           \
                    v            v            v
           +-----------+   +-----------+   +-----------+
           | Consumer A|   | Consumer B|   | Consumer C|
           | (Billing) |   | (Notify)  |   | (Analytics|
           +-----------+   +-----------+   +-----------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Production Pub/Sub Event Pattern
 * Topic partitioning, consumer groups, and idempotency tracking
 */

export interface DomainEvent<T = any> {
  eventId: string;
  eventType: string;
  aggregateId: string;
  data: T;
  publishedAt: string;
}

export type EventHandler<T> = (event: DomainEvent<T>) => Promise<void>;

export class PubSubMessageBroker {
  private topicSubscribers = new Map<string, Array<{ group: string; handler: EventHandler<any> }>>();
  private processedMessageIds = new Set<string>();

  subscribe<T>(topic: string, group: string, handler: EventHandler<T>): void {
    if (!this.topicSubscribers.has(topic)) {
      this.topicSubscribers.set(topic, []);
    }
    this.topicSubscribers.get(topic)!.push({ group, handler });
    console.log(`[Broker] Registered consumer group '${group}' on topic '${topic}'`);
  }

  async publish<T>(topic: string, event: DomainEvent<T>): Promise<void> {
    console.log(`[Broker:Publish] Topic '${topic}', EventId: ${event.eventId}, Type: ${event.eventType}`);
    const subscribers = this.topicSubscribers.get(topic) || [];

    // Each consumer group processes the message once (competing consumers pattern within group)
    const grouped = new Map<string, EventHandler<any>[]>();
    for (const sub of subscribers) {
      if (!grouped.has(sub.group)) grouped.set(sub.group, []);
      grouped.get(sub.group)!.push(sub.handler);
    }

    for (const [groupName, handlers] of grouped.entries()) {
      // Pick one consumer instance per partition/group (Round-robin / hash)
      const selectedHandler = handlers[0];
      const consumerKey = `${groupName}:${event.eventId}`;

      if (this.processedMessageIds.has(consumerKey)) {
        console.warn(`[Broker:Idempotency] Duplicate message ${event.eventId} discarded for group ${groupName}`);
        continue;
      }

      try {
        await selectedHandler(event);
        this.processedMessageIds.add(consumerKey);
      } catch (err: any) {
        console.error(`[Broker:Error] Handler in group ${groupName} failed: ${err.message}`);
        // Route to DLQ in production
      }
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **At-Least-Once Delivery & Duplicates**: Network retries will deliver duplicate events. Consumers MUST be strictly idempotent using unique `eventId` checks or database upsert operations.
2. **Out-of-Order Message Processing**: If message partitions are not keyed by aggregate ID (e.g. orderId), consumer A could process 'OrderDelivered' before consumer B processes 'OrderCreated'. Partition by Aggregate Key!
3. **Poison Pill Messages**: A malformed event causes consumer crashes in an infinite loop. Mitigation: Dead-Letter Queue (DLQ) after 3-5 failed retry attempts.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Event-driven microservices where producers must remain decoupled from downstream side effects and new consumers can be plugged in without touching producers.

### When NOT to Use:
- Synchronous workflows requiring an immediate return value to the user (e.g., verifying credit card CVV and returning immediate validation error).
