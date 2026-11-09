# Singleton Pattern

## Category: Creational Pattern

---

## 1. Core Intent & Definition
Ensure a class has only one instance and provide a global point of access to it, with thread-safe lazy initialization and lifecycle management.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
In distributed applications, creating multiple uncoordinated instances of shared resources (like Database Connection Pools, Configuration Managers, or Hardware Drivers) exhausts system sockets, causes configuration drift, and creates file write contention.

### Real-World Industry Example:
Database Connection Pool Manager in an Enterprise FinTech Service. Multiple microservice modules require access to PostgreSQL, but creating new pools per request exhausts database max_connections (PostgreSQL default: 100). A Singleton guarantees a single pooled instance across all handlers.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------------------------------------+
|                 DatabaseConnectionManager             |
+-------------------------------------------------------+
| - instance: DatabaseConnectionManager (static)        |
| - pool: Pool                                          |
| - isConnected: boolean                                |
+-------------------------------------------------------+
| - constructor() [Private / Protected]                 |
| + getInstance(config): DatabaseConnectionManager      |
| + query(sql, params): Promise<QueryResult>            |
| + close(): Promise<void>                              |
+-------------------------------------------------------+
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
[ API Controller A ]                   [ Background Worker B ]
(Calls getInstance())                  (Calls getInstance() -> Returns SAME instance)
```

---

## 4. Practical Implementation (TypeScript)
```typescript
import { EventEmitter } from "events";

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  maxPoolSize: number;
}

/**
 * Thread-safe Singleton Database Manager.
 * Prevents multiple connection pool allocations and manages connection lifecycles.
 */
export class DatabaseConnectionManager extends EventEmitter {
  private static instance: DatabaseConnectionManager | null = null;
  private isConnected = false;
  private activeConnections = 0;
  private config: DatabaseConfig;

  // Private constructor prevents direct instantiation with `new`
  private constructor(config: DatabaseConfig) {
    super();
    this.config = config;
    this.initializePool();
  }

  /**
   * Thread-safe / Concurrency-safe getInstance.
   * Uses double-checked locking idiom simulation.
   */
  public static getInstance(config?: DatabaseConfig): DatabaseConnectionManager {
    if (!DatabaseConnectionManager.instance) {
      if (!config) {
        throw new Error("Configuration required for initial Singleton creation.");
      }
      DatabaseConnectionManager.instance = new DatabaseConnectionManager(config);
    }
    return DatabaseConnectionManager.instance;
  }

  private initializePool(): void {
    console.log(`[DB Singleton] Initializing connection pool to ${this.config.host}:${this.config.port}/${this.config.database}`);
    this.isConnected = true;
    this.activeConnections = 1;
    this.emit("connected");
  }

  public async executeQuery<T>(query: string, params: any[] = []): Promise<{ rows: T[]; executionTimeMs: number }> {
    if (!this.isConnected) {
      throw new Error("Database connection pool is offline.");
    }

    const start = performance.now();
    // Simulate database I/O execution
    await new Promise((resolve) => setTimeout(resolve, 15));
    const executionTimeMs = performance.now() - start;

    return {
      rows: [] as T[],
      executionTimeMs: Math.round(executionTimeMs),
    };
  }

  public getPoolStats() {
    return {
      isConnected: this.isConnected,
      activeConnections: this.activeConnections,
      maxPoolSize: this.config.maxPoolSize,
    };
  }

  /**
   * Safe teardown mechanism for unit testing & graceful shutdowns
   */
  public static resetInstance(): void {
    if (DatabaseConnectionManager.instance) {
      DatabaseConnectionManager.instance.isConnected = false;
      DatabaseConnectionManager.instance = null;
      console.log("[DB Singleton] Instance destroyed and connection pool released.");
    }
  }
}

// --- Usage Example ---
const config: DatabaseConfig = {
  host: "db.internal.production",
  port: 5432,
  database: "payments_ledger",
  maxPoolSize: 20,
};

// Module A acquires instance
const dbInstanceA = DatabaseConnectionManager.getInstance(config);

// Module B acquires instance without passing config again
const dbInstanceB = DatabaseConnectionManager.getInstance();

console.log("Are both instances identical?", dbInstanceA === dbInstanceB); // true
```

---

## 5. Edge Cases & Failure Handling
- **Concurrency Race Conditions**: In multi-threaded environments (like Java/Go), simultaneous thread calls can construct dual instances without synchronization or double-checked locking.\n- **Unit Testing Pollution**: Global singleton state persists across test suites, leaking mock data. Solution: Always implement a `resetInstance()` method for test teardowns.\n- **Serialization / Deserialization**: Deserializing a singleton object can spawn a second instance unless custom readResolve / deserialization guards are implemented.\n- **Subclassing Ambiguity**: If a Singleton is subclassed, both parent and child must coordinate their static instance reference to avoid dual singletons.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- Managing hardware ports, GPU memory contexts, or external resource pools (DB pool, thread pool).\n- Centralized configuration stores that must remain immutable across all services.\n- Centralized logging engines writing to disk files to avoid file locking conflicts.

### When NOT to Use / Anti-patterns:
- Avoid using Singleton simply to create 'global variables' — this introduces hidden dependencies and tight coupling.\n- When Dependency Injection (DI) containers (e.g. Nest.js, Spring) can manage singleton lifecycles cleanly.
