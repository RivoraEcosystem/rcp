# Lifespan Management

RCP provides a lifespan protocol for application startup and shutdown.

The lifespan scope is:

```python
class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    rcp: RCP
    state: NotRequired[dict[str, Any]]
```

The lifespan scope does not contain HTTP stream or WebTransport session information.

---

## Lifespan Startup

The server sends:

```python
{
    "type": "lifespan.startup",
}
```

The application must respond with either:

```python
{
    "type": "lifespan.startup.complete",
}
```

or:

```python
{
    "type": "lifespan.startup.failed",
    "message": "Reason",
}
```

---

## Lifespan Shutdown

The server sends:

```python
{
    "type": "lifespan.shutdown",
}
```

The application responds with either:

```python
{
    "type": "lifespan.shutdown.complete",
}
```

or:

```python
{
    "type": "lifespan.shutdown.failed",
    "message": "Reason",
}
```

