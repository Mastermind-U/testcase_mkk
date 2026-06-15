# Agents Guide

This repository uses a clean architecture style with four layers:

## 1. Presentation
The outermost layer. It owns HTTP handlers, request/response schemas, and other delivery adapters.
It is responsible for API work and other public interfaces.

Examples:
- `presentation/api/*`

Responsibilities:
- parse input
- call interactors
- translate domain/application results into transport responses
- keep framework code out of business rules

## 2. Application
The use-case layer. It contains interactors, DTOs, and gateway interfaces.

Examples:
- `application/healthcheck/interactor.py`
- `application/healthcheck/dto.py`
- `application/healthcheck/gateway.py`

Responsibilities:
- orchestrate a single use case
- define input/output models for that use case
- depend only on domain types and gateway protocols
- never import infrastructure implementations

## 3. Entities
The innermost layer. It contains domain entities, enums, and domain exceptions.

Examples:
- `entities/entities.py`
- `entities/enums.py`
- `entities/exceptions.py`

Responsibilities:
- store business concepts and invariants
- remain independent from FastAPI, SQLAlchemy, Dishka, and Alembic
- provide the stable core that other layers depend on

## 4. Infrastructure
The outer adapter layer for technical details.
It contains all interaction with internal services such as the database, cache, queues, and other technical integrations.

Examples:
- `infrastructure/sa/pg/gateways/*`
- `infrastructure/sa/pg/tables.py`
- `infrastructure/sa/pg/alembic/*`

Responsibilities:
- implement gateway protocols
- define SQLAlchemy tables and imperative mappings
- hold database and migration setup
- isolate technical frameworks from the application core

## Dependency Direction
Dependencies must point inward:

- `presentation` depends on `application`
- `application` depends on `entities`
- `infrastructure` depends on `application` and `entities`
- `entities` depends on nothing else in the project

Never violate this direction:
- do not import `presentation` from `application`, `entities`, or `infrastructure`
- do not import `application` from `entities`
- do not import `infrastructure` from `application` or `entities` unless it is the declared adapter boundary
- do not create shortcuts that bypass the layer boundary just to reuse code

`Dishka` is the dependency-inversion container. It wires implementations at the edges and injects them into use-case code, so the application layer stays framework-free.

Apply CQS in the application layer: separate command use cases that change state from query use cases that only read state.
Prefer interactors to expose a single public `execute` method when possible, and organize application code into `commands`, `queries`, and `common` packages.

## Why This Separation Matters
- It reduces coupling between business logic and technical details.
- It makes testing easier because each layer can be isolated.
- It keeps SQLAlchemy, FastAPI, and DI code out of domain logic.
- It shortens the context window for agents: each task can be solved inside a smaller, clearer slice of the codebase, which usually improves code generation quality.

## How To Explain This Architecture
When answering user questions about the repo, keep the explanation short and practical:

- Clean architecture means the core business rules do not depend on web frameworks or storage engines.
- `Dishka` builds the object graph and injects dependencies into use-case code.
- Layer separation prevents framework code from leaking into business rules.
- Imperative mapping keeps SQLAlchemy explicit and avoids ORM concerns inside domain entities.
- Imperative mapping also keeps persistence details out of the domain model, so database shape, relationships, and loading rules can change without turning entities into ORM-aware objects.
- That makes behavior easier to test and reduces surprises from hidden ORM magic like implicit joins, lazy loading, or attribute side effects.
- Smaller layer-scoped context helps agents generate better code with less noise.

## Validation
Use these tools to verify changes after every session:

- `lint-imports` for import-layer checks
- `pytest` for tests
- `ruff` for lint and formatting validation
- `mypy` for type validation

For each changed Python file, before the final check, run `ruff` in this order:

1. `ruff format %file%`
2. `ruff check --fix --unsafe-fixes %file%`

Run the validation from the repository root unless the task says otherwise.

## Testing
Keep tests aligned with the layer they exercise:

- `unit` tests cover isolated business logic and small technical helpers with mocks or fakes.
- `gateway` tests cover concrete gateway implementations and their interaction with storage or other adapters.
- `api contract` tests cover HTTP behavior and response shape without relying on real infrastructure.
- `integration` tests cover the use case logic together with the database, but without the HTTP layer, so they exercise the interactor directly.

Pytest asyncio behavior is configured for `auto` mode in `pyproject.toml`. Follow that mode when writing or updating tests:

- async tests may be collected without explicit `@pytest.mark.asyncio` when the plugin can infer them
- async fixtures may be declared in the style expected by `auto` mode
- do not assume `strict` mode conventions unless a test file explicitly overrides them
- keep the `asyncio_default_fixture_loop_scope` and `asyncio_default_test_loop_scope` settings in mind when a test depends on loop lifetime

