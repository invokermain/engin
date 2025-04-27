from typing import TYPE_CHECKING, Any

from engin._dependency import Provide

if TYPE_CHECKING:
    from engin._block import Block


class EnginError(Exception):
    """
    Base class for all custom exceptions in the Engin library.
    """


class AssemblerError(EnginError):
    """
    Base class for all custom exceptions raised by the Assembler.
    """


class InvalidBlockError(EnginError):
    """
    Raised when an invalid block is instantiated.
    """

    def __init__(self, block: "type[Block]", reason: str) -> None:
        self.block = block
        self.block_name = block.name or block.__name__
        self.message = f"block '{self.block_name}' is invalid, reason: '{reason}'"

    def __str__(self) -> str:
        return self.message


class ProviderError(AssemblerError):
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


class NotInScopeError(AssemblerError):
    """
    Raised when a Provider is requested outside of its scope.
    """

    def __init__(self, provider: Provide[Any], scope_stack: list[str]) -> None:
        self.provider = provider
        self.message = (
            f"provider '{provider.name}' was requested outside of its specified scope "
            f"'{provider.scope}', current scope stack is {scope_stack}"
        )

    def __str__(self) -> str:
        return self.message


__all__ = [
    "AssemblerError",
    "EnginError",
    "InvalidBlockError",
    "NotInScopeError",
    "ProviderError",
]
