# CoreAsset — RBAC Inventory Engine

> **Headless API · Enterprise-grade · White-Label Ready**

A hardened, stateless-free backend core for enterprise platforms that demand **identity governance**, **hardware/software asset tracking**, and **tamper-proof audit trails**. Built as a composable Headless API, it is designed to power any white-label frontend without coupling to a specific UI layer.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture — The Four Pillars](#2-system-architecture--the-four-pillars)
3. [Project Directory Structure](#3-project-directory-structure)
4. [API Reference](#4-api-reference)
5. [Local Installation & Deployment](#5-local-installation--deployment)
6. [Production Standards](#6-production-standards)

---

## 1. Executive Summary

CoreAsset-RBAC-Inventory-Engine is the backend nucleus of a White-Label enterprise asset management platform. It exposes a RESTful API built with **Django 5 + Django REST Framework** and runs in a fully isolated **Docker Compose** environment backed by **PostgreSQL 15**.

Its design philosophy prioritizes **security over convenience**, **traceability over speed**, and **composability over monolithic coupling**. Every architectural decision — from session-based authentication to JSONB-backed asset metadata — was made to satisfy enterprise compliance requirements without sacrificing developer ergonomics.

**Core capabilities delivered in the current phase:**

| Capability | Status |
|---|---|
| Session-based authentication (Cookie + CSRF) | ✅ Production-ready |
| Custom UUID-primary-key User model | ✅ Production-ready |
| RBAC via Django Proxy-Model pattern | ✅ Production-ready |
| Granular role assignment via RPC endpoint | ✅ Production-ready |
| Automated HTTP mutation audit trail (JSONB) | ✅ Production-ready |
| Asset inventory with JSONB metadata column | 🔷 Planned — Phase 2 |
| Multi-location filtering for physical assets | 🔷 Planned — Phase 2 |

---

## 2. System Architecture — The Four Pillars

### Pillar I — Containerized Infrastructure

The entire runtime is isolated with **Docker Compose**, defining three independent, networked services:

| Service | Image | Exposed Port (localhost only) |
|---|---|---|
| `db` | `postgres:15-alpine` | `127.0.0.1:5432` |
| `redis` | `redis:7-alpine` | `127.0.0.1:6379` |
| `backend` | Custom (`python:3.11-slim`) | `127.0.0.1:8000` |
| `frontend` | Custom | `127.0.0.1:5173` |

All ports are bound **exclusively to the loopback interface** (`127.0.0.1`), ensuring no service is inadvertently exposed to external networks. PostgreSQL data is persisted in a named Docker volume (`postgres_data`).

Dependency management inside the backend container is handled by **Poetry** (`pyproject.toml` + `poetry.lock`), which pins every transitive dependency to a reproducible hash. Because the container is itself an isolated environment, Poetry is configured to install packages globally within it (`virtualenvs.create = false`), avoiding redundant virtual-environment overhead.

---

### Pillar II — Security & Authentication (No JWT)

This system deliberately **does not implement JWT**. The authentication model relies on **Django's native Session Authentication** with **HTTP-only Cookies and CSRF tokens** — a fundamentally more secure architecture for browser-based clients because:

- Session cookies are `HttpOnly` and cannot be read by JavaScript, eliminating XSS-based token theft.
- Every mutating request must carry a valid CSRF token, eliminating CSRF attacks even with a stolen cookie.
- Session invalidation is server-side and immediate — revoking access requires no token blacklists.

The DRF configuration enforces this contract globally:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':     ['rest_framework.permissions.IsAuthenticated'],
}
```

CORS and CSRF policies are strictly scoped to the frontend origin (`http://localhost:5173` in development), and `CORS_ALLOW_CREDENTIALS = True` permits cross-origin cookie transmission without relaxing the trust boundary.

---

### Pillar III — Identity & Access Management (IAM / RBAC)

**Custom User Model**

The `User` model (`users.User`) extends Django's `AbstractUser` with two critical overrides:

- **UUID v4 as primary key** — eliminates sequential ID enumeration attacks and is globally unique by construction.
- **`is_mfa_enabled` flag** — foundation for future multi-factor authentication enforcement.

```python
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_mfa_enabled = models.BooleanField(default=False)
```

**Role Management via Proxy Model**

Rather than introducing a separate, unrelated `Role` table and duplicating Django's permission infrastructure, the `rbac.Role` model is implemented as a **Proxy Model** over Django's native `Group`:

```python
class Role(Group):
    class Meta:
        proxy = True
        app_label = 'rbac'
```

This means:
- No new DDL table is created — `Role` objects are stored in `auth_group`.
- All of Django's built-in permission decorators (`@permission_required`, `user.has_perm()`) work out of the box.
- The business domain uses the vocabulary "Role" while the ORM uses the battle-tested `Group` infrastructure.

**Granular Role Assignment via Explicit RPC Endpoint**

Role assignment is never a silent side effect of a `PATCH /users/{id}/` call. It is an explicit, intentional, auditable action exposed as a dedicated RPC-style endpoint:

```
POST /api/users/inventory/{uuid}/assign-roles/
```

This ensures that a developer cannot accidentally overwrite a user's roles while updating their profile — the operations are architecturally separated.

---

### Pillar IV — Compliance Engine (Audit Middleware)

Every state-mutating HTTP request — `POST`, `PUT`, `PATCH`, `DELETE` — that returns a successful `2xx` response is **automatically intercepted** by `audit.middleware.AuditMiddleware` and recorded in the `audit_logs` table without any view-level code involvement.

Each audit record captures:

| Field | Content |
|---|---|
| `id` | UUID v4 (immutable primary key) |
| `actor` | FK → authenticated `User` (`PROTECT`) |
| `action` | HTTP method (`POST`, `PUT`, etc.) |
| `entity_type` | Request path (URL) |
| `entity_id` | UUID of the affected resource |
| `ip_address` | Client IP from `REMOTE_ADDR` |
| `metadata_json` | JSONB blob: `status_code`, `user_agent` |
| `created_at` | Auto-set UTC timestamp |

**Protected custody chain**: The `actor` foreign key uses `on_delete=models.PROTECT`. This means that deleting a user who has audit records is a **database-level hard block** — the integrity of the legal audit trail cannot be destroyed through a UI action.

**JSONB storage** (`models.JSONField` → PostgreSQL `jsonb`) enables native indexed querying of the metadata payload without requiring schema changes as the fields evolve.

---

## 3. Project Directory Structure

```
CoreAsset-RBAC-Inventory-Engine/
│
├── docker-compose.yml              # Orchestrates all services (db, redis, backend, frontend)
│
├── backend/                        # Django application root
│   ├── Dockerfile                  # python:3.11-slim image, Poetry install
│   ├── manage.py                   # Django management entry point
│   ├── pyproject.toml              # Poetry project definition & dependency pins
│   ├── poetry.lock                 # Deterministic dependency lock file
│   │
│   ├── core/                       # Django project settings package
│   │   ├── settings.py             # DRF, CORS, CSRF, DB, Middleware config
│   │   ├── urls.py                 # Root URL dispatcher
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── users/                      # IAM — User model & authentication endpoints
│   │   ├── models.py               # Custom User (UUID PK, is_mfa_enabled)
│   │   ├── serializers.py          # UserSerializer, AssignRoleSerializer
│   │   ├── views.py                # LoginView, LogoutView, UserMeView, UserViewSet
│   │   ├── urls.py                 # /login/ /logout/ /me/ /inventory/ routing
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── rbac/                       # Role-Based Access Control
│   │   ├── models.py               # Role (Proxy → auth_group)
│   │   ├── serializers.py          # RoleSerializer
│   │   ├── views.py                # RoleViewSet (CRUD)
│   │   ├── urls.py                 # /roles/ routing
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   └── audit/                      # Compliance Engine
│       ├── middleware.py           # AuditMiddleware (intercepts all mutations)
│       ├── models.py               # AuditLog (JSONB, PROTECT FK, UUID PK)
│       ├── admin.py
│       └── migrations/
│
└── frontend/                       # White-label frontend (separate service)
    └── Dockerfile
```

---

## 4. API Reference

All endpoints are prefixed with `/api/`. Authentication state is managed via session cookies — the client must first obtain a CSRF token via the login flow.

### Authentication

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/api/users/login/` | No | Initiates session, sets `sessionid` + `csrftoken` cookies |
| `GET` | `/api/users/me/` | Yes | Returns the authenticated user's profile |
| `POST` | `/api/users/logout/` | Yes | Destroys the server-side session |

### User Inventory

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/users/inventory/` | Yes | List all users |
| `POST` | `/api/users/inventory/` | Yes | Create a new user |
| `GET` | `/api/users/inventory/{uuid}/` | Yes | Retrieve a specific user |
| `PUT` | `/api/users/inventory/{uuid}/` | Yes | Full update of a user |
| `PATCH` | `/api/users/inventory/{uuid}/` | Yes | Partial update of a user |
| `DELETE` | `/api/users/inventory/{uuid}/` | Yes | Delete a user |
| `POST` | `/api/users/inventory/{uuid}/assign-roles/` | Yes | **RPC** — Overwrite the user's role set |

### Role Management (RBAC)

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/api/rbac/roles/` | Yes | List all roles |
| `POST` | `/api/rbac/roles/` | Yes | Create a new role |
| `GET` | `/api/rbac/roles/{id}/` | Yes | Retrieve a specific role |
| `PUT` | `/api/rbac/roles/{id}/` | Yes | Update a role |
| `DELETE` | `/api/rbac/roles/{id}/` | Yes | Delete a role |

**`POST /api/users/inventory/{uuid}/assign-roles/` — Request Body:**
```json
{
  "role_ids": [1, 3]
}
```

---

## 5. Local Installation & Deployment

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Compose v2)
- [Git](https://git-scm.com/)

### Step 1 — Clone the repository

```bash
git clone https://github.com/CrisLottz/CoreAsset-RBAC-Inventory-Engine.git
cd CoreAsset-RBAC-Inventory-Engine
```

### Step 2 — Build and start all services

```bash
docker compose up --build
```

> On first run, Docker will build the `python:3.11-slim` backend image and install all Poetry-managed dependencies. This takes ~60–90 seconds. Subsequent starts are near-instant.

### Step 3 — Apply database migrations

In a second terminal, while the containers are running:

```bash
docker compose exec backend python manage.py migrate
```

This applies all DDL changes defined in the `migrations/` directories of `users`, `rbac`, and `audit`, creating the necessary tables in PostgreSQL.

### Step 4 — Create a superuser

```bash
docker compose exec backend python manage.py createsuperuser
```

Follow the interactive prompt to set `username`, `email`, and `password`. This account has unrestricted access to the Django Admin panel (`http://127.0.0.1:8000/admin/`) and all API endpoints.

### Step 5 — Verify the stack

| Service | URL |
|---|---|
| API Root | `http://127.0.0.1:8000/api/` |
| Django Admin | `http://127.0.0.1:8000/admin/` |
| Frontend (dev) | `http://127.0.0.1:5173/` |

To stop all services cleanly:

```bash
docker compose down
```

To stop and **destroy the database volume** (full reset):

```bash
docker compose down -v
```

---

## 6. Production Standards

### Schema Migrations (DDL as Code)

All database schema changes are executed **exclusively through Django migrations**. No raw DDL is applied manually to the database. This ensures that the schema history is version-controlled, reproducible across environments, and reversible.

> ⚠️ Never run `ALTER TABLE` or `CREATE TABLE` commands directly against the production database. Generate a migration with `python manage.py makemigrations` and apply it with `python manage.py migrate`.

### Network Security

- All Docker service ports are bound to `127.0.0.1` (loopback) in the Compose configuration. In a production deployment behind a reverse proxy (e.g., Nginx, Caddy), only port `80`/`443` should be exposed externally. The database and Redis ports must never be publicly reachable.
- `SECRET_KEY` must be rotated and injected via environment variables (e.g., Docker secrets, AWS Secrets Manager) — never hardcoded in `settings.py`.
- `DEBUG = False` must be enforced in all production environments. Set `ALLOWED_HOSTS` to the exact production domain.
- `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` must be narrowed to the production frontend domain only.

### Dependency Integrity

The `poetry.lock` file pins every package and its transitive dependencies to an exact version and hash. Commit this file to version control. In CI/CD pipelines, use `poetry install --no-root` to ensure reproducible builds without implicit upgrades.

---

---
---

# CoreAsset — RBAC Inventory Engine *(Traducción al Español)*

> **API Headless · Grado Empresarial · Lista para White-Label**

Un núcleo de backend blindado y libre de estado para plataformas empresariales que exigen **gobernanza de identidades**, **rastreo de activos físicos y virtuales**, y **pistas de auditoría a prueba de manipulaciones**. Construido como una API Headless componible, está diseñado para impulsar cualquier frontend de marca blanca sin acoplarse a una capa de interfaz específica.

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura del Sistema — Los Cuatro Pilares](#2-arquitectura-del-sistema--los-cuatro-pilares)
3. [Estructura de Directorios del Proyecto](#3-estructura-de-directorios-del-proyecto)
4. [Referencia de la API](#4-referencia-de-la-api)
5. [Instalación y Despliegue Local](#5-instalación-y-despliegue-local)
6. [Estándares de Producción](#6-estándares-de-producción)

---

## 1. Resumen Ejecutivo

CoreAsset-RBAC-Inventory-Engine es el núcleo de backend de una plataforma empresarial de gestión de activos con arquitectura White-Label. Expone una API RESTful construida con **Django 5 + Django REST Framework** y corre en un entorno completamente aislado con **Docker Compose** respaldado por **PostgreSQL 15**.

Su filosofía de diseño prioriza la **seguridad sobre la conveniencia**, la **trazabilidad sobre la velocidad** y la **componibilidad sobre el acoplamiento monolítico**. Cada decisión arquitectónica — desde la autenticación basada en sesiones hasta los metadatos de activos respaldados por JSONB — fue tomada para satisfacer los requisitos de cumplimiento empresarial sin sacrificar la ergonomía del desarrollador.

**Capacidades del núcleo entregadas en la fase actual:**

| Capacidad | Estado |
|---|---|
| Autenticación por sesión (Cookie + CSRF) | ✅ Listo para producción |
| Modelo de Usuario con clave primaria UUID | ✅ Listo para producción |
| RBAC mediante patrón Proxy Model de Django | ✅ Listo para producción |
| Asignación granular de roles vía endpoint RPC | ✅ Listo para producción |
| Pista de auditoría automática de mutaciones HTTP (JSONB) | ✅ Listo para producción |
| Inventario de activos con columna de metadatos JSONB | 🔷 Planificado — Fase 2 |
| Filtrado multi-sede para activos físicos | 🔷 Planificado — Fase 2 |

---

## 2. Arquitectura del Sistema — Los Cuatro Pilares

### Pilar I — Infraestructura Contenerizada

Todo el entorno de ejecución está aislado con **Docker Compose**, que define tres servicios independientes e interconectados en red:

| Servicio | Imagen | Puerto expuesto (solo localhost) |
|---|---|---|
| `db` | `postgres:15-alpine` | `127.0.0.1:5432` |
| `redis` | `redis:7-alpine` | `127.0.0.1:6379` |
| `backend` | Personalizada (`python:3.11-slim`) | `127.0.0.1:8000` |
| `frontend` | Personalizada | `127.0.0.1:5173` |

Todos los puertos están vinculados **exclusivamente a la interfaz de loopback** (`127.0.0.1`), asegurando que ningún servicio quede inadvertidamente expuesto a redes externas. Los datos de PostgreSQL se persisten en un volumen Docker con nombre (`postgres_data`).

La gestión de dependencias dentro del contenedor del backend es manejada por **Poetry** (`pyproject.toml` + `poetry.lock`), que fija cada dependencia transitiva a un hash reproducible. Debido a que el contenedor ya es un entorno aislado, Poetry está configurado para instalar paquetes globalmente dentro de él (`virtualenvs.create = false`), evitando la sobrecarga de entornos virtuales redundantes.

---

### Pilar II — Seguridad y Autenticación (Sin JWT)

Este sistema **deliberadamente no implementa JWT**. El modelo de autenticación se basa en la **Autenticación por Sesión nativa de Django** con **Cookies HTTP-only y tokens CSRF** — una arquitectura fundamentalmente más segura para clientes basados en navegador porque:

- Las cookies de sesión son `HttpOnly` y no pueden ser leídas por JavaScript, eliminando el robo de tokens mediante XSS.
- Cada solicitud mutante debe llevar un token CSRF válido, eliminando los ataques CSRF incluso con una cookie robada.
- La invalidación de sesión es del lado del servidor e inmediata — revocar el acceso no requiere listas negras de tokens.

La configuración de DRF impone este contrato globalmente:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':     ['rest_framework.permissions.IsAuthenticated'],
}
```

Las políticas de CORS y CSRF están estrictamente acotadas al origen del frontend (`http://localhost:5173` en desarrollo), y `CORS_ALLOW_CREDENTIALS = True` permite la transmisión de cookies entre orígenes sin relajar el límite de confianza.

---

### Pilar III — Gestión de Identidades y Accesos (IAM / RBAC)

**Modelo de Usuario Personalizado**

El modelo `User` (`users.User`) extiende el `AbstractUser` de Django con dos sobreescrituras críticas:

- **UUID v4 como clave primaria** — elimina los ataques de enumeración de IDs secuenciales y es globalmente único por construcción.
- **Indicador `is_mfa_enabled`** — fundamento para la futura aplicación de autenticación multifactor.

```python
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_mfa_enabled = models.BooleanField(default=False)
```

**Gestión de Roles vía Proxy Model**

En lugar de introducir una tabla `Role` separada y no relacionada y duplicar la infraestructura de permisos de Django, el modelo `rbac.Role` se implementa como un **Proxy Model** sobre el `Group` nativo de Django:

```python
class Role(Group):
    class Meta:
        proxy = True
        app_label = 'rbac'
```

Esto significa que:
- No se crea ninguna tabla DDL nueva — los objetos `Role` se almacenan en `auth_group`.
- Todos los decoradores de permisos integrados de Django (`@permission_required`, `user.has_perm()`) funcionan desde el primer momento.
- El dominio de negocio usa el vocabulario "Rol" mientras que el ORM usa la infraestructura `Group` probada en batalla.

**Asignación Granular de Roles vía Endpoint RPC Explícito**

La asignación de roles nunca es un efecto secundario silencioso de una llamada `PATCH /users/{id}/`. Es una acción explícita, intencional y auditable expuesta como un endpoint dedicado de estilo RPC:

```
POST /api/users/inventory/{uuid}/assign-roles/
```

Esto garantiza que un desarrollador no pueda sobrescribir accidentalmente los roles de un usuario mientras actualiza su perfil — las operaciones están separadas arquitectónicamente.

---

### Pilar IV — Motor de Cumplimiento (Middleware de Auditoría)

Cada solicitud HTTP que muta estado — `POST`, `PUT`, `PATCH`, `DELETE` — que devuelve una respuesta `2xx` exitosa es **interceptada automáticamente** por `audit.middleware.AuditMiddleware` y registrada en la tabla `audit_logs` sin ninguna participación de código a nivel de vista.

Cada registro de auditoría captura:

| Campo | Contenido |
|---|---|
| `id` | UUID v4 (clave primaria inmutable) |
| `actor` | FK → `User` autenticado (`PROTECT`) |
| `action` | Método HTTP (`POST`, `PUT`, etc.) |
| `entity_type` | Ruta de la solicitud (URL) |
| `entity_id` | UUID del recurso afectado |
| `ip_address` | IP del cliente desde `REMOTE_ADDR` |
| `metadata_json` | Blob JSONB: `status_code`, `user_agent` |
| `created_at` | Marca de tiempo UTC auto-establecida |

**Cadena de custodia protegida**: La clave foránea `actor` usa `on_delete=models.PROTECT`. Esto significa que eliminar un usuario que tiene registros de auditoría es un **bloqueo duro a nivel de base de datos** — la integridad de la pista de auditoría legal no puede ser destruida mediante una acción de interfaz de usuario.

**Almacenamiento JSONB** (`models.JSONField` → PostgreSQL `jsonb`) permite consultas indexadas nativas del payload de metadatos sin requerir cambios de esquema a medida que los campos evolucionan.

---

## 3. Estructura de Directorios del Proyecto

```
CoreAsset-RBAC-Inventory-Engine/
│
├── docker-compose.yml              # Orquesta todos los servicios (db, redis, backend, frontend)
│
├── backend/                        # Raíz de la aplicación Django
│   ├── Dockerfile                  # Imagen python:3.11-slim, instalación con Poetry
│   ├── manage.py                   # Punto de entrada de gestión de Django
│   ├── pyproject.toml              # Definición del proyecto Poetry y fijación de dependencias
│   ├── poetry.lock                 # Archivo de bloqueo determinista de dependencias
│   │
│   ├── core/                       # Paquete de configuración del proyecto Django
│   │   ├── settings.py             # Config de DRF, CORS, CSRF, BD, Middleware
│   │   ├── urls.py                 # Despachador de URLs raíz
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── users/                      # IAM — Modelo de usuario y endpoints de autenticación
│   │   ├── models.py               # Usuario personalizado (UUID PK, is_mfa_enabled)
│   │   ├── serializers.py          # UserSerializer, AssignRoleSerializer
│   │   ├── views.py                # LoginView, LogoutView, UserMeView, UserViewSet
│   │   ├── urls.py                 # Enrutamiento /login/ /logout/ /me/ /inventory/
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── rbac/                       # Control de Acceso Basado en Roles
│   │   ├── models.py               # Role (Proxy → auth_group)
│   │   ├── serializers.py          # RoleSerializer
│   │   ├── views.py                # RoleViewSet (CRUD)
│   │   ├── urls.py                 # Enrutamiento /roles/
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   └── audit/                      # Motor de Cumplimiento
│       ├── middleware.py           # AuditMiddleware (intercepta todas las mutaciones)
│       ├── models.py               # AuditLog (JSONB, FK PROTECT, UUID PK)
│       ├── admin.py
│       └── migrations/
│
└── frontend/                       # Frontend White-Label (servicio separado)
    └── Dockerfile
```

---

## 4. Referencia de la API

Todos los endpoints tienen el prefijo `/api/`. El estado de autenticación se gestiona a través de cookies de sesión — el cliente debe primero obtener un token CSRF a través del flujo de inicio de sesión.

### Autenticación

| Método | Endpoint | Auth Requerida | Descripción |
|---|---|---|---|
| `POST` | `/api/users/login/` | No | Inicia sesión, establece cookies `sessionid` + `csrftoken` |
| `GET` | `/api/users/me/` | Sí | Devuelve el perfil del usuario autenticado |
| `POST` | `/api/users/logout/` | Sí | Destruye la sesión del lado del servidor |

### Inventario de Usuarios

| Método | Endpoint | Auth Requerida | Descripción |
|---|---|---|---|
| `GET` | `/api/users/inventory/` | Sí | Lista todos los usuarios |
| `POST` | `/api/users/inventory/` | Sí | Crea un nuevo usuario |
| `GET` | `/api/users/inventory/{uuid}/` | Sí | Recupera un usuario específico |
| `PUT` | `/api/users/inventory/{uuid}/` | Sí | Actualización completa de un usuario |
| `PATCH` | `/api/users/inventory/{uuid}/` | Sí | Actualización parcial de un usuario |
| `DELETE` | `/api/users/inventory/{uuid}/` | Sí | Elimina un usuario |
| `POST` | `/api/users/inventory/{uuid}/assign-roles/` | Sí | **RPC** — Sobreescribe el conjunto de roles del usuario |

### Gestión de Roles (RBAC)

| Método | Endpoint | Auth Requerida | Descripción |
|---|---|---|---|
| `GET` | `/api/rbac/roles/` | Sí | Lista todos los roles |
| `POST` | `/api/rbac/roles/` | Sí | Crea un nuevo rol |
| `GET` | `/api/rbac/roles/{id}/` | Sí | Recupera un rol específico |
| `PUT` | `/api/rbac/roles/{id}/` | Sí | Actualiza un rol |
| `DELETE` | `/api/rbac/roles/{id}/` | Sí | Elimina un rol |

**`POST /api/users/inventory/{uuid}/assign-roles/` — Cuerpo de la Solicitud:**
```json
{
  "role_ids": [1, 3]
}
```

---

## 5. Instalación y Despliegue Local

### Prerrequisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (con Compose v2)
- [Git](https://git-scm.com/)

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/CrisLottz/CoreAsset-RBAC-Inventory-Engine.git
cd CoreAsset-RBAC-Inventory-Engine
```

### Paso 2 — Construir e iniciar todos los servicios

```bash
docker compose up --build
```

> En el primer arranque, Docker construirá la imagen del backend `python:3.11-slim` e instalará todas las dependencias gestionadas por Poetry. Esto tarda ~60–90 segundos. Los arranques posteriores son casi instantáneos.

### Paso 3 — Aplicar las migraciones de base de datos

En una segunda terminal, mientras los contenedores están en ejecución:

```bash
docker compose exec backend python manage.py migrate
```

Esto aplica todos los cambios DDL definidos en los directorios `migrations/` de `users`, `rbac` y `audit`, creando las tablas necesarias en PostgreSQL.

### Paso 4 — Crear un superusuario

```bash
docker compose exec backend python manage.py createsuperuser
```

Sigue el prompt interactivo para establecer `username`, `email` y `password`. Esta cuenta tiene acceso irrestricto al panel de administración de Django (`http://127.0.0.1:8000/admin/`) y a todos los endpoints de la API.

### Paso 5 — Verificar el stack

| Servicio | URL |
|---|---|
| Raíz de la API | `http://127.0.0.1:8000/api/` |
| Django Admin | `http://127.0.0.1:8000/admin/` |
| Frontend (dev) | `http://127.0.0.1:5173/` |

Para detener todos los servicios limpiamente:

```bash
docker compose down
```

Para detener y **destruir el volumen de la base de datos** (reseteo completo):

```bash
docker compose down -v
```

---

## 6. Estándares de Producción

### Migraciones de Esquema (DDL como Código)

Todos los cambios de esquema de base de datos se ejecutan **exclusivamente a través de migraciones de Django**. Ningún DDL se aplica manualmente a la base de datos. Esto garantiza que el historial del esquema esté versionado, sea reproducible entre entornos y reversible.

> ⚠️ Nunca ejecutes comandos `ALTER TABLE` o `CREATE TABLE` directamente contra la base de datos de producción. Genera una migración con `python manage.py makemigrations` y aplícala con `python manage.py migrate`.

### Seguridad de Red

- Todos los puertos de servicios Docker están vinculados a `127.0.0.1` (loopback) en la configuración de Compose. En un despliegue de producción detrás de un proxy inverso (ej. Nginx, Caddy), solo los puertos `80`/`443` deben estar expuestos externamente. Los puertos de la base de datos y Redis nunca deben ser públicamente accesibles.
- La `SECRET_KEY` debe ser rotada e inyectada a través de variables de entorno (ej. Docker secrets, AWS Secrets Manager) — nunca codificada directamente en `settings.py`.
- `DEBUG = False` debe ser aplicado en todos los entornos de producción. Establece `ALLOWED_HOSTS` al dominio de producción exacto.
- `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` deben ser restringidos únicamente al dominio del frontend de producción.

### Integridad de Dependencias

El archivo `poetry.lock` fija cada paquete y sus dependencias transitivas a una versión exacta y hash. Confirma este archivo en el control de versiones. En los pipelines de CI/CD, usa `poetry install --no-root` para garantizar construcciones reproducibles sin actualizaciones implícitas.
