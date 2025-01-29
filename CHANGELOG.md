# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


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