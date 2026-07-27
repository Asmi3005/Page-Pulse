# Page Pulse — Task B: Design for Scale

## Overview

The implementation from Task A works well for normal traffic, but it is designed as a synchronous service where each request waits for the target website to respond. For a workload of **10,000 audits per day** with **bursts of 500 concurrent requests**, this approach can increase latency because API workers remain busy while waiting for external websites.

To make the service production-ready, I would separate request handling from the actual audit work. The API should respond quickly, while background workers perform the slower URL fetches.

### Assumed SLA

- Cache hit: **<100 ms (P95)**
- Cache miss acknowledgement (`POST /audit`): **<300 ms (P95)**
- Audit completion: **<3 seconds (P95)**
- Request timeout: **10 seconds**

---

# 1. Architecture

## Components

| Component | Purpose |
|-----------|---------|
| Load Balancer | Distributes incoming requests across API instances. |
| FastAPI API | Validates requests, checks cache, applies rate limiting, and creates audit jobs. |
| Redis | Stores cached audit results, rate-limit counters, and the job queue. |
| Worker Service | Fetches webpages, extracts metadata, and stores results. |
| PostgreSQL | Stores job status and audit history. |
| Logging | Stores structured logs with request IDs for debugging. |

## Where state lives

- **Redis**
  - Cache
  - Queue
  - Rate limiting

- **PostgreSQL**
  - Job status
  - Audit history

- **API**
  - Stateless

Keeping API instances stateless makes horizontal scaling much easier.

---

## Request Flow

### Cache Hit

1. Client sends `POST /audit`
2. API validates request
3. Rate limit checked
4. Redis cache checked
5. Cached result returned immediately

### Cache Miss

1. Client sends request
2. Validation succeeds
3. Cache miss
4. Job stored in PostgreSQL
5. Job pushed to Redis queue
6. API returns **202 Accepted**
7. Worker processes the job
8. Result stored in PostgreSQL and Redis
9. Client retrieves result using Job ID

---

## Queue Strategy

Instead of allowing hundreds of API requests to simultaneously fetch external websites, all cache misses are placed into a Redis queue.

Benefits:

- Prevents API workers from being blocked
- Smooths sudden traffic spikes
- Allows API and workers to scale independently
- Makes response time predictable

Worker concurrency is intentionally limited so that the service never opens hundreds of outbound connections at once.

---

## Architecture Diagram

```text
            Client
               |
        Load Balancer
               |
        FastAPI API Layer
         /            \
   Cache Hit       Cache Miss
      |                 |
   Return 200      Redis Queue
                        |
                    Worker Pool
                        |
                 Fetch Target URL
                        |
          PostgreSQL + Redis Cache
                        |
               Client polls result
```

---

# 2. Technology Decisions

## FastAPI

Chosen because the project was already implemented using FastAPI in Task A and it provides excellent async support.

**Alternative:** Flask

**Why not Flask?**

Flask would also work, but FastAPI provides request validation and asynchronous support out of the box, making it a better fit.

---

## Redis

Redis is used for three purposes:

- Cache
- Queue
- Rate limiting

Using one technology for all three keeps the system simpler.

**Alternative:** In-memory cache

**Why rejected?**

An in-memory cache only works for a single API instance. Redis allows multiple instances to share the same cached data.

---

## PostgreSQL

Used for storing job status and audit history.

**Alternative:** Redis only

Redis is excellent for temporary data but not ideal as the permanent source of truth.

---

## Background Workers

The API should only accept requests.

Workers perform the slower network operations.

This separation keeps the API responsive during traffic bursts.

---

# 3. Failure Modes

## 1. Traffic Spike

If hundreds of requests arrive together, the queue may grow faster than workers can process jobs.

**Mitigation**

- Monitor queue length
- Increase worker count
- Return `503 Retry-After` if overloaded

---

## 2. Redis Failure

Redis stores the cache, queue, and rate limits.

If Redis becomes unavailable:

- Reject new jobs temporarily
- Alert operators
- Recover using managed Redis failover

---

## 3. External Website Issues

Some websites may be slow or unavailable.

**Mitigation**

- Request timeout
- Retry transient failures
- Mark failed jobs instead of blocking the queue

---

# 4. Monitoring and Alerts

I would monitor:

- API latency (P50/P95/P99)
- Error rate
- Queue depth
- Cache hit ratio
- Worker utilization
- Redis health
- PostgreSQL health
- Number of timeouts

Alerts should trigger when:

- API latency exceeds SLA
- Queue grows continuously
- Error rate becomes unusually high
- Redis or PostgreSQL becomes unavailable

---

# 5. Rollback Strategy

If a deployment introduces errors:

1. Detect the issue using monitoring dashboards.
2. Stop the rollout.
3. Redeploy the previous stable version.
4. Verify latency and error rate return to normal.
5. Investigate the issue before deploying again.

Configuration values such as cache TTL, worker count, and rate limits should be stored as environment variables so they can be changed without modifying code.

---

# Future Improvements

If traffic increases significantly beyond the current requirements, I would consider:

- Webhook notifications instead of polling
- Auto-scaling workers based on queue length
- Distributed tracing using OpenTelemetry
- Kafka if the workload becomes much larger
- Multi-region deployment for higher availability

I do not think these are necessary for 10,000 audits per day, but they would become useful as the system grows.

---

# AI Usage

I used Cursor AI to brainstorm architecture ideas and generate an initial outline for this document. I then rewrote the design in my own words, simplified several technology choices, and selected an architecture that I felt best matched the expected scale of the assignment. I reviewed every design decision to ensure I could explain and justify it during an interview.
