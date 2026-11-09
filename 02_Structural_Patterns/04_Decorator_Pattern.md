# Decorator Pattern

## Category: Structural Pattern

---

## 1. Core Intent & Definition
Attach additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Extending functionality via subclassing produces an unmanageable explosion of classes. If you need logging, encryption, and compression on a data stream, inheritance requires `LoggedCompressedEncryptedStream`, `CompressedStream`, `LoggedStream`, etc. Combining behaviors dynamically at runtime is impossible with static inheritance.

### Real-World Industry Example:
HTTP API Request / Data Streaming Pipeline. Dynamically wrapping a base network data stream with Gzip Compression, AES-256 Encryption, and Telemetry Performance Metrics logging based on request headers.

---

## 3. Architecture & Visual Flow Diagram
```
+-----------------------+
                      |       DataStream      | (Component Interface)
                      +-----------------------+
                      | + write(data): void   |
                      | + read(): Buffer      |
                      +-----------------------+
                                  ▲
            ┌─────────────────────┴─────────────────────┐
            │                                           │
+-----------------------+                   +-----------------------+
|    PlainDataStream    | (Concrete)        |  DataStreamDecorator  | (Base Decorator)
+-----------------------+                   +-----------------------+
| + write()             |                   | - wrappee: DataStream |
| + read()              |                   +-----------------------+
+-----------------------+                               ▲
                                ┌───────────────────────┴───────────────────────┐
                                │                                               │
                    +-----------------------+                       +-----------------------+
                    |  CompressionDecorator |                       |  EncryptionDecorator  |
                    +-----------------------+                       +-----------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
import crypto from "crypto";

// 1. Component Interface
export interface DataStream {
  write(data: string): Promise<void>;
  read(): Promise<string>;
}

// 2. Concrete Component
export class MemoryDataStream implements DataStream {
  private buffer = "";

  async write(data: string): Promise<void> {
    this.buffer = data;
    console.log(`[MemoryStream] Raw bytes written: "${this.buffer}"`);
  }

  async read(): Promise<string> {
    return this.buffer;
  }
}

// 3. Base Decorator
export abstract class StreamDecorator implements DataStream {
  protected wrappee: DataStream;

  constructor(wrappee: DataStream) {
    this.wrappee = wrappee;
  }

  async write(data: string): Promise<void> {
    await this.wrappee.write(data);
  }

  async read(): Promise<string> {
    return this.wrappee.read();
  }
}

// 4. Concrete Decorators
export class EncryptionDecorator extends StreamDecorator {
  private algorithm = "aes-256-cbc";
  private key = crypto.scryptSync("secret-password", "salt", 32);
  private iv = Buffer.alloc(16, 0); // initialization vector

  async write(data: string): Promise<void> {
    const cipher = crypto.createCipheriv(this.algorithm, this.key, this.iv);
    let encrypted = cipher.update(data, "utf8", "hex");
    encrypted += cipher.final("hex");
    console.log(`[Encryption] Transformed plain text -> encrypted cipher: ${encrypted.slice(0, 24)}...`);
    await this.wrappee.write(encrypted);
  }

  async read(): Promise<string> {
    const raw = await this.wrappee.read();
    const decipher = crypto.createDecipheriv(this.algorithm, this.key, this.iv);
    let decrypted = decipher.update(raw, "hex", "utf8");
    decrypted += decipher.final("utf8");
    return decrypted;
  }
}

export class LoggingDecorator extends StreamDecorator {
  async write(data: string): Promise<void> {
    const start = performance.now();
    console.log(`[Telemetry] Starting write operation (Payload size: ${data.length} chars)`);
    await this.wrappee.write(data);
    const duration = (performance.now() - start).toFixed(2);
    console.log(`[Telemetry] Write completed in ${duration}ms`);
  }

  async read(): Promise<string> {
    console.log(`[Telemetry] Reading data stream`);
    return this.wrappee.read();
  }
}

// --- Usage ---
// Dynamically assemble pipeline at runtime: Raw Stream -> Encrypted -> Logged
const rawStream = new MemoryDataStream();
const secureStream = new EncryptionDecorator(rawStream);
const loggedSecureStream = new LoggingDecorator(secureStream);

loggedSecureStream.write("Confidential User Account Statement").then(async () => {
  const recovered = await loggedSecureStream.read();
  console.log("Decrypted & Recovered Data:", recovered);
});
```

---

## 5. Edge Cases & Failure Handling
- **Order of Decorator Application**: Applying decorators in the wrong order produces unexpected bugs (e.g. encrypting already compressed data vs compressing encrypted data — encryption randomizes bytes, drastically degrading compression efficiency).\n- **Decorator Interface Drift**: If concrete decorators add custom methods not present in the base `DataStream` interface, outer layers cannot access them once wrapped.\n- **Removing Decorators**: Removing a specific wrapper from the middle of a multi-layer decorator stack is difficult.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- To assign extra responsibilities to objects dynamically and transparently without affecting other objects.\n- When extension by subclassing is impractical due to class explosion.\n- Designing middleware pipelines (Express/Koa middleware, Axios interceptors).

### When NOT to Use / Anti-patterns:
- When you need to inspect the concrete type of the object (decorators hide the underlying wrapped type).
