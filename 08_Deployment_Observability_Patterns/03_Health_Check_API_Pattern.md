# Health Check API Pattern

## 1. Classification & Intent
- **Pattern Category:** Deployment & Observability Patterns
- **Core Intent:** Expose specialized endpoints to orchestrators (Kubernetes, AWS ALB) distinguishing between process liveness (is it running or deadlocked?) and service readiness (is it ready to accept live traffic?).

---

## 2. Real-Life Industry Example
Kubernetes Liveness, Readiness, and Startup Probes deployed across all production Docker/K8s microservices.

---

## 3. Architecture & Flow Diagram
```
+----------------------------+
              |   Kubernetes Kubelet       |
              +----------------------------+
                     /              \
  GET /healthz/liveness?            GET /healthz/readiness?
        |                                  |
   (Is JVM alive?)                   (Can connect to Postgres & Redis?)
        |                                  |
     [ 200 OK ]                         [ 503 Unavailable ]
        |                                  |
   Keep container alive!             Remove Pod from Load Balancer Pool!
                                     Do NOT restart container yet!
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
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
```

---

## 5. Edge Cases & Failure Scenarios
1. **Cascading Restarts from Heavy DB Checks in Liveness Probe**: If you put a PostgreSQL `SELECT 1` inside the *Liveness* probe and Postgres has a 1-second lag, Kubernetes will simultaneously kill and restart ALL 50 application pods, exacerbating the database overload into an unrecoverable outage! Keep Liveness lightweight; put dependency checks in Readiness only!
2. **Health Probe Denial of Service (DoS)**: If Kubelet probes every 2 seconds across 100 pods, running heavy health queries can consume 10% of database CPU. Use lightweight in-memory cached checks.
3. **Graceful Termination Handshake**: On receiving `SIGTERM`, immediately flip Readiness to 503 so load balancers stop sending new requests, wait 5 seconds for in-flight requests to complete, then exit.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Every containerized service deployed to Kubernetes, AWS ECS, or behind cloud load balancers.

### When NOT to Use:
- Local single-binary command-line CLI tools.
