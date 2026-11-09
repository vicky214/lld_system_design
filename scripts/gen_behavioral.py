import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../03_Behavioral_Patterns"))
os.makedirs(BASE_DIR, exist_ok=True)

patterns = [
    {
        "filename": "01_Chain_of_Responsibility.md",
        "title": "Chain of Responsibility Pattern",
        "category": "Behavioral Pattern",
        "intent": "Avoid coupling the sender of a request to its receiver by giving more than one object a chance to handle the request. Chain the receiving objects and pass the request along the chain until an object handles it.",
        "problem": "In HTTP servers and workflow engines, incoming requests must pass through sequential validation checks: IP blacklists, authentication tokens, rate limits, schema validation, and audit logging. Hardcoding all these checks into a single giant function creates unmaintainable spaghetti code.",
        "scenario": "HTTP API Request Security & Validation Filter Pipeline (Express/Koa Middleware). Each link in the chain verifies one concern (IP Firewall -> Rate Limiter -> JWT Authentication -> JSON Schema Validation) and decides whether to halt the request or call `next()`.",
        "diagram": """
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
""",
        "code": """export interface HttpRequest {
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
""",
        "edgeCases": [
            "**Unterminated Chain**: If no handler in the chain returns a response and there is no default fallback, the request hangs or returns null. Always attach a final default handler or router.",
            "**Circular References in Chains**: If handler A sets handler B as next, and handler B sets handler A, an infinite loop will crash the process with stack overflow.",
            "**Asynchronous Exceptions**: An unhandled exception in one link can halt execution of subsequent links without cleanup."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When more than one object may handle a request, and the handler isn't known a priori.",
                "When you want to issue a request to one of several objects without specifying the receiver explicitly.",
                "Express/Koa middleware, validation interceptors, event bubbling systems."
            ],
            "whenNotToUse": [
                "When every request must always be handled by exactly one deterministic function."
            ]
        }
    },
    {
        "filename": "02_Command_Pattern.md",
        "title": "Command Pattern",
        "category": "Behavioral Pattern",
        "intent": "Encapsulate a request as an object, thereby letting you parameterize clients with different requests, queue or log requests, and support undoable operations.",
        "problem": "Coupling UI buttons or API controllers directly to business operations prevents features like action undo/redo, delayed queueing, macro recordings, and transactional rollback logs.",
        "scenario": "Transactional Banking Ledger with Undo / Reversal Stack. Every debit, credit, or transfer is packaged as an executable Command object that knows how to execute and how to reverse (`undo()`) itself cleanly.",
        "diagram": """
+-----------------------+
|        Command        |
+-----------------------+
| + execute(): void     |
| + undo(): void        |
+-----------------------+
            ▲
     ┌──────┴──────┐
     │             │
+-----------+ +-----------+
| Transfer  | |  Deposit  |
+-----------+ +-----------+
     │
     ▼ (invokes)
+-----------------------+
|     BankAccount       | (Receiver)
+-----------------------+
| + debit(amt): void    |
| + credit(amt): void   |
+-----------------------+
""",
        "code": """// 1. Receiver
export class BankAccount {
  public id: string;
  public balance: number;

  constructor(id: string, initialBalance: number) {
    this.id = id;
    this.balance = initialBalance;
  }

  deposit(amount: number): void {
    this.balance += amount;
    console.log(`[Account ${this.id}] Deposited $${amount}. Balance: $${this.balance}`);
  }

  withdraw(amount: number): boolean {
    if (this.balance < amount) {
      console.log(`[Account ${this.id}] Insufficient funds for $${amount}`);
      return false;
    }
    this.balance -= amount;
    console.log(`[Account ${this.id}] Withdrew $${amount}. Balance: $${this.balance}`);
    return true;
  }
}

// 2. Command Interface
export interface Command {
  execute(): boolean;
  undo(): void;
  getDescription(): string;
}

// 3. Concrete Commands
export class TransferMoneyCommand implements Command {
  private from: BankAccount;
  private to: BankAccount;
  private amount: number;
  private succeeded = false;

  constructor(from: BankAccount, to: BankAccount, amount: number) {
    this.from = from;
    this.to = to;
    this.amount = amount;
  }

  execute(): boolean {
    if (this.from.withdraw(this.amount)) {
      this.to.deposit(this.amount);
      this.succeeded = true;
      return true;
    }
    return false;
  }

  undo(): void {
    if (this.succeeded) {
      console.log(`[UNDO] Reversing transfer of $${this.amount} from ${this.to.id} back to ${this.from.id}...`);
      this.to.withdraw(this.amount);
      this.from.deposit(this.amount);
      this.succeeded = false;
    }
  }

  getDescription(): string {
    return `Transfer $${this.amount} from ${this.from.id} to ${this.to.id}`;
  }
}

// 4. Invoker: Manages History and Undo Stack
export class TransactionManager {
  private history: Command[] = [];
  private undoStack: Command[] = [];

  public executeCommand(command: Command): boolean {
    const success = command.execute();
    if (success) {
      this.history.push(command);
      this.undoStack.push(command);
    }
    return success;
  }

  public undoLast(): boolean {
    const cmd = this.undoStack.pop();
    if (!cmd) {
      console.log("[Invoker] Nothing to undo.");
      return false;
    }
    console.log(`[Invoker] Rolling back: ${cmd.getDescription()}`);
    cmd.undo();
    return true;
  }
}

// --- Usage ---
const accA = new BankAccount("ACC-01", 1000);
const accB = new BankAccount("ACC-02", 500);
const manager = new TransactionManager();

// Execute command
const transfer = new TransferMoneyCommand(accA, accB, 300);
manager.executeCommand(transfer);

console.log("Post-transfer balances: AccA =", accA.balance, "AccB =", accB.balance);

// Undo operation seamlessly
manager.undoLast();
console.log("Post-undo balances: AccA =", accA.balance, "AccB =", accB.balance);
""",
        "edgeCases": [
            "**Non-Reversible Operations**: External API calls like sending an SMS or firing a missile cannot be physically undone. In such cases, a compensating transaction (e.g. sending a cancellation email) must be executed.",
            "**Memory Bloat in Long-Running Apps**: Storing unlimited commands in the undo stack consumes memory. Always bound the undo stack size (e.g. max 50 actions)."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you need to parameterize objects by an action to perform.",
                "When you need to queue, schedule, or execute operations remotely.",
                "When implementing multi-level undo/redo or transactional rollbacks."
            ],
            "whenNotToUse": [
                "For simple direct method calls where undo, queueing, and logging are completely unnecessary."
            ]
        }
    },
    {
        "filename": "03_Interpreter_Pattern.md",
        "title": "Interpreter Pattern",
        "category": "Behavioral Pattern",
        "intent": "Given a language, define a representation for its grammar along with an interpreter that uses the representation to interpret sentences in the language.",
        "problem": "Hardcoding custom filter conditions (e.g. `age > 18 AND (role = 'ADMIN' OR points > 100)`) into procedural if/else blocks fails when users or non-technical business admins need to author dynamic discount rules and filter criteria without deploying new code.",
        "scenario": "Dynamic Discount Rule & Query Filter Engine. E-commerce marketing managers define dynamic rules in JSON/DSL format to evaluate if a user cart qualifies for special promotions.",
        "diagram": """
                    +-----------------------------+
                    |          Expression         | (Abstract Expression)
                    +-----------------------------+
                    | + interpret(context): any   |
                    +-----------------------------+
                                   ▲
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
+-------------------+                               +-------------------+
| NumberExpression  | (Terminal)                    |    AndExpression  | (Non-Terminal)
+-------------------+                               +-------------------+
| - value: number   |                               | - left: Expr      |
+-------------------+                               | - right: Expr     |
                                                    +-------------------+
""",
        "code": """export type Context = Record<string, any>;

// 1. Abstract Expression
export interface Expression {
  interpret(context: Context): boolean;
}

// 2. Terminal Expressions
export class ComparisonExpression implements Expression {
  private field: string;
  private operator: ">" | "<" | "==";
  private targetValue: number;

  constructor(field: string, operator: ">" | "<" | "==", targetValue: number) {
    this.field = field;
    this.operator = operator;
    this.targetValue = targetValue;
  }

  interpret(context: Context): boolean {
    const val = context[this.field];
    if (typeof val !== "number") return false;

    switch (this.operator) {
      case ">": return val > this.targetValue;
      case "<": return val < this.targetValue;
      case "==": return val === this.targetValue;
      default: return false;
    }
  }
}

// 3. Non-Terminal Expressions (Composite logic)
export class AndExpression implements Expression {
  private left: Expression;
  private right: Expression;

  constructor(left: Expression, right: Expression) {
    this.left = left;
    this.right = right;
  }

  interpret(context: Context): boolean {
    return this.left.interpret(context) && this.right.interpret(context);
  }
}

export class OrExpression implements Expression {
  private left: Expression;
  private right: Expression;

  constructor(left: Expression, right: Expression) {
    this.left = left;
    this.right = right;
  }

  interpret(context: Context): boolean {
    return this.left.interpret(context) || this.right.interpret(context);
  }
}

// --- Usage ---
// Construct Rule AST: (cartTotal > 100 AND userLoyaltyPoints > 50) OR isVipMember == 1
const rule = new OrExpression(
  new AndExpression(
    new ComparisonExpression("cartTotal", ">", 100),
    new ComparisonExpression("loyaltyPoints", ">", 50)
  ),
  new ComparisonExpression("isVip", "==", 1)
);

const cartA = { cartTotal: 150, loyaltyPoints: 75, isVip: 0 };
console.log("Cart A qualifies for discount?", rule.interpret(cartA)); // true

const cartB = { cartTotal: 50, loyaltyPoints: 10, isVip: 0 };
console.log("Cart B qualifies for discount?", rule.interpret(cartB)); // false
""",
        "edgeCases": [
            "**Grammar Explosion**: Complex grammars with 50+ operators become hard to maintain as class hierarchies. For large languages, use parser generators (e.g. ANTLR or peg.js) instead.",
            "**Performance Overhead**: Interpreting expressions via deep AST object graphs is slower than compiling rules to bytecode or native functions."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When the grammar is simple and stability is more important than raw execution efficiency.",
                "Custom business rule evaluation, configuration query filters, calculator engines."
            ],
            "whenNotToUse": [
                "Complex programming languages or high-frequency performance-critical parsing loops."
            ]
        }
    },
    {
        "filename": "04_Iterator_Pattern.md",
        "title": "Iterator Pattern",
        "category": "Behavioral Pattern",
        "intent": "Provide a way to access the elements of an aggregate object sequentially without exposing its underlying representation.",
        "problem": "Collections store data in diverse internal structures (binary trees, hash tables, circular buffers, paginated remote REST APIs). Forcing clients to know whether a collection is an Array or a B-Tree breaks encapsulation and makes refactoring internal storage impossible.",
        "scenario": "Asynchronous Paginated API Response Streamer. An API client streams millions of records from a remote paginated endpoint (e.g. Stripe Transactions API), automatically fetching the next page behind the scenes as the caller iterates.",
        "diagram": """
+-----------------------------------+
|             Iterator              |
+-----------------------------------+
| + hasNext(): Promise<boolean>     |
| + next(): Promise<T>              |
+-----------------------------------+
                  ▲
                  │
+-----------------------------------+
|    PaginatedApiStreamIterator     |
+-----------------------------------+
| - currentPage: T[]                |
| - cursor: string                  |
+-----------------------------------+
""",
        "code": """export interface Transaction {
  id: string;
  amount: number;
}

export interface AsyncIteratorEngine<T> {
  hasNext(): Promise<boolean>;
  next(): Promise<T>;
}

export class PaginatedTransactionIterator implements AsyncIteratorEngine<Transaction> {
  private buffer: Transaction[] = [];
  private nextCursor: string | null = "start";
  private isExhausted = false;

  private async fetchNextPage(): Promise<void> {
    if (!this.nextCursor) {
      this.isExhausted = true;
      return;
    }

    console.log(`[API Iterator] Fetching next batch using cursor: ${this.nextCursor}...`);
    // Simulated remote API pagination response
    await new Promise((r) => setTimeout(r, 40));

    const pageCount = this.nextCursor === "page_3" ? 0 : 3;
    const newItems: Transaction[] = [];
    for (let i = 1; i <= pageCount; i++) {
      newItems.push({ id: `txn_${this.nextCursor}_${i}`, amount: i * 50 });
    }

    this.buffer.push(...newItems);
    this.nextCursor = this.nextCursor === "start" ? "page_2" : this.nextCursor === "page_2" ? "page_3" : null;

    if (this.buffer.length === 0 && !this.nextCursor) {
      this.isExhausted = true;
    }
  }

  async hasNext(): Promise<boolean> {
    if (this.buffer.length > 0) return true;
    if (this.isExhausted) return false;

    await this.fetchNextPage();
    return this.buffer.length > 0;
  }

  async next(): Promise<Transaction> {
    if (!(await this.hasNext())) {
      throw new Error("No more transactions available in iterator.");
    }
    return this.buffer.shift()!;
  }
}

// --- Usage ---
async function processAllTransactions() {
  const iterator = new PaginatedTransactionIterator();

  while (await iterator.hasNext()) {
    const txn = await iterator.next();
    console.log(`  Processed: ${txn.id} ($${txn.amount})`);
  }
  console.log("✓ All paginated remote records consumed seamlessly.");
}

processAllTransactions();
""",
        "edgeCases": [
            "**Concurrent Modification**: If the underlying collection is modified (items added or deleted) while iterating, the iterator may skip elements or throw ConcurrentModificationException.",
            "**Network Failure During Pagination**: The iterator must support retry logic when mid-stream HTTP page fetches fail."
        ],
        "tradeoffs": {
            "whenToUse": [
                "To access a collection's contents without exposing its internal representation.",
                "To support multiple simultaneous traversals of a collection.",
                "To provide a uniform interface for traversing different structures."
            ],
            "whenNotToUse": [
                "For simple in-memory arrays where native `for...of` loops are already optimal."
            ]
        }
    },
    {
        "filename": "05_Mediator_Pattern.md",
        "title": "Mediator Pattern",
        "category": "Behavioral Pattern",
        "intent": "Define an object that encapsulates how a set of objects interact. Mediator promotes loose coupling by keeping objects from referring to each other explicitly, and lets you vary their interaction independently.",
        "problem": "When multiple components communicate directly (e.g. 10 airplanes in an airspace coordinating runway access), every component must maintain references to all other 9 components ($O(N^2)$ connections), creating an unmaintainable web of dependencies.",
        "scenario": "Air Traffic Control (ATC) Runway Coordinator / Real-Time Chat Room. Aircraft do not communicate directly with each other; they communicate exclusively through the ATC Mediator, which arbitrates runway reservations safely.",
        "diagram": """
       [ Flight A ]        [ Flight B ]        [ Flight C ]
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ▼
                     +-----------------------+
                     |  AirTrafficMediator   |
                     +-----------------------+
                     | + requestLanding(fl)  |
                     +-----------------------+
                                 │
                                 ▼
                         [ Active Runway ]
""",
        "code": """// 1. Mediator Interface
export interface AirTrafficMediator {
  requestLanding(flight: Flight): boolean;
  notifyRunwayCleared(runwayId: string): void;
}

// 2. Colleague
export class Flight {
  public flightNumber: string;
  private mediator: AirTrafficMediator;

  constructor(flightNumber: string, mediator: AirTrafficMediator) {
    this.flightNumber = flightNumber;
    this.mediator = mediator;
  }

  requestRunway(): boolean {
    console.log(`[${this.flightNumber}] Requesting clearance to land...`);
    return this.mediator.requestLanding(this);
  }

  landed(): void {
    console.log(`[${this.flightNumber}] Wheels down on runway. Vacating...`);
    this.mediator.notifyRunwayCleared("RUNWAY_01");
  }
}

// 3. Concrete Mediator
export class AirportControlTower implements AirTrafficMediator {
  private runwayOccupied = false;
  private landingQueue: Flight[] = [];

  requestLanding(flight: Flight): boolean {
    if (this.runwayOccupied) {
      console.log(`[Tower] Runway 01 occupied. Flight ${flight.flightNumber} placed in holding pattern.`);
      this.landingQueue.push(flight);
      return false;
    }

    this.runwayOccupied = true;
    console.log(`[Tower] Clearance GRANTED for ${flight.flightNumber} on Runway 01.`);
    return true;
  }

  notifyRunwayCleared(runwayId: string): void {
    console.log(`[Tower] ${runwayId} reported clear.`);
    this.runwayOccupied = false;

    if (this.landingQueue.length > 0) {
      const nextFlight = this.landingQueue.shift()!;
      console.log(`[Tower] Releasing next holding flight: ${nextFlight.flightNumber}`);
      nextFlight.requestRunway();
    }
  }
}

// --- Usage ---
const tower = new AirportControlTower();
const flight1 = new Flight("UA-101", tower);
const flight2 = new Flight("BA-202", tower);

flight1.requestRunway(); // Granted
flight2.requestRunway(); // Queued in holding pattern

flight1.landed(); // Runway cleared -> Flight 2 automatically cleared
""",
        "edgeCases": [
            "**God Mediator Anti-Pattern**: Over time, a mediator can become overly complex and turn into a monolithic 'God Object'. Keep mediators focused solely on interaction protocols.",
            "**Single Point of Failure**: If the mediator crashes, all communication between colleagues stops."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When a set of objects communicate in well-defined but complex ways.",
                "When reusing an object is difficult because it refers to and communicates with many other objects.",
                "Chat rooms, dialog windows with interrelated UI controls, air traffic controllers."
            ],
            "whenNotToUse": [
                "When only 2 or 3 components communicate simply (direct communication is clearer)."
            ]
        }
    },
    {
        "filename": "06_Memento_Pattern.md",
        "title": "Memento Pattern",
        "category": "Behavioral Pattern",
        "intent": "Without violating encapsulation, capture and externalize an object's internal state so that the object can be restored to this state later.",
        "problem": "To implement autosave or state rollback, an external history manager might try to inspect and copy private fields of an entity. This breaks encapsulation and exposes internal state.",
        "scenario": "Rich Text Document Editor Revision History & Autosave. The document (Originator) produces an opaque snapshot (Memento) of its internal state and stores it in the History Manager (Caretaker).",
        "diagram": """
+-----------------------+             +-----------------------+
|   DocumentEditor      | (Originator)|    DocumentMemento    | (Memento)
+-----------------------+             +-----------------------+
| - content: string     | ──────────► | - state: string       |
| - cursorPosition: int |  (creates)  +-----------------------+
+-----------------------+                        ▲
| + save(): Memento     |                        │ (stores)
| + restore(m: Memento) |             +-----------------------+
+-----------------------+             |     HistoryManager    | (Caretaker)
                                      +-----------------------+
                                      | - mementos: Memento[] |
                                      +-----------------------+
""",
        "code": """// 1. Memento: Immutable state snapshot
export class DocumentMemento {
  private readonly state: string;
  private readonly timestamp: number;

  constructor(state: string) {
    this.state = state;
    this.timestamp = Date.now();
  }

  // Only the originator should inspect this
  getState(): string {
    return this.state;
  }

  getTimestamp(): number {
    return this.timestamp;
  }
}

// 2. Originator: Object whose state needs saving/restoring
export class DocumentEditor {
  private content = "";

  type(text: string): void {
    this.content += text;
  }

  getContent(): string {
    return this.content;
  }

  save(): DocumentMemento {
    console.log(`[Editor] Snapshotting state: "${this.content}"`);
    return new DocumentMemento(this.content);
  }

  restore(memento: DocumentMemento): void {
    this.content = memento.getState();
    console.log(`[Editor] State restored to: "${this.content}"`);
  }
}

// 3. Caretaker: Manages history without knowing memento contents
export class HistoryCaretaker {
  private snapshots: DocumentMemento[] = [];

  push(memento: DocumentMemento): void {
    this.snapshots.push(memento);
  }

  pop(): DocumentMemento | null {
    return this.snapshots.pop() || null;
  }
}

// --- Usage ---
const editor = new DocumentEditor();
const history = new HistoryCaretaker();

editor.type("Chapter 1: The Beginning. ");
history.push(editor.save()); // Save checkpoint 1

editor.type("Chapter 2: The Storm. ");
history.push(editor.save()); // Save checkpoint 2

editor.type("Chapter 3: Catastrophe! ");
console.log("Current Content:", editor.getContent());

// Restore to checkpoint 2
const lastSave = history.pop();
if (lastSave) editor.restore(lastSave);

console.log("After rollback:", editor.getContent());
""",
        "edgeCases": [
            "**Memory Footprint**: Creating snapshots of large in-memory objects (e.g. 50MB canvas buffers) on every keystroke exhausts RAM quickly. Implement delta-snapshots or bound the history stack.",
            "**State Encapsulation Leaks**: Ensure that Memento does not expose mutable references (always copy deep values)."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When a snapshot of an object's state must be saved so that it can be restored to that state later.",
                "When a direct interface to obtaining the state would expose implementation details and break the object's encapsulation."
            ],
            "whenNotToUse": [
                "When clients create/destroy states so frequently that storage overhead becomes prohibitive."
            ]
        }
    },
    {
        "filename": "07_Observer_Pattern.md",
        "title": "Observer Pattern",
        "category": "Behavioral Pattern",
        "intent": "Define a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.",
        "problem": "Polling a service continuously to check for state updates (e.g. checking if stock prices changed every 500ms) wastes network bandwidth and CPU cycles. Tight coupling occurs if the publisher explicitly calls every single consumer.",
        "scenario": "Real-Time Stock Market Ticker & Crypto Price Streamer. When Bitcoin price updates, multiple subscribers (Trading Dashboard, SMS Alert Trigger, Risk Engine) receive automated broadcast pushes.",
        "diagram": """
+-----------------------------------+
|              Subject              |
+-----------------------------------+
| + attach(observer): void          |
| + detach(observer): void          |
| + notify(data): void              |
+-----------------------------------+
                  ▲
                  │
+-----------------------------------+
|          StockMarketFeed          |
+-----------------------------------+
                  │ (notifies)
                  ▼
+-----------------------------------+
|             Observer              |
+-----------------------------------+
| + update(priceData): void         |
+-----------------------------------+
                  ▲
       ┌──────────┴──────────┐
       │                     │
+-------------+       +--------------+
| MobileAppUI |       | RiskAnalyzer |
+-------------+       +--------------+
""",
        "code": """export interface PriceUpdate {
  symbol: string;
  price: number;
  timestamp: number;
}

// 1. Observer Interface
export interface StockObserver {
  onPriceUpdate(data: PriceUpdate): void;
}

// 2. Subject / Publisher
export class StockMarketFeed {
  private observers = new Set<StockObserver>();
  private currentPrices = new Map<string, number>();

  subscribe(observer: StockObserver): () => void {
    this.observers.add(observer);
    // Returns clean unsubscribe function
    return () => this.observers.delete(observer);
  }

  setPrice(symbol: string, newPrice: number): void {
    this.currentPrices.set(symbol, newPrice);
    const update: PriceUpdate = { symbol, price: newPrice, timestamp: Date.now() };
    this.notify(update);
  }

  private notify(update: PriceUpdate): void {
    for (const observer of this.observers) {
      try {
        observer.onPriceUpdate(update);
      } catch (err) {
        console.error("[Feed] Observer threw error during update broadcast:", err);
      }
    }
  }
}

// 3. Concrete Observers
export class TradingDashboard implements StockObserver {
  onPriceUpdate(data: PriceUpdate): void {
    console.log(`[Dashboard UI] Real-time chart rendered: ${data.symbol} = $${data.price}`);
  }
}

export class StopLossRiskEngine implements StockObserver {
  onPriceUpdate(data: PriceUpdate): void {
    if (data.price < 50000 && data.symbol === "BTC") {
      console.log(`[RISK ALERT] Triggering automated stop-loss liquidation for ${data.symbol}!`);
    }
  }
}

// --- Usage ---
const feed = new StockMarketFeed();
const ui = new TradingDashboard();
const risk = new StopLossRiskEngine();

const unsubUI = feed.subscribe(ui);
feed.subscribe(risk);

feed.setPrice("BTC", 52000);
feed.setPrice("BTC", 48500); // Triggers Risk Alert

unsubUI(); // Unsubscribe UI
feed.setPrice("BTC", 49000); // Only Risk engine notified
""",
        "edgeCases": [
            "**Lapsed Listener / Memory Leak Problem**: In languages with garbage collection, if an observer registers but forgets to unregister, the subject retains a reference to it, preventing the observer from being garbage-collected. Solution: Return explicit unsubscribe functions or use WeakRefs.",
            "**Cascading Update Loops**: Observer A updates Subject B, which triggers Observer C to update Subject A, causing infinite recursive broadcast storms."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When changes to the state of one object may require changing other objects, and the actual set of objects is unknown beforehand or changes dynamically.",
                "Event-driven architectures, GUI event listeners, reactive programming (RxJS)."
            ],
            "whenNotToUse": [
                "When subscribers need notifications in a strict sequential or transactional order."
            ]
        }
    },
    {
        "filename": "08_State_Pattern.md",
        "title": "State Pattern",
        "category": "Behavioral Pattern",
        "intent": "Allow an object to alter its behavior when its internal state changes. The object will appear to change its class.",
        "problem": "Managing state machines with giant `switch (state)` statements across dozens of methods makes code brittle. Adding a new state requires editing every single switch block, violating the Open/Closed Principle.",
        "scenario": "E-Commerce Order State Lifecycle (`PENDING` $\\rightarrow$ `PAID` $\\rightarrow$ `SHIPPED` $\\rightarrow$ `DELIVERED`). An order behaves differently depending on whether it has been paid, shipped, or cancelled.",
        "diagram": """
+-----------------------------------+
|               Order               | (Context)
+-----------------------------------+
| - state: OrderState               |
+-----------------------------------+
| + setState(state): void           |
| + pay(): void                     |
| + ship(): void                    |
| + cancel(): void                  |
+-----------------------------------+
                  │ (delegates)
                  ▼
+-----------------------------------+
|             OrderState            | (State Interface)
+-----------------------------------+
| + pay(order): void                |
| + ship(order): void               |
| + cancel(order): void             |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|  PendingState |   |   PaidState   |
+---------------+   +---------------+
""",
        "code": """export interface OrderState {
  pay(order: OrderContext): void;
  ship(order: OrderContext): void;
  cancel(order: OrderContext): void;
  getName(): string;
}

export class OrderContext {
  private state: OrderState;

  constructor() {
    this.state = new PendingState(); // Initial state
  }

  public setState(state: OrderState): void {
    console.log(`[Order] State transitioning: ${this.state.getName()} -> ${state.getName()}`);
    this.state = state;
  }

  public pay(): void { this.state.pay(this); }
  public ship(): void { this.state.ship(this); }
  public cancel(): void { this.state.cancel(this); }
}

// --- Concrete States ---
export class PendingState implements OrderState {
  getName() { return "PENDING"; }

  pay(order: OrderContext): void {
    console.log("✓ Payment authorized. Transitioning order to PAID.");
    order.setState(new PaidState());
  }

  ship(): void {
    console.log("❌ Cannot ship an unpaid order.");
  }

  cancel(order: OrderContext): void {
    console.log("✓ Order cancelled.");
    order.setState(new CancelledState());
  }
}

export class PaidState implements OrderState {
  getName() { return "PAID"; }

  pay(): void {
    console.log("❌ Order is already paid.");
  }

  ship(order: OrderContext): void {
    console.log("✓ Order dispatched with courier tracking. Transitioning to SHIPPED.");
    order.setState(new ShippedState());
  }

  cancel(): void {
    console.log("❌ Cannot cancel directly. Initiate refund flow first.");
  }
}

export class ShippedState implements OrderState {
  getName() { return "SHIPPED"; }

  pay(): void { console.log("❌ Already paid and shipped."); }
  ship(): void { console.log("❌ Already in transit."); }
  cancel(): void { console.log("❌ Cannot cancel items already in transit."); }
}

export class CancelledState implements OrderState {
  getName() { return "CANCELLED"; }
  pay(): void { console.log("❌ Cannot pay for a cancelled order."); }
  ship(): void { console.log("❌ Cannot ship a cancelled order."); }
  cancel(): void { console.log("❌ Order is already cancelled."); }
}

// --- Usage ---
const order = new OrderContext();
order.ship();   // Blocked
order.pay();    // Transitions to PAID
order.cancel(); // Blocked by business rules
order.ship();   // Transitions to SHIPPED
""",
        "edgeCases": [
            "**State Explosion**: Systems with hundreds of intermediate sub-states can produce an overwhelming number of classes. Combine with Hierarchical State Machines (Statecharts) if complexity grows too large.",
            "**Persistence & Serialization**: In distributed web apps, order state is stored in a database (e.g. `status = 'PAID'`). The Context must rehydrate the appropriate concrete State class based on database records upon request arrival."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When an object behaves differently depending on its current state.",
                "When you have massive conditionals (`if/else` or `switch`) spanning multiple methods based on an object's state.",
                "Workflow engines, document review pipelines, game character animations."
            ],
            "whenNotToUse": [
                "When an object has only 2 simple states that rarely change behavior."
            ]
        }
    },
    {
        "filename": "09_Strategy_Pattern.md",
        "title": "Strategy Pattern",
        "category": "Behavioral Pattern",
        "intent": "Define a family of algorithms, encapsulate each one, and make them interchangeable. Strategy lets the algorithm vary independently from clients that use it.",
        "problem": "Hardcoding multiple pricing discount algorithms or payment routing strategies directly inside a controller leads to massive conditional blocks that must be modified every time marketing adds a new campaign.",
        "scenario": "E-Commerce Dynamic Pricing & Surge Pricing Strategy. Calculating ride fares in Uber (Standard vs Surge vs Peak Hour vs Corporate Discount) dynamically at runtime.",
        "diagram": """
+-----------------------------------+
|           PricingContext          |
+-----------------------------------+
| - strategy: PricingStrategy       |
+-----------------------------------+
| + setStrategy(strategy): void     |
| + calculateFare(dist, time): num  |
+-----------------------------------+
                  │ (delegates)
                  ▼
+-----------------------------------+
|          PricingStrategy          |
+-----------------------------------+
| + calculate(dist, time): number   |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|  StandardFare |   |   SurgeFare   |
+---------------+   +---------------+
""",
        "code": """// 1. Strategy Interface
export interface PricingStrategy {
  calculate(baseRate: number, distanceKm: number, durationMin: number): number;
}

// 2. Concrete Strategies
export class RegularPricingStrategy implements PricingStrategy {
  calculate(baseRate: number, distanceKm: number, durationMin: number): number {
    return baseRate + (distanceKm * 1.5) + (durationMin * 0.25);
  }
}

export class SurgePricingStrategy implements PricingStrategy {
  private multiplier: number;

  constructor(multiplier = 2.0) {
    this.multiplier = multiplier;
  }

  calculate(baseRate: number, distanceKm: number, durationMin: number): number {
    const raw = baseRate + (distanceKm * 1.5) + (durationMin * 0.25);
    return Math.round(raw * this.multiplier * 100) / 100;
  }
}

export class CorporateDiscountStrategy implements PricingStrategy {
  calculate(baseRate: number, distanceKm: number, durationMin: number): number {
    const raw = baseRate + (distanceKm * 1.2) + (durationMin * 0.15);
    return Math.round(raw * 0.85 * 100) / 100; // 15% corporate discount
  }
}

// 3. Context
export class RideFareCalculator {
  private strategy: PricingStrategy;

  constructor(strategy: PricingStrategy) {
    this.strategy = strategy;
  }

  setStrategy(strategy: PricingStrategy): void {
    this.strategy = strategy;
  }

  computeFare(distanceKm: number, durationMin: number): number {
    return this.strategy.calculate(5.0, distanceKm, durationMin);
  }
}

// --- Usage ---
const ride = new RideFareCalculator(new RegularPricingStrategy());
console.log("Regular Ride Fare:", ride.computeFare(10, 20)); // $25.00

// High demand detected -> Switch to surge dynamically
ride.setStrategy(new SurgePricingStrategy(2.5));
console.log("Surge Ride Fare:", ride.computeFare(10, 20)); // $62.50
""",
        "edgeCases": [
            "**Client Awareness Requirement**: Clients must understand how strategies differ in order to select the proper one at runtime.",
            "**Strategy Statelessness**: Strategies should ideally be stateless pure functions to allow sharing instances across concurrent requests without race conditions."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you want to use different variants of an algorithm within an object and be able to switch from one algorithm to another during runtime.",
                "When you have a lot of similar classes that only differ in the way they execute some behavior.",
                "To isolate the business logic of an algorithm from the code that uses it."
            ],
            "whenNotToUse": [
                "If you only have a couple of algorithms that rarely change (a simple function with an if-statement is simpler)."
            ]
        }
    },
    {
        "filename": "10_Template_Method_Pattern.md",
        "title": "Template Method Pattern",
        "category": "Behavioral Pattern",
        "intent": "Define the skeleton of an algorithm in an operation, deferring some steps to subclasses. Template Method lets subclasses redefine certain steps of an algorithm without changing the algorithm's structure.",
        "problem": "ETL data extraction pipelines (CSV, JSON, XML) share identical execution flows: open connection, read raw stream, parse records, validate schema, sanitize fields, load into data warehouse, and close connection. Duplicating this workflow across 10 parser classes leads to duplicated boilerplate and inconsistent error handling.",
        "scenario": "Data Mining ETL Pipeline. A base `DataMiner` enforces the rigid steps: `openFile()` -> `extractData()` -> `parseData()` -> `validateData()` -> `loadToWarehouse()` -> `closeFile()`. Subclasses only implement format-specific parsing.",
        "diagram": """
+-----------------------------------+
|             DataMiner             | (Abstract Class)
+-----------------------------------+
| + mine(path): void (TEMPLATE)     |
| # openFile(path): void            |
| # extractData(): RawData          | (abstract)
| # parseData(raw): Record[]        | (abstract)
| # closeFile(): void               |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|   CsvMiner    |   |   JsonMiner   |
+---------------+   +---------------+
""",
        "code": """export interface ParsedRecord {
  id: string;
  data: Record<string, any>;
}

export abstract class DataMinerTemplate {
  // The Template Method: Final/Fixed skeleton algorithm
  public async mine(filePath: string): Promise<number> {
    console.log(`[ETL] Starting mining pipeline for: ${filePath}`);
    this.openFile(filePath);

    try {
      const raw = await this.extractData();
      const records = this.parseData(raw);
      const validated = this.validateData(records);
      await this.loadToWarehouse(validated);
      return validated.length;
    } finally {
      this.closeFile();
    }
  }

  // Common invariant steps implemented in base
  protected openFile(path: string): void {
    console.log(`  1. File descriptor opened for: ${path}`);
  }

  protected closeFile(): void {
    console.log("  5. File descriptor closed cleanly.");
  }

  protected validateData(records: ParsedRecord[]): ParsedRecord[] {
    console.log(`  3. Validating schema on ${records.length} records`);
    return records.filter((r) => r.id && Object.keys(r.data).length > 0);
  }

  protected async loadToWarehouse(records: ParsedRecord[]): Promise<void> {
    console.log(`  4. Bulk loaded ${records.length} records into Snowflake/BigQuery`);
  }

  // Abstract steps that subclasses MUST override
  protected abstract extractData(): Promise<string>;
  protected abstract parseData(raw: string): ParsedRecord[];
}

// Concrete Implementations
export class CsvDataMiner extends DataMinerTemplate {
  protected async extractData(): Promise<string> {
    return "id,name\\n1,Alice\\n2,Bob";
  }

  protected parseData(raw: string): ParsedRecord[] {
    console.log("  2. [CSV Parser] Splitting commas and headers");
    const lines = raw.split("\\n").slice(1);
    return lines.map((line) => {
      const [id, name] = line.split(",");
      return { id, data: { name } };
    });
  }
}

export class JsonDataMiner extends DataMinerTemplate {
  protected async extractData(): Promise<string> {
    return JSON.stringify([{ id: "3", name: "Charlie" }]);
  }

  protected parseData(raw: string): ParsedRecord[] {
    console.log("  2. [JSON Parser] Deserializing JSON tokens");
    const parsed = JSON.parse(raw);
    return parsed.map((item: any) => ({ id: item.id, data: { name: item.name } }));
  }
}

// --- Usage ---
const csvPipeline = new CsvDataMiner();
csvPipeline.mine("export_2026.csv");

const jsonPipeline = new JsonDataMiner();
jsonPipeline.mine("telemetry.json");
""",
        "edgeCases": [
            "**Breaking the Invariant**: If subclasses can override the master template method itself, the algorithm structure guarantee is lost. (In languages like Java/C#, mark the template method `final`).",
            "**Step Explosion**: If the template algorithm has 25 different abstract steps, implementing a subclass becomes tedious. Provide default implementations (hooks) for optional steps."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you want to let clients extend only particular steps of an algorithm, but not the whole algorithm or its structure.",
                "When multiple classes have almost identical algorithms with only minor differences."
            ],
            "whenNotToUse": [
                "When steps vary so wildly between formats that enforcing a single common skeleton becomes artificial."
            ]
        }
    },
    {
        "filename": "11_Visitor_Pattern.md",
        "title": "Visitor Pattern",
        "category": "Behavioral Pattern",
        "intent": "Represent an operation to be performed on the elements of an object structure. Visitor lets you define a new operation without changing the classes of the elements on which it operates.",
        "problem": "You have a complex object structure (e.g. Products in a cart: Groceries, Electronics, Liquor). Every time finance wants to calculate sales tax, or shipping wants to compute export customs duties, you must modify every single product class (`Grocery.computeTax()`, `Electronics.computeTax()`), cluttering domain models with unrelated concerns.",
        "scenario": "Multi-Category E-Commerce Tax and Export Regulatory Compliance Visitor. Adds new operational passes (US Sales Tax, EU VAT, Hazardous Materials Shipping Audit) without modifying core product classes.",
        "diagram": """
+-----------------------------------+
|              Element              |
+-----------------------------------+
| + accept(visitor: Visitor): void  |
+-----------------------------------+
                  ▲
        ┌─────────┴─────────┐
        │                   │
+---------------+   +---------------+
|   FoodItem    |   | ElectronicItem|
+---------------+   +---------------+
| + accept(v)   |   | + accept(v)   |
+---------------+   +---------------+
        │                   │
        └─────────┬─────────┘
                  ▼ (calls back)
+-----------------------------------+
|              Visitor              |
+-----------------------------------+
| + visitFood(item): void           |
| + visitElectronic(item): void     |
+-----------------------------------+
""",
        "code": """// 1. Visitor Interface
export interface CartVisitor {
  visitFood(item: FoodProduct): void;
  visitElectronic(item: ElectronicProduct): void;
}

// 2. Element Interface
export interface CartItem {
  accept(visitor: CartVisitor): void;
  getPrice(): number;
  getName(): string;
}

// 3. Concrete Elements
export class FoodProduct implements CartItem {
  private name: string;
  private price: number;
  public isOrganic: boolean;

  constructor(name: string, price: number, isOrganic = false) {
    this.name = name;
    this.price = price;
    this.isOrganic = isOrganic;
  }

  getName() { return this.name; }
  getPrice() { return this.price; }

  // Double Dispatch
  accept(visitor: CartVisitor): void {
    visitor.visitFood(this);
  }
}

export class ElectronicProduct implements CartItem {
  private name: string;
  private price: number;
  public batteryWattHours: number;

  constructor(name: string, price: number, batteryWattHours: number) {
    this.name = name;
    this.price = price;
    this.batteryWattHours = batteryWattHours;
  }

  getName() { return this.name; }
  getPrice() { return this.price; }

  accept(visitor: CartVisitor): void {
    visitor.visitElectronic(this);
  }
}

// 4. Concrete Visitors
export class SalesTaxVisitor implements CartVisitor {
  public totalTax = 0;

  visitFood(item: FoodProduct): void {
    // Groceries are tax-exempt (0% tax)
    console.log(`[Tax Visitor] Food item "${item.getName()}" is tax exempt ($0 tax).`);
  }

  visitElectronic(item: ElectronicProduct): void {
    // Electronics have 18% standard VAT
    const tax = Math.round(item.getPrice() * 0.18 * 100) / 100;
    this.totalTax += tax;
    console.log(`[Tax Visitor] Electronic "${item.getName()}" 18% tax: $${tax}`);
  }
}

export class DangerousGoodsShippingVisitor implements CartVisitor {
  public requiresHazmatDeclaration = false;

  visitFood(item: FoodProduct): void {
    // Food is non-hazardous
  }

  visitElectronic(item: ElectronicProduct): void {
    if (item.batteryWattHours > 100) {
      console.log(`[Shipping Visitor] ALERT: "${item.getName()}" exceeds 100Wh battery limit! Requires Hazmat handling.`);
      this.requiresHazmatDeclaration = true;
    }
  }
}

// --- Usage ---
const cart: CartItem[] = [
  new FoodProduct("Organic Apples", 15, true),
  new ElectronicProduct("Gaming Laptop", 1800, 99),
  new ElectronicProduct("Drone High-Capacity Battery Pack", 350, 160),
];

// Run Tax pass
const taxCalculator = new SalesTaxVisitor();
for (const item of cart) {
  item.accept(taxCalculator);
}
console.log(`Total Sales Tax to Remit: $${taxCalculator.totalTax}\\n`);

// Run Hazardous Goods Shipping pass without altering item classes
const shippingAudit = new DangerousGoodsShippingVisitor();
for (const item of cart) {
  item.accept(shippingAudit);
}
console.log("Cart Requires Hazmat Handling?", shippingAudit.requiresHazmatDeclaration);
""",
        "edgeCases": [
            "**Adding New Concrete Elements**: If you add a new element class (e.g. `LiquorProduct`), you MUST add a `visitLiquor()` method to the `CartVisitor` interface and update every single existing concrete visitor.",
            "**Access to Private Encapsulation**: Visitors often need deep access to internal element state, which might tempt developers to make private fields public."
        ],
        "tradeoffs": {
            "whenToUse": [
                "When you need to perform an operation on all elements of a complex object structure (such as an AST or shopping cart).",
                "When you want to clean up the business logic of auxiliary behaviors from the primary classes.",
                "When the element hierarchy rarely changes, but you frequently add new operations over them."
            ],
            "whenNotToUse": [
                "When the element class hierarchy changes frequently (adding an element forces refactoring all visitors)."
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

print(f"[Behavioral] Successfully generated {len(patterns)} in-depth pattern files.")
