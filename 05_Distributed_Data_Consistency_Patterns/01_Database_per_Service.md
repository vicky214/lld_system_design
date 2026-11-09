# Database per Service Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Ensure each microservice has its own private, isolated database so that services are completely decoupled at the data tier and schema changes can occur without cross-service coordination.

---

## 2. Real-Life Industry Example
Amazon & Netflix microservices architecture where Order Service uses PostgreSQL, Catalog uses DynamoDB, and Session/Recommendation uses Redis. No service is permitted direct SQL access to another service's tables.

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Distributed Queries & Loss of SQL JOINs**: Joining data across orders, customers, and shipments cannot be solved with a simple SQL `INNER JOIN`. Mitigation: Use API Composition or CQRS with materialized views.
2. **Distributed Transaction Integrity**: An atomic operation updating both Order status and Account balance cannot use local ACID transactions. Mitigation: Sagas (Choreography or Orchestration).
3. **Polyglot Database Operational Overhead**: Managing different DB technologies (e.g. Postgres + Mongo + Cassandra) requires specialized DBA skills, backups, and monitoring per technology.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- True microservices architecture where teams need autonomy to modify database schemas without breaking other services.
- When different services have radically different storage requirements (e.g., Graph DB for social connections, Time-series DB for metrics, Relational DB for ledgers).

### When NOT to Use:
- Small monolithic applications where single database ACID transactions and SQL joins provide massive development speed without microservice networking overhead.
