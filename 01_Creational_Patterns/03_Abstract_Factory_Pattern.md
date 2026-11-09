# Abstract Factory Pattern

## Category: Creational Pattern

---

## 1. Core Intent & Definition
Provide an interface for creating families of related or dependent objects without specifying their concrete classes.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
When an application must run across distinct environments (e.g. AWS vs Azure vs Local Cloud Emulator, or Dark Theme vs Light Theme), instantiating mismatched components (e.g. pairing an AWS S3 Bucket with an Azure Queue Client) leads to runtime system failures.

### Real-World Industry Example:
Multi-Cloud Infrastructure Abstraction Layer. An enterprise disaster-recovery service can switch its entire persistence and queue family between AWS (S3 + SQS + DynamoDB) and Azure (Blob + Service Bus + CosmosDB) via an environmental flag.

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// --- Abstract Products ---
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
app.runBackup("ledger.csv", Buffer.from("id,amount\n1,500"));
```

---

## 5. Edge Cases & Failure Handling
- **Interface Bloat**: Adding a new product type (e.g. `createSecretManager()`) requires modifying the Abstract Factory interface and all existing concrete factory subclasses.\n- **Cross-Family Mixing**: Ensure client code never bypasses the factory to instantiate a single product directly with `new AwsS3Storage()`, which breaks family consistency.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When a system must be independent of how its products are created, composed, and represented.\n- When a system needs to be configured with one of multiple families of products.\n- When enforcing that a family of related products must always be used together.

### When NOT to Use / Anti-patterns:
- When you only have a single object type to create (use Factory Method instead).
