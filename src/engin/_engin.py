import asyncio
import logging
import signal
import sys
from asyncio import Event
from collections import defaultdict
from contextlib import AsyncExitStack
from enum import Enum
from itertools import chain
from types import FrameType
from typing import TYPE_CHECKING, ClassVar

from anyio import create_task_group, open_signal_receiver

from engin._assembler import AssembledDependency, Assembler
from engin._dependency import Invoke, Modify, Provide, Supply
from engin._graph import DependencyGrapher, Node
from engin._lifecycle import Lifecycle
from engin._option import Option
from engin._supervisor import Supervisor
from engin.exceptions import EnginError

if TYPE_CHECKING:
    from engin._type_utils import TypeId

_OS_IS_WINDOWS = sys.platform == "win32"
LOG = logging.getLogger("engin")


class _EnginState(Enum):
    IDLE = 0
    """
    Engin is not yet started.
    """

    RUNNING = 1
    """
    Engin is currently running.
    """

    SHUTDOWN = 2
    """
    Engin has performed shutdown
    """


class Engin:
    """
    The Engin is a modular application defined by a collection of options.

    Users should instantiate the Engin with a number of options, where options can be an
    instance of Provide, Invoke, or a collection of these combined in a Block.

    To create a useful application, users should pass in one or more providers (Provide or
    Supply) and at least one invocation (Invoke or Entrypoint).

    When instantiated the Engin can be run. This is typically done via the `run` method,
    but for advanced usecases it can be easier to use the `start` and `stop` methods.

    When ran the Engin takes care of the complete application lifecycle:

    1. The Engin assembles all Invocations. Only Providers that are required to satisfy
       the Invoke options parameters are assembled.
    2. All Invocations are run sequentially in the order they were passed in to the Engin.
    3. Lifecycle Startup tasks registered by assembled dependencies are run sequentially.
    4. The Engin waits for a stop signal, i.e. SIGINT or SIGTERM, or a supervised task that
       causes a shutdown.
    5. Lifecyce Shutdown tasks are run in the reverse order to the Startup order.

    Examples:
        ```python
        import asyncio

        from httpx import AsyncClient

        from engin import Engin, Invoke, Lifecycle, Provide


        def httpx_client(lifecycle: Lifecycle) -> AsyncClient:
            client = AsyncClient()
            lifecycle.append(client)
            return client


        async def main(http_client: AsyncClient) -> None:
            print(await http_client.get("https://httpbin.org/get"))

        engin = Engin(Provide(httpx_client), Invoke(main))

        asyncio.run(engin.run())
        ```
    """

    _LIB_OPTIONS: ClassVar[list[Option]] = [Provide(Lifecycle), Provide(Supervisor)]
    _STOP_ON_SINGAL: ClassVar[bool] = True

    def __init__(self, *options: Option) -> None:
        """
        Initialise the class with the provided options.

        Examples:
            >>> engin = Engin(Provide(construct_a), Invoke(do_b), Supply(C()), MyBlock())

        Args:
            *options: an instance of Provide, Supply, Invoke, Entrypoint or a Block.
        """
        self._state = _EnginState.IDLE
        self._start_complete_event = Event()
        self._stop_requested_event = Event()
        self._stop_complete_event = Event()
        self._exit_stack = AsyncExitStack()
        self._async_context_run_task: asyncio.Task | None = None

        self._providers: dict[TypeId, Provide] = {}
        self._multiproviders: dict[TypeId, list[Provide]] = defaultdict(list)
        self._modifiers: dict[TypeId, Modify] = {}
        self._invocations: list[Invoke] = []

        # populates the above
        for option in chain(self._LIB_OPTIONS, options):
            option.apply(self)

        # initialise Assembler
        self._assembler = Assembler.from_mapped_providers(
            providers=self._providers,
            multiproviders=self._multiproviders,
            modifiers=self._modifiers,
        )
        self._assembler.add(Supply(self._assembler))

    @property
    def assembler(self) -> Assembler:
        return self._assembler

    async def run(self) -> None:
        """
        Run the engin.

        The engin will run until it is stopped via an external signal (i.e. SIGTERM or
        SIGINT), the `stop` method is called on the engin, or a lifecycle task errors.
        """
        if self._state != _EnginState.IDLE:
            raise EnginError("Engin is not idle, unable to start")

        LOG.info("starting engin")
        assembled_invocations: list[AssembledDependency] = [
            await self._assembler.assemble(invocation) for invocation in self._invocations
        ]

        for invocation in assembled_invocations:
            try:
                await invocation()
            except Exception as err:
                name = invocation.dependency.name
                LOG.error(f"invocation '{name}' errored, exiting", exc_info=err)
                raise

        lifecycle = await self._assembler.build(Lifecycle)

        try:
            for hook in lifecycle.list():
                await asyncio.wait_for(self._exit_stack.enter_async_context(hook), timeout=15)
        except Exception as err:
            if isinstance(err, TimeoutError):
                msg = "lifecycle startup task timed out after 15s, exiting"
            else:
                msg = "lifecycle startup task errored, exiting"
            LOG.error(msg, exc_info=err)
            await self._shutdown()
            return

        supervisor = await self._assembler.build(Supervisor)

        LOG.info("startup complete")
        self._state = _EnginState.RUNNING
        self._start_complete_event.set()

        async with create_task_group() as tg:
            if self._STOP_ON_SINGAL:
                tg.start_soon(_stop_engin_on_signal, self._stop_requested_event)

            try:
                async with supervisor:
                    await self._stop_requested_event.wait()

                # shutdown after stopping supervised tasks
                await self._shutdown()
            except BaseException:
                await self._shutdown()

            tg.cancel_scope.cancel()

    async def start(self) -> None:
        """
        Starts the engin in the background. This method will wait until the engin is fully
        started to return so it is safe to use immediately after.
        """
        self._async_context_run_task = asyncio.create_task(self.run())
        wait_tasks = [
            asyncio.create_task(self._start_complete_event.wait()),
            asyncio.create_task(self._stop_complete_event.wait()),
        ]
        await asyncio.wait(
            [
                self._async_context_run_task,  # if a provider errors this will return first
                *wait_tasks,
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in wait_tasks:
            task.cancel()

        # raise the exception from the startup during run
        if self._async_context_run_task.done():
            startup_exception = self._async_context_run_task.exception()
            if startup_exception is not None:
                raise startup_exception

    async def stop(self) -> None:
        """
        Stop the engin.

        This method will wait for the shutdown lifecycle to complete before returning.
        Note this method can be safely called at any point, even before the engin is
        started.
        """
        self._stop_requested_event.set()
        if self._state == _EnginState.RUNNING:
            await self._stop_complete_event.wait()

    def graph(self) -> list[Node]:
        """
        Creates a graph representation of the engin's dependencies which can be used for
        introspection or visualisations.

        Returns: a list of Node objects.
        """
        grapher = DependencyGrapher({**self._providers, **self._multiproviders})
        return grapher.resolve(self._invocations)

    def is_running(self) -> bool:
        return self._state == _EnginState.RUNNING

    def is_stopped(self) -> bool:
        return self._state == _EnginState.SHUTDOWN

    async def _shutdown(self) -> None:
        if self._state == _EnginState.RUNNING:
            LOG.info("stopping engin")
            await self._exit_stack.aclose()
            self._stop_complete_event.set()
            LOG.info("shutdown complete")
            self._state = _EnginState.SHUTDOWN


async def _stop_engin_on_signal(stop_requested_event: Event) -> None:
    """
    A task that waits for a stop signal (SIGINT/SIGTERM) and notifies the given event.

    On unix-like systems we can use asyncio's `loop.add_signal_handler` method but this
    does not work on Windows as `signal.set_wakeup_fd` is not supported.

    Therefore on Windows we fallback to using `signal.signal` directly.
    """
    if not _OS_IS_WINDOWS:
        with open_signal_receiver(signal.SIGINT, signal.SIGTERM) as received_signals:
            async for signum in received_signals:
                LOG.debug(f"received signal: {signum.name}")
                stop_requested_event.set()
                break
    else:

        def ctrlc_handler(sig: int, frame: FrameType | None) -> None:
            LOG.debug(f"received signal: {signal.Signals(sig).name}")
            if stop_requested_event.is_set():
                raise KeyboardInterrupt("Forced keyboard interrupt")
            else:
                stop_requested_event.set()

        previous_signal_handler_sigint = signal.signal(signal.SIGINT, ctrlc_handler)

        # technically not needed due to the _OS_IS_WINDOWS checks but keeps mypy happy
        if hasattr(signal, "SIGBREAK"):
            previous_signal_handler_sigbreak = signal.signal(signal.SIGBREAK, ctrlc_handler)

        try:
            await stop_requested_event.wait()
        finally:
            # restore orginal signal handlers
            signal.signal(signal.SIGINT, previous_signal_handler_sigint)
            if hasattr(signal, "SIGBREAK"):
                signal.signal(signal.SIGBREAK, previous_signal_handler_sigbreak)
