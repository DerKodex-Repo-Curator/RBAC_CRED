# 🏗️ RBAC Policy Engine - Design Document

## Overview

This document explains the architecture, design decisions, and trade-offs made while building the RBAC Policy Engine.

## Table of Contents

1. [Architecture](#architecture)
2. [Core Components](#core-components)
3. [Design Decisions](#design-decisions)
4. [Trade-offs](#trade-offs)
5. [AI Integration](#ai-integration)
6. [State Management](#state-management)
7. [Validation Strategy](#validation-strategy)
8. [Future Improvements](#future-improvements)

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Chat UI                            │
│                   (User Interface Layer)                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST
┌─────────────────────────────▼───────────────────────────────────┐
│                     FastAPI Backend                              │
│                   (API Gateway Layer)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Chat Routes │  │ Policy Routes│  │ Discovery Routes        │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  Conversation Agent                              │
│               (AI/NLP Processing Layer)                          │
│  ┌──────────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ Claude API Client│  │ Intent Parser  │  │ State Machine   │  │
│  └──────────────────┘  └────────────────┘  └─────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Core Policy Engine                            │
│                  (Business Logic Layer)                          │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │Policy Builder│  │Decision Engine │  │ Validator           │  │
│  └──────────────┘  └────────────────┘  └─────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      Mock APIs                                   │
│                  (Data Discovery Layer)                          │
│  ┌───────────┐  ┌──────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Roles API │  │ Resources API│  │Context API│  │Validator API│ │
│  └───────────┘  └──────────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  State & Persistence                             │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────────┐  │
│  │ Schema Cache │  │ Session Manager│  │ File Storage        │  │
│  └──────────────┘  └────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Chat UI sends message to API
2. **API Processing** → FastAPI routes request to Conversation Agent
3. **NL Processing** → Claude interprets intent, identifies entities
4. **Validation** → Policy Builder validates against schemas
5. **Policy Update** → Rule added/modified in policy
6. **Response** → Structured response returned to UI
7. **Persistence** → Session and policy saved to disk

---

## Core Components

### 1. Data Models (`src/models/`)

**Purpose**: Type-safe data structures using Pydantic

- **Policy**: Root container for all rules
- **PolicyRule**: Individual access rule
- **PolicyCondition**: Conditional expression
- **ConditionGroup**: Logical grouping (AND/OR/NOT)
- **Role, Permission, Resource**: Schema entities

**Key Design**:
```python
class PolicyRule(BaseModel):
    name: str
    roles: List[str]           # Who
    resources: List[str]       # What
    permissions: List[str]     # How
    conditions: Optional[ConditionGroup]  # When
    effect: Decision           # ALLOW or DENY
    priority: int              # Evaluation order
```

### 2. Mock APIs (`src/mock_apis/`)

**Purpose**: Simulate external discovery services

- **RolesPermissionsAPI**: Role/permission catalog
- **ResourceSchemaAPI**: Resource types and supported actions
- **ContextSchemaAPI**: Available context attributes
- **PolicyValidatorAPI**: Validation logic

**Key Design**: These mock APIs return realistic data that would typically come from:
- IAM service (roles/permissions)
- Resource registry (resources)
- Context provider (attributes)

### 3. Core Engine (`src/core/`)

**PolicyBuilder**:
- Constructs policies from structured inputs
- Validates all inputs against discovered schemas
- Provides helpful error messages for invalid inputs

**DecisionEngine**:
- Evaluates access requests against policies
- Implements priority-based rule matching
- Evaluates complex conditions (AND/OR/NOT)
- Returns decisions with explanations

**SchemaCache**:
- Caches discovery API responses
- Persists cache to disk (JSON)
- TTL-based invalidation (1 hour default)
- Enables fast policy creation without repeated API calls

### 4. Conversation Agent (`src/agent/`)

**Purpose**: Natural language interface powered by Claude

**Key Features**:
- Schema-aware prompting
- Intent extraction
- Ambiguity detection
- Clarifying question generation
- Structured response parsing

**Prompt Engineering**:
```
System Prompt includes:
1. Available roles/resources/permissions
2. Resource-action compatibility matrix
3. Context attribute definitions
4. Response format specification
5. Examples of clarification scenarios
```

### 5. API Layer (`src/api/`)

**FastAPI Application** with endpoints for:
- Chat messaging
- Session management
- Policy CRUD
- Policy evaluation
- Schema discovery
- Export/download

---

## Design Decisions

### 1. Python + FastAPI + Pydantic

**Why**:
- Strong typing with runtime validation (Pydantic)
- Excellent async support (FastAPI)
- Rich AI/ML ecosystem
- Fast development cycle

**Alternative Considered**: Go with gRPC
- Would be faster but slower development
- Less mature AI library ecosystem

### 2. Claude for NL Processing

**Why**:
- Provided API key in assignment
- Excellent instruction following
- JSON output capability
- Context window supports full schema

**Approach**:
- Single system prompt with complete schema
- Structured JSON response format
- Fallback to regex for simple commands

### 3. Streamlit for UI

**Why**:
- Rapid prototyping
- Built-in chat components
- Python-native (consistency)
- Assignment focus is backend, not UI

**Alternative Considered**: React frontend
- Better UX but more development time
- Backend is the focus

### 4. File-Based Persistence

**Why**:
- Simple deployment (no database setup)
- Portable (JSON files)
- Sufficient for demo scale

**Alternative Considered**: SQLite/PostgreSQL
- Overkill for this use case
- Would add deployment complexity

### 5. Schema Caching Strategy

**Why**:
- Performance requirement: no repeated API calls
- Disk persistence: survives restarts
- TTL-based: allows eventual refresh

**Implementation**:
```python
# Cache is loaded on startup
schemas = cache.discover_and_cache_schemas(apis)

# Subsequent policy operations use cached data
# No API calls during normal operation
```

---

## Trade-offs

### 1. Determinism vs Flexibility

**Trade-off**: Claude responses can vary

**Solution**:
- Structured JSON output format
- Fallback parsing logic
- Special commands bypass Claude entirely

### 2. Validation Strictness vs Usability

**Trade-off**: Strict validation can frustrate users

**Solution**:
- Helpful error messages with suggestions
- Show valid options when rejecting input
- Clarifying questions for ambiguity

### 3. State Persistence vs Complexity

**Trade-off**: Full persistence adds complexity

**Solution**:
- File-based JSON storage
- Session IDs for multi-user support
- Graceful degradation if files lost

### 4. Schema Caching vs Freshness

**Trade-off**: Cached data may become stale

**Solution**:
- Configurable TTL (default 1 hour)
- Force refresh endpoint available
- Cache info endpoint for debugging

---

## AI Integration

### How Claude is Used

1. **Intent Detection**: Identify what user wants to do
2. **Entity Extraction**: Extract roles, resources, permissions
3. **Ambiguity Detection**: Recognize incomplete specifications
4. **Question Generation**: Create relevant clarifying questions
5. **Response Structuring**: Format output as JSON

### Prompt Design Principles

1. **Complete Schema**: Full schema in system prompt
2. **Format Specification**: Exact JSON structure expected
3. **Examples**: Clarification scenarios
4. **Constraints**: What to accept/reject

### Fallback Strategy

Non-AI commands are handled directly:
- `list roles/resources/permissions`
- `show policy`
- `validate`
- `help`
- `clear`

This ensures core functionality works even if Claude API fails.

---

## State Management

### Session State

```
data/sessions/{session_id}.json
├── conversation_history
├── policy
├── created_at
├── updated_at
└── metadata
```

### Schema Cache

```
data/schema_cache.json
├── roles (from RolesPermissionsAPI)
├── resources (from ResourceSchemaAPI)
├── context (from ContextSchemaAPI)
├── timestamps
└── discovered_at
```

### Recovery on Restart

1. Load schema cache (if valid)
2. Skip discovery API calls
3. Load existing sessions
4. Resume conversation state

---

## Validation Strategy

### Multi-Layer Validation

1. **Syntax**: Pydantic model validation
2. **Schema**: Check against discovered catalogs
3. **Semantic**: Resource-action compatibility
4. **Logical**: Conflict detection, duplicates

### Validation Flow

```
User Input
    │
    ▼
┌───────────────┐
│ Claude Parse  │ ──▶ Reject invalid JSON
└───────────────┘
    │
    ▼
┌───────────────┐
│ Schema Check  │ ──▶ Reject unknown roles/resources
└───────────────┘
    │
    ▼
┌───────────────┐
│ Compatibility │ ──▶ Reject unsupported actions
└───────────────┘
    │
    ▼
┌───────────────┐
│ Add to Policy │
└───────────────┘
```

### Error Messages

Always include:
- What's wrong
- Why it's wrong
- How to fix it
- Valid alternatives

---

## Future Improvements

### If More Time Was Available

1. **WebSocket Chat**: Real-time streaming responses
2. **Policy Versioning**: Track changes over time
3. **Import/Export**: Load existing policies
4. **Visual Policy Editor**: Drag-and-drop rules
5. **A/B Testing**: Compare policy versions
6. **Audit Logging**: Track all access decisions
7. **Multi-tenant**: Isolate policies per organization
8. **Policy Simulation**: Bulk test with sample requests
9. **Natural Language Queries**: "Who can delete invoices?"
10. **Conflict Resolution**: Automatic rule ordering

### Production Considerations

1. **Authentication**: Add API key/OAuth
2. **Rate Limiting**: Prevent abuse
3. **Database**: PostgreSQL for scale
4. **Caching**: Redis for sessions
5. **Monitoring**: Prometheus/Grafana
6. **CI/CD**: Automated testing/deployment

---

## Conclusion

This RBAC Policy Engine demonstrates:

- **Clean Architecture**: Layered design with clear separation
- **AI Integration**: Thoughtful use of LLM capabilities
- **Validation**: Multi-layer correctness checking
- **State Management**: Persistent, recoverable sessions
- **Performance**: Cached schemas, efficient evaluation
- **Developer Experience**: Good docs, tests, tooling

The system balances simplicity with capability, using AI to enhance usability while maintaining deterministic policy evaluation.
