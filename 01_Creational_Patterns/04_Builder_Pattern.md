# Builder Pattern

## Category: Creational Pattern

---

## 1. Core Intent & Definition
Separate the construction of a complex object from its representation so that the same construction process can create different representations.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
When constructing complex domain objects with dozens of optional configurations, constructors become unwieldy ('Telescoping Constructor Anti-Pattern'), parameters become error-prone (passing 5 boolean flags in a row), and object immutability is difficult to guarantee.

### Real-World Industry Example:
Dynamic SQL Query / API Request Builder. Constructing parameterized, injection-safe SQL queries with dynamic filters, joins, pagination, and sorting based on user search parameters.

---

## 3. Architecture & Visual Flow Diagram
```
+-------------------------------------------------------+
|                      QueryBuilder                     |
+-------------------------------------------------------+
| - table: string                                       |
| - fields: string[]                                    |
| - conditions: string[]                                |
| - params: any[]                                       |
| - limitValue?: number                                 |
+-------------------------------------------------------+
| + select(fields): QueryBuilder                        |
| + from(table): QueryBuilder                           |
| + where(field, operator, value): QueryBuilder         |
| + limit(count): QueryBuilder                          |
| + build(): { sql: string, params: any[] }             |
+-------------------------------------------------------+
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface CompiledQuery {
  sql: string;
  params: any[];
}

export class SqlQueryBuilder {
  private tableName = "";
  private selectFields: string[] = ["*"];
  private whereConditions: string[] = [];
  private orderFields: string[] = [];
  private limitCount?: number;
  private offsetCount?: number;
  private queryParams: any[] = [];

  public from(table: string): this {
    if (!table || table.trim().length === 0) {
      throw new Error("Table name must not be empty.");
    }
    this.tableName = table;
    return this;
  }

  public select(...fields: string[]): this {
    if (fields.length > 0) {
      this.selectFields = fields;
    }
    return this;
  }

  public where(field: string, operator: "=" | "!=" | ">" | "<" | "LIKE", value: any): this {
    this.queryParams.push(value);
    const placeholder = `$${this.queryParams.length}`;
    this.whereConditions.push(`${field} ${operator} ${placeholder}`);
    return this;
  }

  public orderBy(field: string, direction: "ASC" | "DESC" = "ASC"): this {
    this.orderFields.push(`${field} ${direction}`);
    return this;
  }

  public paginate(page: number, pageSize: number): this {
    this.limitCount = pageSize;
    this.offsetCount = (Math.max(1, page) - 1) * pageSize;
    return this;
  }

  public build(): CompiledQuery {
    if (!this.tableName) {
      throw new Error("Cannot build query without target table name. Call .from('table') first.");
    }

    let sql = `SELECT ${this.selectFields.join(", ")} FROM ${this.tableName}`;

    if (this.whereConditions.length > 0) {
      sql += ` WHERE ${this.whereConditions.join(" AND ")}`;
    }

    if (this.orderFields.length > 0) {
      sql += ` ORDER BY ${this.orderFields.join(", ")}`;
    }

    if (this.limitCount !== undefined) {
      sql += ` LIMIT ${this.limitCount}`;
    }

    if (this.offsetCount !== undefined) {
      sql += ` OFFSET ${this.offsetCount}`;
    }

    return {
      sql: sql + ";",
      params: [...this.queryParams],
    };
  }
}

// --- Usage ---
const query = new SqlQueryBuilder()
  .from("users")
  .select("id", "email", "created_at")
  .where("status", "=", "ACTIVE")
  .where("age", ">", 21)
  .orderBy("created_at", "DESC")
  .paginate(1, 20)
  .build();

console.log("Generated SQL:", query.sql);
console.log("Sanitized Parameters:", query.params);
```

---

## 5. Edge Cases & Failure Handling
- **Incomplete State Building**: Client calls `.build()` before mandatory fields (e.g. `.from()`) are specified. Throw informative validation errors inside `.build()`.\n- **Reusability Contamination**: Calling `.build()` multiple times on the same builder without clearing state can accidentally append duplicate conditions. Solution: Make builders single-use or clone internal state.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- To get rid of a 'telescoping constructor' with 4+ optional parameters.\n- When construction of an object must allow different representations for the object that's constructed.\n- When you want to enforce immutable objects after construction.

### When NOT to Use / Anti-patterns:
- For simple, data-only entities with only 1 or 2 fields (plain object literals are cleaner).
