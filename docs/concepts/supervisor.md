# Supervisor

The Supervisor manages background tasks for your application.

Background tasks are long-running coroutines that need to run concurrently while your
application is running. The Supervisor handles starting these tasks, monitoring them for errors,
and cancelling them when the application is shutting down.

## Using the Supervisor

The Supervisor is automatically provided by the Engin and can be injected into any provider or invocation:

```python
from engin import Engin, Provide, Supervisor, OnException


def background_worker(supervisor: Supervisor) -> WorkerService:
    worker = WorkerService()
    
    # Register the worker's run method as a supervised task
    supervisor.supervise(worker.run)
    
    return worker


engin = Engin(Provide(background_worker))
```


## Error Handling

The Supervisor provides three error handling strategies via the `OnException` enum:

### `OnException.SHUTDOWN`

Stops the entire application when the task fails:

```python
supervisor.supervise(critical_task)  # Will shutdown app on error
```

This is the default behaviour.

### `OnException.RETRY`

Automatically restarts the task when it fails:

```python
supervisor.supervise(
    flaky_network_task,
    on_exception=OnException.RETRY
)
```

### `OnException.IGNORE`

Logs the error but continues running other tasks:

```python
supervisor.supervise(
    optional_monitoring_task,
    on_exception=OnException.IGNORE
)
```

## Task Shutdown Hook

When the Engin is shutdown (e.g. when receiving a SIGTERM) the Supervisor will cancel all
supervised tasks using the underlying async backend cancellation mechanism, for
example by raising a `CancellationError` for `asyncio` projects. This is OK for the
majority of cases, however some supervised tasks might manage their own shutdown procedure
and do not handle cancellation well. For these cases the `Supervisor` exposes a
`shutdown_hook` which will be called just before the task is cancelled.

To set a `shutdown_hook` simply pass in the relevant parameter when calling
`Supervisor.supervise`.
