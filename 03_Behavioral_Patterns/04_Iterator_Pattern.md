# Iterator Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Provide a way to access the elements of an aggregate object sequentially without exposing its underlying representation.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Collections store data in diverse internal structures (binary trees, hash tables, circular buffers, paginated remote REST APIs). Forcing clients to know whether a collection is an Array or a B-Tree breaks encapsulation and makes refactoring internal storage impossible.

### Real-World Industry Example:
Asynchronous Paginated API Response Streamer. An API client streams millions of records from a remote paginated endpoint (e.g. Stripe Transactions API), automatically fetching the next page behind the scenes as the caller iterates.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------------------+
|             Iterator              |
+-----------------------------------+
| + hasNext(): Promise<boolean>     |
| + next(): Promise<T>              |
+-----------------------------------+
                  ▲
                  │
+-----------------------------------+
|    PaginatedApiStreamIterator     |
+-----------------------------------+
| - currentPage: T[]                |
| - cursor: string                  |
+-----------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface Transaction {
  id: string;
  amount: number;
}

export interface AsyncIteratorEngine<T> {
  hasNext(): Promise<boolean>;
  next(): Promise<T>;
}

export class PaginatedTransactionIterator implements AsyncIteratorEngine<Transaction> {
  private buffer: Transaction[] = [];
  private nextCursor: string | null = "start";
  private isExhausted = false;

  private async fetchNextPage(): Promise<void> {
    if (!this.nextCursor) {
      this.isExhausted = true;
      return;
    }

    console.log(`[API Iterator] Fetching next batch using cursor: ${this.nextCursor}...`);
    // Simulated remote API pagination response
    await new Promise((r) => setTimeout(r, 40));

    const pageCount = this.nextCursor === "page_3" ? 0 : 3;
    const newItems: Transaction[] = [];
    for (let i = 1; i <= pageCount; i++) {
      newItems.push({ id: `txn_${this.nextCursor}_${i}`, amount: i * 50 });
    }

    this.buffer.push(...newItems);
    this.nextCursor = this.nextCursor === "start" ? "page_2" : this.nextCursor === "page_2" ? "page_3" : null;

    if (this.buffer.length === 0 && !this.nextCursor) {
      this.isExhausted = true;
    }
  }

  async hasNext(): Promise<boolean> {
    if (this.buffer.length > 0) return true;
    if (this.isExhausted) return false;

    await this.fetchNextPage();
    return this.buffer.length > 0;
  }

  async next(): Promise<Transaction> {
    if (!(await this.hasNext())) {
      throw new Error("No more transactions available in iterator.");
    }
    return this.buffer.shift()!;
  }
}

// --- Usage ---
async function processAllTransactions() {
  const iterator = new PaginatedTransactionIterator();

  while (await iterator.hasNext()) {
    const txn = await iterator.next();
    console.log(`  Processed: ${txn.id} ($${txn.amount})`);
  }
  console.log("✓ All paginated remote records consumed seamlessly.");
}

processAllTransactions();
```

---

## 5. Edge Cases & Failure Handling
- **Concurrent Modification**: If the underlying collection is modified (items added or deleted) while iterating, the iterator may skip elements or throw ConcurrentModificationException.\n- **Network Failure During Pagination**: The iterator must support retry logic when mid-stream HTTP page fetches fail.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- To access a collection's contents without exposing its internal representation.\n- To support multiple simultaneous traversals of a collection.\n- To provide a uniform interface for traversing different structures.

### When NOT to Use / Anti-patterns:
- For simple in-memory arrays where native `for...of` loops are already optimal.
