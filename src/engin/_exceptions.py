from typing import Any

from engin._dependency import Provide


class ProviderError(Exception):
    """
    Raised when a Provider errors during Assembly.
    """

    def __init__(
        self,
        provider: Provide[Any],
        error_type: type[Exception],
        error_message: str,
    ) -> None:
        self.provider = provider
        self.error_type = error_type
        self.error_message = error_message
        self.message = (
            f"provider '{provider.name}' errored with error "
            f"({error_type.__name__}): '{error_message}'"
        )

    def __str__(self) -> str:
        return self.message
