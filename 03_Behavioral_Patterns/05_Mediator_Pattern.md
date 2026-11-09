# Mediator Pattern

## Category: Behavioral Pattern

---

## 1. Core Intent & Definition
Define an object that encapsulates how a set of objects interact. Mediator promotes loose coupling by keeping objects from referring to each other explicitly, and lets you vary their interaction independently.

---

## 2. Real-Life Problem & Industry Scenario
### The Problem:
When multiple components communicate directly (e.g. 10 airplanes in an airspace coordinating runway access), every component must maintain references to all other 9 components ($O(N^2)$ connections), creating an unmaintainable web of dependencies.

### Real-World Industry Example:
Air Traffic Control (ATC) Runway Coordinator / Real-Time Chat Room. Aircraft do not communicate directly with each other; they communicate exclusively through the ATC Mediator, which arbitrates runway reservations safely.

---

## 3. Architecture & Visual Flow Diagram
```
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
```

---

## 4. Practical Implementation (TypeScript)
```typescript
// 1. Mediator Interface
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
```

---

## 5. Edge Cases & Failure Handling
- **God Mediator Anti-Pattern**: Over time, a mediator can become overly complex and turn into a monolithic 'God Object'. Keep mediators focused solely on interaction protocols.\n- **Single Point of Failure**: If the mediator crashes, all communication between colleagues stops.

---

## 6. Trade-offs & Production Considerations
### When to Use:
- When a set of objects communicate in well-defined but complex ways.\n- When reusing an object is difficult because it refers to and communicates with many other objects.\n- Chat rooms, dialog windows with interrelated UI controls, air traffic controllers.

### When NOT to Use / Anti-patterns:
- When only 2 or 3 components communicate simply (direct communication is clearer).
