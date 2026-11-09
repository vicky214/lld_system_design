# Memento Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Without violating encapsulation, capture and externalize an object's internal state so that the object can be restored to this state later.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
To implement autosave or state rollback, an external history manager might try to inspect and copy private fields of an entity. This breaks encapsulation and exposes internal state.

### Real-World Industry Example:
Rich Text Document Editor Revision History & Autosave. The document (Originator) produces an opaque snapshot (Memento) of its internal state and stores it in the History Manager (Caretaker).

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Memento: Immutable state snapshot
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
```

---

## 5. Edge Cases & Failure Handling
- **Memory Footprint**: Creating snapshots of large in-memory objects (e.g. 50MB canvas buffers) on every keystroke exhausts RAM quickly. Implement delta-snapshots or bound the history stack.\n- **State Encapsulation Leaks**: Ensure that Memento does not expose mutable references (always copy deep values).

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When a snapshot of an object's state must be saved so that it can be restored to that state later.\n- When a direct interface to obtaining the state would expose implementation details and break the object's encapsulation.

### When NOT to Use / Anti-patterns:
- When clients create/destroy states so frequently that storage overhead becomes prohibitive.
