# Strangler Fig Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Incrementally migrate a monolithic application by gradually replacing specific features with microservices behind an intercepting routing facade until the old monolith is decommissioned.

---

## 2. Real-Life Industry Example
Shopify migrating its monolithic Ruby on Rails application to modular microservices and GraphQL backend services without downtime or risky 'big-bang' rewrites.

---

## 3. Architecture & Flow Diagram
```
Incoming HTTP Request
                          |
                          v
         +----------------------------------+
         |      Strangler Reverse Proxy     |
         |    (Route Interceptor / Gateway) |
         +----------------------------------+
                 /                  \
 (Legacy Routes)/                    \(Migrated Routes)
               v                      v
     +-------------------+    +--------------------+
     | Legacy Monolith   |    | New Microservice   |
     | - Auth (Old)      |    | - Payments (V2)    |
     | - Cart (Old)      |    | - Orders (V2)      |
     +-------------------+    +--------------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Strangler Fig Migration Pattern
 * Routing proxy interceptor with dual-run verification and progressive rollout
 */

export interface HttpRequest {
  path: string;
  method: string;
  headers: Record<string, string>;
  body?: any;
}

export interface HttpResponse {
  statusCode: number;
  data: any;
}

export class StranglerRoutingProxy {
  private migratedRoutes = new Map<string, { serviceUrl: string; rolloutPercent: number }>();

  registerMigratedRoute(pathPrefix: string, serviceUrl: string, rolloutPercent: number): void {
    this.migratedRoutes.set(pathPrefix, { serviceUrl, rolloutPercent });
  }

  async handleRequest(req: HttpRequest): Promise<HttpResponse> {
    for (const [prefix, config] of this.migratedRoutes.entries()) {
      if (req.path.startsWith(prefix)) {
        // Feature flag / Canary percentage check
        const randomRollout = Math.random() * 100;
        if (randomRollout < config.rolloutPercent) {
          console.log(`[StranglerProxy] Intercepted -> Routing ${req.path} to Microservice: ${config.serviceUrl}`);
          return await this.forwardToNewService(config.serviceUrl, req);
        }
      }
    }

    // Default route to Legacy Monolith
    console.log(`[StranglerProxy] Fallback -> Routing ${req.path} to Legacy Monolith`);
    return await this.forwardToLegacyMonolith(req);
  }

  private async forwardToNewService(targetUrl: string, req: HttpRequest): Promise<HttpResponse> {
    // Simulated microservice response
    return {
      statusCode: 200,
      data: { source: 'NewMicroservice_V2', path: req.path, timestamp: Date.now() }
    };
  }

  private async forwardToLegacyMonolith(req: HttpRequest): Promise<HttpResponse> {
    // Simulated legacy monolith response
    return {
      statusCode: 200,
      data: { source: 'LegacyMonolith_V1', path: req.path, legacyData: true }
    };
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Dual-Write Consistency**: When migrating an active write path, writes must be dual-written or synchronized back to the legacy database to keep legacy reporting and dependent tables consistent during transition.
2. **Session / Authentication Sharing**: Legacy monolithic cookies or session tokens must be validated seamlessly by both the legacy server and new microservices (e.g., via a JWT conversion sidecar or token translation layer).
3. **Rollback Safety**: If the new microservice fails or has data bugs, the reverse proxy must instantly down-weight traffic to 0% back to the monolith without code redeployment.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Safely modernizing high-revenue production monoliths where a complete big-bang rewrite poses existential business risks.

### When NOT to Use:
- Greenfield projects or systems with low complexity where rewriting the entire service in weeks is faster than building routing facades and dual-write synchronizers.
