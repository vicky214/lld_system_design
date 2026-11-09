# Transactional Log Tailing (Change Data Capture) Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Read the database's native transaction log (Postgres WAL, MySQL binlog, MongoDB Oplog) at the storage engine level to publish changes to an event stream without modifying application code or running polling SQL queries.

---

## 2. Real-Life Industry Example
Debezium and Kafka Connect deployed at Uber and Yelp to stream real-time database modifications directly into Kafka for downstream cache invalidation and search index updates.

---

## 3. Architecture & Flow Diagram
```
Application -> writes to DB
                    |
                    v
    +--------------------------------+
    | PostgreSQL Database            |
    | [ Write-Ahead Log (WAL) ]      |
    +--------------------------------+
                    |
     Tails raw log byte stream
                    v
    +--------------------------------+
    | CDC Engine (e.g. Debezium)     |
    +--------------------------------+
                    |
     Publishes formatted event JSON
                    v
    +--------------------------------+
    | Apache Kafka Topic             |
    +--------------------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Transactional Log Tailing (CDC) Simulation
 * Reading low-level write-ahead log entries and streaming to message broker
 */

export interface WalLogEntry {
  lsn: number; // Log Sequence Number
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
  table: string;
  before?: Record<string, any>;
  after?: Record<string, any>;
  commitTimestamp: number;
}

export class WalStreamSimulator {
  private subscribers: Array<(entry: WalLogEntry) => Promise<void>> = [];

  onLogEntry(handler: (entry: WalLogEntry) => Promise<void>): void {
    this.subscribers.push(handler);
  }

  // Emulate Postgres writing to Write-Ahead Log (WAL)
  async emitWalChange(entry: WalLogEntry): Promise<void> {
    console.log(`[WAL] New commit at LSN #${entry.lsn}: ${entry.operation} on table '${entry.table}'`);
    for (const sub of this.subscribers) {
      await sub(entry);
    }
  }
}

export class DebeziumCdcConnector {
  private lastProcessedLsn = 0;

  constructor(private walStream: WalStreamSimulator, private kafkaSink: (topic: string, event: any) => Promise<void>) {
    this.walStream.onLogEntry(async (entry) => {
      await this.processEntry(entry);
    });
  }

  private async processEntry(entry: WalLogEntry): Promise<void> {
    if (entry.lsn <= this.lastProcessedLsn) return; // Prevent duplicate ingestion

    const topic = `cdc.${entry.table}`;
    const cdcEnvelope = {
      source: 'postgres-production',
      lsn: entry.lsn,
      operation: entry.operation,
      timestamp: entry.commitTimestamp,
      data: entry.after || entry.before
    };

    console.log(`[CDC Connector] Emitting change event to Kafka topic '${topic}'`);
    await this.kafkaSink(topic, cdcEnvelope);
    this.lastProcessedLsn = entry.lsn;
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Log Compaction / Retention Expiration**: If the CDC consumer is offline for days, the database may purge old WAL logs before they are read, breaking replication. Mitigation: Monitor replication slot lag and WAL disk quotas closely.
2. **DDL Schema Alterations**: If a column is dropped or renamed in PostgreSQL, downstream consumers parsing CDC JSON events may crash. Mitigation: Use schema registries (Confluent Schema Registry / Avro) with backward compatibility checks.
3. **Internal Schema Exposure**: CDC exposes raw internal database table structures directly to external consumers, which can violate bounded context encapsulation.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- High-throughput database replication, real-time cache invalidation, and syncing database changes to Elasticsearch without adding any application-level polling code.

### When NOT to Use:
- When application-level business events (e.g. `UserPromotedToAdminEvent`) are needed rather than raw database column mutations (`UPDATE users SET role_id = 2`).
