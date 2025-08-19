# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements a real-time synchronous coupon issuance system designed for large-scale concurrent environments. The system handles 1 million potential clients competing for 1,000 limited coupons with immediate Pass/Fail responses.

## Architecture Overview

The system uses a hybrid synchronous/asynchronous architecture with the following key components:

### Core Design Principles
1. **Aggressive Edge Traffic Management** - Control traffic before reaching core services using API Gateway
2. **Atomic In-Memory Operations** - Redis + Lua scripting for lock-free concurrency control
3. **Decoupled Persistence** - Separate synchronous response from database writes using message queues
4. **Resilience & High Availability** - Multi-layer fault tolerance and recovery mechanisms

### System Components
- **API Gateway**: Rate limiting and throttling (Amazon API Gateway, NGINX Plus)
- **Load Balancer**: Horizontal scaling (AWS ALB, HAProxy)
- **Application Server**: Python with Docker containerization (FastAPI/Flask on EKS/ECS)
- **Redis Cluster**: Atomic coupon operations with multi-AZ deployment
- **Message Queue**: Asynchronous persistence (Apache Kafka, AWS SQS)
- **Database**: Final record store (PostgreSQL/MySQL with replication)
- **Consumer Service**: Python with Docker containers (Kubernetes Pods, ECS Tasks)

### Request Flow
1. Client request → API Gateway (rate limiting) → Load Balancer → App Server
2. App Server executes atomic Lua script on Redis Cluster
3. Immediate synchronous response to client (success/failure)
4. On success: Publish event to message queue
5. Consumer service processes queue → Write to database
6. Dead Letter Queue handles failed messages

## Implementation Tasks

### Infrastructure & Traffic Management
- [ ] **1. API Gateway Setup** - Configure rate limiting and throttling using token bucket algorithm
- [ ] **2. Load Balancer** - Implement horizontal scaling configuration  
- [ ] **3. Redis Cluster** - Design and implement multi-AZ deployment for high availability

### Core Logic & Data Models
- [ ] **4. Redis Stock Management** - Create data model for coupon stock (`coupon:event_id:stock`)
- [ ] **5. Redis Participant Tracking** - Create data model for participants (`coupon:event_id:participants`)
- [ ] **6. Lua Script Development** - Develop atomic coupon issuance with race condition prevention
- [ ] **7. Python Application Server** - Build with Docker containerization
- [ ] **8. Coupon API Endpoint** - Implement synchronous coupon issuance API using FastAPI/Flask

### Persistence & Messaging
- [ ] **9. Message Queue System** - Set up Apache Kafka or AWS SQS
- [ ] **10. Asynchronous Event Publishing** - Implement event publishing to message queue
- [ ] **11. Database Schema** - Design coupons and coupon_issuances tables
- [ ] **12. Consumer Service** - Create Python service with Docker for processing messages from queue
- [ ] **13. Idempotent Database Writes** - Implement with UNIQUE constraints

### Reliability & Error Handling
- [ ] **14. Dead Letter Queue** - Set up DLQ for failed message handling
- [ ] **15. Retry Logic** - Implement exponential backoff for consumer service
- [ ] **16. Data Integrity** - Create verification and reconciliation process
- [ ] **17. Monitoring** - Set up alerting for queue depth, DLQ, and Redis metrics
- [ ] **18. Client Error Handling** - Implement graceful failure handling for 429/503 errors

### Development & Operations
- [ ] **19. Load Testing** - Conduct comprehensive performance tuning
- [ ] **22. Docker Configuration** - Create Docker configuration files (Dockerfile, docker-compose.yml)
- [ ] **23. Python Project Setup** - Set up Python project structure with requirements.txt

## Key Design Principles

1. **Aggressive Edge Traffic Management** - Control traffic before reaching core services using API Gateway with token bucket rate limiting
2. **Atomic In-Memory Operations** - Redis + Lua scripting for lock-free concurrency control preventing race conditions
3. **Decoupled Persistence** - Separate synchronous response from database writes using message queues for performance
4. **Resilience & High Availability** - Multi-layer fault tolerance with DLQ, retry logic, and multi-AZ deployments

## Key Files

- `report.txt` - Detailed architecture design document (Korean)
- `TODO.md` - Standalone English implementation task list  
- `TODO_KO.md` - Standalone Korean implementation task list
- `CLAUDE_KO.md` - Korean version of this documentation

## Technology Stack Requirements

- **Programming Language**: Python 3.9+
- **Web Framework**: FastAPI (recommended) or Flask
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for local development, Kubernetes/ECS for production
- **Python Libraries**: redis-py, asyncio, pydantic, sqlalchemy, kafka-python

## Communication Guidelines

- Respond in both English and Korean for all interactions
- Keep CLAUDE.md in English and maintain CLAUDE_KO.md as the Korean version
- When updating CLAUDE.md, automatically update CLAUDE_KO.md with the Korean translation

## Notes

- This is a fresh repository with minimal content
- The `.qodo` directory exists but is empty
- Project scope appears to be coupon-related based on the repository name