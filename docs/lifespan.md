# Lifespan Management

RCP provides a lifespan protocol for application startup and shutdown.

The lifespan scope is:

```python
class LifespanScope(TypedDict):
    type: Literal[ScopeType.LIFESPAN]
    rcp: RCP
    state: NotRequired[dict[str, Any]]
```

The lifespan scope does not contain HTTP stream or WebTransport session information.

---

## Lifespan Startup

The server sends:

```python
{
    "type": LifespanEventType.STARTUP,
}
```

The application must respond with either:

```python
{
    "type": LifespanEventType.STARTUP_COMPLETE,
}
```

or:

```python
{
    "type": LifespanEventType.STARTUP_FAILED,
    "message": "Reason",
}
```

---

## Lifespan Shutdown

The server sends:

```python
{
    "type": LifespanEventType.SHUTDOWN,
}
```

The application responds with either:

```python
{
    "type": LifespanEventType.SHUTDOWN_COMPLETE,
}
```

or:

```python
{
    "type": LifespanEventType.SHUTDOWN_FAILED,
    "message": "Reason",
}
```

