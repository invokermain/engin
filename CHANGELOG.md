# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - UNRELEASED

### Added

- Supervisor class which can safely supervise long running tasks.

### Changed

- `ASGIEngin.run()` now raises an error to prevent incorrect usage.


## [0.0.20] - 2025-06-18

### Changed

- Improved string representation of Provide & Supply to make error messages more helpful.

### Fixed

- Engin now correctly supports postponed evaluation of annotations, e.g. `x: "MyType"` in
  a factory function.


## [0.0.19] - 2025-04-27

### Added

- A new exception: `InvalidBlockError`.

### Changed

- Improved performance of Provide & Assembler by a factor of >2x (in certain scenarios).
- Renamed the `ext` subpackage to `extensions`.
- Errors are now imported from `engin.exceptions.*` instead of `engin.*`
- Blocks will now raise an `InvalidBlockError` if the block has methods which are not
  decorated with `@provide` & `@invoke`.

### Fixed

- `Assembler.add` incorrect cache invalidation logic.


## [0.0.18] - 2025-04-25

### Added

- A new cli option `engin inspect` that can be used to inspect providers, e.g.
  `engin inspect examples.simple.main:engin --module httpx`


## [0.0.17] - 2025-04-20

### Added

- `Provide` now has the `as_type` parameter that `Supply` had previously.

### Changed

- Renamed `parameter_types` property on dependencies to `parameter_type_ids` to be more
  explicit.


## [0.0.16] - 2025-04-16

### Added

- Preliminary support for scoped providers. Scoped providers are only accessible when
  the assembler is in the matching scope, and the built output is only cached until the
  assembler leaves the matching scope. This can be used for example to have request scoped
  providers in a Web Server.

### Changed

- Minor improvements to the work-in-progress dependency grapher.


## [0.0.15] - 2025-03-25

### Changed

- `Provide` & `Supply` will now raise an error if overriding an existing provider from the
  same package. This is to prevent accidental overrides. Users can explicitly allow
  overrides by specifying the `override` parameter when defining the provider
  `Provide(..., override=True)` or `@provide(override=True)`.
- Lifecycle startup tasks will now timeout after 15 seconds and raise an error.
- Assembler's `get` method has been renamed to `build`.
- Supply's `type_hint` parameter has been renamed to `as_type`.

### Fixed

- `Assembler` would occasionally fail to call all multiproviders due to inconsistent
  ordering.


## [0.0.14] - 2025-03-23

### Added

- `LifecycleHook` class to help build simple lifecycles with a start and stop call.

### Changed

- `engin-graph` has been replaced by `engin graph`.
- Engin now uses `typer` for an improved cli experience. Note the package now has an extra `cli` which must be installed to use the cli.
- `Assembler.add(...)` does not error when adding already registered providers.
- Use a more performant algorithm for inspecting frame stack.

### Fixed

- `ASGIEngin` now properly surfaces startup errors.
- `Engin.run()` doing a double shutdown.


## [0.0.13] - 2025-03-22

### Changed

- `Provide` now supports union types.


## [0.0.12] - 2025-03-03

### Added

- `Assembler` has a new method `add(provider: Provide) -> None` which allows adding a
  provider to the Assembler post initialisation.

### Changed

- `Provide` now raises a `ValueError` if the factory function is circular, i.e. one of its
  parameters is the same as its return type as the behaviour of this is undefined.
- The ASGI utility method `engin_to_lifespan` has been improved so that it works "out of
  the box" for more use cases now.


## [0.0.11] - 2025-03-02

### Added

- Dependency types now have two new attributes `source_module` & `source_package`.

### Changed

- `engin-graph` now highlights external dependencies.


## [0.0.10] - 2025-02-27

### Added

- A utility function for ASGI extension `engin_to_lifespan` enabling users to easily
  integrate Engin into an existing ASGI application.
- Further documentation work, including a FastAPI guide.

### Fixed

- The warning for missing multiproviders is only logged once for each given type now.


## [0.0.9] - 2025-02-22

### Added

- Dependency class now has a new attribute: `func_name`.

### Changed

- Improved `engin-graph` output.
- The `module` attribute of dependencies has been renamed to `origin`

### Fixed

- Options provided under the `options` on a Block now have the `block_name` set.


## [0.0.8] - 2025-02-22

### Added

- A package script, `engin-graph` for visualising the dependency graph.


## [0.0.7] - 2025-02-20

### Changed

- TypeId retains Annotations allowing them to be used to discriminate otherwise identical
  types.


## [0.0.6] - 2025-02-19

### Fixed

- Engin now respects intended multiproviders behaviour instead of treating them as normal
  providers and overwriting existing multiproviders for that type.
- `Engin.shutdown()` does not block if shutdown is called before startup, or after aborted
  startup.


## [0.0.5] - 2025-01-29

### Added

- Docstrings for every public class, method and function.

### Changed

- AssemblyError has been renamed to ProviderError.
- Lifecycle now supports synchronous Context Managers.


## [0.0.4] - 2025-01-27

### Changed

- Invocations, startups tasks and shutdown tasks are now all run sequentially.
- Improved error handling, if an Invocation errors, or a Lifecycle startup tasks errors
  then the Engin will exit. Whilst errors in shutdown tasks are logged and ignored. 
- Improved error messaging when Invocations or Lifecycle tasks error.
- Removed non-public methods from the Lifecycle class, and renamed `register_context` to
  `append`.


## [0.0.3] - 2025-01-15

### Added

- Blocks can now provide options via the `options` class variable. This allows packaged
  Blocks to easily expose Providers and Invocations as normal functions whilst allowing
  them to be part of a Block as well. This makes usage of the Block optional which makes
  it more flexible for end users.
- Added missing type hints and enabled mypy strict mode.

### Fixed

- Engin now performs Lifecycle shutdown.


## [0.0.2] - 2025-01-10

### Added

- The `ext` sub-package is now explicitly exported in the package `__init__.py`


## [0.0.1] - 2024-12-12

### Added

- Initial release