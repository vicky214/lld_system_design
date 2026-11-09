import os

TARGET_DIR = "/home/vicky/Documents/Antigravity/lld/05_Distributed_Data_Consistency_Patterns"
os.makedirs(TARGET_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Database_per_Service.md",
        "title": "Database per Service Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Ensure each microservice has its own private, isolated database so that services are completely decoupled at the data tier and schema changes can occur without cross-service coordination.",
        "industry_example": "Amazon & Netflix microservices architecture where Order Service uses PostgreSQL, Catalog uses DynamoDB, and Session/Recommendation uses Redis. No service is permitted direct SQL access to another service's tables.",
        "diagram": """
+--------------------+        +--------------------+        +--------------------+
|   Order Service    |        |  Customer Service  |        |  Inventory Service |
+--------------------+        +--------------------+        +--------------------+
          |                             |                             |
          v                             v                             v
+--------------------+        +--------------------+        +--------------------+
|  PostgreSQL (Order)|        |   MongoDB (Users)  |        |  DynamoDB (Stock)  |
+--------------------+        +--------------------+        +--------------------+
   (Private Schema)              (Private Schema)              (Private Schema)
          ^                             ^                             ^
          |                             |                             |
          +---- NEVER ALLOW DIRECT CROSS-DATABASE SQL QUERIES / JOINS +
""",
        "code": """/**
 * Database-per-Service Pattern
 * Strict encapsulation of private data stores with public API/Event contracts
 */

export interface OrderRecord {
  orderId: string;
  customerId: string;
  amount: number;
}

export interface CustomerSummary {
  customerId: string;
  email: string;
  tier: 'FREE' | 'VIP';
}

// 1. Order Service with Private PostgreSQL-like Store
export class OrderService {
  private privateOrderDb = new Map<string, OrderRecord>();

  constructor(private customerServiceClient: ICustomerServiceClient) {}

  async createOrder(orderId: string, customerId: string, amount: number): Promise<void> {
    // Cannot do a SQL JOIN with the User database! Must call Customer Service API
    const customer = await this.customerServiceClient.getCustomerById(customerId);
    if (!customer) {
      throw new Error(`Customer ${customerId} does not exist`);
    }

    // Persist to private Order store
    this.privateOrderDb.set(orderId, { orderId, customerId, amount });
    console.log(`[OrderService] Order ${orderId} saved for ${customer.tier} customer ${customer.email}`);
  }

  async getOrder(orderId: string): Promise<OrderRecord | undefined> {
    return this.privateOrderDb.get(orderId);
  }
}

// 2. Customer Service with Private MongoDB-like Store
export interface ICustomerServiceClient {
  getCustomerById(customerId: string): Promise<CustomerSummary | null>;
}

export class CustomerService implements ICustomerServiceClient {
  private privateCustomerDb = new Map<string, CustomerSummary>([
    ['cust-101', { customerId: 'cust-101', email: 'alice@example.com', tier: 'VIP' }],
    ['cust-102', { customerId: 'cust-102', email: 'bob@example.com', tier: 'FREE' }]
  ]);

  async getCustomerById(customerId: string): Promise<CustomerSummary | null> {
    const cust = this.privateCustomerDb.get(customerId);
    return cust ? { ...cust } : null; // return defensive copy
  }
}
""",
        "edge_cases": """1. **Distributed Queries & Loss of SQL JOINs**: Joining data across orders, customers, and shipments cannot be solved with a simple SQL `INNER JOIN`. Mitigation: Use API Composition or CQRS with materialized views.
2. **Distributed Transaction Integrity**: An atomic operation updating both Order status and Account balance cannot use local ACID transactions. Mitigation: Sagas (Choreography or Orchestration).
3. **Polyglot Database Operational Overhead**: Managing different DB technologies (e.g. Postgres + Mongo + Cassandra) requires specialized DBA skills, backups, and monitoring per technology.""",
        "tradeoffs": """### When to Use:
- True microservices architecture where teams need autonomy to modify database schemas without breaking other services.
- When different services have radically different storage requirements (e.g., Graph DB for social connections, Time-series DB for metrics, Relational DB for ledgers).

### When NOT to Use:
- Small monolithic applications where single database ACID transactions and SQL joins provide massive development speed without microservice networking overhead."""
    },
    {
        "filename": "02_Saga_Orchestration_Pattern.md",
        "title": "Saga Orchestration Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Coordinate distributed multi-service transactions through a centralized orchestrator that executes sequential local transactions and issues compensating undo operations if any step fails.",
        "industry_example": "Uber Trip Booking / Flight Booking Engines (Book Flight -> Reserve Hotel -> Rent Car; if car rental fails, the orchestrator triggers refund flight and cancel hotel reservation).",
        "diagram": """
                 +--------------------------------+
                 |       Saga Orchestrator        |
                 +--------------------------------+
                    |             |            |
         1. Process |  2. Process | 3. Process |
            Payment |     Seat    |    Hotel   |
                    v             v            v
           +-----------+  +-----------+  +-----------+
           | Payment   |  | Seat      |  | Hotel     |
           | Service   |  | Service   |  | Service   |
           +-----------+  +-----------+  +-----------+
                    |             |            |
           (OK)     |   (OK)      |   (FAILS)  |
                    |             |            |
                    +=============+============+
                                  |
                   Trigger Compensating Rollbacks:
                   <- 4. Cancel Seat Reservation
                   <- 5. Refund Captured Payment
""",
        "code": """/**
 * Saga Orchestrator Pattern
 * Deterministic multi-step transaction with automated rollback compensation
 */

export interface SagaStep {
  name: string;
  execute: () => Promise<boolean>;
  compensate: () => Promise<void>;
}

export class OrderBookingSagaOrchestrator {
  private executedSteps: SagaStep[] = [];

  async executeSaga(steps: SagaStep[]): Promise<boolean> {
    console.log('[SagaOrchestrator] Starting distributed Saga execution...');

    for (const step of steps) {
      try {
        console.log(`[SagaOrchestrator] Executing step: ${step.name}`);
        const success = await step.execute();
        
        if (!success) {
          throw new Error(`Step ${step.name} returned failure flag.`);
        }

        this.executedSteps.push(step);
      } catch (err: any) {
        console.error(`[SagaOrchestrator] Step '${step.name}' failed: ${err.message}. Initiating rollback compensation!`);
        await this.rollback();
        return false;
      }
    }

    console.log('[SagaOrchestrator] Saga successfully completed all steps.');
    return true;
  }

  private async rollback(): Promise<void> {
    // Compensate in exact reverse order
    while (this.executedSteps.length > 0) {
      const step = this.executedSteps.pop()!;
      try {
        console.log(`[SagaOrchestrator] Executing compensating rollback: ${step.name}`);
        await step.compensate();
      } catch (compensateError: any) {
        // Critical: Compensations must be idempotent and retryable
        console.error(`[SagaOrchestrator CRITICAL] Failed to compensate ${step.name}: ${compensateError.message}`);
      }
    }
  }
}

// Practical usage example: E-Commerce Checkout Saga
export function buildCheckoutSaga(orderId: string, amount: number) {
  const orchestrator = new OrderBookingSagaOrchestrator();

  const steps: SagaStep[] = [
    {
      name: 'ReserveInventory',
      execute: async () => {
        console.log(` -> Reserving stock items for order ${orderId}`);
        return true;
      },
      compensate: async () => {
        console.log(` <- Restoring reserved stock items for order ${orderId}`);
      }
    },
    {
      name: 'ChargePayment',
      execute: async () => {
        console.log(` -> Processing payment of $${amount} via Stripe`);
        return true;
      },
      compensate: async () => {
        console.log(` <- Issuing refund for order ${orderId}`);
      }
    },
    {
      name: 'DispatchLogistics',
      execute: async () => {
        console.log(` -> Calling FedEx dispatch API`);
        // Simulate logistics failure
        throw new Error('FedEx API 503 Courier Unavailable');
      },
      compensate: async () => {
        console.log(` <- Voiding shipment dispatch`);
      }
    }
  ];

  return { orchestrator, steps };
}
""",
        "edge_cases": """1. **Compensation Failures**: What happens if the refund API call in `compensate()` throws an error? The orchestrator must retry compensations with exponential backoff or emit an alert to a Human Escalation Queue.
2. **Semantic Lock Violations / Dirty Reads**: Because local transactions commit immediately before subsequent steps complete, other transactions can read intermediate states. Mitigation: Use status flags (`PENDING_APPROVAL`) until final confirmation.
3. **Orchestrator Node Crash**: If the orchestrator server dies mid-saga, the transaction is abandoned. Mitigation: Persist state transitions to a durable Saga Log (e.g. Temporal.io or AWS Step Functions).""",
        "tradeoffs": """### When to Use:
- Complex distributed workflows involving 3 or more services where strict step sequencing and error recovery visibility is mandatory.

### When NOT to Use:
- Simple 2-service interactions where Choreography (event-driven) is simpler without needing a dedicated orchestrator service."""
    },
    {
        "filename": "03_Saga_Choreography_Pattern.md",
        "title": "Saga Choreography Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Coordinate distributed transactions across microservices through decentralized event publishing and subscribing where each service reacts to events and emits subsequent events without a central coordinator.",
        "industry_example": "Stripe Payment Lifecycle (PaymentAuthorized event triggers FraudService; FraudCleared event triggers TransferService; TransferFailed event triggers PaymentRefundService).",
        "diagram": """
 [Order Service]       [Payment Service]       [Inventory Service]
       |                      |                         |
       |-- 1. OrderCreated -->|                         |
       |                      |-- 2. PaymentApproved -->|
       |                      |                         | (Stockout!)
       |                      |<-- 3. StockReservationFailed
       |<-- 4. PaymentRefunded-
""",
        "code": """/**
 * Saga Choreography Pattern
 * Decentralized event-driven state transitions with compensating events
 */

export interface Event<T = any> {
  id: string;
  name: string;
  payload: T;
}

export type EventBusListener = (event: Event) => Promise<void>;

export class ChoreographyEventBus {
  private listeners = new Map<string, EventBusListener[]>();

  subscribe(eventName: string, handler: EventBusListener): void {
    if (!this.listeners.has(eventName)) this.listeners.set(eventName, []);
    this.listeners.get(eventName)!.push(handler);
  }

  async emit(event: Event): Promise<void> {
    console.log(`[ChoreographyBus] Event Emitted: ${event.name} (ID: ${event.id})`);
    const handlers = this.listeners.get(event.name) || [];
    for (const handler of handlers) {
      await handler(event);
    }
  }
}

// 1. Order Service Choreographer
export class ChoreographedOrderService {
  constructor(private bus: ChoreographyEventBus) {
    this.bus.subscribe('PaymentFailed', async (evt) => {
      console.log(`[OrderService] Marking order ${evt.payload.orderId} as CANCELLED due to payment failure`);
    });
    this.bus.subscribe('InventoryReserved', async (evt) => {
      console.log(`[OrderService] Marking order ${evt.payload.orderId} as COMPLETED!`);
    });
  }

  async placeOrder(orderId: string, amount: number): Promise<void> {
    console.log(`[OrderService] Initiating order: ${orderId}`);
    await this.bus.emit({
      id: `evt-${Date.now()}`,
      name: 'OrderCreated',
      payload: { orderId, amount }
    });
  }
}

// 2. Payment Service Choreographer
export class ChoreographedPaymentService {
  constructor(private bus: ChoreographyEventBus) {
    this.bus.subscribe('OrderCreated', async (evt) => {
      await this.processPayment(evt.payload.orderId, evt.payload.amount);
    });
  }

  async processPayment(orderId: string, amount: number): Promise<void> {
    if (amount > 1000) {
      // Payment decline simulation
      console.warn(`[PaymentService] Card limit exceeded for order ${orderId}`);
      await this.bus.emit({
        id: `evt-pay-fail-${Date.now()}`,
        name: 'PaymentFailed',
        payload: { orderId, reason: 'INSUFFICIENT_FUNDS' }
      });
      return;
    }

    console.log(`[PaymentService] Payment approved for order ${orderId}`);
    await this.bus.emit({
      id: `evt-pay-ok-${Date.now()}`,
      name: 'PaymentApproved',
      payload: { orderId, amount }
    });
  }
}
""",
        "edge_cases": """1. **Cyclic Event Loops**: If Service A listens to Event B, and emits Event C, which triggers Service B to emit Event B, an infinite storm occurs. Strict event hierarchy contracts and correlation IDs must be documented.
2. **Observability Complexity**: Tracking the end-to-end status of an order requires correlating distributed log messages across 5+ services without a single orchestrator state table. Distributed tracing (OpenTelemetry) is essential.
3. **Out-of-Order Events**: A network delay may cause `PaymentFailed` to arrive before `OrderCreated` is acknowledged.""",
        "tradeoffs": """### When to Use:
- Simple, loosely coupled workflows with 2-4 services where autonomous peer-to-peer reactions are natural and no central coordinator bottle-neck is desired.

### When NOT to Use:
- Complex business processes with 10+ steps or branching conditional logic where understanding workflow state requires reverse engineering multiple independent codebase listeners."""
    },
    {
        "filename": "04_CQRS_Pattern.md",
        "title": "Command Query Responsibility Segregation (CQRS) Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Segregate read operations (Queries) from write/update operations (Commands) using separate data models and optimized storage engines for each path.",
        "industry_example": "Twitter / X (Writes go to MySQL / Redis queues via Command model; Timeline reads hit denormalized in-memory timeline caches via Query model).",
        "diagram": """
                       +-----------------------+
                       |    Client / User      |
                       +-----------------------+
                        /                     \\
        [Write Commands]                       [Read Queries]
              /                                         \\
             v                                           v
   +--------------------+                      +--------------------+
   |   Command Model    |                      |    Query Model     |
   | (Domain Validation)|                      |  (Denormalized)    |
   +--------------------+                      +--------------------+
             |                                           ^
             v                                           |
      [ Write Database ] ===== Event / CDC Stream =====> [ Read Database ]
     (Normalized Postgres)                              (Elasticsearch / Redis)
""",
        "code": """/**
 * CQRS Pattern
 * Separation of Write Command Aggregate from Denormalized Read Projections
 */

// 1. COMMAND SIDE: Write model enforcing business rules
export interface RegisterProductCommand {
  productId: string;
  name: string;
  price: number;
}

export class ProductCommandService {
  constructor(private writeDb: Map<string, any>, private eventPublisher: (topic: string, event: any) => Promise<void>) {}

  async handleRegisterProduct(cmd: RegisterProductCommand): Promise<void> {
    if (cmd.price <= 0) {
      throw new Error('Product price must be greater than zero');
    }

    const entity = {
      id: cmd.productId,
      name: cmd.name,
      price: cmd.price,
      version: 1,
      createdAt: new Date().toISOString()
    };

    // Save to normalized transactional Write DB
    this.writeDb.set(cmd.productId, entity);
    console.log(`[CommandService] Saved entity ${cmd.productId} to Write DB`);

    // Emit event to update Query Read Model
    await this.eventPublisher('product.created', entity);
  }
}

// 2. QUERY SIDE: Read model denormalized for lightning-fast search
export interface ProductReadView {
  id: string;
  displayName: string;
  formattedPrice: string;
}

export class ProductQueryService {
  private readStore = new Map<string, ProductReadView>();

  // Projection updater (Subscriber to Command events)
  async onProductCreated(eventData: any): Promise<void> {
    const projection: ProductReadView = {
      id: eventData.id,
      displayName: eventData.name.toUpperCase(),
      formattedPrice: `$${(eventData.price).toFixed(2)}`
    };
    this.readStore.set(eventData.id, projection);
    console.log(`[QueryService] Denormalized read projection created for ${eventData.id}`);
  }

  async getProductView(productId: string): Promise<ProductReadView | null> {
    return this.readStore.get(productId) || null;
  }
}
""",
        "edge_cases": """1. **Eventual Consistency Latency**: A user updates their profile (Write Command), immediately refreshes the page (Read Query), but the projection hasn't received the event yet. Mitigation: Read-your-own-writes session caching or returning optimistic client updates.
2. **Projection Rebuilding**: If the Query schema changes (e.g. adding a new field), all historical events must be replayed from the beginning to repopulate the read model.
3. **Data Divergence**: Bugs in the event projection handler can cause the read model to drift out of sync with the write model. Mitigation: Periodic audit reconcilers.""",
        "tradeoffs": """### When to Use:
- Read-heavy systems with asymmetric scaling needs (e.g., 10,000 reads for every 1 write, like e-commerce catalogs or news feeds).
- When read queries require complex joins across dozens of tables that kill write database performance.

### When NOT to Use:
- Simple CRUD applications where reading and writing the same relational table is fast, predictable, and requires zero eventual consistency handling."""
    },
    {
        "filename": "05_Event_Sourcing_Pattern.md",
        "title": "Event Sourcing Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Instead of storing current state, persist all state changes as an immutable, append-only sequence of domain events; reconstruct current state at any point by replaying historical events.",
        "industry_example": "Banking Ledgers & Git Version Control (A bank account doesn't just store `$500`; it stores `Deposited($1000)`, `Withdrew($200)`, `Withdrew($300)`. Balance is calculated by replaying transactions).",
        "diagram": """
        +-------------------------------------------------------------+
        |                 Append-Only Event Store                     |
        |  [Evt 1: AccountOpened] -> [Evt 2: Deposited] -> [Evt 3]    |
        +-------------------------------------------------------------+
                        |                                |
             Replay to reconstruct             Stream to Read Projections
                        v                                v
             Current Aggregate State            Elasticsearch / Views
             (Balance: $500.00)                 (Reporting / Audit)
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Long Event Streams & Rehydration Latency**: If an account has 200,000 events, replaying them to calculate current balance causes huge CPU/memory delays. Mitigation: Snapshots (persist state every 1,000 events and replay only subsequent events).
2. **Schema Evolution & Versioning**: If event payload structures change over time, older serialized events in the database cannot be parsed by new code. Mitigation: Event upcasters or strict backward-compatible protobuf/Avro schemas.
3. **Data Privacy (GDPR 'Right to be Forgotten')**: Immutable event stores cannot delete customer personal data easily without breaking hash chains. Mitigation: Cryptographic shredding (encrypt PII with per-user key; deleting the key renders data unreadable).""",
        "tradeoffs": """### When to Use:
- Highly regulated audit domains (banking, insurance, medical records, legal compliance) where every single historical change must be verifiably preserved.

### When NOT to Use:
- Standard CRUD websites where historical state is irrelevant and current state updates are completely sufficient."""
    },
    {
        "filename": "06_Transactional_Outbox_Pattern.md",
        "title": "Transactional Outbox Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Atomically commit business data and outgoing domain events within the same local database transaction into an 'outbox' table, guaranteeing zero event loss even if the message broker is temporarily offline.",
        "industry_example": "PayPal & Stripe payment webhook delivery engines (Writing payment record and webhook event to PostgreSQL in one local ACID commit, then an async worker relays events to Kafka/RabbitMQ).",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **At-Least-Once Delivery to Broker**: If the worker publishes to Kafka and crashes before marking the outbox row as `SENT`, the next iteration will republish the same message. Downstream consumers MUST be idempotent.
2. **Outbox Polling Table Bloat**: Frequent table polling (`SELECT * FROM outbox WHERE status='PENDING'`) adds database read load. Mitigation: Use indexed status columns, batch queries with `SKIP LOCKED`, or switch to Transaction Log Tailing (CDC).
3. **Outbox Growth & Retention**: Sent messages will accumulate indefinitely. Set up a daily cron purge job for records where `status = 'SENT' AND createdAt < NOW() - INTERVAL '7 days'`.""",
        "tradeoffs": """### When to Use:
- Essential in distributed systems whenever a database mutation must reliably trigger an external message (Kafka, RabbitMQ, SQS) with zero message loss guarantee.

### When NOT to Use:
- When using native Change Data Capture (Debezium) or in systems where missing occasional events is tolerable (e.g. non-critical user telemetry analytics)."""
    },
    {
        "filename": "07_Transactional_Log_Tailing_CDC.md",
        "title": "Transactional Log Tailing (Change Data Capture) Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Read the database's native transaction log (Postgres WAL, MySQL binlog, MongoDB Oplog) at the storage engine level to publish changes to an event stream without modifying application code or running polling SQL queries.",
        "industry_example": "Debezium and Kafka Connect deployed at Uber and Yelp to stream real-time database modifications directly into Kafka for downstream cache invalidation and search index updates.",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Log Compaction / Retention Expiration**: If the CDC consumer is offline for days, the database may purge old WAL logs before they are read, breaking replication. Mitigation: Monitor replication slot lag and WAL disk quotas closely.
2. **DDL Schema Alterations**: If a column is dropped or renamed in PostgreSQL, downstream consumers parsing CDC JSON events may crash. Mitigation: Use schema registries (Confluent Schema Registry / Avro) with backward compatibility checks.
3. **Internal Schema Exposure**: CDC exposes raw internal database table structures directly to external consumers, which can violate bounded context encapsulation.""",
        "tradeoffs": """### When to Use:
- High-throughput database replication, real-time cache invalidation, and syncing database changes to Elasticsearch without adding any application-level polling code.

### When NOT to Use:
- When application-level business events (e.g. `UserPromotedToAdminEvent`) are needed rather than raw database column mutations (`UPDATE users SET role_id = 2`)."""
    },
    {
        "filename": "08_Materialized_View_Pattern.md",
        "title": "Materialized View Pattern",
        "category": "Distributed Data Consistency Patterns",
        "intent": "Precompute, denormalize, and store complex query results across multiple tables or services in advance to provide ultra-fast, single-lookup read query responses.",
        "industry_example": "LinkedIn Profile View & Amazon Order History (Pre-calculating a user's total spend, recent order cards, and delivery tracking status into a single pre-rendered JSON document in DynamoDB or Redis).",
        "diagram": """
Distributed Event Stream (Orders, Shipments, Reviews)
                     |
                     v
   +------------------------------------+
   |   Materialized View Builder Engine |
   +------------------------------------+
                     |
         Continuous Upsert / Projection
                     v
   +------------------------------------+
   |  Materialized View Store (Redis)   |
   |  Key: user:101:dashboard_summary   |
   +------------------------------------+
                     ^
       Instant O(1) single fetch
                     |
               Client Browser
""",
        "code": """/**
 * Materialized View Pattern
 * Continuous event-driven projection updates for sub-millisecond query execution
 */

export interface UserDashboardView {
  userId: string;
  lifetimeSpendCents: number;
  totalOrdersCount: number;
  lastOrderDate: string;
  recentOrders: Array<{ orderId: string; amount: number; status: string }>;
  lastUpdated: string;
}

export class MaterializedViewStore {
  private viewCache = new Map<string, UserDashboardView>();

  getView(userId: string): UserDashboardView | null {
    return this.viewCache.get(userId) || null;
  }

  upsertView(userId: string, updater: (existing: UserDashboardView) => UserDashboardView): void {
    const defaultView: UserDashboardView = {
      userId,
      lifetimeSpendCents: 0,
      totalOrdersCount: 0,
      lastOrderDate: 'N/A',
      recentOrders: [],
      lastUpdated: new Date().toISOString()
    };

    const current = this.viewCache.get(userId) || defaultView;
    const updated = updater(current);
    this.viewCache.set(userId, updated);
  }
}

export class DashboardProjectionEngine {
  constructor(private viewStore: MaterializedViewStore) {}

  // Event handler for new orders
  async onOrderCompleted(event: { userId: string; orderId: string; amountCents: number; timestamp: string }): Promise<void> {
    console.log(`[ProjectionEngine] Updating materialized dashboard view for user: ${event.userId}`);

    this.viewStore.upsertView(event.userId, (view) => {
      view.lifetimeSpendCents += event.amountCents;
      view.totalOrdersCount += 1;
      view.lastOrderDate = event.timestamp;
      view.recentOrders.unshift({
        orderId: event.orderId,
        amount: event.amountCents / 100,
        status: 'COMPLETED'
      });
      // Keep only top 5 recent orders in precomputed view
      if (view.recentOrders.length > 5) view.recentOrders.pop();
      view.lastUpdated = new Date().toISOString();
      return view;
    });
  }
}
""",
        "edge_cases": """1. **Stale View Inconsistency**: If event delivery is delayed, the materialized view may show older summary data than the real-time order status. Display an 'Updated X seconds ago' indicator or provide a manual refresh fallback.
2. **Projection Store Desynchronization**: If the projection engine crashes or skips an event, the summary numbers (e.g. lifetime spend) become permanently inaccurate. Mitigation: Nightly reconciliation batch job to verify and recalculate views.
3. **Memory/Storage Cost**: Materialized views duplicate data. If views are rarely read, storage costs outstrip query performance savings.""",
        "tradeoffs": """### When to Use:
- Heavy read queries requiring aggregations (`SUM`, `COUNT`, `AVG`) across millions of rows that would otherwise freeze transactional databases.

### When NOT to Use:
- Rapidly mutating real-time counters that require strict immediate ACID consistency on read (e.g. live stock exchange order book prices)."""
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
    print("[Distributed Data] Successfully generated all 8 patterns.")
