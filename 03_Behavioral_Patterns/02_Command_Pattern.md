# Command Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Encapsulate a request as an object, thereby letting you parameterize clients with different requests, queue or log requests, and support undoable operations.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Coupling UI buttons or API controllers directly to business operations prevents features like action undo/redo, delayed queueing, macro recordings, and transactional rollback logs.

### Real-World Industry Example:
Transactional Banking Ledger with Undo / Reversal Stack. Every debit, credit, or transfer is packaged as an executable Command object that knows how to execute and how to reverse (`undo()`) itself cleanly.

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Receiver
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
```

---

## 5. Edge Cases & Failure Handling
- **Non-Reversible Operations**: External API calls like sending an SMS or firing a missile cannot be physically undone. In such cases, a compensating transaction (e.g. sending a cancellation email) must be executed.\n- **Memory Bloat in Long-Running Apps**: Storing unlimited commands in the undo stack consumes memory. Always bound the undo stack size (e.g. max 50 actions).

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you need to parameterize objects by an action to perform.\n- When you need to queue, schedule, or execute operations remotely.\n- When implementing multi-level undo/redo or transactional rollbacks.

### When NOT to Use / Anti-patterns:
- For simple direct method calls where undo, queueing, and logging are completely unnecessary.
