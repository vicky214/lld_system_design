# Materialized View Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Precompute, denormalize, and store complex query results across multiple tables or services in advance to provide ultra-fast, single-lookup read query responses.

---

## 2. Real-Life Industry Example
LinkedIn Profile View & Amazon Order History (Pre-calculating a user's total spend, recent order cards, and delivery tracking status into a single pre-rendered JSON document in DynamoDB or Redis).

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Stale View Inconsistency**: If event delivery is delayed, the materialized view may show older summary data than the real-time order status. Display an 'Updated X seconds ago' indicator or provide a manual refresh fallback.
2. **Projection Store Desynchronization**: If the projection engine crashes or skips an event, the summary numbers (e.g. lifetime spend) become permanently inaccurate. Mitigation: Nightly reconciliation batch job to verify and recalculate views.
3. **Memory/Storage Cost**: Materialized views duplicate data. If views are rarely read, storage costs outstrip query performance savings.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Heavy read queries requiring aggregations (`SUM`, `COUNT`, `AVG`) across millions of rows that would otherwise freeze transactional databases.

### When NOT to Use:
- Rapidly mutating real-time counters that require strict immediate ACID consistency on read (e.g. live stock exchange order book prices).
