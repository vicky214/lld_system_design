import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../01_Creational_Patterns"))
os.makedirs(BASE_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Singleton_Pattern.md",
        "title": "Singleton Pattern",
        "category": "Creational Pattern",
        "intent": "Ensure a class has only one instance and provide a global point of access to it, with thread-safe lazy initialization and lifecycle management.",
        "problem": "In distributed applications, creating multiple uncoordinated instances of shared resources (like Database Connection Pools, Configuration Managers, or Hardware Drivers) exhausts system sockets, causes configuration drift, and creates file write contention.",
        "scenario": "Database Connection Pool Manager in an Enterprise FinTech Service. Multiple microservice modules require access to PostgreSQL, but creating new pools per request exhausts database max_connections (PostgreSQL default: 100). A Singleton guarantees a single pooled instance across all handlers.",
        "diagram": """
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
""",
        "code": """import { EventEmitter } from "events";

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
""",
        "edgeCases": [
            "**Concurrency Race Conditions**: In multi-threaded environments (like Java/Go), simultaneous thread calls can construct dual instances without synchronization or double-checked locking.",
            "**Unit Testing Pollution**: Global singleton state persists across test suites, leaking mock data. Solution: Always implement a `resetInstance()` method for test teardowns.",
            "**Serialization / Deserialization**: Deserializing a singleton object can spawn a second instance unless custom readResolve / deserialization guards are implemented.",
            "**Subclassing Ambiguity**: If a Singleton is subclassed, both parent and child must coordinate their static instance reference to avoid dual singletons."
        ],
        "tradeoffs": {
            "whenToUse": [
                "Managing hardware ports, GPU memory contexts, or external resource pools (DB pool, thread pool).",
                "Centralized configuration stores that must remain immutable across all services.",
                "Centralized logging engines writing to disk files to avoid file locking conflicts."
            ],
            "whenNotToUse": [
                "Avoid using Singleton simply to create 'global variables' — this introduces hidden dependencies and tight coupling.",
                "When Dependency Injection (DI) containers (e.g. Nest.js, Spring) can manage singleton lifecycles cleanly."
            ]
        }
    },
    {
        "filename": "02_Factory_Method_Pattern.md",
        "title": "Factory Method Pattern",
        "category": "Creational Pattern",
        "intent": "Define an interface for creating an object, but let subclasses or specialized creator classes decide which class to instantiate.",
        "problem": "Hardcoding concrete class instantiations (`new TwilioSmsService()`, `new SendGridEmailService()`) directly inside business controllers tightly couples the core system to third-party vendor APIs, making vendor migration or dynamic multi-channel routing difficult and error-prone.",
        "scenario": "Omnichannel Notification Dispatcher. An enterprise platform sends transactional alerts via SMS, Email, Push Notification, or WhatsApp based on user preferences and regional regulatory compliance.",
        "diagram": """
                    +-----------------------+
                    |      Notification     | <--- (Product Interface)
                    +-----------------------+
                    | + send(to, msg): void |
                    +-----------------------+
                               ▲
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
+---------------+      +----------------+     +----------------+
|  EmailChannel |      |   SmsChannel   |     | PushChannel    |
+---------------+      +----------------+     +----------------+
| + send()      |      | + send()       |     | + send()       |
+---------------+      +----------------+     +----------------+
        ▲                      ▲                      ▲
        │                      │                      │
+--------------------------------------------------------------+
|                    NotificationFactory                       |
+--------------------------------------------------------------+
| + createChannel(type: ChannelType): Notification             |
+--------------------------------------------------------------+
""",
        "code": """export type ChannelType = "EMAIL" | "SMS" | "PUSH" | "WHATSAPP";

export interface NotificationPayload {
  recipient: string;
  message: string;
  metadata?: Record<string, any>;
}

// 1. Product Interface
export interface NotificationChannel {
  send(payload: NotificationPayload): Promise<{ success: boolean; messageId: string }>;
}

// 2. Concrete Products
export class EmailNotificationChannel implements NotificationChannel {
  async send(payload: NotificationPayload) {
    console.log(`[Email Channel] Dispatching SMTP message to ${payload.recipient}: "${payload.message}"`);
    return { success: true, messageId: `email-${Date.now()}` };
  }
}

export class SmsNotificationChannel implements NotificationChannel {
  async send(payload: NotificationPayload) {
    console.log(`[SMS Channel] Transmitting carrier SMS to ${payload.recipient}: "${payload.message}"`);
    return { success: true, messageId: `sms-${Date.now()}` };
  }
}

export class PushNotificationChannel implements NotificationChannel {
  async send(payload: NotificationPayload) {
    console.log(`[Push Channel] Emitting APNS/FCM device token push to ${payload.recipient}`);
    return { success: true, messageId: `push-${Date.now()}` };
  }
}

// 3. Creator / Factory
export class NotificationFactory {
  private static registry = new Map<ChannelType, () => NotificationChannel>([
    ["EMAIL", () => new EmailNotificationChannel()],
    ["SMS", () => new SmsNotificationChannel()],
    ["PUSH", () => new PushNotificationChannel()],
  ]);

  /**
   * Open/Closed Principle: Dynamically register new channels without editing factory core
   */
  public static registerChannel(type: ChannelType, creator: () => NotificationChannel): void {
    NotificationFactory.registry.set(type, creator);
  }

  public static create(type: ChannelType): NotificationChannel {
    const creator = NotificationFactory.registry.get(type);
    if (!creator) {
      throw new Error(`Unsupported notification channel: ${type}. Register channel provider first.`);
    }
    return creator();
  }
}

// --- Usage ---
const channel = NotificationFactory.create("SMS");
channel.send({ recipient: "+15551234567", message: "Your OTP code is 482910" });
""",
        "edgeCases": [
            "**Unsupported Type Runtime Failure**: Passing an unrecognized enum string causes runtime exceptions. Always maintain a dynamic registry with fallback providers.",
            "**Configuration Injection**: Concrete products often need distinct API keys (SendGrid key vs Twilio key). Use factory constructors or parameter factories to inject environment configs.",
            "**Object Lifetime**: Determine if the factory should return fresh instances each time or cache reusable instances (Flyweight / Object Pool)."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When the exact types and dependencies of objects cannot be known beforehand at compile time.",
                "When you want to extend your library or framework by allowing users to plug in custom classes.",
                "When consolidating scattered `new` operations into a centralized, auditable location."
            ],
            "whenNotToUse": [
                "For simple, static class hierarchies where objects never vary at runtime (avoid unnecessary factory overhead)."
            ]
        }
    },
    {
        "filename": "03_Abstract_Factory_Pattern.md",
        "title": "Abstract Factory Pattern",
        "category": "Creational Pattern",
        "intent": "Provide an interface for creating families of related or dependent objects without specifying their concrete classes.",
        "problem": "When an application must run across distinct environments (e.g. AWS vs Azure vs Local Cloud Emulator, or Dark Theme vs Light Theme), instantiating mismatched components (e.g. pairing an AWS S3 Bucket with an Azure Queue Client) leads to runtime system failures.",
        "scenario": "Multi-Cloud Infrastructure Abstraction Layer. An enterprise disaster-recovery service can switch its entire persistence and queue family between AWS (S3 + SQS + DynamoDB) and Azure (Blob + Service Bus + CosmosDB) via an environmental flag.",
        "diagram": """
                          +------------------------+
                          |   CloudServiceFactory  | (Abstract Factory)
                          +------------------------+
                          | + createStorage()      |
                          | + createQueue()        |
                          +------------------------+
                                      ▲
                ┌─────────────────────┴─────────────────────┐
                │                                           │
+-------------------------------+           +-------------------------------+
|        AwsServiceFactory      |           |       AzureServiceFactory     |
+-------------------------------+           +-------------------------------+
| + createStorage() -> S3       |           | + createStorage() -> Blob     |
| + createQueue()   -> SQS      |           | + createQueue()   -> Bus      |
+-------------------------------+           +-------------------------------+
""",
        "code": """// --- Abstract Products ---
export interface StorageService {
  uploadFile(path: string, content: Buffer): Promise<string>;
}

export interface QueueService {
  publishMessage(topic: string, message: any): Promise<void>;
}

// --- Concrete Products (AWS Family) ---
export class AwsS3Storage implements StorageService {
  async uploadFile(path: string, content: Buffer): Promise<string> {
    console.log(`[AWS S3] Uploaded ${content.length} bytes to s3://prod-bucket/${path}`);
    return `https://prod-bucket.s3.amazonaws.com/${path}`;
  }
}

export class AwsSqsQueue implements QueueService {
  async publishMessage(topic: string, message: any): Promise<void> {
    console.log(`[AWS SQS] Enqueued message to https://sqs.us-east-1.amazonaws.com/queue/${topic}`);
  }
}

// --- Concrete Products (Azure Family) ---
export class AzureBlobStorage implements StorageService {
  async uploadFile(path: string, content: Buffer): Promise<string> {
    console.log(`[Azure Blob] Uploaded ${content.length} bytes to https://prod.blob.core.windows.net/${path}`);
    return `https://prod.blob.core.windows.net/${path}`;
  }
}

export class AzureServiceBusQueue implements QueueService {
  async publishMessage(topic: string, message: any): Promise<void> {
    console.log(`[Azure Service Bus] Published message to sb://prod.servicebus.windows.net/${topic}`);
  }
}

// --- Abstract Factory Interface ---
export interface CloudInfrastructureFactory {
  createStorage(): StorageService;
  createQueue(): QueueService;
}

// --- Concrete Factories ---
export class AwsCloudFactory implements CloudInfrastructureFactory {
  createStorage(): StorageService {
    return new AwsS3Storage();
  }
  createQueue(): QueueService {
    return new AwsSqsQueue();
  }
}

export class AzureCloudFactory implements CloudInfrastructureFactory {
  createStorage(): StorageService {
    return new AzureBlobStorage();
  }
  createQueue(): QueueService {
    return new AzureServiceBusQueue();
  }
}

// --- Client / Bootstrap ---
export class ApplicationEngine {
  private storage: StorageService;
  private queue: QueueService;

  constructor(factory: CloudInfrastructureFactory) {
    // Guarantees all created services belong to the same cloud family
    this.storage = factory.createStorage();
    this.queue = factory.createQueue();
  }

  async runBackup(filename: string, data: Buffer) {
    const url = await this.storage.uploadFile(filename, data);
    await this.queue.publishMessage("backup-events", { url, timestamp: Date.now() });
  }
}

// Execution:
const factory = process.env.CLOUD_PROVIDER === "AZURE" ? new AzureCloudFactory() : new AwsCloudFactory();
const app = new ApplicationEngine(factory);
app.runBackup("ledger.csv", Buffer.from("id,amount\\n1,500"));
""",
        "edgeCases": [
            "**Interface Bloat**: Adding a new product type (e.g. `createSecretManager()`) requires modifying the Abstract Factory interface and all existing concrete factory subclasses.",
            "**Cross-Family Mixing**: Ensure client code never bypasses the factory to instantiate a single product directly with `new AwsS3Storage()`, which breaks family consistency."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When a system must be independent of how its products are created, composed, and represented.",
                "When a system needs to be configured with one of multiple families of products.",
                "When enforcing that a family of related products must always be used together."
            ],
            "whenNotToUse": [
                "When you only have a single object type to create (use Factory Method instead)."
            ]
        }
    },
    {
        "filename": "04_Builder_Pattern.md",
        "title": "Builder Pattern",
        "category": "Creational Pattern",
        "intent": "Separate the construction of a complex object from its representation so that the same construction process can create different representations.",
        "problem": "When constructing complex domain objects with dozens of optional configurations, constructors become unwieldy ('Telescoping Constructor Anti-Pattern'), parameters become error-prone (passing 5 boolean flags in a row), and object immutability is difficult to guarantee.",
        "scenario": "Dynamic SQL Query / API Request Builder. Constructing parameterized, injection-safe SQL queries with dynamic filters, joins, pagination, and sorting based on user search parameters.",
        "diagram": """
+-------------------------------------------------------+
|                      QueryBuilder                     |
+-------------------------------------------------------+
| - table: string                                       |
| - fields: string[]                                    |
| - conditions: string[]                                |
| - params: any[]                                       |
| - limitValue?: number                                 |
+-------------------------------------------------------+
| + select(fields): QueryBuilder                        |
| + from(table): QueryBuilder                           |
| + where(field, operator, value): QueryBuilder         |
| + limit(count): QueryBuilder                          |
| + build(): { sql: string, params: any[] }             |
+-------------------------------------------------------+
""",
        "code": """export interface CompiledQuery {
  sql: string;
  params: any[];
}

export class SqlQueryBuilder {
  private tableName = "";
  private selectFields: string[] = ["*"];
  private whereConditions: string[] = [];
  private orderFields: string[] = [];
  private limitCount?: number;
  private offsetCount?: number;
  private queryParams: any[] = [];

  public from(table: string): this {
    if (!table || table.trim().length === 0) {
      throw new Error("Table name must not be empty.");
    }
    this.tableName = table;
    return this;
  }

  public select(...fields: string[]): this {
    if (fields.length > 0) {
      this.selectFields = fields;
    }
    return this;
  }

  public where(field: string, operator: "=" | "!=" | ">" | "<" | "LIKE", value: any): this {
    this.queryParams.push(value);
    const placeholder = `$${this.queryParams.length}`;
    this.whereConditions.push(`${field} ${operator} ${placeholder}`);
    return this;
  }

  public orderBy(field: string, direction: "ASC" | "DESC" = "ASC"): this {
    this.orderFields.push(`${field} ${direction}`);
    return this;
  }

  public paginate(page: number, pageSize: number): this {
    this.limitCount = pageSize;
    this.offsetCount = (Math.max(1, page) - 1) * pageSize;
    return this;
  }

  public build(): CompiledQuery {
    if (!this.tableName) {
      throw new Error("Cannot build query without target table name. Call .from('table') first.");
    }

    let sql = `SELECT ${this.selectFields.join(", ")} FROM ${this.tableName}`;

    if (this.whereConditions.length > 0) {
      sql += ` WHERE ${this.whereConditions.join(" AND ")}`;
    }

    if (this.orderFields.length > 0) {
      sql += ` ORDER BY ${this.orderFields.join(", ")}`;
    }

    if (this.limitCount !== undefined) {
      sql += ` LIMIT ${this.limitCount}`;
    }

    if (this.offsetCount !== undefined) {
      sql += ` OFFSET ${this.offsetCount}`;
    }

    return {
      sql: sql + ";",
      params: [...this.queryParams],
    };
  }
}

// --- Usage ---
const query = new SqlQueryBuilder()
  .from("users")
  .select("id", "email", "created_at")
  .where("status", "=", "ACTIVE")
  .where("age", ">", 21)
  .orderBy("created_at", "DESC")
  .paginate(1, 20)
  .build();

console.log("Generated SQL:", query.sql);
console.log("Sanitized Parameters:", query.params);
""",
        "edgeCases": [
            "**Incomplete State Building**: Client calls `.build()` before mandatory fields (e.g. `.from()`) are specified. Throw informative validation errors inside `.build()`.",
            "**Reusability Contamination**: Calling `.build()` multiple times on the same builder without clearing state can accidentally append duplicate conditions. Solution: Make builders single-use or clone internal state."
        ],
        "tradeoffs": {
            "whenToUse": [
                "To get rid of a 'telescoping constructor' with 4+ optional parameters.",
                "When construction of an object must allow different representations for the object that's constructed.",
                "When you want to enforce immutable objects after construction."
            ],
            "whenNotToUse": [
                "For simple, data-only entities with only 1 or 2 fields (plain object literals are cleaner)."
            ]
        }
    },
    {
        "filename": "05_Prototype_Pattern.md",
        "title": "Prototype Pattern",
        "category": "Creational Pattern",
        "intent": "Specify the kinds of objects to create using a prototypical instance, and create new objects by copying this prototype rather than through expensive initialization.",
        "problem": "Instantiating complex domain objects from scratch involves expensive database reads, network lookups, and parsing operations. If 1,000 similar objects are needed, repeating this pipeline exhausts CPU and increases latency.",
        "scenario": "Game Entity Spawning / Document Template Generator. In a real-time multiplayer combat simulation, spawning 500 enemy NPC soldiers with identical mesh physics, armor, weapon stats, and behavior trees from disk is too slow. A base prototype is loaded once into memory and cloned with unique IDs and coordinates.",
        "diagram": """
+-----------------------------------+
|             Prototype             |
+-----------------------------------+
| + clone(): Prototype              |
+-----------------------------------+
                  ▲
                  │
+-----------------------------------+
|           EnemySoldier            |
+-----------------------------------+
| - weaponStats: object             |
| - health: number                  |
| - position: { x, y }              |
+-----------------------------------+
| + clone(): EnemySoldier           |
+-----------------------------------+
""",
        "code": """export interface Clonable<T> {
  clone(): T;
}

export interface WeaponLoadout {
  primary: string;
  damage: number;
  ammoCapacity: number;
}

export class EnemyNpc implements Clonable<EnemyNpc> {
  public id: string;
  public rank: string;
  public health: number;
  public position: { x: number; y: number };
  public loadout: WeaponLoadout;

  constructor(
    id: string,
    rank: string,
    health: number,
    position: { x: number; y: number },
    loadout: WeaponLoadout
  ) {
    this.id = id;
    this.rank = rank;
    this.health = health;
    this.position = position;
    this.loadout = loadout;
  }

  /**
   * Deep Copy Clone implementation.
   * Ensures mutable nested objects (loadout, position) do not share references.
   */
  public clone(): EnemyNpc {
    return new EnemyNpc(
      `npc-${crypto.randomUUID().slice(0, 8)}`,
      this.rank,
      this.health,
      { ...this.position },
      { ...this.loadout }
    );
  }
}

// Prototype Registry
export class PrototypeRegistry {
  private prototypes = new Map<string, Clonable<any>>();

  register(name: string, prototype: Clonable<any>): void {
    this.prototypes.set(name, prototype);
  }

  create(name: string): any {
    const proto = this.prototypes.get(name);
    if (!proto) {
      throw new Error(`Prototype with key "${name}" not found in registry.`);
    }
    return proto.clone();
  }
}

// --- Usage ---
const registry = new PrototypeRegistry();

// Initialize expensive template once
const eliteSniperPrototype = new EnemyNpc(
  "base-sniper",
  "ELITE",
  100,
  { x: 0, y: 0 },
  { primary: "Barrett .50", damage: 150, ammoCapacity: 5 }
);
registry.register("ELITE_SNIPER", eliteSniperPrototype);

// Instant cheap clones during gameplay
const spawnedSniper1 = registry.create("ELITE_SNIPER");
spawnedSniper1.position.x = 250;

const spawnedSniper2 = registry.create("ELITE_SNIPER");
spawnedSniper2.position.x = 420;

console.log("Clone 1 ID:", spawnedSniper1.id, "Pos:", spawnedSniper1.position);
console.log("Clone 2 ID:", spawnedSniper2.id, "Pos:", spawnedSniper2.position);
""",
        "edgeCases": [
            "**Shallow vs Deep Copy**: A shallow copy only duplicates top-level primitives. Modifying a nested object (e.g. `clone.loadout.damage = 999`) will corrupt the original prototype if deep cloning is omitted.",
            "**Circular References**: Objects containing circular pointer graphs cause infinite recursion during naive recursive serialization cloning."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When object creation is computationally or I/O expensive.",
                "When your code shouldn't depend on the concrete classes of objects you need to copy.",
                "When avoiding inheritance subclasses that differ only in initial variable states."
            ],
            "whenNotToUse": [
                "Cloning complex objects with circular references or external socket/file handles that cannot be cloned safely."
            ]
        }
    },
    {
        "filename": "06_Object_Pool_Pattern.md",
        "title": "Object Pool Pattern",
        "category": "Creational Pattern",
        "intent": "Manage the reuse of a pool of pre-allocated, expensive-to-create objects rather than continuously allocating and destroying them, minimizing Garbage Collection (GC) pressure and socket exhaustion.",
        "problem": "Continuously creating and tearing down high-overhead resources (TCP sockets, database connections, SSL handshake sessions) causes severe CPU spikes, memory fragmentation, and frequent Garbage Collection pauses that degrade real-time performance.",
        "scenario": "Database / Network Connection Pool. An API handling 10,000 requests per second leases pre-warmed connection instances from an active pool, executes queries, and returns connections to the pool for reuse.",
        "diagram": """
+-------------------------------------------------------+
|                       ObjectPool                      |
+-------------------------------------------------------+
| - available: Resource[]                               |
| - inUse: Map<string, Resource>                        |
| - maxCapacity: number                                 |
+-------------------------------------------------------+
| + acquire(timeoutMs): Promise<Resource>               |
| + release(resource): void                             |
+-------------------------------------------------------+
           ▲                             │
           │ (Returns resource)          │ (Leases resource)
           │                             ▼
    [ Client Request ] ◄─────── [ Active Resource ]
""",
        "code": """export interface PoolableResource {
  id: string;
  isValid(): boolean;
  reset(): void;
}

export class MockDbConnection implements PoolableResource {
  public id: string;
  private isAlive = true;

  constructor(id: string) {
    this.id = id;
  }

  isValid(): boolean {
    return this.isAlive;
  }

  reset(): void {
    // Reset transaction state, session variables, etc.
  }

  close(): void {
    this.isAlive = false;
  }
}

export class ObjectPool<T extends PoolableResource> {
  private available: T[] = [];
  private inUse = new Set<T>();
  private maxCapacity: number;
  private factoryFn: () => T;
  private waitingQueue: Array<(resource: T) => void> = [];

  constructor(factoryFn: () => T, minSize = 2, maxCapacity = 10) {
    this.factoryFn = factoryFn;
    this.maxCapacity = maxCapacity;

    // Pre-warm minimum pool
    for (let i = 0; i < minSize; i++) {
      this.available.push(this.factoryFn());
    }
  }

  public async acquire(timeoutMs = 3000): Promise<T> {
    // 1. Reuse existing available resource if valid
    while (this.available.length > 0) {
      const resource = this.available.pop()!;
      if (resource.isValid()) {
        this.inUse.add(resource);
        return resource;
      }
    }

    // 2. Expand pool if under max capacity
    if (this.inUse.size < this.maxCapacity) {
      const newResource = this.factoryFn();
      this.inUse.add(newResource);
      return newResource;
    }

    // 3. Queue request if capacity reached
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        const index = this.waitingQueue.indexOf(resolve);
        if (index !== -1) {
          this.waitingQueue.splice(index, 1);
          reject(new Error("Connection pool acquisition timeout: Pool exhausted."));
        }
      }, timeoutMs);

      this.waitingQueue.push((resource: T) => {
        clearTimeout(timer);
        this.inUse.add(resource);
        resolve(resource);
      });
    });
  }

  public release(resource: T): void {
    if (!this.inUse.has(resource)) return;
    this.inUse.delete(resource);

    if (resource.isValid()) {
      resource.reset();

      if (this.waitingQueue.length > 0) {
        const nextCaller = this.waitingQueue.shift()!;
        nextCaller(resource);
      } else {
        this.available.push(resource);
      }
    }
  }

  public getStats() {
    return {
      available: this.available.length,
      inUse: this.inUse.size,
      queuedRequests: this.waitingQueue.length,
    };
  }
}

// --- Usage ---
let connCounter = 1;
const pool = new ObjectPool(() => new MockDbConnection(`conn-${connCounter++}`), 2, 5);

async function executeQuery() {
  const conn = await pool.acquire();
  try {
    console.log(`[Worker] Leased connection ${conn.id}`);
    await new Promise((r) => setTimeout(r, 40));
  } finally {
    pool.release(conn);
    console.log(`[Worker] Returned connection ${conn.id}`);
  }
}

executeQuery();
executeQuery();
""",
        "edgeCases": [
            "**Resource Leaks (Forgotten Releases)**: If a client throws an unhandled error and fails to execute `pool.release()`, the resource is leaked, eventually starving the pool. Always wrap acquire/release in `try ... finally` blocks.",
            "**Dirty State Leakage**: When resources are returned, uncommitted database transactions or lingering socket buffers must be reset (`resource.reset()`) to avoid cross-request data leaks.",
            "**Stale Resource Detection**: Network connections can silently drop behind firewalls. The pool must perform periodic health checks (`isValid()`) before leasing."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When object creation cost is high and rate of instantiation/destruction is extreme.",
                "Managing finite external connections (DB sockets, TCP channels, audio/render buffers)."
            ],
            "whenNotToUse": [
                "For lightweight objects with low creation overhead (creating a pool for simple POJOs increases memory overhead and GC burden)."
            ]
        }
    }
]

for p in patterns:
    edge_cases_str = "\\n".join([f"- {e}" for e in p["edgeCases"]])
    when_to_use_str = "\\n".join([f"- {w}" for w in p["tradeoffs"]["whenToUse"]])
    when_not_to_use_str = "\\n".join([f"- {w}" for w in p["tradeoffs"]["whenNotToUse"]])
    
    content = f"""# {p['title']}

## Category: {p['category']}

---

## 1. Core Intent & Definition
{p['intent']}

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
{p['problem']}

### Real-World Industry Example:
{p['scenario']}

---

## 3. Architecture & Visual Flow Diagram
```
{p['diagram'].strip()}
```

---

## 4. Practical Implementation (TypeScript)
```typescript
{p['code'].strip()}
```

---

## 5. Edge Cases & Failure Handling
{edge_cases_str}

---

## 6. Trade-offs & Production Considerations
### When to Use:
{when_to_use_str}

### When NOT to Use / Anti-patterns:
{when_not_to_use_str}
"""
    file_path = os.path.join(BASE_DIR, p["filename"])
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"[Creational] Successfully generated {len(patterns)} in-depth pattern files.")
