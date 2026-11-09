# Log Aggregation Pattern

## 1. Classification & Intent
- **Pattern Category:** Deployment & Observability Patterns
- **Core Intent:** Standardize all distributed service logs into structured JSON streams, automatically enriching them with contextual metadata (traceId, environment, tenant) and shipping them to a centralized search engine.

---

## 2. Real-Life Industry Example
ELK Stack (Elasticsearch, Logstash, Kibana) and Grafana Loki deployed at Stripe and Airbnb for real-time log querying across tens of thousands of container nodes.

---

## 3. Architecture & Flow Diagram
```
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
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Unformatted Multi-line Stack Traces**: Printing raw multiline stack traces causes log splitters to treat each line of a stack trace as a separate event. Always serialize stack traces into a single JSON string property.
2. **Log Flooding / Disk Full Outages**: A runaway loop emitting 1,000,000 ERROR logs per minute can saturate the container node's disk. Mitigation: Rate-limited loggers and log rotation (`max-size: 50m`).
3. **Data Security & GDPR Compliance**: Accidental logging of customer social security numbers or API tokens creates severe legal liability. Automated PII scrubbing regexes must run at the application logger level.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Mandatory for all microservice deployments to avoid SSHing into individual servers to grep log files.

### When NOT to Use:
- High-frequency inner loops processing millions of network packets per second where JSON serialization CPU overhead slows down packet transit.
