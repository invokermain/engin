Let's start by creating a minimal application using Engin. We do this by instantiating the
Engin class which will serve as our application runtime.

```python title="app.py"
import asyncio
import logging

from engin import Engin

engin = Engin()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(engin.run())
```

If we run the application using `python app.py` we will see the following output:

```
INFO:engin:starting engin
INFO:engin:startup complete
```

And if we stop the application using `ctrl + c` or equivalent we will see:

```
INFO:engin:stopping engin
INFO:engin:shutdown complete
```

Now that we have an empty application, let's give it something to do.

!!! note
    
    Engin is typically used for long running application such as Web Servers or an Event
    Consumers. In these scenarios the engin would run until it receives a SIGINT signal (for
    example when a new deployment happens) at which point it would shutdown.
