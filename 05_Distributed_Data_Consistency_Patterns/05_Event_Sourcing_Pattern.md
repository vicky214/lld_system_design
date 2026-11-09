# Event Sourcing Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Instead of storing current state, persist all state changes as an immutable, append-only sequence of domain events; reconstruct current state at any point by replaying historical events.

---

## 2. Real-Life Industry Example
Banking Ledgers & Git Version Control (A bank account doesn't just store `$500`; it stores `Deposited($1000)`, `Withdrew($200)`, `Withdrew($300)`. Balance is calculated by replaying transactions).

---

## 3. Architecture & Flow Diagram
```
+-------------------------------------------------------------+
        |                 Append-Only Event Store                     |
        |  [Evt 1: AccountOpened] -> [Evt 2: Deposited] -> [Evt 3]    |
        +-------------------------------------------------------------+
                        |                                |
             Replay to reconstruct             Stream to Read Projections
                        v                                v
             Current Aggregate State            Elasticsearch / Views
             (Balance: $500.00)                 (Reporting / Audit)
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Event Sourcing Pattern
 * Immutable event stream with aggregate rehydration and snapshotting
 */

export interface EventRecord {
  streamId: string;
  version: number;
  type: string;
  data: any;
  timestamp: number;
}

export class BankAccountAggregate {
  private id!: string;
  private balanceCents: number = 0;
  private version: number = 0;
  private uncommittedEvents: EventRecord[] = [];

  constructor(public readonly accountId: string) {
    this.id = accountId;
  }

  // Command 1: Open Account
  open(initialDepositCents: number): void {
    if (this.version !== 0) throw new Error('Account already open');
    this.applyChange({
      streamId: this.id,
      version: this.version + 1,
      type: 'AccountOpened',
      data: { initialDepositCents },
      timestamp: Date.now()
    });
  }

  // Command 2: Deposit Funds
  deposit(amountCents: number): void {
    if (amountCents <= 0) throw new Error('Deposit must be positive');
    this.applyChange({
      streamId: this.id,
      version: this.version + 1,
      type: 'FundsDeposited',
      data: { amountCents },
      timestamp: Date.now()
    });
  }

  // Apply event mutations
  private applyChange(evt: EventRecord): void {
    this.mutate(evt);
    this.uncommittedEvents.push(evt);
  }

  private mutate(evt: EventRecord): void {
    this.version = evt.version;
    switch (evt.type) {
      case 'AccountOpened':
        this.balanceCents = evt.data.initialDepositCents;
        break;
      case 'FundsDeposited':
        this.balanceCents += evt.data.amountCents;
        break;
      default:
        break;
    }
  }

  // Rebuild state from historical events
  static loadFromHistory(accountId: string, history: EventRecord[]): BankAccountAggregate {
    const aggregate = new BankAccountAggregate(accountId);
    for (const evt of history) {
      aggregate.mutate(evt);
    }
    return aggregate;
  }

  getBalance(): number {
    return this.balanceCents / 100;
  }

  flushUncommittedEvents(): EventRecord[] {
    const events = [...this.uncommittedEvents];
    this.uncommittedEvents = [];
    return events;
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Long Event Streams & Rehydration Latency**: If an account has 200,000 events, replaying them to calculate current balance causes huge CPU/memory delays. Mitigation: Snapshots (persist state every 1,000 events and replay only subsequent events).
2. **Schema Evolution & Versioning**: If event payload structures change over time, older serialized events in the database cannot be parsed by new code. Mitigation: Event upcasters or strict backward-compatible protobuf/Avro schemas.
3. **Data Privacy (GDPR 'Right to be Forgotten')**: Immutable event stores cannot delete customer personal data easily without breaking hash chains. Mitigation: Cryptographic shredding (encrypt PII with per-user key; deleting the key renders data unreadable).

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Highly regulated audit domains (banking, insurance, medical records, legal compliance) where every single historical change must be verifiably preserved.

### When NOT to Use:
- Standard CRUD websites where historical state is irrelevant and current state updates are completely sufficient.
