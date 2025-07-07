# Tutorial

In this tutorial we will build a small toy application from scratch.

Our application will publish random numbers to a Valkey stream, and then consume them and
update a running total.

## 1. Create a Valkey client

```python
from valkey import Valkey

def valkey_client() -> Valkey:
    ...
```