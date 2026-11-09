# Dead-Letter Queue (DLQ) Pattern

## 1. Classification & Intent
- **Pattern Category:** Resilience & Fault Tolerance Patterns
- **Core Intent:** Route unprocessable, poison-pill messages that repeatedly fail consumer processing into a dedicated quarantine queue for offline inspection, diagnostics, and replay without blocking main message processing.

---

## 2. Real-Life Industry Example
AWS SQS DLQ, Apache Kafka dead-letter topics at Uber and Shopify (isolating corrupted JSON payloads or deleted account references so normal transactions continue uninterrupted).

---

## 3. Architecture & Flow Diagram
```
+----------------------+
   |  Main Message Queue  |
   +----------------------+
              |
      Consume message
              v
   +----------------------+
   |   Consumer Worker    | ==(3 Failures)==> [ Move to DLQ ]
   +----------------------+                          |
              |                                      v
     (Successful msgs)                     +--------------------+
              v                            | Dead-Letter Queue  |
       Database Commit                     +--------------------+
                                                     |
                                            Admin Triage / Replay
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Dead-Letter Queue Pattern
 * Poison-pill isolation with error metadata envelope and redrive management
 */

export interface PoisonEnvelope<T = any> {
  originalMessageId: string;
  originalTopic: string;
  payload: T;
  retryCount: number;
  failureReason: string;
  failedAt: string;
}

export class DeadLetterQueueManager<T> {
  private dlqStorage: PoisonEnvelope<T>[] = [];

  constructor(private maxRetries: number = 3) {}

  async processWithDlq(
    topic: string,
    messageId: string,
    payload: T,
    processor: (payload: T) => Promise<void>
  ): Promise<boolean> {
    let retries = 0;
    let lastError: any;

    while (retries < this.maxRetries) {
      try {
        await processor(payload);
        return true; // Success
      } catch (err: any) {
        retries++;
        lastError = err;
        console.warn(`[QueueWorker] Message ${messageId} processing attempt ${retries}/${this.maxRetries} failed: ${err.message}`);
      }
    }

    // Max retries exceeded -> Route to Dead-Letter Queue
    console.error(`[DLQ] Quarantining poison message ${messageId} to Dead-Letter Queue.`);
    this.dlqStorage.push({
      originalMessageId: messageId,
      originalTopic: topic,
      payload,
      retryCount: retries,
      failureReason: lastError?.message || 'Unknown error',
      failedAt: new Date().toISOString()
    });

    return false;
  }

  getDlqMessages(): PoisonEnvelope<T>[] {
    return [...this.dlqStorage];
  }

  // Administrative Redrive / Replay back to primary queue
  async redrive(messageId: string, reprocessFn: (payload: T) => Promise<void>): Promise<boolean> {
    const idx = this.dlqStorage.findIndex(m => m.originalMessageId === messageId);
    if (idx === -1) return false;

    const envelope = this.dlqStorage[idx];
    console.log(`[DLQ Redrive] Attempting administrative replay for message ${messageId}...`);

    try {
      await reprocessFn(envelope.payload);
      this.dlqStorage.splice(idx, 1); // Removed from DLQ upon successful fix
      console.log(`[DLQ Redrive] Message ${messageId} replayed and removed from DLQ.`);
      return true;
    } catch (err: any) {
      console.error(`[DLQ Redrive] Replay failed: ${err.message}`);
      return false;
    }
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **DLQ Silent Accumulation**: If a software bug causes 100% of messages to route to the DLQ, and no alerts are configured, thousands of orders silently fail unnoticed. Set up CloudWatch / Datadog alerts on `DLQ.Depth > 0`.
2. **Redrive Storms**: Replaying 50,000 backlogged DLQ messages simultaneously after deploying a bugfix can overwhelm downstream databases. Use throttled batch redrive.
3. **Message Expiry in DLQ**: Cloud SQS DLQs have default message retention limits (e.g. 14 days). If unaddressed within 14 days, poison messages are deleted permanently.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- All mission-critical asynchronous message queues to prevent single corrupted messages from halting an entire consumer group partition.

### When NOT to Use:
- Synchronous HTTP request-response APIs (use standard HTTP 4xx/5xx responses and client logs instead).
