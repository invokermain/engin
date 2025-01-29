import asyncio
import logging
import os
import signal
from asyncio import Event, Task
from collections.abc import Iterable
from contextlib import AsyncExitStack
from itertools import chain
from types import FrameType
from typing import ClassVar, TypeAlias

from engin import Entrypoint
from engin._assembler import AssembledDependency, Assembler
from engin._block import Block
from engin._dependency import Dependency, Invoke, Provide, Supply
from engin._lifecycle import Lifecycle
from engin._type_utils import TypeId

LOG = logging.getLogger("engin")

Option: TypeAlias = Invoke | Provide | Supply | Block
_Opt: TypeAlias = Invoke | Provide | Supply

_OS_IS_WINDOWS = os.name == "nt"


class Engin:
    """
    The Engin is a modular application defined by a collection of options.

    Users should instantiate the Engin with a number of options, where options can be an
    instance of Provide, Invoke, or a collection of these combined in a Block.

    To create a useful application, users should pass in one or more providers (Provide or
    Supply) and at least one invocation (Invoke or Entrypoint).

    When instantiated the Engin can be run. This is typically done via the `run` method,
    but certain use cases, e.g. testing, it can be easier to use the `start` and `stop`
    methods.

    When ran the Engin takes care of the complete application lifecycle:
    1. The Engin assembles all Invocations. Only Providers that are required to satisfy
       the Invoke options parameters are assembled.
    2. All Invocations are run sequentially in the order they were passed in to the Engin.
    3. Any Lifecycle Startup defined by a provider that was assembled in order to satisfy
       the constructors is ran.
    4. The Engin waits for a stop signal, i.e. SIGINT or SIGTERM.
    5. Any Lifecyce Shutdown task is ran, in the reverse order to the Startup order.

    Examples:
        ```python
        import asyncio

        from httpx import AsyncClient

        from engin import Engin, Invoke, Provide


        def httpx_client() -> AsyncClient:
            return AsyncClient()


        async def main(http_client: AsyncClient) -> None:
            print(await http_client.get("https://httpbin.org/get"))

        engin = Engin(Provide(httpx_client), Invoke(main))

        asyncio.run(engin.run())
        ```
    """

    _LIB_OPTIONS: ClassVar[list[Option]] = [Provide(Lifecycle)]

    def __init__(self, *options: Option) -> None:
        """
        Initialise the class with the provided options.

        Examples:
            >>> engin = Engin(Provide(construct_a), Invoke(do_b), Supply(C()), MyBlock())

        Args:
            *options: an instance of Provide, Supply, Invoke, Entrypoint or a Block.
        """
        self._providers: dict[TypeId, Provide] = {TypeId.from_type(Engin): Provide(self._self)}
        self._invokables: list[Invoke] = []

        self._stop_requested_event = Event()
        self._stop_complete_event = Event()
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._shutdown_task: Task | None = None
        self._run_task: Task | None = None

        self._destruct_options(chain(self._LIB_OPTIONS, options))
        self._assembler = Assembler(self._providers.values())

    @property
    def assembler(self) -> Assembler:
        return self._assembler

    async def run(self) -> None:
        """
        Run the engin.

        The engin will run until it is stopped via an external signal (i.e. SIGTERM or
        SIGINT) or the `stop` method is called on the engin.
        """
        await self.start()
        self._run_task = asyncio.create_task(_wait_for_stop_signal(self._stop_requested_event))
        await self._stop_requested_event.wait()
        await self._shutdown()

    async def start(self) -> None:
        """
        Start the engin.

        This is an alternative to calling `run`. This method waits for the startup
        lifecycle to complete and then returns. The caller is then responsible for
        calling `stop`.
        """
        LOG.info("starting engin")
        assembled_invocations: list[AssembledDependency] = [
            await self._assembler.assemble(invocation) for invocation in self._invokables
        ]

        for invocation in assembled_invocations:
            try:
                await invocation()
            except Exception as err:
                name = invocation.dependency.name
                LOG.error(f"invocation '{name}' errored, exiting", exc_info=err)
                return

        lifecycle = await self._assembler.get(Lifecycle)

        try:
            for hook in lifecycle.list():
                await self._exit_stack.enter_async_context(hook)
        except Exception as err:
            LOG.error("lifecycle startup error, exiting", exc_info=err)
            await self._exit_stack.aclose()
            return

        LOG.info("startup complete")

        self._shutdown_task = asyncio.create_task(self._shutdown_when_stopped())

    async def stop(self) -> None:
        """
        Stop the engin.

        This method will wait for the shutdown lifecycle to complete before returning.
        Note this method can be safely called at any point, even before the engin is
        started.
        """
        self._stop_requested_event.set()
        await self._stop_complete_event.wait()

    async def _shutdown(self) -> None:
        LOG.info("stopping engin")
        await self._exit_stack.aclose()
        self._stop_complete_event.set()
        LOG.info("shutdown complete")

    async def _shutdown_when_stopped(self) -> None:
        await self._stop_requested_event.wait()
        await self._shutdown()

    def _destruct_options(self, options: Iterable[Option]) -> None:
        for opt in options:
            if isinstance(opt, Block):
                self._destruct_options(opt)
            if isinstance(opt, Provide | Supply):
                existing = self._providers.get(opt.return_type_id)
                self._log_option(opt, overwrites=existing)
                self._providers[opt.return_type_id] = opt
            elif isinstance(opt, Invoke):
                self._log_option(opt)
                self._invokables.append(opt)

    @staticmethod
    def _log_option(opt: Dependency, overwrites: Dependency | None = None) -> None:
        if overwrites is not None:
            extra = f"\tOVERWRITES {overwrites.name}"
            if overwrites.block_name:
                extra += f" [{overwrites.block_name}]"
        else:
            extra = ""
        if isinstance(opt, Supply):
            LOG.debug(f"SUPPLY      {opt.return_type_id!s:<35}{extra}")
        elif isinstance(opt, Provide):
            LOG.debug(f"PROVIDE     {opt.return_type_id!s:<35} <- {opt.name}() {extra}")
        elif isinstance(opt, Entrypoint):
            type_id = opt.parameter_types[0]
            LOG.debug(f"ENTRYPOINT  {type_id!s:<35}")
        elif isinstance(opt, Invoke):
            LOG.debug(f"INVOKE      {opt.name:<35}")

    def _self(self) -> "Engin":
        return self


async def _wait_for_stop_signal(stop_requested_event: Event) -> None:
    try:
        # try to gracefully handle sigint/sigterm
        if not _OS_IS_WINDOWS:
            loop = asyncio.get_running_loop()
            for signame in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(signame, stop_requested_event.set)

            await stop_requested_event.wait()
        else:
            should_stop = False

            # windows does not support signal_handlers, so this is the workaround
            def ctrlc_handler(sig: int, frame: FrameType | None) -> None:
                nonlocal should_stop
                if should_stop:
                    raise KeyboardInterrupt("Forced keyboard interrupt")
                should_stop = True

            signal.signal(signal.SIGINT, ctrlc_handler)

            while not should_stop:
                # In case engin is stopped via external `stop` call.
                if stop_requested_event.is_set():
                    return
                await asyncio.sleep(0.1)

            stop_requested_event.set()
    except asyncio.CancelledError:
        pass
