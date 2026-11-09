# Observer Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Define a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
Polling a service continuously to check for state updates (e.g. checking if stock prices changed every 500ms) wastes network bandwidth and CPU cycles. Tight coupling occurs if the publisher explicitly calls every single consumer.

### Real-World Industry Example:
Real-Time Stock Market Ticker & Crypto Price Streamer. When Bitcoin price updates, multiple subscribers (Trading Dashboard, SMS Alert Trigger, Risk Engine) receive automated broadcast pushes.

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
export interface PriceUpdate {
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
```

---

## 5. Edge Cases & Failure Handling
- **Lapsed Listener / Memory Leak Problem**: In languages with garbage collection, if an observer registers but forgets to unregister, the subject retains a reference to it, preventing the observer from being garbage-collected. Solution: Return explicit unsubscribe functions or use WeakRefs.\n- **Cascading Update Loops**: Observer A updates Subject B, which triggers Observer C to update Subject A, causing infinite recursive broadcast storms.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When changes to the state of one object may require changing other objects, and the actual set of objects is unknown beforehand or changes dynamically.\n- Event-driven architectures, GUI event listeners, reactive programming (RxJS).

### When NOT to Use / Anti-patterns:
- When subscribers need notifications in a strict sequential or transactional order.
