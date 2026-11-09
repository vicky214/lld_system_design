# Saga Orchestration Pattern

## 1. Classification & Intent
- **Pattern Category:** Distributed Data Consistency Patterns
- **Core Intent:** Coordinate distributed multi-service transactions through a centralized orchestrator that executes sequential local transactions and issues compensating undo operations if any step fails.

---

## 2. Real-Life Industry Example
Uber Trip Booking / Flight Booking Engines (Book Flight -> Reserve Hotel -> Rent Car; if car rental fails, the orchestrator triggers refund flight and cancel hotel reservation).

---

## 3. Architecture & Flow Diagram
```
+--------------------------------+
                 |       Saga Orchestrator        |
                 +--------------------------------+
                    |             |            |
         1. Process |  2. Process | 3. Process |
            Payment |     Seat    |    Hotel   |
                    v             v            v
           +-----------+  +-----------+  +-----------+
           | Payment   |  | Seat      |  | Hotel     |
           | Service   |  | Service   |  | Service   |
           +-----------+  +-----------+  +-----------+
                    |             |            |
           (OK)     |   (OK)      |   (FAILS)  |
                    |             |            |
                    +=============+============+
                                  |
                   Trigger Compensating Rollbacks:
                   <- 4. Cancel Seat Reservation
                   <- 5. Refund Captured Payment
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Saga Orchestrator Pattern
 * Deterministic multi-step transaction with automated rollback compensation
 */

export interface SagaStep {
  name: string;
  execute: () => Promise<boolean>;
  compensate: () => Promise<void>;
}

export class OrderBookingSagaOrchestrator {
  private executedSteps: SagaStep[] = [];

  async executeSaga(steps: SagaStep[]): Promise<boolean> {
    console.log('[SagaOrchestrator] Starting distributed Saga execution...');

    for (const step of steps) {
      try {
        console.log(`[SagaOrchestrator] Executing step: ${step.name}`);
        const success = await step.execute();
        
        if (!success) {
          throw new Error(`Step ${step.name} returned failure flag.`);
        }

        this.executedSteps.push(step);
      } catch (err: any) {
        console.error(`[SagaOrchestrator] Step '${step.name}' failed: ${err.message}. Initiating rollback compensation!`);
        await this.rollback();
        return false;
      }
    }

    console.log('[SagaOrchestrator] Saga successfully completed all steps.');
    return true;
  }

  private async rollback(): Promise<void> {
    // Compensate in exact reverse order
    while (this.executedSteps.length > 0) {
      const step = this.executedSteps.pop()!;
      try {
        console.log(`[SagaOrchestrator] Executing compensating rollback: ${step.name}`);
        await step.compensate();
      } catch (compensateError: any) {
        // Critical: Compensations must be idempotent and retryable
        console.error(`[SagaOrchestrator CRITICAL] Failed to compensate ${step.name}: ${compensateError.message}`);
      }
    }
  }
}

// Practical usage example: E-Commerce Checkout Saga
export function buildCheckoutSaga(orderId: string, amount: number) {
  const orchestrator = new OrderBookingSagaOrchestrator();

  const steps: SagaStep[] = [
    {
      name: 'ReserveInventory',
      execute: async () => {
        console.log(` -> Reserving stock items for order ${orderId}`);
        return true;
      },
      compensate: async () => {
        console.log(` <- Restoring reserved stock items for order ${orderId}`);
      }
    },
    {
      name: 'ChargePayment',
      execute: async () => {
        console.log(` -> Processing payment of $${amount} via Stripe`);
        return true;
      },
      compensate: async () => {
        console.log(` <- Issuing refund for order ${orderId}`);
      }
    },
    {
      name: 'DispatchLogistics',
      execute: async () => {
        console.log(` -> Calling FedEx dispatch API`);
        // Simulate logistics failure
        throw new Error('FedEx API 503 Courier Unavailable');
      },
      compensate: async () => {
        console.log(` <- Voiding shipment dispatch`);
      }
    }
  ];

  return { orchestrator, steps };
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Compensation Failures**: What happens if the refund API call in `compensate()` throws an error? The orchestrator must retry compensations with exponential backoff or emit an alert to a Human Escalation Queue.
2. **Semantic Lock Violations / Dirty Reads**: Because local transactions commit immediately before subsequent steps complete, other transactions can read intermediate states. Mitigation: Use status flags (`PENDING_APPROVAL`) until final confirmation.
3. **Orchestrator Node Crash**: If the orchestrator server dies mid-saga, the transaction is abandoned. Mitigation: Persist state transitions to a durable Saga Log (e.g. Temporal.io or AWS Step Functions).

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Complex distributed workflows involving 3 or more services where strict step sequencing and error recovery visibility is mandatory.

### When NOT to Use:
- Simple 2-service interactions where Choreography (event-driven) is simpler without needing a dedicated orchestrator service.
