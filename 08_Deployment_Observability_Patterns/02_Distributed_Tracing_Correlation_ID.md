# Distributed Tracing and Correlation ID Pattern

## 1. Classification & Intent
- **Pattern Category:** Deployment & Observability Patterns
- **Core Intent:** Generate and propagate unique trace and correlation identifiers across distributed asynchronous network hops to reconstruct full end-to-end request call trees and isolate latency bottlenecks.

---

## 2. Real-Life Industry Example
OpenTelemetry, Jaeger, and AWS X-Ray deployed across Uber and Spotify microservices to trace a single ride request or song playback across 40+ downstream services.

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Context Stripping in Async Background Handlers**: When spawning unawaited `setTimeout()` or worker threads, thread-local contexts (e.g. `AsyncLocalStorage` in Node.js) can lose active trace context if not explicitly bound.
2. **Sampling Overhead & Storage Costs**: Tracing 100% of 100,000 requests/sec generates petabytes of trace data. Implement probabilistic or adaptive sampling (e.g. trace 1% of normal requests, but 100% of 5xx errors and requests taking > 1,000ms).
3. **Trace Header Tampering**: Ensure external untrusted clients cannot inject malicious or spoofed `X-Correlation-ID` values into internal security audit systems.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Mandatory in any microservices system consisting of more than 3 services to diagnose high-latency p99 queries and intermittent network timeouts.

### When NOT to Use:
- Monolithic applications with simple single-threaded execution stacks where standard stack traces and line debuggers provide immediate answers.
