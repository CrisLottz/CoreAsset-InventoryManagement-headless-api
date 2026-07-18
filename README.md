<div align="center"> 
 
# CoreAsset — Inventory Management Headless API

**Multi-Tenant Backend Engine for Asset Tracking, Identity Governance & Automated Compliance**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST_Framework-3.17-A30000?style=for-the-badge)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Swagger](https://img.shields.io/badge/OpenAPI-Swagger_UI-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)](https://swagger.io/)
[![Poetry](https://img.shields.io/badge/Poetry-Dependency_Mgmt-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/License-Proprietary-EF4444?style=for-the-badge)](#)

---

> **⚡ Decoupled Architecture** — This repository contains **only the API engine** (Headless Backend).
>
> The web client (Frontend) built with **Astro / React** lives in a separate repository:
>
> **🔗 [CoreAsset-InventoryManagement-web-client](https://github.com/CrisLottz/CoreAsset-InventoryManagement-web-client)**

---

</div>

## Table of Contents 

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture & Design Decisions](#architecture--design-decisions)
  - [1. Session Authentication (No JWT)](#1-session-authentication-no-jwt)
  - [2. RBAC & Object-Level Permissions](#2-rbac--object-level-permissions)
  - [3. Hybrid Database — JSONB + GIN Index](#3-hybrid-database--jsonb--gin-index)
  - [4. Declarative Validation — jsonschema](#4-declarative-validation--jsonschema)
  - [5. Cache & Performance — Redis Write-Through](#5-cache--performance--redis-write-through)
  - [6. Security Hardening — Pickle RCE Mitigation](#6-security-hardening--pickle-rce-mitigation)
  - [7. Compliance Engine — Audit Middleware](#7-compliance-engine--audit-middleware)
  - [8. Destructive Action Safeguards](#8-destructive-action-safeguards)
- [Security & Compliance Standards](#security--compliance-standards)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Local Deployment](#installation--local-deployment)
- [API Documentation](#api-documentation)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [User Management](#user-management)
  - [Roles (RBAC)](#roles-rbac)
  - [Employees](#employees)
  - [Asset Inventory](#asset-inventory)
  - [Locations](#locations)
- [Production Checklist](#production-checklist)

---

## Overview

CoreAsset is an enterprise-grade, white-label Headless API engineered for organizations that require centralized **hardware/software asset tracking**, **location-scoped identity governance**, and **tamper-proof audit trails** — all behind a single, composable REST interface.

The backend is completely decoupled from any frontend. It communicates exclusively through a versioned RESTful API (`/api/v1/`), enabling any client — React SPA, mobile app, or third-party integration — to consume its services without coupling.

---

## Key Features

| Domain | Capability | Implementation |
|---|---|---|
| **Authentication** | Session-based auth (Cookie + CSRF) | `SessionAuthentication` — no JWT |
| **Identity (IAM)** | Custom User model with UUID v4 PK | `users.User` → `AbstractUser` |
| **Employees** | Identity linking & metadata | `employees.Employee` |
| **RBAC** | Role = Proxy over Django Group | `rbac.Role` → `auth_group` (zero DDL) |
| **Permissions** | Geographic write-scoping per location | `IsLocationManagerStrict` object permission |
| **Inventory** | Polymorphic assets via relational trunk + JSONB | `Asset.metadata_json` + GIN index |
| **Validation** | Declarative schema contracts on JSONB | `jsonschema` in DRF serializers |
| **Caching** | Per-user Redis cache with reactive invalidation | `django-redis` + Pickle serializer |
| **Audit** | Automatic mutation logging via HTTP middleware | `AuditMiddleware` → `audit_logs` (JSONB) |
| **Docs** | Auto-generated interactive API docs | `drf-spectacular` → Swagger UI |
| **Infra** | Fully containerized, loopback-only ports | Docker Compose (4 services) |

---

## Architecture & Design Decisions

Every choice documented below answers a specific **"why?"** — not just what the system does, but why the alternative was deliberately rejected.

### 1. Session Authentication (No JWT)

> **Decision**: Use `SessionAuthentication` (HTTP-only Cookies + CSRF tokens) instead of JWT.

```python
# core/settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':     ['rest_framework.permissions.IsAuthenticated'],
}
```

**Why not JWT?**

| Concern | Session Cookies | JWT |
|---|---|---|
| XSS token theft | ✅ Immune — `HttpOnly` cookies are invisible to JS | ❌ Tokens stored in `localStorage` are readable by any script |
| Session revocation | ✅ Instant — server deletes session row | ❌ Requires token blacklist infrastructure |
| CSRF protection | ✅ Built-in — Django enforces `csrftoken` on every mutation | ⚠️ Not applicable (stateless) |
| Token management | ✅ Browser handles cookie lifecycle | ❌ Developer must implement refresh/rotation logic |

CORS and CSRF trust boundaries are scoped exclusively to the frontend origin:

```python
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
```

---

### 2. RBAC & Object-Level Permissions

> **Decision**: Permissions are not global. Write access is geographically scoped — a manager in Denver **cannot** modify assets in Utah, not even via direct API injection.

The system implements two layers of access control:

**Layer 1 — Role as Proxy Model** (`rbac/models.py`)

```python
class Role(Group):
    class Meta:
        proxy = True  # No new table. Uses auth_group. All Django decorators work.
```

**Layer 2 — Location-Scoped Object Permissions** (`assets/permissions.py`)

```python
class IsLocationManagerStrict(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser or request.user.has_perm('assets.manage_global_inventory'):
            return True
        # Geographic gate: user.assigned_locations must include the asset's location
        location = obj if hasattr(obj, 'name') else obj.location
        return request.user.assigned_locations.filter(id=location.id).exists()
```

The `User` model carries a `ManyToManyField` to `Location`, creating a per-user geographic scope. The `AssetViewSet.get_queryset()` pre-filters results at the database level (not in Python), ensuring that even `GET` requests respect the boundary:

```python
if not user.is_superuser and not user.has_perm('assets.view_global_inventory'):
    queryset = queryset.filter(location__in=user.assigned_locations.all())
```

**Custom model-level permissions** provide additional granularity:

| Permission Codename | Effect |
|---|---|
| `assets.view_global_inventory` | Read assets across ALL locations |
| `assets.manage_global_inventory` | Write/delete assets across ALL locations |

---

### 3. Hybrid Database — JSONB + GIN Index

> **Decision**: Use a strict relational trunk (`internal_tag`, `location`, `status`) combined with a `metadata_json` JSONB column for dynamic, type-specific attributes — instead of multi-table inheritance or EAV.

```python
class Asset(models.Model):
    internal_tag  = models.CharField(max_length=50, unique=True)
    location      = models.ForeignKey(Location, on_delete=models.PROTECT)
    status        = models.CharField(choices=STATUS_CHOICES)
    metadata_json = models.JSONField(default=dict, blank=True)  # ← JSONB

    class Meta:
        indexes = [
            models.Index(fields=['location', 'status']),
            GinIndex(fields=['metadata_json']),  # ← O(1) lookups inside JSON
        ]
```

**Why this matters**:

- A **laptop** stores `{"type": "laptop", "mac_address": "AA:BB:...", "cpu": "i7"}`.
- A **license** stores `{"type": "license", "tenant": "Contoso"}`.
- Adding a new asset type (e.g., `"monitor"`) requires **zero migrations** — only a schema update.
- The **GIN index** ensures that queries like `WHERE metadata_json @> '{"type": "laptop"}'` execute at index speed, not via sequential scan.

---

### 4. Declarative Validation — jsonschema 

> **Decision**: Protect the JSONB column with a `jsonschema` contract in the DRF serializer — not with imperative `if/else` chains in Python.

```python
ASSET_METADATA_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["laptop", "license", "mobile"]}
    },
    "allOf": [
        {
            "if": {"properties": {"type": {"const": "laptop"}}},
            "then": {
                "properties": {
                    "mac_address": {"type": "string", "pattern": "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"},
                    "cpu": {"type": "string"}
                }
            }
        },
        {
            "if": {"properties": {"type": {"const": "license"}}},
            "then": {
                "required": ["tenant"],
                "properties": {"tenant": {"type": "string"}}
            }
        }
    ]
}
```

**Design trade-off**: Technical fields like `mac_address` and `cpu` are validated **if present** but are not a requirement. This prevents blocking logistics operators who register assets before technical details are available. However, the `tenant` field for licenses **is** required because a license without an owner is semantically useless.

The validation fires at the serializer layer — before any database write:

```python
def validate_metadata_json(self, value):
    jsonschema.validate(instance=value, schema=ASSET_METADATA_SCHEMA)
    return value
```

---

### 5. Cache & Performance — Redis Write-Through

> **Decision**: Cache heavy `GET /inventory/` responses per-user in Redis with a **reactive invalidation** pattern — purge only the cache of the user who mutates, not the entire cache.

```python
# AssetViewSet.list() — Read path
cache_key = f"inventory_user_{request.user.id}_loc_{location_id}"
cached_data = cache.get(cache_key)
if cached_data:
    return Response(cached_data)  # Served from Redis (~0.1ms)

# AssetViewSet.perform_create/update/destroy() — Write path
def _invalidate_user_cache(self):
    pattern = f"inventory_user_{self.request.user.id}_*"
    cache.delete_pattern(pattern)  # Purge only THIS user's stale entries
```

**Cache configuration** (`core/settings.py`):

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
        }
    }
}
CACHE_TTL = 60 * 15  # 15-minute TTL fallback
```

**Why per-user invalidation?** If User A creates an asset and we flush the entire cache, we force Users B through Z to re-query PostgreSQL on their next request. By scoping invalidation to User A's keys, we maintain O(1) cache hits for everyone else while guaranteeing that User A sees fresh data immediately.

---

### 6. Security Hardening — Pickle RCE Mitigation

> **Decision**: We chose `PickleSerializer` for Redis (maximum serialization speed for complex Django QuerySets), but Pickle deserialization from an untrusted source enables **Remote Code Execution (RCE)**. We mitigate this by requiring authentication on the Redis container.

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: redis-server --requirepass "T3mpP@ssw0rd2026!"
  ports:
    - "127.0.0.1:6379:6379"  # Loopback-only — never exposed to network
```

```yaml
backend:
  environment:
    - REDIS_URL=redis://:T3mpP@ssw0rd2026!@redis:6379/0
```

**Threat model**: If an attacker gains network access to an unauthenticated Redis instance, they can inject a crafted Pickle payload that executes arbitrary code when deserialized by the Django backend. By enforcing `--requirepass` and binding to `127.0.0.1`, we eliminate the two primary attack vectors: network exposure and anonymous access.

---

### 7. Compliance Engine — Audit Middleware

> **Decision**: Every state-mutating HTTP request (`POST`, `PUT`, `PATCH`, `DELETE`) that returns a `2xx` is automatically logged by `AuditMiddleware` — with zero view-level code.

```python
class AuditMiddleware:
    def __call__(self, request):
        response = self.get_response(request)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and 200 <= response.status_code < 300:
            if hasattr(request, 'user') and request.user.is_authenticated:
                AuditLog.objects.create(
                    actor=request.user,        # FK with on_delete=PROTECT
                    action=request.method,
                    entity_type=request.path,
                    ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                    metadata_json={
                        "status_code": response.status_code,
                        "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown')
                    }
                )
        return response
```

**`on_delete=models.PROTECT`**: The `actor` foreign key blocks deletion of any user who has audit records. This is a deliberate, hard database-level constraint — the legal chain of custody cannot be broken through a UI action.

**JSONB storage**: The `metadata_json` field uses PostgreSQL's native `jsonb` type, enabling indexed queries over the audit payload without schema changes as the captured fields evolve.

---

### 8. Destructive Action Safeguards

> **Decision**: Standard `DELETE` operations act as non-destructive "Soft Deletes". Permanent data destruction requires a separate endpoint and an out-of-band administrative re-authentication step.

```python
# Non-destructive Soft Delete (Deactivate)
def perform_destroy(self, instance):
    instance.is_active = False
    instance.save()

# Destructive Hard Delete (Requires Re-Authentication)
@action(detail=True, methods=['post'], url_path='hard-delete')
def hard_delete(self, request, pk=None):
    instance = self.get_object()
    password = request.data.get('password')
    user = authenticate(username=request.user.username, password=password)
    
    if user is not None:
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
```

**Why separate Soft and Hard Deletes?**
- **Data Integrity**: Soft deletes preserve relational integrity (e.g. historical audit logs tied to an employee) while preventing the entity from logging in or appearing in active queries.
- **Accident Prevention**: A simple UI click can trigger a soft delete. Hard deletes require the actor to actively input their password, breaking muscle memory and preventing accidental data loss.

---

## Security & Compliance Standards

The architectural foundation of this API is engineered to align with industry-leading security frameworks and compliance mandates:

* **SOC 2 Type II Readiness (Audit & Accountability):** The system features an immutable audit trail (`AuditMiddleware`). Every state-mutating request is automatically logged to a JSONB store. The relational design enforces `on_delete=models.PROTECT` on user accounts, guaranteeing that the chain of custody for historical asset modifications cannot be destroyed by administrative deletion.
* **OWASP Top 10 Mitigation:**
  * **A01:2021-Broken Access Control:** Mitigated via multi-layered RBAC and strict geographical boundary enforcement (`IsLocationManagerStrict`). Even authenticated managers cannot inject records into unauthorized locations.
  * **A05:2021-Security Misconfiguration:** All internal container ports (Redis, PostgreSQL) are bound strictly to loopback interfaces (`127.0.0.1`) with required authentication, eliminating external network attack vectors for Remote Code Execution (RCE).
  * **A08:2021-Software and Data Integrity Failures:** Defended by declarative JSON Schema validation at the DRF serialization layer, ensuring the database never processes malformed or malicious payloads.

---


## Project Structure

```
CoreAsset-RBAC-Inventory-Engine/
│
├── docker-compose.yml              # 4 services: db, redis, backend, frontend
│
├── backend/                        # Django application root
│   ├── Dockerfile                  # python:3.11-slim + Poetry
│   ├── manage.py
│   ├── pyproject.toml              # Dependency definitions (Poetry)
│   ├── poetry.lock                 # Deterministic lock file
│   │
│   ├── core/                       # Django project configuration
│   │   ├── settings.py             # DRF, CORS, CSRF, Redis, DB, Middleware
│   │   ├── urls.py                 # Root URL dispatcher (api/v1/ namespace)
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── users/                      # IAM — Identity & Session Management
│   │   ├── models.py               # User (UUID PK, assigned_locations M2M)
│   │   ├── serializers.py          # UserSerializer, AssignRoleSerializer
│   │   ├── views.py                # Login, Logout, Me, UserViewSet
│   │   ├── urls.py                 # /login/ /logout/ /me/ /inventory/
│   │   └── admin.py
│   │
│   ├── rbac/                       # Role-Based Access Control
│   │   ├── models.py               # Role (Proxy → auth_group)
│   │   ├── serializers.py          # RoleSerializer
│   │   ├── views.py                # RoleViewSet (CRUD)
│   │   ├── urls.py                 # /roles/
│   │   └── admin.py
│   │
│   ├── assets/                     # Inventory Engine (JSONB + GIN)
│   │   ├── models.py               # Location, Asset (JSONB, GIN index)
│   │   ├── permissions.py          # IsLocationManagerStrict
│   │   ├── serializers.py          # AssetSerializer (jsonschema validation)
│   │   ├── views.py                # AssetViewSet (Redis cache + scope filter)
│   │   ├── urls.py                 # /locations/ /inventory/
│   │   └── admin.py
│   │
│   ├── employees/                  # Employee Management
│   │   ├── models.py               # Employee (is_active for soft delete)
│   │   ├── serializers.py          # EmployeeSerializer
│   │   ├── views.py                # EmployeeViewSet (reactivate, hard-delete, csv-import)
│   │   ├── urls.py                 # /employees/
│   │   └── admin.py
│   │
│   └── audit/                      # Compliance Engine
│       ├── middleware.py            # AuditMiddleware (intercepts all mutations)
│       ├── models.py               # AuditLog (JSONB, PROTECT FK, UUID PK)
│       └── admin.py
│
└── frontend/                       # Separate service (see linked repo)
    └── Dockerfile
```

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | ≥ 24.x | Container runtime with Compose v2 |
| [Git](https://git-scm.com/) | ≥ 2.x | Version control |

No local Python, PostgreSQL, or Redis installation is required. Everything runs inside Docker.

---

## Installation & Local Deployment

### 1. Clone the repository

```bash
git clone https://github.com/CrisLottz/CoreAsset-RBAC-Inventory-Engine.git
cd CoreAsset-RBAC-Inventory-Engine
```

### 2. Configure Environment Variables

Create your local environment file from the provided template. This step is **strictly required** to authorize your custom frontend's domain via CORS.

```bash
cp .env.example .env
```

*Open `.env` and edit `CORS_ALLOWED_ORIGINS` to match your frontend's port or domain (e.g., `http://localhost:4321`).*

### 3. Build and start all services

```bash
docker compose up --build
```

> First build takes ~60–90s (Python image + Poetry dependency install). Subsequent starts are near-instant.

### 4. Apply database migrations

Open a second terminal:

```bash
docker compose exec backend python manage.py migrate
```

### 5. Create a superuser

```bash
docker compose exec backend python manage.py createsuperuser
```

### 6. Verify the stack

| Service | URL |
|---|---|
| Swagger UI (API Docs) | [http://127.0.0.1:8000/api/v1/docs/](http://127.0.0.1:8000/api/v1/docs/) |
| OpenAPI Schema (YAML) | [http://127.0.0.1:8000/api/v1/schema/](http://127.0.0.1:8000/api/v1/schema/) |
| Django Admin | [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) |
| Frontend (dev) | [http://127.0.0.1:5173/](http://127.0.0.1:5173/) |

### Shutdown

```bash
docker compose down       # Stop services, preserve data
docker compose down -v    # Stop services + destroy database volume (full reset)
```

---

## API Documentation

This project uses [**drf-spectacular**](https://drf-spectacular.readthedocs.io/) to auto-generate an OpenAPI 3.0 schema from the DRF codebase. The interactive Swagger UI is served at:

```
http://127.0.0.1:8000/api/v1/docs/
```

The raw OpenAPI schema (JSON/YAML) is available at:

```
http://127.0.0.1:8000/api/v1/schema/
```

Both endpoints are live when the backend container is running. Admin routes are excluded from the public schema.

---

## API Reference

All endpoints are versioned under `/api/v1/`. Authentication is managed via session cookies — the client must first call the login endpoint to establish a session.

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/users/login/` | ✗ | Authenticate and receive `sessionid` + `csrftoken` cookies |
| `GET` | `/api/v1/users/me/` | ✓ | Return the authenticated user's profile |
| `POST` | `/api/v1/users/logout/` | ✓ | Destroy the server-side session |

### User Management

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/users/inventory/` | ✓ | List all users |
| `POST` | `/api/v1/users/inventory/` | ✓ | Create a user |
| `GET` | `/api/v1/users/inventory/{uuid}/` | ✓ | Retrieve a user |
| `PUT/PATCH` | `/api/v1/users/inventory/{uuid}/` | ✓ | Update a user |
| `DELETE` | `/api/v1/users/inventory/{uuid}/` | ✓ | Delete a user |
| `POST` | `/api/v1/users/inventory/{uuid}/assign-roles/` | ✓ | **RPC** — Overwrite user's role set |

### Roles (RBAC)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/rbac/roles/` | ✓ | List all roles |
| `POST` | `/api/v1/rbac/roles/` | ✓ | Create a role |
| `GET` | `/api/v1/rbac/roles/{id}/` | ✓ | Retrieve a role |
| `PUT/PATCH` | `/api/v1/rbac/roles/{id}/` | ✓ | Update a role |
| `DELETE` | `/api/v1/rbac/roles/{id}/` | ✓ | Delete a role |

### Employees

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/employees/` | ✓ | List employees (filter by status) |
| `POST` | `/api/v1/employees/` | ✓ | Create an employee |
| `GET` | `/api/v1/employees/{uuid}/` | ✓ | Retrieve an employee |
| `PUT/PATCH` | `/api/v1/employees/{uuid}/` | ✓ | Update an employee |
| `DELETE` | `/api/v1/employees/{uuid}/` | ✓ | Soft-delete (deactivate) an employee |
| `POST` | `/api/v1/employees/{uuid}/reactivate/` | ✓ | Reactivate a soft-deleted employee |
| `POST` | `/api/v1/employees/{uuid}/hard-delete/` | ✓ | Permanently delete (requires admin password) |
| `POST` | `/api/v1/employees/import-csv/` | ✓ | Bulk import via CSV mapping |

### Asset Inventory

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/assets/inventory/` | ✓ | List assets (filtered by user's location scope) |
| `POST` | `/api/v1/assets/inventory/` | ✓ | Create an asset (location-gated) |
| `GET` | `/api/v1/assets/inventory/{uuid}/` | ✓ | Retrieve an asset |
| `PUT/PATCH` | `/api/v1/assets/inventory/{uuid}/` | ✓ | Update an asset (location-gated) |
| `DELETE` | `/api/v1/assets/inventory/{uuid}/` | ✓ | Delete an asset (location-gated) |

**Query parameters**: `?location_id={uuid}` — Filter assets by a specific location.

### Locations

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/assets/locations/` | ✓ | List all locations |
| `POST` | `/api/v1/assets/locations/` | ✓ | Create a location |
| `GET` | `/api/v1/assets/locations/{uuid}/` | ✓ | Retrieve a location |
| `PUT/PATCH` | `/api/v1/assets/locations/{uuid}/` | ✓ | Update a location |
| `DELETE` | `/api/v1/assets/locations/{uuid}/` | ✓ | Delete a location |

---

## Production Checklist

| Area | Requirement |
|---|---|
| **Secret Key** | Rotate `SECRET_KEY` via environment variable (Docker secrets, AWS SSM). Never hardcode. |
| **Debug Mode** | Set `DEBUG = False`. Configure `ALLOWED_HOSTS` to the production domain. |
| **CORS / CSRF** | Narrow `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the production frontend domain only. |
| **Redis Password** | Replace the development password with a strong, rotated secret via environment variable. |
| **Network** | All Docker ports are already bound to `127.0.0.1`. In production, place behind a reverse proxy (Nginx/Caddy) exposing only `443`. |
| **Migrations** | All DDL is executed exclusively via `python manage.py migrate`. Never run raw `ALTER TABLE` against production. |
| **Dependencies** | `poetry.lock` pins every transitive dependency. Use `poetry install --no-root` in CI/CD for reproducible builds. |

---

---

---

<div align="center">

# CoreAsset — Inventory Management Headless API

**Motor Backend Multi-Tenant para Rastreo de Activos, Gobernanza de Identidades y Cumplimiento Automatizado**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST_Framework-3.17-A30000?style=for-the-badge)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Swagger](https://img.shields.io/badge/OpenAPI-Swagger_UI-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)](https://swagger.io/)
[![Poetry](https://img.shields.io/badge/Poetry-Gestión_Deps-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/Licencia-Propietaria-EF4444?style=for-the-badge)](#)

---

> **⚡ Arquitectura Desacoplada** — Este repositorio contiene **únicamente el motor API** (Backend Headless).
>
> El cliente web (Frontend) construido con **Astro / React** se encuentra en un repositorio separado:
>
> **🔗 [CoreAsset-InventoryManagement-web-client](https://github.com/CrisLottz/CoreAsset-InventoryManagement-web-client)**

---

</div>

## Tabla de Contenidos

- [Resumen](#resumen)
- [Características Principales](#características-principales)
- [Arquitectura y Decisiones de Diseño](#arquitectura-y-decisiones-de-diseño)
  - [1. Autenticación por Sesión (Sin JWT)](#1-autenticación-por-sesión-sin-jwt)
  - [2. RBAC y Permisos a Nivel de Objeto](#2-rbac-y-permisos-a-nivel-de-objeto)
  - [3. Base de Datos Híbrida — JSONB + Índice GIN](#3-base-de-datos-híbrida--jsonb--índice-gin)
  - [4. Validación Declarativa — jsonschema](#4-validación-declarativa--jsonschema)
  - [5. Caché y Rendimiento — Redis Write-Through](#5-caché-y-rendimiento--redis-write-through)
  - [6. Blindaje de Seguridad — Mitigación Pickle RCE](#6-blindaje-de-seguridad--mitigación-pickle-rce)
  - [7. Motor de Cumplimiento — Middleware de Auditoría](#7-motor-de-cumplimiento--middleware-de-auditoría)
  - [8. Salvaguardas de Acciones Destructivas](#8-salvaguardas-de-acciones-destructivas)
- [Estándares de Seguridad y Cumplimiento](#estandares-de-seguridad-y-cumplimiento)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Prerrequisitos](#prerrequisitos)
- [Instalación y Despliegue Local](#instalación-y-despliegue-local)
- [Documentación de la API](#documentación-de-la-api)
- [Referencia de la API](#referencia-de-la-api)
  - [Autenticación](#autenticación)
  - [Gestión de Usuarios](#gestión-de-usuarios)
  - [Roles (RBAC)](#roles-rbac)
  - [Empleados](#empleados)
  - [Inventario de Activos](#inventario-de-activos)
  - [Ubicaciones](#ubicaciones)
- [Lista de Verificación para Producción](#lista-de-verificación-para-producción)

---

## Resumen

CoreAsset es una API Headless de grado empresarial y marca blanca, diseñada para organizaciones que requieren **rastreo centralizado de activos físicos y virtuales**, **gobernanza de identidades con alcance geográfico** y **pistas de auditoría a prueba de manipulaciones** — todo detrás de una única interfaz REST componible.

El backend está completamente desacoplado de cualquier frontend. Se comunica exclusivamente a través de una API RESTful versionada (`/api/v1/`), permitiendo que cualquier cliente — SPA React, aplicación móvil o integración de terceros — consuma sus servicios sin acoplamiento.

---

## Características Principales

| Dominio | Capacidad | Implementación |
|---|---|---|
| **Autenticación** | Auth basada en sesión (Cookie + CSRF) | `SessionAuthentication` — sin JWT |
| **Identidad (IAM)** | Modelo de Usuario con UUID v4 como PK | `users.User` → `AbstractUser` |
| **Empleados** | Enlace de identidad y metadatos | `employees.Employee` |
| **RBAC** | Rol = Proxy sobre Group de Django | `rbac.Role` → `auth_group` (cero DDL) |
| **Permisos** | Escritura acotada geográficamente por sede | Permiso de objeto `IsLocationManagerStrict` |
| **Inventario** | Activos polimórficos via tronco relacional + JSONB | `Asset.metadata_json` + índice GIN |
| **Validación** | Contratos de esquema declarativos sobre JSONB | `jsonschema` en serializadores DRF |
| **Caché** | Caché Redis por usuario con invalidación reactiva | `django-redis` + serializador Pickle |
| **Auditoría** | Registro automático de mutaciones via middleware HTTP | `AuditMiddleware` → `audit_logs` (JSONB) |
| **Documentación** | Docs interactivos auto-generados | `drf-spectacular` → Swagger UI |
| **Infraestructura** | Completamente contenerizado, puertos solo en loopback | Docker Compose (4 servicios) |

---

## Arquitectura y Decisiones de Diseño

Cada decisión documentada a continuación responde un **"¿por qué?"** específico — no solo qué hace el sistema, sino por qué la alternativa fue deliberadamente rechazada.

### 1. Autenticación por Sesión (Sin JWT)

> **Decisión**: Usar `SessionAuthentication` (Cookies HTTP-only + tokens CSRF) en lugar de JWT.

```python
# core/settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':     ['rest_framework.permissions.IsAuthenticated'],
}
```

**¿Por qué no JWT?**

| Preocupación | Cookies de Sesión | JWT |
|---|---|---|
| Robo de token vía XSS | ✅ Inmune — cookies `HttpOnly` invisibles a JS | ❌ Tokens en `localStorage` son legibles por cualquier script |
| Revocación de sesión | ✅ Instantánea — el servidor elimina la fila de sesión | ❌ Requiere infraestructura de lista negra de tokens |
| Protección CSRF | ✅ Integrada — Django exige `csrftoken` en cada mutación | ⚠️ No aplica (stateless) |
| Gestión de tokens | ✅ El navegador gestiona el ciclo de vida de la cookie | ❌ El desarrollador debe implementar lógica de refresh/rotación |

Los límites de confianza de CORS y CSRF están acotados exclusivamente al origen del frontend:

```python
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
```

---

### 2. RBAC y Permisos a Nivel de Objeto

> **Decisión**: Los permisos no son globales. El acceso de escritura está acotado geográficamente — un manager en Denver **no puede** modificar activos en Utah, ni siquiera mediante inyección directa a la API.

El sistema implementa dos capas de control de acceso:

**Capa 1 — Rol como Proxy Model** (`rbac/models.py`)

```python
class Role(Group):
    class Meta:
        proxy = True  # Sin tabla nueva. Usa auth_group. Todos los decoradores de Django funcionan.
```

**Capa 2 — Permisos de Objeto con Alcance Geográfico** (`assets/permissions.py`)

```python
class IsLocationManagerStrict(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser or request.user.has_perm('assets.manage_global_inventory'):
            return True
        # Compuerta geográfica: user.assigned_locations debe incluir la sede del activo
        location = obj if hasattr(obj, 'name') else obj.location
        return request.user.assigned_locations.filter(id=location.id).exists()
```

El modelo `User` lleva un `ManyToManyField` hacia `Location`, creando un alcance geográfico por usuario. El `AssetViewSet.get_queryset()` pre-filtra los resultados a nivel de base de datos (no en Python), asegurando que incluso las peticiones `GET` respeten el límite:

```python
if not user.is_superuser and not user.has_perm('assets.view_global_inventory'):
    queryset = queryset.filter(location__in=user.assigned_locations.all())
```

**Permisos personalizados a nivel de modelo** proporcionan granularidad adicional:

| Codename del Permiso | Efecto |
|---|---|
| `assets.view_global_inventory` | Leer activos de TODAS las sedes |
| `assets.manage_global_inventory` | Escribir/eliminar activos de TODAS las sedes |

---

### 3. Base de Datos Híbrida — JSONB + Índice GIN

> **Decisión**: Usar un tronco relacional estricto (`internal_tag`, `location`, `status`) combinado con una columna `metadata_json` de tipo JSONB para atributos dinámicos específicos por tipo — en lugar de herencia multi-tabla o EAV.

```python
class Asset(models.Model):
    internal_tag  = models.CharField(max_length=50, unique=True)
    location      = models.ForeignKey(Location, on_delete=models.PROTECT)
    status        = models.CharField(choices=STATUS_CHOICES)
    metadata_json = models.JSONField(default=dict, blank=True)  # ← JSONB

    class Meta:
        indexes = [
            models.Index(fields=['location', 'status']),
            GinIndex(fields=['metadata_json']),  # ← Búsquedas O(1) dentro del JSON
        ]
```

**Por qué esto importa**:

- Una **laptop** almacena `{"type": "laptop", "mac_address": "AA:BB:...", "cpu": "i7"}`.
- Una **licencia** almacena `{"type": "license", "tenant": "Contoso"}`.
- Agregar un nuevo tipo de activo (ej. `"monitor"`) requiere **cero migraciones** — solo una actualización del esquema.
- El **índice GIN** garantiza que consultas como `WHERE metadata_json @> '{"type": "laptop"}'` se ejecuten a velocidad de índice, no mediante escaneo secuencial.

---

### 4. Validación Declarativa — jsonschema

> **Decisión**: Proteger la columna JSONB con un contrato `jsonschema` en el serializador de DRF — no con cadenas imperativas `if/else` en Python.

```python
ASSET_METADATA_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"type": "string", "enum": ["laptop", "license", "mobile"]}
    },
    "allOf": [
        {
            "if": {"properties": {"type": {"const": "laptop"}}},
            "then": {
                "properties": {
                    "mac_address": {"type": "string", "pattern": "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"},
                    "cpu": {"type": "string"}
                }
            }
        },
        {
            "if": {"properties": {"type": {"const": "license"}}},
            "then": {
                "required": ["tenant"],
                "properties": {"tenant": {"type": "string"}}
            }
        }
    ]
}
```

**Compromiso de diseño**: Los campos técnicos como `mac_address` y `cpu` se validan **si están presentes** pero no son obligatorios. Esto evita bloquear a los operadores de logística que registran activos antes de que los detalles técnicos estén disponibles. Sin embargo, el campo `tenant` para licencias **sí es obligatorio** porque una licencia sin propietario es semánticamente inútil.

La validación se ejecuta en la capa del serializador — antes de cualquier escritura en base de datos:

```python
def validate_metadata_json(self, value):
    jsonschema.validate(instance=value, schema=ASSET_METADATA_SCHEMA)
    return value
```

---

### 5. Caché y Rendimiento — Redis Write-Through

> **Decisión**: Cachear las respuestas pesadas de `GET /inventory/` por usuario en Redis con un patrón de **invalidación reactiva** — purgar solo la caché del usuario que realiza la mutación, no la caché completa.

```python
# AssetViewSet.list() — Ruta de lectura
cache_key = f"inventory_user_{request.user.id}_loc_{location_id}"
cached_data = cache.get(cache_key)
if cached_data:
    return Response(cached_data)  # Servido desde Redis (~0.1ms)

# AssetViewSet.perform_create/update/destroy() — Ruta de escritura
def _invalidate_user_cache(self):
    pattern = f"inventory_user_{self.request.user.id}_*"
    cache.delete_pattern(pattern)  # Purga solo las entradas obsoletas de ESTE usuario
```

**Configuración de caché** (`core/settings.py`):

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.pickle.PickleSerializer",
        }
    }
}
CACHE_TTL = 60 * 15  # TTL de respaldo de 15 minutos
```

**¿Por qué invalidación por usuario?** Si el Usuario A crea un activo y purgamos toda la caché, forzamos a los Usuarios B hasta Z a re-consultar PostgreSQL en su siguiente petición. Al acotar la invalidación a las claves del Usuario A, mantenemos cache hits O(1) para todos los demás mientras garantizamos que el Usuario A vea datos frescos inmediatamente.

---

### 6. Blindaje de Seguridad — Mitigación Pickle RCE

> **Decisión**: Elegimos `PickleSerializer` para Redis (máxima velocidad de serialización para QuerySets complejos de Django), pero la deserialización de Pickle desde una fuente no confiable habilita **Ejecución Remota de Código (RCE)**. Mitigamos esto requiriendo autenticación en el contenedor de Redis.

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: redis-server --requirepass "T3mpP@ssw0rd2026!"
  ports:
    - "127.0.0.1:6379:6379"  # Solo loopback — nunca expuesto a la red
```

```yaml
backend:
  environment:
    - REDIS_URL=redis://:T3mpP@ssw0rd2026!@redis:6379/0
```

**Modelo de amenaza**: Si un atacante obtiene acceso de red a una instancia de Redis sin autenticación, puede inyectar un payload Pickle diseñado que ejecuta código arbitrario cuando es deserializado por el backend de Django. Al forzar `--requirepass` y vincular a `127.0.0.1`, eliminamos los dos vectores de ataque principales: exposición de red y acceso anónimo.

---

### 7. Motor de Cumplimiento — Middleware de Auditoría

> **Decisión**: Toda petición HTTP que muta estado (`POST`, `PUT`, `PATCH`, `DELETE`) y retorna un `2xx` es automáticamente registrada por `AuditMiddleware` — con cero código a nivel de vista.

```python
class AuditMiddleware:
    def __call__(self, request):
        response = self.get_response(request)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and 200 <= response.status_code < 300:
            if hasattr(request, 'user') and request.user.is_authenticated:
                AuditLog.objects.create(
                    actor=request.user,        # FK con on_delete=PROTECT
                    action=request.method,
                    entity_type=request.path,
                    ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                    metadata_json={
                        "status_code": response.status_code,
                        "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown')
                    }
                )
        return response
```

**`on_delete=models.PROTECT`**: La clave foránea `actor` bloquea la eliminación de cualquier usuario que tenga registros de auditoría. Esta es una restricción deliberada y dura a nivel de base de datos — la cadena de custodia legal no puede romperse a través de una acción de interfaz de usuario.

**Almacenamiento JSONB**: El campo `metadata_json` usa el tipo nativo `jsonb` de PostgreSQL, permitiendo consultas indexadas sobre el payload de auditoría sin cambios de esquema a medida que evolucionan los campos capturados.

---

### 8. Salvaguardas de Acciones Destructivas

> **Decisión**: Las operaciones estándar de `DELETE` actúan como "Soft Deletes" no destructivos. La destrucción permanente de datos requiere un endpoint separado y un paso de re-autenticación administrativa out-of-band.

```python
# Soft Delete no destructivo (Desactivar)
def perform_destroy(self, instance):
    instance.is_active = False
    instance.save()

# Hard Delete Destructivo (Requiere Re-Autenticación)
@action(detail=True, methods=['post'], url_path='hard-delete')
def hard_delete(self, request, pk=None):
    instance = self.get_object()
    password = request.data.get('password')
    user = authenticate(username=request.user.username, password=password)
    
    if user is not None:
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
```

**¿Por qué separar Soft y Hard Deletes?**
- **Integridad de Datos**: Los soft deletes preservan la integridad relacional (ej. logs de auditoría históricos vinculados a un empleado) mientras evitan que la entidad inicie sesión o aparezca en consultas activas.
- **Prevención de Accidentes**: Un simple clic en la UI puede desencadenar un soft delete. Los hard deletes requieren que el actor introduzca activamente su contraseña, rompiendo la memoria muscular y previniendo la pérdida accidental de datos.

---

## Estándares de Seguridad y Cumplimiento

La base arquitectónica de esta API está diseñada para alinearse con los marcos de seguridad y mandatos de cumplimiento líderes en la industria:

* **Preparación para SOC 2 Type II (Auditoría y Responsabilidad):** El sistema cuenta con una pista de auditoría inmutable (`AuditMiddleware`). Cada petición que muta estado se registra automáticamente en un almacén JSONB. El diseño relacional impone `on_delete=models.PROTECT` en las cuentas de usuario, garantizando que la cadena de custodia de las modificaciones históricas de activos no pueda ser destruida por eliminaciones administrativas.
* **Mitigación OWASP Top 10:**
  * **A01:2021-Broken Access Control:** Mitigado a través de RBAC multicapa y una aplicación estricta de límites geográficos (`IsLocationManagerStrict`). Ni siquiera los gerentes autenticados pueden inyectar registros en sedes no autorizadas.
  * **A05:2021-Security Misconfiguration:** Todos los puertos internos de contenedores (Redis, PostgreSQL) están vinculados estrictamente a interfaces de loopback (`127.0.0.1`) con autenticación requerida, eliminando vectores de ataque de red externos para Ejecución Remota de Código (RCE).
  * **A08:2021-Software and Data Integrity Failures:** Defendido mediante validación declarativa de JSON Schema en la capa de serialización de DRF, asegurando que la base de datos nunca procese payloads malformados o maliciosos.
 
---

## Estructura del Proyecto

```
CoreAsset-RBAC-Inventory-Engine/
│
├── docker-compose.yml              # 4 servicios: db, redis, backend, frontend
│
├── backend/                        # Raíz de la aplicación Django
│   ├── Dockerfile                  # python:3.11-slim + Poetry
│   ├── manage.py
│   ├── pyproject.toml              # Definiciones de dependencias (Poetry)
│   ├── poetry.lock                 # Archivo de bloqueo determinista
│   │
│   ├── core/                       # Configuración del proyecto Django
│   │   ├── settings.py             # DRF, CORS, CSRF, Redis, BD, Middleware
│   │   ├── urls.py                 # Despachador de URLs raíz (namespace api/v1/)
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── users/                      # IAM — Identidad y Gestión de Sesiones
│   │   ├── models.py               # User (UUID PK, assigned_locations M2M)
│   │   ├── serializers.py          # UserSerializer, AssignRoleSerializer
│   │   ├── views.py                # Login, Logout, Me, UserViewSet
│   │   ├── urls.py                 # /login/ /logout/ /me/ /inventory/
│   │   └── admin.py
│   │
│   ├── rbac/                       # Control de Acceso Basado en Roles
│   │   ├── models.py               # Role (Proxy → auth_group)
│   │   ├── serializers.py          # RoleSerializer
│   │   ├── views.py                # RoleViewSet (CRUD)
│   │   ├── urls.py                 # /roles/
│   │   └── admin.py
│   │
│   ├── assets/                     # Motor de Inventario (JSONB + GIN)
│   │   ├── models.py               # Location, Asset (JSONB, índice GIN)
│   │   ├── permissions.py          # IsLocationManagerStrict
│   │   ├── serializers.py          # AssetSerializer (validación jsonschema)
│   │   ├── views.py                # AssetViewSet (caché Redis + filtro de alcance)
│   │   ├── urls.py                 # /locations/ /inventory/
│   │   └── admin.py
│   │
│   └── audit/                      # Motor de Cumplimiento
│       ├── middleware.py            # AuditMiddleware (intercepta todas las mutaciones)
│       ├── models.py               # AuditLog (JSONB, FK PROTECT, UUID PK)
│       └── admin.py
│
└── frontend/                       # Servicio separado (ver repositorio enlazado)
    └── Dockerfile
```

---

## Prerrequisitos

| Herramienta | Versión | Propósito |
|---|---|---|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | ≥ 24.x | Runtime de contenedores con Compose v2 |
| [Git](https://git-scm.com/) | ≥ 2.x | Control de versiones |

No se requiere instalación local de Python, PostgreSQL ni Redis. Todo corre dentro de Docker.

---

## Instalación y Despliegue Local

### 1. Clonar el repositorio

```bash
git clone https://github.com/CrisLottz/CoreAsset-RBAC-Inventory-Engine.git
cd CoreAsset-RBAC-Inventory-Engine
```
### 2. Configurar Variables de Entorno

Crea tu archivo de entorno local a partir de la plantilla provista. Este paso es **estrictamente obligatorio** para autorizar el dominio de tu frontend personalizado mediante CORS.

```bash
cp .env.example .env
```

*Abre el archivo `.env` y edita `CORS_ALLOWED_ORIGINS` para que coincida con el puerto o dominio de tu frontend (ej. `http://localhost:4321`).*

### 3. Construir e iniciar todos los servicios

```bash
docker compose up --build
```

> La primera construcción tarda ~60–90s (imagen Python + instalación de dependencias con Poetry). Los arranques posteriores son casi instantáneos.

### 4. Aplicar las migraciones de base de datos

Abrir una segunda terminal:

```bash
docker compose exec backend python manage.py migrate
```

### 5. Crear un superusuario

```bash
docker compose exec backend python manage.py createsuperuser
```

### 6. Verificar el stack

| Servicio | URL |
|---|---|
| Swagger UI (Docs API) | [http://127.0.0.1:8000/api/v1/docs/](http://127.0.0.1:8000/api/v1/docs/) |
| Esquema OpenAPI (YAML) | [http://127.0.0.1:8000/api/v1/schema/](http://127.0.0.1:8000/api/v1/schema/) |
| Django Admin | [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) |
| Frontend (dev) | [http://127.0.0.1:5173/](http://127.0.0.1:5173/) |

### Apagado

```bash
docker compose down       # Detener servicios, preservar datos
docker compose down -v    # Detener servicios + destruir volumen de BD (reseteo completo)
```

---

## Documentación de la API

Este proyecto usa [**drf-spectacular**](https://drf-spectacular.readthedocs.io/) para auto-generar un esquema OpenAPI 3.0 desde el código de DRF. La interfaz interactiva Swagger UI se sirve en:

```
http://127.0.0.1:8000/api/v1/docs/
```

El esquema OpenAPI sin procesar (JSON/YAML) está disponible en:

```
http://127.0.0.1:8000/api/v1/schema/
```

Ambos endpoints están activos cuando el contenedor del backend está corriendo. Las rutas de admin están excluidas del esquema público.

---

## Referencia de la API

Todos los endpoints están versionados bajo `/api/v1/`. La autenticación se gestiona via cookies de sesión — el cliente debe primero llamar al endpoint de login para establecer una sesión.

### Autenticación

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/users/login/` | ✗ | Autenticar y recibir cookies `sessionid` + `csrftoken` |
| `GET` | `/api/v1/users/me/` | ✓ | Retornar el perfil del usuario autenticado |
| `POST` | `/api/v1/users/logout/` | ✓ | Destruir la sesión del lado del servidor |

### Gestión de Usuarios

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/users/inventory/` | ✓ | Listar todos los usuarios |
| `POST` | `/api/v1/users/inventory/` | ✓ | Crear un usuario |
| `GET` | `/api/v1/users/inventory/{uuid}/` | ✓ | Recuperar un usuario |
| `PUT/PATCH` | `/api/v1/users/inventory/{uuid}/` | ✓ | Actualizar un usuario |
| `DELETE` | `/api/v1/users/inventory/{uuid}/` | ✓ | Eliminar un usuario |
| `POST` | `/api/v1/users/inventory/{uuid}/assign-roles/` | ✓ | **RPC** — Sobreescribir el conjunto de roles del usuario |

### Roles (RBAC)

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/rbac/roles/` | ✓ | Listar todos los roles |
| `POST` | `/api/v1/rbac/roles/` | ✓ | Crear un rol |
| `GET` | `/api/v1/rbac/roles/{id}/` | ✓ | Recuperar un rol |
| `PUT/PATCH` | `/api/v1/rbac/roles/{id}/` | ✓ | Actualizar un rol |
| `DELETE` | `/api/v1/rbac/roles/{id}/` | ✓ | Eliminar un rol |

### Inventario de Activos

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/assets/inventory/` | ✓ | Listar activos (filtrado por alcance geográfico del usuario) |
| `POST` | `/api/v1/assets/inventory/` | ✓ | Crear un activo (restringido por sede) |
| `GET` | `/api/v1/assets/inventory/{uuid}/` | ✓ | Recuperar un activo |
| `PUT/PATCH` | `/api/v1/assets/inventory/{uuid}/` | ✓ | Actualizar un activo (restringido por sede) |
| `DELETE` | `/api/v1/assets/inventory/{uuid}/` | ✓ | Eliminar un activo (restringido por sede) |

**Parámetros de consulta**: `?location_id={uuid}` — Filtrar activos por una sede específica.

### Sedes (Locations)

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/assets/locations/` | ✓ | Listar todas las sedes |
| `POST` | `/api/v1/assets/locations/` | ✓ | Crear una sede |
| `GET` | `/api/v1/assets/locations/{uuid}/` | ✓ | Recuperar una sede |
| `PUT/PATCH` | `/api/v1/assets/locations/{uuid}/` | ✓ | Actualizar una sede |
| `DELETE` | `/api/v1/assets/locations/{uuid}/` | ✓ | Eliminar una sede |

---

## Lista de Verificación para Producción

| Área | Requisito |
|---|---|
| **Clave Secreta** | Rotar `SECRET_KEY` vía variable de entorno (Docker secrets, AWS SSM). Nunca codificar en duro. |
| **Modo Debug** | Establecer `DEBUG = False`. Configurar `ALLOWED_HOSTS` al dominio de producción. |
| **CORS / CSRF** | Acotar `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` únicamente al dominio del frontend de producción. |
| **Contraseña Redis** | Reemplazar la contraseña de desarrollo con un secreto fuerte y rotado vía variable de entorno. |
| **Red** | Todos los puertos Docker ya están vinculados a `127.0.0.1`. En producción, colocar detrás de un proxy inverso (Nginx/Caddy) exponiendo solo `443`. |
| **Migraciones** | Todo DDL se ejecuta exclusivamente vía `python manage.py migrate`. Nunca ejecutar `ALTER TABLE` directo contra producción. |
| **Dependencias** | `poetry.lock` fija cada dependencia transitiva. Usar `poetry install --no-root` en CI/CD para builds reproducibles. |
