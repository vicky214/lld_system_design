# Template Method Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Define the skeleton of an algorithm in an operation, deferring some steps to subclasses. Template Method lets subclasses redefine certain steps of an algorithm without changing the algorithm's structure.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
ETL data extraction pipelines (CSV, JSON, XML) share identical execution flows: open connection, read raw stream, parse records, validate schema, sanitize fields, load into data warehouse, and close connection. Duplicating this workflow across 10 parser classes leads to duplicated boilerplate and inconsistent error handling.

### Real-World Industry Example:
Data Mining ETL Pipeline. A base `DataMiner` enforces the rigid steps: `openFile()` -> `extractData()` -> `parseData()` -> `validateData()` -> `loadToWarehouse()` -> `closeFile()`. Subclasses only implement format-specific parsing.

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface ParsedRecord {
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
    return "id,name\n1,Alice\n2,Bob";
  }

  protected parseData(raw: string): ParsedRecord[] {
    console.log("  2. [CSV Parser] Splitting commas and headers");
    const lines = raw.split("\n").slice(1);
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
```

---

## 5. Edge Cases & Failure Handling
- **Breaking the Invariant**: If subclasses can override the master template method itself, the algorithm structure guarantee is lost. (In languages like Java/C#, mark the template method `final`).\n- **Step Explosion**: If the template algorithm has 25 different abstract steps, implementing a subclass becomes tedious. Provide default implementations (hooks) for optional steps.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When you want to let clients extend only particular steps of an algorithm, but not the whole algorithm or its structure.\n- When multiple classes have almost identical algorithms with only minor differences.

### When NOT to Use / Anti-patterns:
- When steps vary so wildly between formats that enforcing a single common skeleton becomes artificial.
