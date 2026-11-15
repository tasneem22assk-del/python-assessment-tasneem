#AI usage :
tool used:claude(anthropic)
T6 - REST API AND JSON design
- The solution were written by AI (Claude).
- I copied the code into my project.
- I read through the code to understand how it works.





# Ticket REST API Design

This document describes a REST API for managing support tickets. It is a design only; no web server is implemented. The rules follow the `Ticket` class in `tasks/t3_ticket.py`.

## 1. Resource model

A **ticket** has the following fields:

| Field      | Type            | Description                                         |
|------------|-----------------|-----------------------------------------------------|
| `id`       | integer         | Positive number, created by the server              |
| `title`    | string          | Required, must not be empty                         |
| `priority` | string          | Required: `LOW`, `MEDIUM` or `HIGH`                 |
| `assignee` | string or null  | Username of the agent, `null` when not assigned     |
| `status`   | string          | `OPEN`, `IN_PROGRESS` or `RESOLVED`                 |

New tickets always start with `status = "OPEN"` and `assignee = null`. The client cannot set these on creation.

### Valid status transitions

```
OPEN ──────► IN_PROGRESS ──────► RESOLVED
  ▲     (only when assigned)        │
  └─────────────────────────────────┘
```

Any other transition is rejected with `409 Conflict`.

## 2. Endpoints

All requests and responses use `Content-Type: application/json`.

### 2.1 `POST /tickets` — Create a ticket

**Request**

```http
POST /tickets
Content-Type: application/json
```

```json
{
  "title": "Laptop issue",
  "priority": "HIGH"
}
```

**Responses**

| Code | Meaning                | When                                              |
|------|------------------------|---------------------------------------------------|
| 201  | Created                | Ticket created successfully                       |
| 422  | Unprocessable Entity   | Missing or empty `title`, or invalid `priority`   |

**201 Created**

```http
HTTP/1.1 201 Created
Location: /tickets/1
```

```json
{
  "id": 1,
  "title": "Laptop issue",
  "priority": "HIGH",
  "assignee": null,
  "status": "OPEN"
}
```

**422 Unprocessable Entity**

```json
{
  "error": "INVALID_PAYLOAD",
  "message": "title must not be empty"
}
```

### 2.2 `GET /tickets/{id}` — Get one ticket

**Request**

```http
GET /tickets/1
```

**Responses**

| Code | Meaning     | When                              |
|------|-------------|-----------------------------------|
| 200  | OK          | Ticket found                      |
| 404  | Not Found   | No ticket with this `id`          |

**200 OK**

```json
{
  "id": 1,
  "title": "Laptop issue",
  "priority": "HIGH",
  "assignee": "AgentA",
  "status": "IN_PROGRESS"
}
```

**404 Not Found**

```json
{
  "error": "TICKET_NOT_FOUND",
  "message": "Ticket 99 does not exist"
}
```

### 2.3 `GET /tickets?status=OPEN` — List tickets by status

**Request**

```http
GET /tickets?status=OPEN
```

The `status` query parameter is optional. Without it, all tickets are returned.

**Responses**

| Code | Meaning                | When                                         |
|------|------------------------|----------------------------------------------|
| 200  | OK                     | Returns a list (can be empty)                |
| 422  | Unprocessable Entity   | `status` is not a valid value                |

**200 OK**

```json
[
  {
    "id": 1,
    "title": "Laptop issue",
    "priority": "HIGH",
    "assignee": null,
    "status": "OPEN"
  },
  {
    "id": 3,
    "title": "VPN access",
    "priority": "LOW",
    "assignee": "AgentB",
    "status": "OPEN"
  }
]
```

If no tickets match, the response is `200 OK` with an empty list `[]`, not `404`. The list exists; it is just empty.

**422 Unprocessable Entity**

```json
{
  "error": "INVALID_PAYLOAD",
  "message": "status must be one of OPEN, IN_PROGRESS, RESOLVED"
}
```

### 2.4 `PATCH /tickets/{id}/status` — Change ticket status

**Request**

```http
PATCH /tickets/1/status
Content-Type: application/json
```

```json
{
  "status": "IN_PROGRESS"
}
```

**Responses**

| Code | Meaning                | When                                                       |
|------|------------------------|------------------------------------------------------------|
| 200  | OK                     | Status changed                                             |
| 404  | Not Found              | No ticket with this `id`                                   |
| 422  | Unprocessable Entity   | `status` missing or not a known value                      |
| 409  | Conflict               | Valid value, but not allowed from the current status       |

**200 OK**

```json
{
  "id": 1,
  "title": "Laptop issue",
  "priority": "HIGH",
  "assignee": "AgentA",
  "status": "IN_PROGRESS"
}
```

**409 Conflict** (example: trying to resolve an `OPEN` ticket)

```json
{
  "error": "INVALID_TRANSITION",
  "message": "Ticket is not in a valid state"
}
```

**422 vs 409:** `422` means the request itself is wrong (for example `"status": "DONE"`, which does not exist). `409` means the request is correct, but it conflicts with the ticket's current state (for example `"status": "RESOLVED"` while the ticket is still `OPEN`).

## 3. Error format

Every error response uses the same JSON structure, so clients can handle all errors the same way:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable explanation"
}
```

| HTTP code | `error` value          |
|-----------|------------------------|
| 404       | `TICKET_NOT_FOUND`     |
| 409       | `INVALID_TRANSITION`   |
| 422       | `INVALID_PAYLOAD`      |

## 4. Status code summary

| Code | Name                   | Used by                                           |
|------|------------------------|---------------------------------------------------|
| 200  | OK                     | `GET /tickets/{id}`, `GET /tickets`, `PATCH`      |
| 201  | Created                | `POST /tickets`                                   |
| 404  | Not Found              | `GET /tickets/{id}`, `PATCH`                      |
| 409  | Conflict               | `PATCH /tickets/{id}/status`                      |
| 422  | Unprocessable Entity   | `POST`, `GET /tickets?status=`, `PATCH`           |

## 5. API semantics

### Idempotency of GET

A request is **idempotent** when sending it once or many times leaves the server in the same state.

`GET` only **reads** data and never changes it. Calling `GET /tickets/1` ten times gives the same result each time (unless someone else changes the ticket), and the ticket itself is not affected by being read. Because of this, `GET` is also **safe**: clients, browsers and proxies can retry or cache it without side effects.

By contrast, `POST /tickets` is **not idempotent**: sending it twice creates two different tickets.

### PUT vs PATCH

| | PUT | PATCH |
|---|---|---|
| What it does | Replaces the **whole** resource | Updates **part** of the resource |
| Request body | Must contain **all** fields | Contains **only** the fields to change |
| Missing fields | Are cleared or reset | Stay unchanged |
| Idempotent | Yes | Not guaranteed |

**Example:** change only the status of ticket 1.

With `PATCH`, send just the field that changes:

```json
{ "status": "IN_PROGRESS" }
```

With `PUT`, the full ticket must be sent:

```json
{
  "title": "Laptop issue",
  "priority": "HIGH",
  "assignee": "AgentA",
  "status": "IN_PROGRESS"
}
```

This API uses `PATCH /tickets/{id}/status` because changing the status is a partial update, and it lets the server check the transition rules for that one field.