When a test needs a local dependency override, create a test-specific `Dishka` provider and register it in the test container. Prefer this over monkeypatching application code. A typical API test pattern is:

```python
class TestBobProvider(Provider):
    __test__ = False
    interactor = from_context(
        provides=BobCheckInteractor,
        scope=Scope.RUNTIME,
    )

@pytest.fixture
def bob_interactor_mock() -> AsyncMock:
    return AsyncMock(spec=BobCheckInteractor)

@pytest_asyncio.fixture
async def container(
    config: Config,
    bob_interactor_mock: AsyncMock,
) -> AsyncIterator[AsyncContainer]:
    container = make_async_container(
        TestProvider(),
        TestBobProvider(),
        context={
            Config: config,
            BobCheckInteractor: bob_interactor_mock,
        },
        start_scope=Scope.RUNTIME,
    )
    yield container
    await container.close()
```

This keeps overrides close to the test and lets API tests swap only the dependency they need.

When the override should apply to the whole test module or test class, expose a test-local `container` fixture in `tests/conftest.py` or the test module itself and build it with `make_async_container(...)`, adding `TestBobProvider()` alongside the default provider set. That way the test can replace the shared container cleanly without patching application code.

If the test uses the shared test container, keep the container setup in the common `tests/conftest.py` fixture and override the module-level `container` or `app` fixture only when the test needs a different provider set. The container should still be assembled through `make_async_container(...)`, with the test provider added alongside the default one.

Integration tests should use the real database setup and call the interactor directly, but they should not go through the API router or the HTTP client.

## New Feature Template
When adding a new feature, follow the same shape used by `healthcheck`:

1. Create the interactor in `application/<feature>/interactor.py`.
2. Add feature DTOs in `application/<feature>/dto.py`.
3. Define the gateway interface as a `Protocol` in `application/<feature>/gateway.py`.
4. Implement the gateway in `infrastructure/sa/pg/gateways/<feature>_gw.py`.
5. Add or extend domain entities in `entities/` if the feature needs new business concepts.
6. Add SQLAlchemy tables in `infrastructure/sa/pg/tables.py`.
7. Map entities imperatively with the SQLAlchemy registry, as in the existing outbox mapping.
8. Register the gateway and interactor in `ioc.py`.
9. Expose the use case through `presentation/`.
10. Add or update an Alembic migration when the schema changes.

## Practical Examples
- `healthcheck` shows the minimal path: DTO, gateway protocol, interactor, infrastructure gateway, and HTTP endpoint.
- `outbox` shows the persistence path: a domain entity in `entities`, a SQLAlchemy table in `infrastructure/sa/pg/tables.py`, and imperative registry mapping.

## Advanced Cases
Some use cases are simpler if the gateway returns a domain entity directly instead of a primitive value or a transport DTO.

Use this pattern when:
- the use case needs business behavior on the entity
- the loaded object is part of the domain model
- returning the entity keeps the application layer simpler and more explicit

In these cases:
- the gateway protocol in `application/<feature>/gateway.py` may declare a domain entity as the return type
- the interactor can work with the entity directly
- the infrastructure implementation still owns all SQLAlchemy details

When persistence becomes more than a single read or write, use SQLAlchemy repository and unit-of-work patterns in infrastructure:

- `repository` encapsulates entity loading and persistence operations
- `uow` groups multiple repository operations into one transaction boundary
- `session` stays inside infrastructure and should not leak into application code

Rules for these cases:
- application code depends on the gateway protocol, not on SQLAlchemy
- repositories may use SQLAlchemy sessions internally
- a unit of work should manage commit, rollback, and transaction scope
- if a use case needs multiple coordinated changes, prefer `uow + repositories` over passing a raw session upward

## IOC Wiring
Create dependencies in `ioc.py` by binding a gateway protocol to its implementation.

Pattern:

1. Import the gateway `Protocol` from `application/<feature>/gateway.py`.
2. Import the concrete implementation from `infrastructure/`.
3. Register the implementation with `Dishka` using `provide(...)`.
4. Set `provides=` to the protocol type so application code receives the interface, not the implementation.
5. Pick the narrowest scope that matches the dependency lifetime.

Example:

```python
feature_gw = provide(
    FeatureGatewayImpl,
    provides=FeatureGateway,
    scope=Scope.REQUEST,
)
```

Rules:
- application code should depend on `FeatureGateway`, not on `FeatureGatewayImpl`
- infrastructure owns the concrete class and any SQLAlchemy/session usage
- if the gateway depends on session or engine objects, declare those as separate provider methods in the same container
- keep scope aligned with the dependency lifetime; request-scoped gateways are the default when they use a request-scoped session

## Rules Of Thumb
- Keep HTTP and database details at the edges.
- Keep use cases small and focused.
- Prefer explicit mapping over hidden ORM behavior.
- Add new abstractions only when a feature needs them.
