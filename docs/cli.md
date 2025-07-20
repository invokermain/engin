# CLI Commands

Engin provides a set of CLI commands to aid with application development. To use these commands,
you need to install Engin with the `cli` extra, which can safely be treated as a
development only dependency.

```shell
uv add engin[cli]
```

!!! tip
    
    It is recommended to configure a default instance in your `pyproject.toml`.
    
    ```toml
    [tool.engin]
    default-instance = "myapp.main:engin"
    ```
    
    When configured, you can run any CLI command without the app argument:
    
    ```shell
    # Uses the default instance from pyproject.toml
    engin check
    
    # Passing an explicit instance always overrides the default instance
    engin check myapp.main:engin
    ```

## Commands

- `engin check`: checks for missing providers.
- `engin inspect`: show metadata about providers.
- `engin graph`: visualise your dependency graph.

### engin check

Checks that all dependencies in your Engin instance are satisfied.

If there are any missing providers it will return with exit code 1.

Note, this command only validates there are providers for all dependencies required by
invocations, any dependencies built dynamically at runtime via the Assembler will not be
checked for as these cannot be statically analysed.

#### Usage
```shell
engin check [OPTIONS]
```

#### Options

- `--app`: the path to your application in the format `<module>:<attribute>`, e.g. `myapp.main:engin`. Not
   required if you set a `default-instance` in your `pyproject.toml`.

#### Example

```shell
engin check myapp.main:engin
```

=== "Success"

    ```
    ✅ All dependencies are satisfied!
    ```

=== "Missing Dependencies"

    ```
    ❌ Missing providers found:
      • httpx.AsyncClient
      • DatabaseConfig

    Available providers:
      • str
      • engin._assembler.Assembler
      • engin._lifecycle.Lifecycle
    ```

### engin inspect

Shows detailed metadata for providers in your Engin instance. You can filter providers by type
or module.

#### Usage
```shell
engin inspect [OPTIONS]
```

#### Options

- `--app`: the path to your application in the format `<module>:<attribute>`, e.g. `myapp.main:engin`. Not
   required if you set a `default-instance` in your `pyproject.toml`.
- `--type`: filter providers by return type name. Note that multiproviders take the form of `type[]`.
- `--module`: filter providers by the return type's module.
- `--verbose`: enable verbose output.

#### Example

```shell
engin inspect myapp.main:engin --module httpx
```

=== "Output"
    
    ```
    Found 1 matching provider
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ name           │ Provide(factory=httpx_client, type=AsyncClient)  │
    │ scope          │ N/A                                              │
    │ func           │ httpx_client                                     │
    │ block          │ N/A                                              │
    │ source module  │ myapp.main                                       │
    │ source package │ myapp                                            │
    └─────────────────────────────────────────────────────────────────────────┘
    ```

### engin graph

Creates a visual representation of your application's dependency graph.

This starts a local web server which displays an interactive graph of your dependencies.

#### Usage
```shell
engin graph [OPTIONS]
```

#### Options

- `--app`: the path to your application in the format `<module>:<attribute>`, e.g. `myapp.main:engin`. Not
   required if you set a `default-instance` in your `pyproject.toml`.

#### Example

```shell
engin graph myapp.main:engin
```

=== "Visualisation"

    ![engin-graph-output.png](engin-graph-output.png)

=== "Console"

    ```
    Serving dependency graph on http://localhost:8123
    ```
