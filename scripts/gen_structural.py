import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../02_Structural_Patterns"))
os.makedirs(BASE_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Adapter_Pattern.md",
        "title": "Adapter Pattern",
        "category": "Structural Pattern",
        "intent": "Convert the interface of a class into another interface clients expect. Adapter lets classes work together that couldn't otherwise because of incompatible interfaces.",
        "problem": "Modern cloud services consume RESTful JSON interfaces, but legacy banking partners and mainframe systems only expose XML/SOAP protocols with archaic parameter conventions. Rewriting core business logic to accommodate third-party quirks couples the domain model to external vendors.",
        "scenario": "Modern Fintech Payment Gateway integrating with a Legacy Core Banking Host. The internal checkout engine uses standardized PaymentProcessor interfaces ({ amountInCents, currency, token }), while the legacy host expects raw XML strings with merchant terminal IDs and date-formatted payloads.",
        "diagram": """
+-------------------------------------------------------+
|                    PaymentProcessor                   | (Target Interface)
+-------------------------------------------------------+
| + charge(amount: number, token: string): Promise<res> |
+-------------------------------------------------------+
                           ▲
                           │
+-------------------------------------------------------+
|                LegacyBankSoapAdapter                  | (Adapter)
+-------------------------------------------------------+
| - legacySoapClient: LegacyBankSoapHost               |
+-------------------------------------------------------+
| + charge(amount, token): Promise<res>                 |
|   1. Transform JSON -> XML                            |
|   2. Call legacySoapClient.executeIsoWireTransfer()   |
|   3. Transform XML response -> Standardized JSON      |
+-------------------------------------------------------+
                           │
                           ▼
+-------------------------------------------------------+
|                 LegacyBankSoapHost                    | (Adaptee)
+-------------------------------------------------------+
| + executeIsoWireTransfer(xmlPayload: string): string  |
+-------------------------------------------------------+
""",
        "code": """export interface PaymentResult {
  transactionId: string;
  status: "SUCCESS" | "DECLINED" | "ERROR";
  amountProcessed: number;
}

// 1. Target Interface expected by modern microservices
export interface PaymentProcessor {
  charge(amountCents: number, currency: string, paymentToken: string): Promise<PaymentResult>;
}

// 2. Adaptee: Legacy Banking Host (Incompatible XML/SOAP Interface)
export class LegacyBankSoapHost {
  public executeIsoWireTransfer(xmlPayload: string): string {
    console.log("[Legacy SOAP Host] Received raw XML wire message:");
    console.log(xmlPayload);
    // Returns simulated XML response
    return `
      <TransferResponse>
        <Status>00_APPROVED</Status>
        <ReferenceNum>TXN-LEGACY-98214</ReferenceNum>
        <SettledMinorUnits>5000</SettledMinorUnits>
      </TransferResponse>
    `;
  }
}

// 3. Adapter: Bridges modern PaymentProcessor to LegacyBankSoapHost
export class LegacyBankSoapAdapter implements PaymentProcessor {
  private soapHost: LegacyBankSoapHost;

  constructor(soapHost: LegacyBankSoapHost) {
    this.soapHost = soapHost;
  }

  async charge(amountCents: number, currency: string, paymentToken: string): Promise<PaymentResult> {
    // A. Translate JSON domain parameters to SOAP XML payload
    const xmlPayload = `
      <PaymentRequest>
        <TerminalId>TERM_NY_01</TerminalId>
        <AccountToken>${paymentToken}</AccountToken>
        <Currency>${currency}</Currency>
        <AmountUnits>${amountCents}</AmountUnits>
        <Timestamp>${new Date().toISOString()}</Timestamp>
      </PaymentRequest>
    `.trim();

    // B. Invoke incompatible third-party system
    const rawXmlResponse = this.soapHost.executeIsoWireTransfer(xmlPayload);

    // C. Parse raw response back to standardized modern interface
    const isApproved = rawXmlResponse.includes("<Status>00_APPROVED</Status>");
    const refMatch = rawXmlResponse.match(/<ReferenceNum>(.*?)<\\/ReferenceNum>/);
    const transactionId = refMatch ? refMatch[1] : `TXN-UNKNOWN-${Date.now()}`;

    return {
      transactionId,
      status: isApproved ? "SUCCESS" : "DECLINED",
      amountProcessed: amountCents / 100,
    };
  }
}

// --- Usage ---
const legacyHost = new LegacyBankSoapHost();
const paymentGateway: PaymentProcessor = new LegacyBankSoapAdapter(legacyHost);

// Domain layer calls standardized interface with zero knowledge of SOAP/XML
paymentGateway.charge(5000, "USD", "tok_visa_4242").then((result) => {
  console.log("[Checkout Service] Charge processed:", result);
});
""",
        "edgeCases": [
            "**Data Truncation & Type Incompatibilities**: The modern interface may support 64-bit precision numbers while the legacy host truncates to 32-bit floats. The adapter must validate numeric bounds before passing payloads.",
            "**Error Code Misinterpretation**: Legacy hosts often return HTTP 200 OK containing an embedded `<ErrorCode>14_INSUFFICIENT_FUNDS</ErrorCode>`. The adapter must parse embedded error structures and throw domain exceptions.",
            "**Two-Way Adapters**: When both systems need to invoke each other interchangeably, two-way adapter patterns must be implemented."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When integrating third-party libraries or legacy services whose interface does not match your internal standards.",
                "When creating a reusable SDK that must support multiple vendor implementations without altering client code."
            ],
            "whenNotToUse": [
                "When you have full control over both codebases (refactoring the target class directly is cleaner than introducing adapter layers)."
            ]
        }
    },
    {
        "filename": "02_Bridge_Pattern.md",
        "title": "Bridge Pattern",
        "category": "Structural Pattern",
        "intent": "Decouple an abstraction from its implementation so that the two can vary independently, avoiding a Cartesian product explosion of subclasses.",
        "problem": "If you have 3 payment client platforms (Web, Mobile App, POS Terminal) and 3 payment providers (Stripe, PayPal, Adyen), traditional inheritance forces you to create 9 subclasses (`WebStripePayment`, `WebPayPalPayment`, `MobileStripePayment`, etc.). Adding 1 new provider requires creating subclasses for every single platform.",
        "scenario": "Cross-Platform Payment Architecture. Decoupling Checkout Presentation Abstractions (SubscriptionCheckout, OneTimeCheckout) from Payment Processing Implementations (StripeGateway, AdyenGateway).",
        "diagram": """
         Abstraction Layer                     Implementation Layer
      +-----------------------+              +-----------------------+
      |       Checkout        | ───────────► |    PaymentGateway     | (Implementor)
      +-----------------------+ (has-a)      +-----------------------+
      | + processCheckout()   |              | + authorizePayment()  |
      +-----------------------+              +-----------------------+
                  ▲                                      ▲
         ┌────────┴────────┐                    ┌────────┴────────┐
         │                 │                    │                 │
+-----------------+ +---------------+  +-----------------+ +---------------+
| OneTimeCheckout | | SubscrCheckout|  |  StripeGateway  | |  AdyenGateway |
+-----------------+ +---------------+  +-----------------+ +---------------+
""",
        "code": """// 1. Implementation Interface
export interface PaymentGatewayImplementor {
  authorize(amount: number, token: string): Promise<{ authCode: string; success: boolean }>;
  capture(authCode: string, amount: number): Promise<boolean>;
}

// 2. Concrete Implementations
export class StripeGatewayImplementor implements PaymentGatewayImplementor {
  async authorize(amount: number, token: string) {
    console.log(`[Stripe] Authorized $${amount} with customer token ${token}`);
    return { authCode: `stripe_auth_${Date.now()}`, success: true };
  }
  async capture(authCode: string, amount: number) {
    console.log(`[Stripe] Captured $${amount} against auth ${authCode}`);
    return true;
  }
}

export class AdyenGatewayImplementor implements PaymentGatewayImplementor {
  async authorize(amount: number, token: string) {
    console.log(`[Adyen] Authorized $${amount} via 3DSecure session ${token}`);
    return { authCode: `adyen_auth_${Date.now()}`, success: true };
  }
  async capture(authCode: string, amount: number) {
    console.log(`[Adyen] Captured $${amount} against auth ${authCode}`);
    return true;
  }
}

// 3. Abstraction
export abstract class CheckoutAbstraction {
  protected gateway: PaymentGatewayImplementor;

  constructor(gateway: PaymentGatewayImplementor) {
    this.gateway = gateway;
  }

  public setGateway(gateway: PaymentGatewayImplementor): void {
    this.gateway = gateway;
  }

  abstract execute(amount: number, token: string): Promise<boolean>;
}

// 4. Refined Abstractions
export class OneTimeCheckout extends CheckoutAbstraction {
  async execute(amount: number, token: string): Promise<boolean> {
    console.log(`[Checkout] Processing Standard One-Time Checkout of $${amount}`);
    const auth = await this.gateway.authorize(amount, token);
    if (!auth.success) return false;
    return this.gateway.capture(auth.authCode, amount);
  }
}

export class SubscriptionCheckout extends CheckoutAbstraction {
  private recurrencePeriodDays: number;

  constructor(gateway: PaymentGatewayImplementor, recurrencePeriodDays = 30) {
    super(gateway);
    this.recurrencePeriodDays = recurrencePeriodDays;
  }

  async execute(amount: number, token: string): Promise<boolean> {
    console.log(`[Checkout] Setting up ${this.recurrencePeriodDays}-day recurring subscription of $${amount}`);
    const auth = await this.gateway.authorize(amount, token);
    return auth.success;
  }
}

// --- Usage ---
const stripe = new StripeGatewayImplementor();
const adyen = new AdyenGatewayImplementor();

// Seamlessly combine any checkout abstraction with any gateway implementation
const instantOrder = new OneTimeCheckout(stripe);
instantOrder.execute(99, "tok_123");

const monthlySub = new SubscriptionCheckout(adyen, 30);
monthlySub.execute(29, "tok_456");
""",
        "edgeCases": [
            "**Mismatched Feature Sets**: If Stripe supports instant refunds but Adyen requires batch settlements, the implementor interface must gracefully handle optional capabilities without throwing unexpected errors.",
            "**Runtime Hot-Swapping**: Switching the gateway implementation mid-transaction requires state validation to prevent orphaned authorizations."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you want to divide and organize a monolithic class that has multiple variants of some functionality (e.g. cross-platform GUI engines, multi-cloud storage).",
                "When you need to be able to switch implementations at runtime.",
                "To prevent an exponential explosion of inheritance classes ($M \\times N$ classes reduced to $M + N$)."
            ],
            "whenNotToUse": [
                "When your domain has only one concrete platform and implementation (introduces unnecessary indirection)."
            ]
        }
    },
    {
        "filename": "03_Composite_Pattern.md",
        "title": "Composite Pattern",
        "category": "Structural Pattern",
        "intent": "Compose objects into tree structures to represent part-whole hierarchies. Composite lets clients treat individual objects and compositions of objects uniformly.",
        "problem": "In e-commerce catalogs or organization hierarchies, orders can contain standalone individual items (a single book) or bundled packages (a gaming bundle containing a console, 2 games, and cables, where cables are themselves a sub-bundle). Writing separate logic to calculate pricing, shipping weights, or discounts for items vs bundles introduces nested branching spaghetti.",
        "scenario": "Multi-Level E-Commerce Bundle Pricing & Discount Rollup Engine. Calculates aggregate prices, stock validation, and promotional discounts across arbitrarily nested item hierarchies.",
        "diagram": """
                       +-------------------------+
                       |     CatalogComponent    | (Component)
                       +-------------------------+
                       | + getPrice(): number    |
                       | + getWeightKg(): number |
                       | + display(indent): void |
                       +-------------------------+
                                    ▲
                   ┌────────────────┴────────────────┐
                   │                                 │
        +--------------------+            +--------------------+
        |    SingleProduct   | (Leaf)     |     ProductBundle  | (Composite)
        +--------------------+            +--------------------+
        | - price: number    |            | - children: Comp[] |
        | - weightKg: number |            +--------------------+
        +--------------------+            | + add(component)   |
                                          | + getPrice(): sum  |
                                          +--------------------+
""",
        "code": """// 1. Component Interface
export interface CatalogComponent {
  getName(): string;
  getPrice(): number;
  getWeightKg(): number;
  display(indent?: string): void;
}

// 2. Leaf Node: Single Standalone Product
export class ProductItem implements CatalogComponent {
  private name: string;
  private price: number;
  private weightKg: number;

  constructor(name: string, price: number, weightKg: number) {
    this.name = name;
    this.price = price;
    this.weightKg = weightKg;
  }

  getName(): string { return this.name; }
  getPrice(): number { return this.price; }
  getWeightKg(): number { return this.weightKg; }

  display(indent = ""): void {
    console.log(`${indent}📦 Item: ${this.name} | Price: $${this.price} | Weight: ${this.weightKg}kg`);
  }
}

// 3. Composite Node: Bundle containing Products and/or Sub-Bundles
export class ProductBundle implements CatalogComponent {
  private name: string;
  private discountPercentage: number;
  private children: CatalogComponent[] = [];

  constructor(name: string, discountPercentage = 0) {
    this.name = name;
    this.discountPercentage = discountPercentage;
  }

  add(component: CatalogComponent): void {
    this.children.push(component);
  }

  remove(component: CatalogComponent): void {
    const idx = this.children.indexOf(component);
    if (idx !== -1) this.children.splice(idx, 1);
  }

  getName(): string { return this.name; }

  getPrice(): number {
    const rawTotal = this.children.reduce((sum, item) => sum + item.getPrice(), 0);
    const discount = (rawTotal * this.discountPercentage) / 100;
    return Math.round((rawTotal - discount) * 100) / 100;
  }

  getWeightKg(): number {
    return this.children.reduce((sum, item) => sum + item.getWeightKg(), 0);
  }

  display(indent = ""): void {
    console.log(`${indent}📁 Bundle: ${this.name} (${this.discountPercentage}% Bundle Discount)`);
    for (const child of this.children) {
      child.display(indent + "   ");
    }
    console.log(`${indent}   ── Total Bundle Price: $${this.getPrice()} | Total Weight: ${this.getWeightKg()}kg`);
  }
}

// --- Usage ---
// Standalone Leaves
const consoleItem = new ProductItem("PlayStation 5", 499, 4.5);
const controller = new ProductItem("DualSense Controller", 69, 0.3);
const game1 = new ProductItem("God of War Ragnarok", 69, 0.1);
const game2 = new ProductItem("Spider-Man 2", 69, 0.1);

// Sub-Bundle: Games Duo Pack with 10% discount
const gamesDuo = new ProductBundle("Gamer 2-Pack Bundle", 10);
gamesDuo.add(game1);
gamesDuo.add(game2);

// Master Holiday Bundle: Console + Controller + Games Duo Pack with 15% discount
const megaHolidayBundle = new ProductBundle("Ultimate Holiday Console Bundle", 15);
megaHolidayBundle.add(consoleItem);
megaHolidayBundle.add(controller);
megaHolidayBundle.add(gamesDuo);

// Client interacts uniformly with composite as if it were a single item
megaHolidayBundle.display();
console.log(`\\nTotal Cart Charge: $${megaHolidayBundle.getPrice()}`);
""",
        "edgeCases": [
            "**Recursive Tree Traversal Stack Overflow**: Unusually deep nesting (1,000+ levels) can trigger call stack exhaustion. Consider iterative breadth-first traversal for very deep trees.",
            "**Circular Composition**: If bundle A adds bundle B, and bundle B accidentally adds bundle A, recursive pricing calculations will result in infinite loops. Solution: Maintain an ancestor set check in `.add()`.",
            "**Leaf vs Composite Interface Discrepancies**: Leaves shouldn't expose `.add()` or `.remove()`. Following Interface Segregation Principle keeps Leaf clean."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you need to implement a tree-like object structure (DOM trees, menus, file systems, organizational units).",
                "When you want the client code to treat both simple and complex elements uniformly."
            ],
            "whenNotToUse": [
                "When components do not naturally share common methods and forcing an interface leads to empty/dummy method implementations on leaves."
            ]
        }
    },
    {
        "filename": "04_Decorator_Pattern.md",
        "title": "Decorator Pattern",
        "category": "Structural Pattern",
        "intent": "Attach additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality.",
        "problem": "Extending functionality via subclassing produces an unmanageable explosion of classes. If you need logging, encryption, and compression on a data stream, inheritance requires `LoggedCompressedEncryptedStream`, `CompressedStream`, `LoggedStream`, etc. Combining behaviors dynamically at runtime is impossible with static inheritance.",
        "scenario": "HTTP API Request / Data Streaming Pipeline. Dynamically wrapping a base network data stream with Gzip Compression, AES-256 Encryption, and Telemetry Performance Metrics logging based on request headers.",
        "diagram": """
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
""",
        "code": """import crypto from "crypto";

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
""",
        "edgeCases": [
            "**Order of Decorator Application**: Applying decorators in the wrong order produces unexpected bugs (e.g. encrypting already compressed data vs compressing encrypted data — encryption randomizes bytes, drastically degrading compression efficiency).",
            "**Decorator Interface Drift**: If concrete decorators add custom methods not present in the base `DataStream` interface, outer layers cannot access them once wrapped.",
            "**Removing Decorators**: Removing a specific wrapper from the middle of a multi-layer decorator stack is difficult."
        ],
        "tradeoffs": {
            "whenToUse": [
                "To assign extra responsibilities to objects dynamically and transparently without affecting other objects.",
                "When extension by subclassing is impractical due to class explosion.",
                "Designing middleware pipelines (Express/Koa middleware, Axios interceptors)."
            ],
            "whenNotToUse": [
                "When you need to inspect the concrete type of the object (decorators hide the underlying wrapped type)."
            ]
        }
    },
    {
        "filename": "05_Facade_Pattern.md",
        "title": "Facade Pattern",
        "category": "Structural Pattern",
        "intent": "Provide a unified interface to a set of interfaces in a subsystem. Facade defines a higher-level interface that makes the subsystem easier to use.",
        "problem": "Complex enterprise backends consist of dozens of decoupled subsystems (Inventory, Payment Gateways, Fraud Detection, Shipping Courier APIs, SMS/Email Notifications). Forcing client code or web controllers to orchestrate all these subsystems manually leads to massive code duplication and tight coupling.",
        "scenario": "E-Commerce Checkout Facade. An online store coordinates 5 distinct microservice calls to complete an order. The CheckoutFacade exposes a single `.placeOrder()` method that orchestrates the entire workflow.",
        "diagram": """
       [ Web App / Mobile Client ]
                   │
                   ▼
       +-----------------------+
       |     CheckoutFacade    | (Facade)
       +-----------------------+
       | + placeOrder(): res   |
       +-----------------------+
                   │
       ┌───────────┼───────────┬───────────┐
       ▼           ▼           ▼           ▼
  [Inventory]  [Payment]   [Shipping]  [NotifService]
""",
        "code": """export interface OrderRequest {
  userId: string;
  items: Array<{ sku: string; quantity: number; price: number }>;
  paymentToken: string;
  shippingAddress: string;
}

export interface OrderConfirmation {
  orderId: string;
  totalAmount: number;
  trackingNumber: string;
  status: "PLACED" | "FAILED";
}

// --- Complex Subsystems ---
export class InventorySubsystem {
  async reserveStock(items: Array<{ sku: string; quantity: number }>): Promise<boolean> {
    console.log(`[Inventory] Reserved stock for ${items.length} items`);
    return true;
  }
}

export class PaymentSubsystem {
  async processPayment(amount: number, token: string): Promise<{ txnId: string; success: boolean }> {
    console.log(`[Payment] Charged $${amount} via payment token ${token}`);
    return { txnId: `TXN-${Date.now()}`, success: true };
  }
}

export class ShippingSubsystem {
  async createShipmentLabel(address: string, itemsCount: number): Promise<string> {
    console.log(`[Shipping] Created courier dispatch label for ${address}`);
    return `TRACK-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
  }
}

export class NotificationSubsystem {
  async sendOrderConfirmation(userId: string, orderId: string, tracking: string): Promise<void> {
    console.log(`[Notifications] Sent SMS/Email confirmation for order ${orderId} to user ${userId}`);
  }
}

// --- The Facade ---
export class OrderPlacementFacade {
  private inventory: InventorySubsystem;
  private payment: PaymentSubsystem;
  private shipping: ShippingSubsystem;
  private notifications: NotificationSubsystem;

  constructor() {
    this.inventory = new InventorySubsystem();
    this.payment = new PaymentSubsystem();
    this.shipping = new ShippingSubsystem();
    this.notifications = new NotificationSubsystem();
  }

  /**
   * Unified, simplified entrypoint for client applications.
   */
  public async placeOrder(request: OrderRequest): Promise<OrderConfirmation> {
    console.log(`[Facade] Starting orchestrated order placement for user ${request.userId}...`);

    // 1. Calculate total
    const totalAmount = request.items.reduce((sum, item) => sum + item.price * item.quantity, 0);

    // 2. Reserve stock
    const stockReserved = await this.inventory.reserveStock(request.items);
    if (!stockReserved) throw new Error("Inventory reservation failed.");

    // 3. Process payment
    const paymentResult = await this.payment.processPayment(totalAmount, request.paymentToken);
    if (!paymentResult.success) throw new Error("Payment processing declined.");

    // 4. Arrange courier logistics
    const trackingNumber = await this.shipping.createShipmentLabel(request.shippingAddress, request.items.length);

    // 5. Notify customer
    const orderId = `ORD-${Date.now()}`;
    await this.notifications.sendOrderConfirmation(request.userId, orderId, trackingNumber);

    console.log(`[Facade] Order ${orderId} successfully completed!`);

    return {
      orderId,
      totalAmount,
      trackingNumber,
      status: "PLACED",
    };
  }
}

// --- Client Usage ---
const facade = new OrderPlacementFacade();
facade.placeOrder({
  userId: "usr_9918",
  items: [{ sku: "MACBOOK_PRO", quantity: 1, price: 1999 }],
  paymentToken: "tok_visa_valid",
  shippingAddress: "742 Evergreen Terrace",
});
""",
        "edgeCases": [
            "**God Object Anti-Pattern**: A Facade can easily turn into an unmanageable 'God Object' if developers cram unrelated system methods into it. Keep facades focused on cohesive workflows.",
            "**Subsystem Bypassing**: Facade provides a convenient simplified interface, but clients should still be allowed to access low-level subsystems directly if they require specialized fine-grained control."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you need to provide a simple, high-level interface to a complex subsystem.",
                "When structuring subsystems into layers — use facades to define entry points to each subsystem level.",
                "Decoupling client applications from intricate implementation details of multiple third-party libraries."
            ],
            "whenNotToUse": [
                "When client applications genuinely need fine-grained, low-level configuration of every subsystem parameter."
            ]
        }
    },
    {
        "filename": "06_Flyweight_Pattern.md",
        "title": "Flyweight Pattern",
        "category": "Structural Pattern",
        "intent": "Use sharing to support large numbers of fine-grained objects efficiently by separating intrinsic state (shared, immutable) from extrinsic state (unique, context-dependent).",
        "problem": "Rendering 1,000,000 forest trees in a 3D game or loading 500,000 formatted text characters in a word processor exhausts memory (e.g. allocating 2GB of RAM) if each object stores its own texture mesh, font metrics, and color palettes.",
        "scenario": "Rich Text Document Editor / Gaming Particle Engine. 1,000,000 character glyphs rendered in a document. The font family, size, weight, and vector outline (Intrinsic State) are shared, while character code and screen coordinates (Extrinsic State) are unique.",
        "diagram": """
+-------------------------------------------------------+
|                    FlyweightFactory                   |
+-------------------------------------------------------+
| - flyweights: Map<string, FontFlyweight>              |
+-------------------------------------------------------+
| + getFont(fontFamily, size, bold): FontFlyweight      |
+-------------------------------------------------------+
                           │ (Returns shared instance)
                           ▼
+-------------------------------------------------------+
|                     FontFlyweight                     | (Intrinsic State)
+-------------------------------------------------------+
| - fontFamily: string                                  |
| - size: number                                        |
| - isBold: boolean                                     |
| - vectorGlyphMesh: Buffer (Heavy: 500KB)              |
+-------------------------------------------------------+
| + render(char: string, x: number, y: number): void    | (Extrinsic)
+-------------------------------------------------------+
""",
        "code": """// 1. Flyweight: Stores Intrinsic (Shared) Immutable State
export class CharacterFormatFlyweight {
  public readonly fontFamily: string;
  public readonly fontSize: number;
  public readonly isBold: boolean;
  public readonly colorHex: string;

  constructor(fontFamily: string, fontSize: number, isBold: boolean, colorHex: string) {
    this.fontFamily = fontFamily;
    this.fontSize = fontSize;
    this.isBold = isBold;
    this.colorHex = colorHex;
  }

  // Receives Extrinsic (Unique) State at runtime
  render(char: string, x: number, y: number): void {
    // In real engines, this invokes GPU draw calls
    // console.log(`Draw '${char}' at (${x},${y}) using ${this.fontFamily} ${this.fontSize}px ${this.colorHex}`);
  }
}

// 2. Flyweight Factory: Caches and reuses shared instances
export class FormatFlyweightFactory {
  private static pool = new Map<string, CharacterFormatFlyweight>();

  public static getFormat(fontFamily: string, fontSize: number, isBold: boolean, colorHex: string): CharacterFormatFlyweight {
    const key = `${fontFamily}_${fontSize}_${isBold}_${colorHex}`;
    let format = FormatFlyweightFactory.pool.get(key);

    if (!format) {
      format = new CharacterFormatFlyweight(fontFamily, fontSize, isBold, colorHex);
      FormatFlyweightFactory.pool.set(key, format);
    }

    return format;
  }

  public static getPoolSize(): number {
    return FormatFlyweightFactory.pool.size;
  }
}

// 3. Context Object: Stores Extrinsic State & Holds reference to Flyweight
export class CharacterGlyph {
  public char: string;
  public x: number;
  public y: number;
  public format: CharacterFormatFlyweight; // Reference to shared flyweight

  constructor(char: string, x: number, y: number, format: CharacterFormatFlyweight) {
    this.char = char;
    this.x = x;
    this.y = y;
    this.format = format;
  }

  draw(): void {
    this.format.render(this.char, this.x, this.y);
  }
}

// --- Usage Simulation ---
console.log("Simulating loading a 100,000-character document...");
const documentGlyphs: CharacterGlyph[] = [];

for (let i = 0; i < 100000; i++) {
  // Most text uses identical styles (e.g. Body text vs Heading)
  const isHeading = i % 500 === 0;
  const format = isHeading
    ? FormatFlyweightFactory.getFormat("Inter", 24, true, "#111827")
    : FormatFlyweightFactory.getFormat("Inter", 14, false, "#4B5563");

  documentGlyphs.push(new CharacterGlyph("A", i % 80, Math.floor(i / 80), format));
}

console.log(`✓ Total Character Glyphs allocated: ${documentGlyphs.length}`);
console.log(`✓ Unique Flyweight format objects in memory: ${FormatFlyweightFactory.getPoolSize()}`);
console.log(`Memory optimization: 100,000 items sharing only 2 format memory allocations!`);
""",
        "edgeCases": [
            "**Accidental Mutation of Intrinsic State**: Flyweights MUST be strictly immutable (using `readonly` / `Object.freeze`). If one client mutates a flyweight property, it inadvertently modifies millions of objects sharing that flyweight.",
            "**CPU vs Memory Trade-off**: Flyweights save massive amounts of RAM, but computing and passing extrinsic parameters during every render loop incurs minor CPU cycles."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When your application needs to spawn millions of similar objects.",
                "When RAM consumption is a critical bottleneck.",
                "When duplicate state can be neatly separated into intrinsic (shared) and extrinsic (contextual) components."
            ],
            "whenNotToUse": [
                "When memory is not a constraint or objects have unique properties that cannot be shared."
            ]
        }
    },
    {
        "filename": "07_Proxy_Pattern.md",
        "title": "Proxy Pattern",
        "category": "Structural Pattern",
        "intent": "Provide a surrogate or placeholder for another object to control access to it, support lazy initialization, logging, caching, or access control.",
        "problem": "Instantiating heavy third-party services (e.g. fetching gigabyte-sized satellite images from remote APIs, opening expensive database cursors) before they are actually needed degrades startup latency. Furthermore, auditing and caching access directly inside business logic violates Single Responsibility.",
        "scenario": "High-Resolution Image / Cloud Asset Loader with Redis Caching and RBAC Protection. A proxy intercepts asset downloads, enforces user security permissions, checks in-memory cache, and only lazily downloads the raw binary from S3 upon cache misses.",
        "diagram": """
+-------------------------------------------------------+
|                       AssetLoader                     | (Subject Interface)
+-------------------------------------------------------+
| + loadAsset(assetId, userRole): Promise<Buffer>       |
+-------------------------------------------------------+
                           ▲
             ┌─────────────┴─────────────┐
             │                           │
+-------------------------+ +-------------------------+
|     RealAssetLoader     | |    CachedSecureProxy    |
+-------------------------+ +-------------------------+
| + loadAsset() -> S3 DL  | | - realLoader: Subject   |
+-------------------------+ | - cache: Map            |
                            +-------------------------+
                            | + loadAsset()           |
                            |   1. Check RBAC role    |
                            |   2. Check Cache Hit    |
                            |   3. Call realLoader()  |
                            +-------------------------+
""",
        "code": """export interface AssetLoader {
  loadAsset(assetId: string, userRole: string): Promise<{ data: string; fromCache: boolean }>;
}

// 1. Real Subject: Heavy Remote Storage Loader
export class RemoteS3AssetLoader implements AssetLoader {
  async loadAsset(assetId: string, _userRole: string) {
    console.log(`[S3 Storage] Executing expensive network download for asset: "${assetId}"`);
    // Simulated remote network latency
    await new Promise((r) => setTimeout(r, 150));
    return { data: `RAW_BINARY_DATA_FOR_${assetId}`, fromCache: false };
  }
}

// 2. Proxy: Security Verification + In-Memory Caching + Telemetry
export class SecureCachedAssetProxy implements AssetLoader {
  private realSubject: RemoteS3AssetLoader;
  private cache = new Map<string, string>();
  private readonly RESTRICTED_ASSETS = new Set(["TOP_SECRET_FINANCIALS", "INTERNAL_AUDIT_DOC"]);

  constructor(realSubject?: RemoteS3AssetLoader) {
    this.realSubject = realSubject || new RemoteS3AssetLoader();
  }

  async loadAsset(assetId: string, userRole: string) {
    console.log(`[Proxy] Intercepted access request for "${assetId}" by user role [${userRole}]`);

    // A. Security Access Control (Protection Proxy)
    if (this.RESTRICTED_ASSETS.has(assetId) && userRole !== "ADMIN") {
      throw new Error(`403 Forbidden: Role [${userRole}] cannot access restricted asset ${assetId}`);
    }

    // B. Caching Layer (Caching Proxy)
    if (this.cache.has(assetId)) {
      console.log(`[Proxy] Cache HIT for "${assetId}". Returning cached copy without S3 download.`);
      return { data: this.cache.get(assetId)!, fromCache: true };
    }

    // C. Lazy Delegation to Real Subject
    const result = await this.realSubject.loadAsset(assetId, userRole);
    this.cache.set(assetId, result.data);

    return result;
  }

  clearCache(): void {
    this.cache.clear();
  }
}

// --- Usage ---
const assetService: AssetLoader = new SecureCachedAssetProxy();

async function run() {
  // First Call: Fetches from Remote S3
  const res1 = await assetService.loadAsset("USER_AVATAR_101", "GUEST");
  console.log("Result 1:", res1);

  // Second Call: Immediate Cache Hit (Zero S3 I/O)
  const res2 = await assetService.loadAsset("USER_AVATAR_101", "GUEST");
  console.log("Result 2:", res2);

  // Security Check: Unauthorized access blocked at Proxy boundary
  try {
    await assetService.loadAsset("TOP_SECRET_FINANCIALS", "GUEST");
  } catch (err: any) {
    console.error("Blocked:", err.message);
  }
}

run();
""",
        "edgeCases": [
            "**Cache Invalidation Staleness**: Cached proxies can return outdated data if the underlying remote asset changes. Implement TTLs or cache eviction hooks.",
            "**Recursive Proxy Overheads**: Wrapping proxies inside proxies (e.g. LoggingProxy -> CachingProxy -> SecurityProxy) can introduce latency if call stacks become excessive."
        ],
        "tradeoffs": {
            "whenToUse": [
                "Lazy initialization (Virtual Proxy) for high-overhead objects.",
                "Access control and permission verification (Protection Proxy).",
                "Caching query results and API responses (Caching Proxy).",
                "Logging and instrumentation without modifying the original class."
            ],
            "whenNotToUse": [
                "When the overhead of proxy indirection exceeds the cost of direct instantiation."
            ]
        }
    }
]

for p in patterns:
    edge_cases_str = "\\n".join([f"- {e}" for e in p["edgeCases"]])
    when_to_use_str = "\\n".join([f"- {w}" for w in p["tradeoffs"]["whenToUse"]])
    when_not_to_use_str = "\\n".join([f"- {w}" for w in p["tradeoffs"]["whenNotToUse"]])
    
    content = f"""# {p['title']}

## Category: {p['category']}

---

## 1. Core Intent & Definition
{p['intent']}

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
{p['problem']}

### Real-World Industry Example:
{p['scenario']}

---

## 3. Architecture & Visual Flow Diagram
```
{p['diagram'].strip()}
```

---

## 4. Practical Implementation (TypeScript)
```typescript
{p['code'].strip()}
```

---

## 5. Edge Cases & Failure Handling
{edge_cases_str}

---

## 6. Trade-offs & Production Considerations
### When to Use:
{when_to_use_str}

### When NOT to Use / Anti-patterns:
{when_not_to_use_str}
"""
    file_path = os.path.join(BASE_DIR, p["filename"])
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"[Structural] Successfully generated {len(patterns)} in-depth pattern files.")
