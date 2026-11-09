# Command Query Responsibility Segregation (CQRS) Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Segregate read operations (Queries) from write/update operations (Commands) using separate data models and optimized storage engines for each path.

---

## 2. Real-Life Industry Example
Twitter / X (Writes go to MySQL / Redis queues via Command model; Timeline reads hit denormalized in-memory timeline caches via Query model).

---

## 3. Architecture & Flow Diagram
```
+-----------------------+
                       |    Client / User      |
                       +-----------------------+
                        /                     \
        [Write Commands]                       [Read Queries]
              /                                         \
             v                                           v
   +--------------------+                      +--------------------+
   |   Command Model    |                      |    Query Model     |
   | (Domain Validation)|                      |  (Denormalized)    |
   +--------------------+                      +--------------------+
             |                                           ^
             v                                           |
      [ Write Database ] ===== Event / CDC Stream =====> [ Read Database ]
     (Normalized Postgres)                              (Elasticsearch / Redis)
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Eventual Consistency Latency**: A user updates their profile (Write Command), immediately refreshes the page (Read Query), but the projection hasn't received the event yet. Mitigation: Read-your-own-writes session caching or returning optimistic client updates.
2. **Projection Rebuilding**: If the Query schema changes (e.g. adding a new field), all historical events must be replayed from the beginning to repopulate the read model.
3. **Data Divergence**: Bugs in the event projection handler can cause the read model to drift out of sync with the write model. Mitigation: Periodic audit reconcilers.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Read-heavy systems with asymmetric scaling needs (e.g., 10,000 reads for every 1 write, like e-commerce catalogs or news feeds).
- When read queries require complex joins across dozens of tables that kill write database performance.

### When NOT to Use:
- Simple CRUD applications where reading and writing the same relational table is fast, predictable, and requires zero eventual consistency handling.
