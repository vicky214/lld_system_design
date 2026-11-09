# Chain of Responsibility Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Avoid coupling the sender of a request to its receiver by giving more than one object a chance to handle the request. Chain the receiving objects and pass the request along the chain until an object handles it.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
In HTTP servers and workflow engines, incoming requests must pass through sequential validation checks: IP blacklists, authentication tokens, rate limits, schema validation, and audit logging. Hardcoding all these checks into a single giant function creates unmaintainable spaghetti code.

### Real-World Industry Example:
HTTP API Request Security & Validation Filter Pipeline (Express/Koa Middleware). Each link in the chain verifies one concern (IP Firewall -> Rate Limiter -> JWT Authentication -> JSON Schema Validation) and decides whether to halt the request or call `next()`.

---

## 3. Architecture & Visual Flow Diagram
```
[ Incoming Request ]
         │
         ▼
+---------------------+
|  IpBlacklistFilter  | ──(Blocked)──► Reject 403 Forbidden
+---------------------+
         │ (next)
         ▼
+---------------------+
|  RateLimiterFilter  | ──(Exceeded)─► Reject 429 Too Many Requests
+---------------------+
         │ (next)
         ▼
+---------------------+
|   JwtAuthFilter     | ──(Invalid)──► Reject 401 Unauthorized
+---------------------+
         │ (next)
         ▼
+---------------------+
|   BusinessHandler   | ─────────────► Return 200 OK (Success)
+---------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface HttpRequest {
  ip: string;
  token?: string;
  body: any;
  user?: { id: string; role: string };
}

export interface HttpResponse {
  status: number;
  body: any;
}

// 1. Handler Interface
export abstract class AbstractMiddlewareHandler {
  private nextHandler: AbstractMiddlewareHandler | null = null;

  public setNext(handler: AbstractMiddlewareHandler): AbstractMiddlewareHandler {
    this.nextHandler = handler;
    return handler; // Allows fluent chaining: a.setNext(b).setNext(c)
  }

  public async handle(req: HttpRequest): Promise<HttpResponse | null> {
    if (this.nextHandler) {
      return this.nextHandler.handle(req);
    }
    return null;
  }
}

// 2. Concrete Handlers
export class IpBlacklistHandler extends AbstractMiddlewareHandler {
  private blacklistedIps = new Set(["192.168.1.100", "10.0.0.99"]);

  async handle(req: HttpRequest): Promise<HttpResponse | null> {
    if (this.blacklistedIps.has(req.ip)) {
      console.log(`[IpBlacklist] Blocked malicious IP: ${req.ip}`);
      return { status: 403, body: { error: "Access Denied: IP Blacklisted" } };
    }
    return super.handle(req);
  }
}

export class RateLimiterHandler extends AbstractMiddlewareHandler {
  private requestCounts = new Map<string, number>();

  async handle(req: HttpRequest): Promise<HttpResponse | null> {
    const current = (this.requestCounts.get(req.ip) || 0) + 1;
    this.requestCounts.set(req.ip, current);

    if (current > 5) {
      console.log(`[RateLimiter] Rate limit exceeded for IP: ${req.ip}`);
      return { status: 429, body: { error: "Too Many Requests" } };
    }
    return super.handle(req);
  }
}

export class JwtAuthenticationHandler extends AbstractMiddlewareHandler {
  async handle(req: HttpRequest): Promise<HttpResponse | null> {
    if (!req.token || req.token !== "valid_bearer_token") {
      console.log(`[Auth] Missing or invalid bearer token`);
      return { status: 401, body: { error: "Unauthorized: Invalid JWT" } };
    }
    req.user = { id: "usr_4829", role: "ADMIN" };
    return super.handle(req);
  }
}

export class BusinessControllerHandler extends AbstractMiddlewareHandler {
  async handle(req: HttpRequest): Promise<HttpResponse> {
    console.log(`[Controller] Executing business transaction for user ${req.user?.id}`);
    return { status: 200, body: { message: "Order processed successfully!" } };
  }
}

// --- Usage ---
// Assembling the chain
const chain = new IpBlacklistHandler();
chain
  .setNext(new RateLimiterHandler())
  .setNext(new JwtAuthenticationHandler())
  .setNext(new BusinessControllerHandler());

async function run() {
  // Test valid request
  const validReq: HttpRequest = { ip: "127.0.0.1", token: "valid_bearer_token", body: {} };
  const res1 = await chain.handle(validReq);
  console.log("Valid Request Response:", res1);

  // Test unauthorized request
  const unauthReq: HttpRequest = { ip: "127.0.0.1", token: "bad_token", body: {} };
  const res2 = await chain.handle(unauthReq);
  console.log("Unauth Request Response:", res2);
}

run();
```

---

## 5. Edge Cases & Failure Handling
- **Unterminated Chain**: If no handler in the chain returns a response and there is no default fallback, the request hangs or returns null. Always attach a final default handler or router.\n- **Circular References in Chains**: If handler A sets handler B as next, and handler B sets handler A, an infinite loop will crash the process with stack overflow.\n- **Asynchronous Exceptions**: An unhandled exception in one link can halt execution of subsequent links without cleanup.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When more than one object may handle a request, and the handler isn't known a priori.\n- When you want to issue a request to one of several objects without specifying the receiver explicitly.\n- Express/Koa middleware, validation interceptors, event bubbling systems.

### When NOT to Use / Anti-patterns:
- When every request must always be handled by exactly one deterministic function.
