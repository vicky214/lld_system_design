import os

TARGET_DIR = "/home/vicky/Documents/Antigravity/lld/04_Microservices_Architecture_Patterns"
os.makedirs(TARGET_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Decompose_by_Business_Capability.md",
        "title": "Decompose by Business Capability Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Decompose a large monolithic system into autonomous services structured around distinct business domains and business capabilities rather than technical layers.",
        "industry_example": "Amazon E-Commerce Architecture (Separating Order Management, Inventory Fulfillment, Billing, and Recommendation capabilities into independent services).",
        "diagram": """
Client / Frontend
       |
       v
+-------------------------------------------------------------+
|                     API Gateway Router                      |
+-------------------------------------------------------------+
       |                           |                          |
       v                           v                          v
+---------------+          +---------------+          +---------------+
| Order Service |          | Billing Svc   |          | Inventory Svc |
| (Orders, Cart)|          | (Invoices, Tx)|          | (Stock, SKU)  |
+---------------+          +---------------+          +---------------+
       |                           |                          |
       v                           v                          v
[ Order DB ]               [ Billing DB ]             [ Inventory DB ]
""",
        "code": """/**
 * Business Capability Decomposition Pattern
 * Independent Bounded Contexts with Domain Services and Message Contracts
 */

// 1. Order Capability Domain
export interface OrderPlacedEvent {
  orderId: string;
  customerId: string;
  items: Array<{ sku: string; quantity: number; unitPriceCents: number }>;
  totalAmountCents: number;
  timestamp: string;
}

export class OrderCapabilityService {
  constructor(private eventBus: EventBus) {}

  async createOrder(customerId: string, items: Array<{ sku: string; quantity: number; unitPriceCents: number }>): Promise<string> {
    const orderId = `ORD-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    const totalAmountCents = items.reduce((sum, item) => sum + item.quantity * item.unitPriceCents, 0);

    // Save to Order DB (omitted for brevity)
    console.log(`[OrderCapability] Order ${orderId} created for customer ${customerId}`);

    const event: OrderPlacedEvent = {
      orderId,
      customerId,
      items,
      totalAmountCents,
      timestamp: new Date().toISOString()
    };

    await this.eventBus.publish('order.placed', event);
    return orderId;
  }
}

// 2. Inventory Capability Domain
export class InventoryCapabilityService {
  private stockLevels = new Map<string, number>([
    ['SKU-LAPTOP-01', 50],
    ['SKU-MOUSE-02', 120]
  ]);

  constructor(private eventBus: EventBus) {
    this.subscribeEvents();
  }

  private subscribeEvents(): void {
    this.eventBus.subscribe('order.placed', async (payload: OrderPlacedEvent) => {
      await this.reserveInventory(payload.orderId, payload.items);
    });
  }

  async reserveInventory(orderId: string, items: Array<{ sku: string; quantity: number }>): Promise<boolean> {
    // Check all stock availability first (atomic reservation)
    for (const item of items) {
      const current = this.stockLevels.get(item.sku) || 0;
      if (current < item.quantity) {
        console.error(`[InventoryCapability] Stockout for SKU ${item.sku} on order ${orderId}`);
        await this.eventBus.publish('inventory.reservation_failed', { orderId, reason: `Insufficient stock for ${item.sku}` });
        return false;
      }
    }

    // Deduct stock
    for (const item of items) {
      const current = this.stockLevels.get(item.sku)!;
      this.stockLevels.set(item.sku, current - item.quantity);
    }

    console.log(`[InventoryCapability] Inventory successfully reserved for order ${orderId}`);
    await this.eventBus.publish('inventory.reserved', { orderId });
    return true;
  }
}

// 3. Billing Capability Domain
export class BillingCapabilityService {
  constructor(private eventBus: EventBus) {
    this.subscribeEvents();
  }

  private subscribeEvents(): void {
    this.eventBus.subscribe('inventory.reserved', async (payload: { orderId: string }) => {
      await this.chargeCustomer(payload.orderId);
    });
  }

  async chargeCustomer(orderId: string): Promise<void> {
    console.log(`[BillingCapability] Successfully charged payment method for order ${orderId}`);
    await this.eventBus.publish('billing.payment_captured', { orderId, transactionId: `TX-${Date.now()}` });
  }
}

// Lightweight in-memory broker contract for demonstration
export class EventBus {
  private listeners = new Map<string, Array<(payload: any) => Promise<void>>>();

  subscribe(topic: string, handler: (payload: any) => Promise<void>): void {
    if (!this.listeners.has(topic)) this.listeners.set(topic, []);
    this.listeners.get(topic)!.push(handler);
  }

  async publish(topic: string, payload: any): Promise<void> {
    const handlers = this.listeners.get(topic) || [];
    for (const handler of handlers) {
      await handler(payload);
    }
  }
}
""",
        "edge_cases": """1. **Cross-Capability Transaction Failures**: When one business domain succeeds (e.g. Order created) but another fails (e.g. Inventory unavailable), traditional ACID two-phase locks across services degrade availability. Mitigation: Use Saga Orchestration or Choreography with compensating undo actions.
2. **Data Duplication & Synchronization**: Shared concepts (e.g. Customer Name and Address) needed by both Order and Shipping. Mitigation: Event-driven replication with eventual consistency and bounded context domain models.
3. **Misaligned Domain Boundaries**: Slicing along technical layers (UI service, Database service) instead of business capabilities leads to 'distributed monolith' anti-pattern where every change requires synchronized deployment across all services.""",
        "tradeoffs": """### When to Use:
- Large, multi-team engineering organizations requiring autonomous deployments and fast product release velocity.
- Complex enterprise software where business capabilities evolve at different rates (e.g., Billing changes rarely, Catalog/Search changes daily).

### When NOT to Use:
- Early-stage startups where domain boundaries are still ambiguous and constantly shifting.
- Small engineering teams (1-5 devs) where operational overhead of multiple deployments and network RPC outweighs organizational benefits."""
    },
    {
        "filename": "02_Decompose_by_Subdomain_DDD.md",
        "title": "Decompose by Subdomain (Domain-Driven Design) Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Decompose a monolithic system by analyzing Domain-Driven Design (DDD) subdomains: Core Domain (competitive advantage), Supporting Domain (enhances core), and Generic Domain (off-the-shelf/commodity capability).",
        "industry_example": "Uber Transportation Platform (Core: Dynamic Dispatch & Surge Pricing Algorithm; Supporting: Driver Onboarding; Generic: Invoicing, SMS OTP notification via Twilio).",
        "diagram": """
+------------------------------------------------------------------------+
|                              UBER DOMAIN                               |
+------------------------------------------------------------------------+
       |                                |                       |
       v                                v                       v
+--------------------+        +--------------------+  +--------------------+
|    CORE DOMAIN     |        | SUPPORTING DOMAIN  |  |   GENERIC DOMAIN   |
| (Proprietary IP)   |        | (Complementary)    |  | (Commodity Svc)    |
| - Surge Pricing    |        | - Driver KYC       |  | - Auth / IAM       |
| - Dispatch Match   |        | - Vehicle Audit    |  | - SMS Notification |
| - Realtime Routing |        | - Trip History     |  | - Payment Gateway  |
+--------------------+        +--------------------+  +--------------------+
""",
        "code": """/**
 * DDD Subdomain Decomposition Pattern
 * Clean separation between Core, Supporting, and Generic Subdomains
 */

// 1. GENERIC SUBDOMAIN (Generic capabilities, can even be SaaS integrations)
export interface NotificationService {
  sendSMS(phone: string, message: string): Promise<boolean>;
  sendEmail(to: string, subject: string, body: string): Promise<boolean>;
}

export class GenericNotificationService implements NotificationService {
  async sendSMS(phone: string, message: string): Promise<boolean> {
    console.log(`[GenericDomain:SMS] Sent to ${phone}: "${message}"`);
    return true;
  }
  async sendEmail(to: string, subject: string, body: string): Promise<boolean> {
    console.log(`[GenericDomain:Email] Sent to ${to}: ${subject}`);
    return true;
  }
}

// 2. SUPPORTING SUBDOMAIN (Business context specific, but not core competitive moat)
export interface DriverProfile {
  driverId: string;
  licenseNumber: string;
  isBackgroundChecked: boolean;
  vehicleStatus: 'INSPECTED' | 'PENDING' | 'REJECTED';
}

export class DriverOnboardingService {
  private drivers = new Map<string, DriverProfile>();

  async verifyAndApprove(driverId: string, license: string): Promise<DriverProfile> {
    const profile: DriverProfile = {
      driverId,
      licenseNumber: license,
      isBackgroundChecked: true,
      vehicleStatus: 'INSPECTED'
    };
    this.drivers.set(driverId, profile);
    console.log(`[SupportingDomain:DriverOnboarding] Approved driver ${driverId}`);
    return profile;
  }

  isDriverEligible(driverId: string): boolean {
    const d = this.drivers.get(driverId);
    return !!d && d.isBackgroundChecked && d.vehicleStatus === 'INSPECTED';
  }
}

// 3. CORE DOMAIN (Proprietary algorithms, competitive moat, custom engineered)
export interface GeoLocation {
  lat: number;
  lng: number;
}

export class CoreDispatchMatchingEngine {
  constructor(
    private driverService: DriverOnboardingService,
    private notifier: NotificationService
  ) {}

  calculateSurgeMultiplier(demandCount: number, supplyCount: number): number {
    if (supplyCount === 0) return 3.0; // Max surge cap
    const ratio = demandCount / supplyCount;
    if (ratio > 2.0) return 2.2;
    if (ratio > 1.2) return 1.5;
    return 1.0;
  }

  findOptimalDriver(
    riderLocation: GeoLocation,
    availableDrivers: Array<{ driverId: string; location: GeoLocation }>
  ): string | null {
    // Only dispatch to vetted drivers from the supporting domain
    const eligibleDrivers = availableDrivers.filter(d => 
      this.driverService.isDriverEligible(d.driverId)
    );

    if (eligibleDrivers.length === 0) return null;

    // Core proprietary geospatial nearest-neighbor algorithm
    let bestDriverId = eligibleDrivers[0].driverId;
    let minDistance = Infinity;

    for (const d of eligibleDrivers) {
      const dist = Math.hypot(d.location.lat - riderLocation.lat, d.location.lng - riderLocation.lng);
      if (dist < minDistance) {
        minDistance = dist;
        bestDriverId = d.driverId;
      }
    }

    this.notifier.sendSMS('+15550199', `Dispatch match confirmed with driver ${bestDriverId}`);
    return bestDriverId;
  }
}
""",
        "edge_cases": """1. **Domain Boundary Leakage**: When developers mix generic domain logic (e.g., raw SQL parsing or Stripe webhook handling) directly inside the Core algorithmic domain model. Mitigation: Enforce strict hexagonal/ports-and-adapters architecture.
2. **Context Mapping Conflicts**: The term 'Account' means completely different entities to Billing (ledger balance), Identity (credentials and scopes), and Risk (fraud score). Mitigation: Bounded contexts with explicit anti-corruption layers (ACLs).""",
        "tradeoffs": """### When to Use:
- Complex business ecosystems where allocating engineering talent needs strategic focus (spend senior algorithm engineering on Core Domain; leverage off-the-shelf or junior teams for Generic/Supporting Domains).

### When NOT to Use:
- Simple CRUD apps or systems with no significant algorithmic or distinct domain boundaries."""
    },
    {
        "filename": "03_Strangler_Fig_Pattern.md",
        "title": "Strangler Fig Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Incrementally migrate a monolithic application by gradually replacing specific features with microservices behind an intercepting routing facade until the old monolith is decommissioned.",
        "industry_example": "Shopify migrating its monolithic Ruby on Rails application to modular microservices and GraphQL backend services without downtime or risky 'big-bang' rewrites.",
        "diagram": """
                Incoming HTTP Request
                          |
                          v
         +----------------------------------+
         |      Strangler Reverse Proxy     |
         |    (Route Interceptor / Gateway) |
         +----------------------------------+
                 /                  \\
 (Legacy Routes)/                    \\(Migrated Routes)
               v                      v
     +-------------------+    +--------------------+
     | Legacy Monolith   |    | New Microservice   |
     | - Auth (Old)      |    | - Payments (V2)    |
     | - Cart (Old)      |    | - Orders (V2)      |
     +-------------------+    +--------------------+
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Dual-Write Consistency**: When migrating an active write path, writes must be dual-written or synchronized back to the legacy database to keep legacy reporting and dependent tables consistent during transition.
2. **Session / Authentication Sharing**: Legacy monolithic cookies or session tokens must be validated seamlessly by both the legacy server and new microservices (e.g., via a JWT conversion sidecar or token translation layer).
3. **Rollback Safety**: If the new microservice fails or has data bugs, the reverse proxy must instantly down-weight traffic to 0% back to the monolith without code redeployment.""",
        "tradeoffs": """### When to Use:
- Safely modernizing high-revenue production monoliths where a complete big-bang rewrite poses existential business risks.

### When NOT to Use:
- Greenfield projects or systems with low complexity where rewriting the entire service in weeks is faster than building routing facades and dual-write synchronizers."""
    },
    {
        "filename": "04_API_Gateway_Pattern.md",
        "title": "API Gateway Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Provide a single, unified entry point for all client applications that handles routing, protocol translation, rate limiting, authentication, and request aggregation across backend microservices.",
        "industry_example": "Netflix Zuul / Spring Cloud Gateway handling billions of daily device requests, terminating SSL, enforcing OAuth JWT verification, and routing to hundreds of internal microservices.",
        "diagram": """
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
""",
        "code": """/**
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
""",
        "edge_cases": """1. **Single Point of Failure (SPOF)**: If the API Gateway crashes, the entire backend becomes inaccessible. Mitigation: Deploy gateways horizontally across availability zones behind an Elastic Load Balancer (NLB/ALB) with health checks.
2. **Gateway Bloat / Anti-Pattern**: Putting domain business logic, SQL queries, or complex transformations inside the Gateway turns it into an unmaintainable monolithic proxy. Keep it strictly focused on cross-cutting concerns (auth, routing, observability, TLS).""",
        "tradeoffs": """### When to Use:
- Multi-client architectures (Mobile, Web, Third-party APIs) needing a consolidated security boundary, rate limiting, and telemetry.

### When NOT to Use:
- Direct internal service-to-service communication within the private cluster network (use Service Mesh or internal mTLS instead)."""
    },
    {
        "filename": "05_Backend_For_Frontend_BFF.md",
        "title": "Backend for Frontend (BFF) Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Create separate specialized API gateways tailored specifically to the requirements of different client frontend interfaces (e.g., Mobile App vs Desktop Web vs Smart TV) rather than one generic catch-all gateway.",
        "industry_example": "SoundCloud & Netflix (Mobile BFF strips out heavy payload fields to conserve 4G data and battery; Desktop BFF aggregates rich metadata and analytics; TV BFF formats optimized grid views).",
        "diagram": """
Mobile App                  Web Desktop Browser
     |                              |
     v                              v
+---------------+             +---------------+
|   Mobile BFF  |             |    Web BFF    |
| (Lightweight, |             | (Rich payload,|
|  Aggregated)  |             |  High bandw.) |
+---------------+             +---------------+
        \\                             /
         v                           v
  +-----------------------------------------+
  | Downstream Microservices                |
  | [User Svc] [Catalog Svc] [Playback Svc] |
  +-----------------------------------------+
""",
        "code": """/**
 * Backend For Frontend (BFF) Pattern
 * Tailored client payloads minimizing roundtrips and bandwidth
 */

export interface RawCatalogItem {
  id: string;
  title: string;
  hdPosterUrl: string;
  uhdPosterUrl: string;
  synopsis: string;
  cast: string[];
  producerNotes: string;
  analyticsTokens: string[];
}

export class DownstreamCatalogService {
  async fetchMedia(id: string): Promise<RawCatalogItem> {
    return {
      id,
      title: 'Interstellar Odyssey',
      hdPosterUrl: 'https://cdn.example.com/poster-hd.jpg',
      uhdPosterUrl: 'https://cdn.example.com/poster-4k.jpg',
      synopsis: 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.',
      cast: ['Actor A', 'Actor B', 'Actor C'],
      producerNotes: 'Production budget $150M. Shot on IMAX 70mm.',
      analyticsTokens: ['trk_88291', 'trk_99120']
    };
  }
}

// 1. Mobile BFF: Optimized for low mobile bandwidth and small screen
export class MobileBff {
  constructor(private catalog: DownstreamCatalogService) {}

  async getMediaScreen(id: string) {
    const raw = await this.catalog.fetchMedia(id);
    return {
      id: raw.id,
      title: raw.title,
      // Provide compressed HD image only, omit 4k
      poster: raw.hdPosterUrl,
      shortSynopsis: raw.synopsis.slice(0, 60) + '...',
      castCount: raw.cast.length
      // internal producerNotes and analytics are stripped out!
    };
  }
}

// 2. Desktop Web BFF: High bandwidth, full cast details, 4K artwork
export class WebDesktopBff {
  constructor(private catalog: DownstreamCatalogService) {}

  async getMediaScreen(id: string) {
    const raw = await this.catalog.fetchMedia(id);
    return {
      id: raw.id,
      title: raw.title,
      backdrop: raw.uhdPosterUrl,
      fullSynopsis: raw.synopsis,
      topBilledCast: raw.cast,
      hasProductionNotes: !!raw.producerNotes
    };
  }
}
""",
        "edge_cases": """1. **Code Duplication Across BFFs**: Different BFFs often need identical authentication, logging, and error handling. Mitigation: Share core npm libraries/middlewares across BFF codebases while maintaining independent deployment pipelines.
2. **BFF Team Ownership Silos**: If frontend developers don't own the BFF and backend teams build them, communication bottlenecks remain. The BFF should ideally be owned and deployed by the respective frontend team.""",
        "tradeoffs": """### When to Use:
- Multi-platform products with radically different user experiences, network constraints, or screen form factors.

### When NOT to Use:
- Single client applications (e.g. only a desktop web application exists). A standard API Gateway is sufficient."""
    },
    {
        "filename": "06_Service_Mesh_Pattern.md",
        "title": "Service Mesh Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Decouple service-to-service communication logic (mTLS encryption, dynamic service discovery, load balancing, circuit breaking, traffic shaping) into a dedicated sidecar proxy infrastructure layer.",
        "industry_example": "Istio / Envoy proxy deployed across Kubernetes clusters at Lyft, Pinterest, and Google Cloud, transparently securing polyglot services without code modifications.",
        "diagram": """
   +-----------------------+              +-----------------------+
   | Pod A (Order Service) |              | Pod B (Payment Svc)   |
   |  +-----------------+  |              |  +-----------------+  |
   |  | Service App     |  |              |  | Service App     |  |
   |  +-----------------+  |              |  +-----------------+  |
   |          | localhost  |              |          ^ localhost  |
   |          v            |              |          |            |
   |  +-----------------+  |   mTLS over  |  +-----------------+  |
   |  | Envoy Sidecar   |==|==============|=>| Envoy Sidecar   |  |
   |  +-----------------+  |    Network   |  +-----------------+  |
   +-----------------------+              +-----------------------+
              ^                                      ^
              |               Control Plane          |
              +--------------[ Istiod / Kube ]-------+
""",
        "code": """/**
 * Service Mesh Sidecar Proxy Emulation
 * Transparent out-of-process traffic routing, mTLS check, and fault injection
 */

export interface MeshPacket {
  traceId: string;
  sourceService: string;
  targetService: string;
  encryptedWithMtls: boolean;
  payload: any;
}

export class EnvoySidecarProxy {
  private serviceRegistry = new Map<string, string[]>([
    ['payment-service', ['10.0.1.12:8080', '10.0.1.13:8080', '10.0.1.14:8080']]
  ]);
  private roundRobinIdx = 0;

  constructor(private serviceName: string) {}

  async sendOutboundRequest(targetService: string, payload: any): Promise<any> {
    console.log(`[MeshSidecar:${this.serviceName}] Intercepted outbound request to: ${targetService}`);

    // 1. Service Discovery & Client-side Load Balancing
    const endpoints = this.serviceRegistry.get(targetService);
    if (!endpoints || endpoints.length === 0) {
      throw new Error(`[Mesh] No healthy instances found for ${targetService}`);
    }
    const chosenEndpoint = endpoints[this.roundRobinIdx % endpoints.length];
    this.roundRobinIdx++;

    // 2. Mutual TLS (mTLS) Handshake & Packet Wrapping
    const packet: MeshPacket = {
      traceId: `trace-${Math.random().toString(36).substr(2, 9)}`,
      sourceService: this.serviceName,
      targetService,
      encryptedWithMtls: true,
      payload
    };

    console.log(`[MeshSidecar:${this.serviceName}] Routing via mTLS to ${chosenEndpoint} (Trace: ${packet.traceId})`);
    return await this.simulateNetworkTransit(chosenEndpoint, packet);
  }

  private async simulateNetworkTransit(endpoint: string, packet: MeshPacket): Promise<any> {
    // In production, Envoy handles TCP socket pooling, retries, and rate limiting
    return { status: 'OK', destination: endpoint, echo: packet.payload };
  }
}
""",
        "edge_cases": """1. **Latency Overhead**: Every hop incurs two sidecar proxy traversals (outbound Envoy -> network -> inbound Envoy), adding 1-3ms per hop. For extreme low-latency systems (e.g. High Frequency Trading), sidecars may be prohibitive.
2. **Control Plane Saturation**: If hundreds of pods restart simultaneously, Istio/Envoy control plane can experience CPU spikes pushing updated xDS configurations.
3. **Debugging Complexity**: Packet issues can stem from application code, Envoy config, iptables redirects, or TLS certificate expiration.""",
        "tradeoffs": """### When to Use:
- Polyglot microservice clusters (Go, Java, Python, Node) requiring zero-trust security (mTLS), standardized telemetry, and canary traffic routing without touching app code.

### When NOT to Use:
- Small microservice footprints (<10 services) where running an Envoy sidecar next to every container increases cloud memory costs and cluster maintenance disproportionately."""
    },
    {
        "filename": "07_Publish_Subscribe_Pattern.md",
        "title": "Publish-Subscribe (Pub/Sub) Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Enable asynchronous, loosely coupled communication where message producers (publishers) broadcast events to topics without knowing which or how many consumers (subscribers) will receive them.",
        "industry_example": "Apache Kafka or RabbitMQ at LinkedIn & Uber (publishing 'RiderRequested' or 'ConnectionAccepted' consumed concurrently by Notification, Billing, Driver Search, and ML Data Pipelines).",
        "diagram": """
                       +-------------------+
                       |    Publisher      |
                       |  (Order Service)  |
                       +-------------------+
                                 |
                          publish('OrderCreated')
                                 v
               +-----------------------------------+
               |       Message Broker / Kafka      |
               |       Topic: 'orders.v1'          |
               +-----------------------------------+
                     /           |           \\
                    v            v            v
           +-----------+   +-----------+   +-----------+
           | Consumer A|   | Consumer B|   | Consumer C|
           | (Billing) |   | (Notify)  |   | (Analytics|
           +-----------+   +-----------+   +-----------+
""",
        "code": """/**
 * Production Pub/Sub Event Pattern
 * Topic partitioning, consumer groups, and idempotency tracking
 */

export interface DomainEvent<T = any> {
  eventId: string;
  eventType: string;
  aggregateId: string;
  data: T;
  publishedAt: string;
}

export type EventHandler<T> = (event: DomainEvent<T>) => Promise<void>;

export class PubSubMessageBroker {
  private topicSubscribers = new Map<string, Array<{ group: string; handler: EventHandler<any> }>>();
  private processedMessageIds = new Set<string>();

  subscribe<T>(topic: string, group: string, handler: EventHandler<T>): void {
    if (!this.topicSubscribers.has(topic)) {
      this.topicSubscribers.set(topic, []);
    }
    this.topicSubscribers.get(topic)!.push({ group, handler });
    console.log(`[Broker] Registered consumer group '${group}' on topic '${topic}'`);
  }

  async publish<T>(topic: string, event: DomainEvent<T>): Promise<void> {
    console.log(`[Broker:Publish] Topic '${topic}', EventId: ${event.eventId}, Type: ${event.eventType}`);
    const subscribers = this.topicSubscribers.get(topic) || [];

    // Each consumer group processes the message once (competing consumers pattern within group)
    const grouped = new Map<string, EventHandler<any>[]>();
    for (const sub of subscribers) {
      if (!grouped.has(sub.group)) grouped.set(sub.group, []);
      grouped.get(sub.group)!.push(sub.handler);
    }

    for (const [groupName, handlers] of grouped.entries()) {
      // Pick one consumer instance per partition/group (Round-robin / hash)
      const selectedHandler = handlers[0];
      const consumerKey = `${groupName}:${event.eventId}`;

      if (this.processedMessageIds.has(consumerKey)) {
        console.warn(`[Broker:Idempotency] Duplicate message ${event.eventId} discarded for group ${groupName}`);
        continue;
      }

      try {
        await selectedHandler(event);
        this.processedMessageIds.add(consumerKey);
      } catch (err: any) {
        console.error(`[Broker:Error] Handler in group ${groupName} failed: ${err.message}`);
        // Route to DLQ in production
      }
    }
  }
}
""",
        "edge_cases": """1. **At-Least-Once Delivery & Duplicates**: Network retries will deliver duplicate events. Consumers MUST be strictly idempotent using unique `eventId` checks or database upsert operations.
2. **Out-of-Order Message Processing**: If message partitions are not keyed by aggregate ID (e.g. orderId), consumer A could process 'OrderDelivered' before consumer B processes 'OrderCreated'. Partition by Aggregate Key!
3. **Poison Pill Messages**: A malformed event causes consumer crashes in an infinite loop. Mitigation: Dead-Letter Queue (DLQ) after 3-5 failed retry attempts.""",
        "tradeoffs": """### When to Use:
- Event-driven microservices where producers must remain decoupled from downstream side effects and new consumers can be plugged in without touching producers.

### When NOT to Use:
- Synchronous workflows requiring an immediate return value to the user (e.g., verifying credit card CVV and returning immediate validation error)."""
    },
    {
        "filename": "08_Asynchronous_Request_Reply.md",
        "title": "Asynchronous Request-Reply Pattern",
        "category": "Microservices Architecture Patterns",
        "intent": "Decouple long-running synchronous HTTP requests by returning an immediate HTTP 202 Accepted status with a polling status URL or webhook callback reference while processing proceeds asynchronously in the background.",
        "industry_example": "Stripe Export API, AWS Async Video Transcoder, and OpenAI Batch API (submitting a multi-gigabyte financial CSV export returns a job token; client polls `/v1/jobs/{id}` until status is COMPLETED).",
        "diagram": """
Client                             API Server                   Worker / Queue
  |                                    |                              |
  |-- 1. POST /api/v1/video/transcode->|                              |
  |                                    |-- 2. Push job to queue ----->|
  |<- 3. 202 Accepted (Location: /jobs)|                              |
  |      { jobId: "job-123" }          |                              |
  |                                    |                              |-- 3. Transcode 4K video...
  |-- 4. GET /api/v1/jobs/job-123 ---->|                              |   (Takes 5 minutes)
  |<- 5. 200 OK { status: "RUNNING" } -|                              |
  |                                    |                              |
  |                                    |<-- 6. Job Completed Event ---|
  |-- 7. GET /api/v1/jobs/job-123 ---->|                              |
  |<- 8. 200 OK { status: "COMPLETED", |                              |
  |      downloadUrl: "https://..." } -|                              |
""",
        "code": """/**
 * Asynchronous Request-Reply Pattern
 * Handling long-running tasks with polling tokens and async background execution
 */

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface AsyncJob<T = any> {
  jobId: string;
  status: JobStatus;
  progressPercent: number;
  result?: T;
  error?: string;
  createdAt: number;
  updatedAt: number;
}

export class AsyncRequestReplyService {
  private jobStore = new Map<string, AsyncJob>();

  async submitJob(taskPayload: { videoUrl: string; targetResolution: string }): Promise<{ jobId: string; statusUrl: string }> {
    const jobId = `job-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
    
    const newJob: AsyncJob = {
      jobId,
      status: 'PENDING',
      progressPercent: 0,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    this.jobStore.set(jobId, newJob);

    // Trigger async background processing without awaiting
    this.processJobAsync(jobId, taskPayload).catch(err => {
      console.error(`[Worker] Unhandled failure on job ${jobId}: ${err.message}`);
    });

    console.log(`[AsyncRequestReply] Job ${jobId} accepted. Returning 202 to client.`);
    return {
      jobId,
      statusUrl: `/api/v1/jobs/${jobId}`
    };
  }

  getJobStatus(jobId: string): AsyncJob | null {
    return this.jobStore.get(jobId) || null;
  }

  private async processJobAsync(jobId: string, payload: any): Promise<void> {
    const job = this.jobStore.get(jobId)!;
    job.status = 'PROCESSING';
    job.updatedAt = Date.now();

    // Emulate long multi-stage processing
    for (let progress = 20; progress <= 100; progress += 40) {
      await new Promise(resolve => setTimeout(resolve, 50));
      job.progressPercent = progress;
      job.updatedAt = Date.now();
      console.log(`[Worker] Job ${jobId} progress: ${progress}%`);
    }

    job.status = 'COMPLETED';
    job.result = {
      downloadUrl: `https://storage.example.com/rendered/${jobId}.mp4`,
      filesizeBytes: 524288000
    };
    job.updatedAt = Date.now();
    console.log(`[Worker] Job ${jobId} finished successfully.`);
  }
}
""",
        "edge_cases": """1. **Client Polling Stampede**: Clients aggressive polling every 100ms can overwhelm the API gateway. Mitigation: Include `Retry-After: 10` headers in HTTP 202 responses or provide WebSocket/Server-Sent Events (SSE) alternative push channels.
2. **Worker Node Termination During Job Execution**: If the worker pod crashes mid-execution, the job status remains stuck in `PROCESSING`. Mitigation: Heartbeat timestamps and an orphaned job sweeper worker to re-enqueue.
3. **Job Store Retention**: Accumulation of completed job records wastes memory/disk. Implement TTL auto-expiry (e.g., Redis EXPIRE or DynamoDB TTL) after 24 hours.""",
        "tradeoffs": """### When to Use:
- Long operations taking more than 2-3 seconds (batch report exports, video encoding, AI model inferences, ledger reconciliations) where HTTP timeouts would occur.

### When NOT to Use:
- Fast read/write queries (< 200ms) where traditional synchronous request-response is simpler and more responsive for the user."""
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
    print("[Microservices] Successfully generated all 8 patterns.")
