# Asynchronous Request-Reply Pattern

## 1. Classification & Intent
- **Pattern Category:** Microservices Architecture Patterns
- **Core Intent:** Decouple long-running synchronous HTTP requests by returning an immediate HTTP 202 Accepted status with a polling status URL or webhook callback reference while processing proceeds asynchronously in the background.

---

## 2. Real-Life Industry Example
Stripe Export API, AWS Async Video Transcoder, and OpenAI Batch API (submitting a multi-gigabyte financial CSV export returns a job token; client polls `/v1/jobs/{id}` until status is COMPLETED).

---

## 3. Architecture & Flow Diagram
```
Client                             API Server                   Worker / Queue
  |                                    |                              |
  |-- 1. POST /api/v1/video/transcode->|                              |
  |                                    |-- 2. Push job to queue ----->|
  |<- 3. 202 Accepted (Location: /jobs)|                              |
  |      { jobId: "job-123" }          |                              |
  |                                    |                              |-- 3. Transcode 4K video...
  |-- 4. GET /api/v1/jobs/job-123 ---->|                              |   (Takes 5 minutes)
  |<- 5. 200 OK { status: "RUNNING" } -|                              |
  |                                    |                              |
  |                                    |<-- 6. Job Completed Event ---|
  |-- 7. GET /api/v1/jobs/job-123 ---->|                              |
  |<- 8. 200 OK { status: "COMPLETED", |                              |
  |      downloadUrl: "https://..." } -|                              |
```

---

## 4. Practical Production Implementation (TypeScript)
```typescript
/**
 * Asynchronous Request-Reply Pattern
 * Handling long-running tasks with polling tokens and async background execution
 */

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface AsyncJob<T = any> {
  jobId: string;
  status: JobStatus;
  progressPercent: number;
  result?: T;
  error?: string;
  createdAt: number;
  updatedAt: number;
}

export class AsyncRequestReplyService {
  private jobStore = new Map<string, AsyncJob>();

  async submitJob(taskPayload: { videoUrl: string; targetResolution: string }): Promise<{ jobId: string; statusUrl: string }> {
    const jobId = `job-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
    
    const newJob: AsyncJob = {
      jobId,
      status: 'PENDING',
      progressPercent: 0,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    this.jobStore.set(jobId, newJob);

    // Trigger async background processing without awaiting
    this.processJobAsync(jobId, taskPayload).catch(err => {
      console.error(`[Worker] Unhandled failure on job ${jobId}: ${err.message}`);
    });

    console.log(`[AsyncRequestReply] Job ${jobId} accepted. Returning 202 to client.`);
    return {
      jobId,
      statusUrl: `/api/v1/jobs/${jobId}`
    };
  }

  getJobStatus(jobId: string): AsyncJob | null {
    return this.jobStore.get(jobId) || null;
  }

  private async processJobAsync(jobId: string, payload: any): Promise<void> {
    const job = this.jobStore.get(jobId)!;
    job.status = 'PROCESSING';
    job.updatedAt = Date.now();

    // Emulate long multi-stage processing
    for (let progress = 20; progress <= 100; progress += 40) {
      await new Promise(resolve => setTimeout(resolve, 50));
      job.progressPercent = progress;
      job.updatedAt = Date.now();
      console.log(`[Worker] Job ${jobId} progress: ${progress}%`);
    }

    job.status = 'COMPLETED';
    job.result = {
      downloadUrl: `https://storage.example.com/rendered/${jobId}.mp4`,
      filesizeBytes: 524288000
    };
    job.updatedAt = Date.now();
    console.log(`[Worker] Job ${jobId} finished successfully.`);
  }
}
```

---

## 5. Edge Cases & Failure Scenarios
1. **Client Polling Stampede**: Clients aggressive polling every 100ms can overwhelm the API gateway. Mitigation: Include `Retry-After: 10` headers in HTTP 202 responses or provide WebSocket/Server-Sent Events (SSE) alternative push channels.
2. **Worker Node Termination During Job Execution**: If the worker pod crashes mid-execution, the job status remains stuck in `PROCESSING`. Mitigation: Heartbeat timestamps and an orphaned job sweeper worker to re-enqueue.
3. **Job Store Retention**: Accumulation of completed job records wastes memory/disk. Implement TTL auto-expiry (e.g., Redis EXPIRE or DynamoDB TTL) after 24 hours.

---

## 6. Trade-offs: When to Use vs When NOT to Use
### When to Use:
- Long operations taking more than 2-3 seconds (batch report exports, video encoding, AI model inferences, ledger reconciliations) where HTTP timeouts would occur.

### When NOT to Use:
- Fast read/write queries (< 200ms) where traditional synchronous request-response is simpler and more responsive for the user.
