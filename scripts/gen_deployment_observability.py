import os

TARGET_DIR = "/home/vicky/Documents/Antigravity/lld/08_Deployment_Observability_Patterns"
os.makedirs(TARGET_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Sidecar_and_Ambassador_Pattern.md",
        "title": "Sidecar and Ambassador Pattern",
        "category": "Deployment & Observability Patterns",
        "intent": "Deploy a helper process alongside the main application container within the same lifecycle boundary (e.g. Kubernetes Pod) to offload secondary tasks like logging, TLS termination, proxying, or external service adaptation.",
        "industry_example": "Envoy / Linkerd Sidecars and CloudSQL Auth Proxy on Google Kubernetes Engine (GKE) allowing containerized applications to connect to CloudSQL via localhost without managing IAM database certificates.",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Pod Startup Order Race**: If the main container starts before the Envoy/CloudSQL sidecar is ready, the main container fails to connect to the database and crashes. Use Kubernetes container lifecycle hooks (`preStop`, `postStart`) or native Sidecar Containers in K8s 1.28+.
2. **Resource Starvation**: Uncapped sidecars (e.g. fluentbit consuming unexpected CPU) can cause the main business application to be throttled or OOM-killed. Always define explicit CPU and memory resource requests/limits for all containers in the pod.
3. **Shutdown Signal Handling**: When a Pod terminates, the sidecar might terminate before the main app flushes remaining logs or completes active transactions.""",
        "tradeoffs": """### When to Use:
- Multi-language polyglot environments where cross-cutting concerns (mTLS, telemetry, log shipping, DB proxies) must be updated and maintained without re-compiling every application codebase.

### When NOT to Use:
- High-density single-process microservices where doubling container count per pod adds unnecessary Kubernetes scheduler and memory overhead."""
    },
    {
        "filename": "02_Distributed_Tracing_Correlation_ID.md",
        "title": "Distributed Tracing and Correlation ID Pattern",
        "category": "Deployment & Observability Patterns",
        "intent": "Generate and propagate unique trace and correlation identifiers across distributed asynchronous network hops to reconstruct full end-to-end request call trees and isolate latency bottlenecks.",
        "industry_example": "OpenTelemetry, Jaeger, and AWS X-Ray deployed across Uber and Spotify microservices to trace a single ride request or song playback across 40+ downstream services.",
        "diagram": """
Client Request
      |
      | Headers: [traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01]
      v
[ API Gateway ] (Span A: 20ms)
      |
      +---> [ Auth Svc ] (Span B: 15ms)
      |
      +---> [ Order Svc ] (Span C: 120ms)
                 |
                 +---> [ Postgres Query ] (Span D: 85ms) <-- Bottleneck Found!
""",
        "code": """/**
 * Distributed Tracing & W3C TraceContext Pattern
 * Context propagation across asynchronous microservice boundaries
 */

export interface Span {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  serviceName: string;
  operationName: string;
  startTime: number;
  durationMs?: number;
  tags: Record<string, string>;
}

export class DistributedTracer {
  private spans: Span[] = [];

  startSpan(serviceName: string, operationName: string, parentContext?: { traceId: string; spanId: string }): Span {
    const traceId = parentContext?.traceId || `trace-${Math.random().toString(36).substr(2, 12)}`;
    const spanId = `span-${Math.random().toString(36).substr(2, 8)}`;

    const span: Span = {
      traceId,
      spanId,
      parentSpanId: parentContext?.spanId,
      serviceName,
      operationName,
      startTime: Date.now(),
      tags: {}
    };

    return span;
  }

  finishSpan(span: Span): void {
    span.durationMs = Date.now() - span.startTime;
    this.spans.push(span);
    console.log(`[Tracer] Finished Span: [${span.serviceName}:${span.operationName}] Duration: ${span.durationMs}ms (TraceId: ${span.traceId})`);
  }

  exportTraceTree(traceId: string): Span[] {
    return this.spans.filter(s => s.traceId === traceId);
  }
}

// Inter-service propagation demonstration
export async function simulateTraceFlow() {
  const tracer = new DistributedTracer();

  // 1. Gateway receives request
  const gatewaySpan = tracer.startSpan('api-gateway', 'POST /checkout');
  
  // 2. Gateway calls Order Service (Propagating TraceContext)
  const orderSpan = tracer.startSpan('order-service', 'CreateOrderEntity', {
    traceId: gatewaySpan.traceId,
    spanId: gatewaySpan.spanId
  });

  // 3. Order Service calls DB
  const dbSpan = tracer.startSpan('order-service', 'SQL: INSERT INTO orders', {
    traceId: orderSpan.traceId,
    spanId: orderSpan.spanId
  });
  await new Promise(r => setTimeout(r, 45)); // Simulate DB latency
  tracer.finishSpan(dbSpan);

  tracer.finishSpan(orderSpan);
  tracer.finishSpan(gatewaySpan);
}
""",
        "edge_cases": """1. **Context Stripping in Async Background Handlers**: When spawning unawaited `setTimeout()` or worker threads, thread-local contexts (e.g. `AsyncLocalStorage` in Node.js) can lose active trace context if not explicitly bound.
2. **Sampling Overhead & Storage Costs**: Tracing 100% of 100,000 requests/sec generates petabytes of trace data. Implement probabilistic or adaptive sampling (e.g. trace 1% of normal requests, but 100% of 5xx errors and requests taking > 1,000ms).
3. **Trace Header Tampering**: Ensure external untrusted clients cannot inject malicious or spoofed `X-Correlation-ID` values into internal security audit systems.""",
        "tradeoffs": """### When to Use:
- Mandatory in any microservices system consisting of more than 3 services to diagnose high-latency p99 queries and intermittent network timeouts.

### When NOT to Use:
- Monolithic applications with simple single-threaded execution stacks where standard stack traces and line debuggers provide immediate answers."""
    },
    {
        "filename": "03_Health_Check_API_Pattern.md",
        "title": "Health Check API Pattern",
        "category": "Deployment & Observability Patterns",
        "intent": "Expose specialized endpoints to orchestrators (Kubernetes, AWS ALB) distinguishing between process liveness (is it running or deadlocked?) and service readiness (is it ready to accept live traffic?).",
        "industry_example": "Kubernetes Liveness, Readiness, and Startup Probes deployed across all production Docker/K8s microservices.",
        "diagram": """
              +----------------------------+
              |   Kubernetes Kubelet       |
              +----------------------------+
                     /              \\
  GET /healthz/liveness?            GET /healthz/readiness?
        |                                  |
   (Is JVM alive?)                   (Can connect to Postgres & Redis?)
        |                                  |
     [ 200 OK ]                         [ 503 Unavailable ]
        |                                  |
   Keep container alive!             Remove Pod from Load Balancer Pool!
                                     Do NOT restart container yet!
""",
        "code": """/**
 * Health Check API Pattern
 * Decoupled Liveness and Readiness probes with deep dependency health verification
 */

export interface HealthStatus {
  status: 'UP' | 'DOWN';
  timestamp: string;
  uptimeSeconds: number;
  checks?: Record<string, { status: 'UP' | 'DOWN'; latencyMs?: number; message?: string }>;
}

export class HealthCheckController {
  private startTime = Date.now();
  private isShuttingDown = false;

  constructor(
    private dbCheck: () => Promise<boolean>,
    private redisCheck: () => Promise<boolean>
  ) {}

  setShuttingDown(val: boolean): void {
    this.isShuttingDown = val;
  }

  // Liveness Probe: Simple heartbeat. If this fails, container is deadlocked and K8s restarts it!
  getLiveness(): { statusCode: number; body: HealthStatus } {
    if (this.isShuttingDown) {
      return {
        statusCode: 503,
        body: { status: 'DOWN', timestamp: new Date().toISOString(), uptimeSeconds: this.getUptime() }
      };
    }

    return {
      statusCode: 200,
      body: { status: 'UP', timestamp: new Date().toISOString(), uptimeSeconds: this.getUptime() }
    };
  }

  // Readiness Probe: Deep dependency validation. If this fails, K8s stops routing traffic to this pod!
  async getReadiness(): Promise<{ statusCode: number; body: HealthStatus }> {
    if (this.isShuttingDown) {
      return { statusCode: 503, body: { status: 'DOWN', timestamp: new Date().toISOString(), uptimeSeconds: this.getUptime() } };
    }

    const checks: Record<string, any> = {};
    let allHealthy = true;

    // Check Postgres DB
    try {
      const t0 = Date.now();
      const dbOk = await this.dbCheck();
      checks['database'] = { status: dbOk ? 'UP' : 'DOWN', latencyMs: Date.now() - t0 };
      if (!dbOk) allHealthy = false;
    } catch (err: any) {
      checks['database'] = { status: 'DOWN', message: err.message };
      allHealthy = false;
    }

    // Check Redis
    try {
      const t0 = Date.now();
      const redisOk = await this.redisCheck();
      checks['redis'] = { status: redisOk ? 'UP' : 'DOWN', latencyMs: Date.now() - t0 };
      if (!redisOk) allHealthy = false;
    } catch (err: any) {
      checks['redis'] = { status: 'DOWN', message: err.message };
      allHealthy = false;
    }

    return {
      statusCode: allHealthy ? 200 : 503,
      body: {
        status: allHealthy ? 'UP' : 'DOWN',
        timestamp: new Date().toISOString(),
        uptimeSeconds: this.getUptime(),
        checks
      }
    };
  }

  private getUptime(): number {
    return Math.floor((Date.now() - this.startTime) / 1000);
  }
}
""",
        "edge_cases": """1. **Cascading Restarts from Heavy DB Checks in Liveness Probe**: If you put a PostgreSQL `SELECT 1` inside the *Liveness* probe and Postgres has a 1-second lag, Kubernetes will simultaneously kill and restart ALL 50 application pods, exacerbating the database overload into an unrecoverable outage! Keep Liveness lightweight; put dependency checks in Readiness only!
2. **Health Probe Denial of Service (DoS)**: If Kubelet probes every 2 seconds across 100 pods, running heavy health queries can consume 10% of database CPU. Use lightweight in-memory cached checks.
3. **Graceful Termination Handshake**: On receiving `SIGTERM`, immediately flip Readiness to 503 so load balancers stop sending new requests, wait 5 seconds for in-flight requests to complete, then exit.""",
        "tradeoffs": """### When to Use:
- Every containerized service deployed to Kubernetes, AWS ECS, or behind cloud load balancers.

### When NOT to Use:
- Local single-binary command-line CLI tools."""
    },
    {
        "filename": "04_Log_Aggregation_Pattern.md",
        "title": "Log Aggregation Pattern",
        "category": "Deployment & Observability Patterns",
        "intent": "Standardize all distributed service logs into structured JSON streams, automatically enriching them with contextual metadata (traceId, environment, tenant) and shipping them to a centralized search engine.",
        "industry_example": "ELK Stack (Elasticsearch, Logstash, Kibana) and Grafana Loki deployed at Stripe and Airbnb for real-time log querying across tens of thousands of container nodes.",
        "diagram": """
Service Pod A ---> [ Structured JSON stdout ] --+
                                                |
Service Pod B ---> [ Structured JSON stdout ] --+--> [ DaemonSet Log Collector ]
                                                |    (Fluentbit / Promtail)
Service Pod C ---> [ Structured JSON stdout ] --+               |
                                                                v
                                                   [ Centralized Log Store ]
                                                   (Elasticsearch / Loki)
                                                                |
                                                                v
                                                   [ Kibana / Grafana UI ]
""",
        "code": """/**
 * Structured Log Aggregation Pattern
 * Standardized JSON formatting, context enrichment, and PII masking
 */

export interface LogEnvelope {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  service: string;
  environment: string;
  traceId?: string;
  message: string;
  context?: Record<string, any>;
}

export class ProductionJsonLogger {
  constructor(
    private serviceName: string,
    private environment: string = 'production'
  ) {}

  info(message: string, context?: Record<string, any>, traceId?: string): void {
    this.emit('INFO', message, context, traceId);
  }

  error(message: string, error?: Error, context?: Record<string, any>, traceId?: string): void {
    const errorContext = {
      ...context,
      errorName: error?.name,
      errorMessage: error?.message,
      stackTrace: error?.stack
    };
    this.emit('ERROR', message, errorContext, traceId);
  }

  private emit(level: LogEnvelope['level'], message: string, context?: Record<string, any>, traceId?: string): void {
    const sanitizedContext = this.maskSensitivePii(context || {});

    const logEntry: LogEnvelope = {
      timestamp: new Date().toISOString(),
      level,
      service: this.serviceName,
      environment: this.environment,
      traceId,
      message,
      context: sanitizedContext
    };

    // Standardized single-line JSON written to stdout for 12-factor log ingestion
    console.log(JSON.stringify(logEntry));
  }

  // Crucial Production Requirement: Mask PII / PCI data before shipping
  private maskSensitivePii(obj: Record<string, any>): Record<string, any> {
    const copy = { ...obj };
    for (const key of Object.keys(copy)) {
      if (/password|secret|token|apikey/i.test(key)) {
        copy[key] = '********';
      } else if (/creditcard|pan|cardnumber/i.test(key)) {
        copy[key] = `****-****-****-${String(copy[key]).slice(-4)}`;
      }
    }
    return copy;
  }
}
""",
        "edge_cases": """1. **Unformatted Multi-line Stack Traces**: Printing raw multiline stack traces causes log splitters to treat each line of a stack trace as a separate event. Always serialize stack traces into a single JSON string property.
2. **Log Flooding / Disk Full Outages**: A runaway loop emitting 1,000,000 ERROR logs per minute can saturate the container node's disk. Mitigation: Rate-limited loggers and log rotation (`max-size: 50m`).
3. **Data Security & GDPR Compliance**: Accidental logging of customer social security numbers or API tokens creates severe legal liability. Automated PII scrubbing regexes must run at the application logger level.""",
        "tradeoffs": """### When to Use:
- Mandatory for all microservice deployments to avoid SSHing into individual servers to grep log files.

### When NOT to Use:
- High-frequency inner loops processing millions of network packets per second where JSON serialization CPU overhead slows down packet transit."""
    },
    {
        "filename": "05_Feature_Toggles_Canary_Release.md",
        "title": "Feature Toggles and Canary Release Pattern",
        "category": "Deployment & Observability Patterns",
        "intent": "Decouple code deployment from feature release by wrapping new code paths behind dynamic runtime feature flags and routing a small percentage of real production traffic to canary versions to verify stability before full rollout.",
        "industry_example": "LaunchDarkly, Split.io, and Meta Gatekeeper (Facebook deploying code to production daily with features dark; enabling features dynamically for 1% of users, monitoring error rates, and expanding to 100%).",
        "diagram": """
Client Request (User ID: 'usr-9281')
                |
                v
  +-------------------------------+
  | Feature Flag Evaluator        |
  | Hash(userId + flag) % 100 < 5 |
  +-------------------------------+
         /                 \\
   (In 5% Canary)       (In 95% Baseline)
        v                     v
[ New Checkout V2 ]   [ Stable Checkout V1 ]
        |                     |
        v                     v
   Log Error Rates       Log Error Rates
   (If Error Spike -> Kill switch drops Canary to 0% instantly!)
""",
        "code": """/**
 * Feature Toggles & Canary Release Pattern
 * Deterministic hash-based percentage rollout with targeted rule evaluation
 */

export interface ToggleUserContext {
  userId: string;
  email?: string;
  country?: string;
  isInternalEmployee?: boolean;
}

export interface FeatureFlagRule {
  key: string;
  enabled: boolean;
  canaryPercentage: number; // 0 to 100
  allowedUserIds?: string[];
  allowedCountries?: string[];
}

export class FeatureFlagEngine {
  private flags = new Map<string, FeatureFlagRule>();

  registerFlag(rule: FeatureFlagRule): void {
    this.flags.set(rule.key, rule);
  }

  // Instant emergency kill switch
  killSwitch(key: string): void {
    const flag = this.flags.get(key);
    if (flag) {
      flag.enabled = false;
      flag.canaryPercentage = 0;
      console.warn(`[FeatureFlag KILL SWITCH] Flag '${key}' has been forcibly DISABLED.`);
    }
  }

  isEnabled(key: string, user: ToggleUserContext): boolean {
    const flag = this.flags.get(key);
    if (!flag || !flag.enabled) return false;

    // 1. Rule: Explicit user ID whitelist
    if (flag.allowedUserIds && flag.allowedUserIds.includes(user.userId)) {
      return true;
    }

    // 2. Rule: Internal employees always get canary features
    if (user.isInternalEmployee) {
      return true;
    }

    // 3. Rule: Geographic targeting
    if (flag.allowedCountries && user.country && !flag.allowedCountries.includes(user.country)) {
      return false;
    }

    // 4. Deterministic Canary Rollout Percentage via hashing
    // Ensures the same user consistently sees the same feature version on page reloads!
    const userHashBucket = this.hashUserToPercent(user.userId, key);
    return userHashBucket < flag.canaryPercentage;
  }

  private hashUserToPercent(userId: string, flagKey: string): number {
    const str = `${userId}:${flagKey}`;
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0; // Convert to 32bit integer
    }
    return Math.abs(hash) % 100;
  }
}
""",
        "edge_cases": """1. **Dead Feature Flag Debt**: Obsolete flags left in code for years create combinatorial test permutations and unreadable spaghetti code. Establish a policy to remove flag checks once a feature is at 100% for 30 days.
2. **Flag Evaluation Latency**: Fetching flags via remote HTTP on every user request adds 50ms latency. Always cache flags locally in memory and stream updates via WebSockets / Redis Pub/Sub.
3. **Database Schema Divergence**: If Canary V2 writes a new column that Baseline V1 cannot read, rolling back the canary corrupts baseline queries. Always make database changes backward-compatible before rolling out canaries.""",
        "tradeoffs": """### When to Use:
- Continuous deployment workflows where teams release code multiple times daily and require zero-downtime progressive rollouts and instant rollback capabilities.

### When NOT to Use:
- Core low-level mathematical or cryptographic utility libraries where behavior must remain invariant across all invocations."""
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
    print("[Observability] Successfully generated all 5 patterns.")
