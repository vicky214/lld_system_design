# Interpreter Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Given a language, define a representation for its grammar along with an interpreter that uses the representation to interpret sentences in the language.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Hardcoding custom filter conditions (e.g. `age > 18 AND (role = 'ADMIN' OR points > 100)`) into procedural if/else blocks fails when users or non-technical business admins need to author dynamic discount rules and filter criteria without deploying new code.

### Real-World Industry Example:
Dynamic Discount Rule & Query Filter Engine. E-commerce marketing managers define dynamic rules in JSON/DSL format to evaluate if a user cart qualifies for special promotions.

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export type Context = Record<string, any>;

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
```

---

## 5. Edge Cases & Failure Handling
- **Grammar Explosion**: Complex grammars with 50+ operators become hard to maintain as class hierarchies. For large languages, use parser generators (e.g. ANTLR or peg.js) instead.\n- **Performance Overhead**: Interpreting expressions via deep AST object graphs is slower than compiling rules to bytecode or native functions.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When the grammar is simple and stability is more important than raw execution efficiency.\n- Custom business rule evaluation, configuration query filters, calculator engines.

### When NOT to Use / Anti-patterns:
- Complex programming languages or high-frequency performance-critical parsing loops.
