# Sidecar and Ambassador Pattern

## 1. Classification & Intent
- **Pattern Category:** Deployment & Observability Patterns
- **Core Intent:** Deploy a helper process alongside the main application container within the same lifecycle boundary (e.g. Kubernetes Pod) to offload secondary tasks like logging, TLS termination, proxying, or external service adaptation.

---

## 2. Real-Life Industry Example
Envoy / Linkerd Sidecars and CloudSQL Auth Proxy on Google Kubernetes Engine (GKE) allowing containerized applications to connect to CloudSQL via localhost without managing IAM database certificates.

---

## 3. Architecture & Flow Diagram
```
+-------------------------------------------------------------+
|                      Kubernetes Pod                         |
|                                                             |
|  +--------------------+             +--------------------+  |
|  | Main App Container |             | Sidecar Container  |  |
|  | (Business Logic)   |             | (Envoy / Proxy)    |  |
|  +--------------------+             +--------------------+  |
|            |                                  |             |
|            | localhost:5432                   | mTLS        |
|            v                                  v             |
|    Shared Loopback                     Secured Network      |
+-------------------------------------------------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Sidecar & Ambassador Pattern
 * Main Application and Out-of-Process Proxy Co-location
 */

export interface AppLogger {
  log(level: string, message: string, meta?: any): void;
}

// 1. Sidecar Process: Handles buffering, formatting, and shipping to Splunk/Datadog
export class LogShippingSidecar {
  private logBuffer: Array<{ timestamp: string; level: string; message: string; meta?: any }> = [];

  receiveFromApp(level: string, message: string, meta?: any): void {
    const entry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      meta
    };
    this.logBuffer.push(entry);

    if (this.logBuffer.length >= 5) {
      this.flushToRemoteCollector();
    }
  }

  private flushToRemoteCollector(): void {
    console.log(`[Sidecar] Shipping batch of ${this.logBuffer.length} logs to centralized Datadog agent...`);
    this.logBuffer = [];
  }
}

// 2. Main Application: Focuses 100% on domain logic without remote network logging dependencies
export class MainOrderApplication {
  constructor(private sidecar: LogShippingSidecar) {}

  processCheckout(orderId: string, amount: number): void {
    // App writes to localhost sidecar with zero blocking network latency
    this.sidecar.receiveFromApp('INFO', `Checkout started for order ${orderId}`, { amount });

    // Business domain computation
    console.log(`[MainApp] Processing core business logic for order: ${orderId}`);

    this.sidecar.receiveFromApp('INFO', `Checkout successfully committed for order ${orderId}`);
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Pod Startup Order Race**: If the main container starts before the Envoy/CloudSQL sidecar is ready, the main container fails to connect to the database and crashes. Use Kubernetes container lifecycle hooks (`preStop`, `postStart`) or native Sidecar Containers in K8s 1.28+.
2. **Resource Starvation**: Uncapped sidecars (e.g. fluentbit consuming unexpected CPU) can cause the main business application to be throttled or OOM-killed. Always define explicit CPU and memory resource requests/limits for all containers in the pod.
3. **Shutdown Signal Handling**: When a Pod terminates, the sidecar might terminate before the main app flushes remaining logs or completes active transactions.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Multi-language polyglot environments where cross-cutting concerns (mTLS, telemetry, log shipping, DB proxies) must be updated and maintained without re-compiling every application codebase.

### When NOT to Use:
- High-density single-process microservices where doubling container count per pod adds unnecessary Kubernetes scheduler and memory overhead.
