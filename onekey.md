# Onekey

## Tagline

One key for every integration.

## About

Onekey is a unified API key platform that helps developers manage and use multiple third-party integrations through a single platform key. Instead of handling a separate key, auth flow, and SDK setup for each provider, users can securely store provider credentials once and access them through a standardized interface.

The project combines a backend proxy layer, a categorized SDK, and a web dashboard. This lets teams work with LLMs, databases, vector stores, data engineering tools, DevOps APIs, and utility APIs from one place while keeping provider-specific complexity behind the scenes.

## Motivation

Modern products depend on many external services. Every new integration usually brings repeated work:

- New auth setup and secret handling
- New request formats and endpoint patterns
- New SDK learning curve
- New monitoring and error handling logic

This creates fragmentation in developer workflows and increases the chance of misconfiguration, security leaks, and integration regressions.

Onekey was built to reduce this integration overhead by providing:

- A single platform key for day-to-day usage
- Consistent proxy routes for multiple categories
- Shared observability and usage tracking
- A predictable SDK experience across providers

## Features

### Unified Platform Key

- Generates and manages one platform key per user
- Allows provider access without exposing raw provider credentials in client code
- Supports secure key storage and controlled access through authenticated routes

### Multi-Category Integration Architecture

- LLM integrations
- Vector database integrations
- Cloud database integrations
- Data engineering integrations
- DevOps integrations
- API utility integrations

### Categorized Backend Mapping

- Provider routing is organized by category modules
- Operation mapping standardizes provider-specific endpoints and payloads
- Common auth and passthrough behaviors are centralized

### SDK for Developer Experience

- Python SDK with category clients
- Operation-based helper methods
- Environment-driven testing support for fast local and deployed validation

### Web Dashboard

- API key onboarding and management
- Unified key visibility and copy flow
- Usage monitoring and status views
- Integration testing workflows from the UI

### Usage Tracking and Monitoring

- Request metadata and status code logging
- Latency and token usage tracking where applicable
- Error visibility across providers

### Payment-Based Premium Upgrade

- Premium upgrade flow integrated with Dodo Payments
- Checkout session creation and verification
- Auto-refresh of subscription status on dashboard return

### Email Alerting

- User email notifications for integration request outcomes
- Status-aware alerting for success and negative responses
- Context included for provider/model/endpoint where available

## Challenges

### Provider Diversity

Different providers have different authentication models, endpoint structures, and payload conventions. Normalizing them without losing flexibility requires careful abstraction.

### Consistent Error Handling

Each provider returns different error formats. Building a unified developer experience while preserving useful provider-level detail is non-trivial.

### Secure Secret Management

The platform must decrypt and use provider keys server-side while preventing accidental exposure in logs, client payloads, or frontend rendering.

### Cross-Category Scalability

As the number of integrations grows, route and operation mapping can become hard to maintain without strict modularization and naming conventions.

### Payment Verification Reliability

Subscription upgrades must only activate after verified payment completion. This requires robust status checks and resilient return-flow handling.

### Requestly and External Tool Workflow Gaps

External tools may not always provide direct deep-link import APIs for fully automated prefilled requests. Maintaining a reliable fallback workflow is necessary.

## Vision

Onekey aims to become a developer-first integration layer where adding a new provider feels as simple as adding a new operation map, not building a new integration stack from scratch.

The long-term goal is to make integration development faster, safer, and easier to scale for both solo builders and engineering teams.
