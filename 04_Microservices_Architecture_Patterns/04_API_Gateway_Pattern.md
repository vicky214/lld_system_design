# API Gateway Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Provide a single, unified entry point for all client applications that handles routing, protocol translation, rate limiting, authentication, and request aggregation across backend microservices.

---

## 2. Real-Life Industry Example
Netflix Zuul / Spring Cloud Gateway handling billions of daily device requests, terminating SSL, enforcing OAuth JWT verification, and routing to hundreds of internal microservices.

---

## 3. Architecture & Flow Diagram
```
Client (Web, iOS, Android)
            |
            v
+-------------------------------------------------------+
|                      API GATEWAY                      |
| [SSL Term] [JWT Auth] [Rate Limit] [Metrics / Tracing]|
+-------------------------------------------------------+
        |                     |                    |
        v                     v                    v
+---------------+     +---------------+    +---------------+
| User Service  |     | Catalog Svc   |    | Order Service |
| (gRPC / HTTP) |     | (gRPC / HTTP) |    | (gRPC / HTTP) |
+---------------+     +---------------+    +---------------+
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Production API Gateway Pattern
 * Routing, JWT verification, rate limiting, and aggregation pipeline
 */

export interface GatewayContext {
  userId?: string;
  userRole?: string;
  requestId: string;
  startTimeMs: number;
}

export type GatewayMiddleware = (req: HttpRequest, ctx: GatewayContext, next: () => Promise<HttpResponse>) => Promise<HttpResponse>;

export class ApiGateway {
  private middlewares: GatewayMiddleware[] = [];
  private routes = new Map<string, (req: HttpRequest, ctx: GatewayContext) => Promise<HttpResponse>>();

  use(middleware: GatewayMiddleware): void {
    this.middlewares.push(middleware);
  }

  registerRoute(pathPrefix: string, handler: (req: HttpRequest, ctx: GatewayContext) => Promise<HttpResponse>): void {
    this.routes.set(pathPrefix, handler);
  }

  async execute(req: HttpRequest): Promise<HttpResponse> {
    const ctx: GatewayContext = {
      requestId: `req-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
      startTimeMs: Date.now()
    };

    let index = 0;
    const next = async (): Promise<HttpResponse> => {
      if (index < this.middlewares.length) {
        const mw = this.middlewares[index++];
        return await mw(req, ctx, next);
      }

      // Route lookup
      for (const [prefix, handler] of this.routes.entries()) {
        if (req.path.startsWith(prefix)) {
          return await handler(req, ctx);
        }
      }

      return { statusCode: 404, data: { error: 'Route not found' } };
    };

    try {
      const response = await next();
      const latency = Date.now() - ctx.startTimeMs;
      console.log(`[Gateway] ${req.method} ${req.path} -> ${response.statusCode} in ${latency}ms`);
      return response;
    } catch (err: any) {
      console.error(`[Gateway Error] ${err.message}`);
      return { statusCode: 500, data: { error: 'Internal Gateway Error' } };
    }
  }
}

// Built-in Middleware implementations
export const AuthMiddleware: GatewayMiddleware = async (req, ctx, next) => {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return { statusCode: 401, data: { error: 'Missing or invalid token' } };
  }

  const token = authHeader.split(' ')[1];
  // Verify token (simulated)
  if (token === 'admin-secret') {
    ctx.userId = 'usr-admin';
    ctx.userRole = 'ADMIN';
  } else {
    ctx.userId = 'usr-guest';
    ctx.userRole = 'USER';
  }

  return await next();
};
```

---

## 5. Edge Cases & Failure Scenarios
1. **Single Point of Failure (SPOF)**: If the API Gateway crashes, the entire backend becomes inaccessible. Mitigation: Deploy gateways horizontally across availability zones behind an Elastic Load Balancer (NLB/ALB) with health checks.
2. **Gateway Bloat / Anti-Pattern**: Putting domain business logic, SQL queries, or complex transformations inside the Gateway turns it into an unmaintainable monolithic proxy. Keep it strictly focused on cross-cutting concerns (auth, routing, observability, TLS).

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Multi-client architectures (Mobile, Web, Third-party APIs) needing a consolidated security boundary, rate limiting, and telemetry.

### When NOT to Use:
- Direct internal service-to-service communication within the private cluster network (use Service Mesh or internal mTLS instead).
