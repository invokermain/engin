import asyncio
import logging
import os
import signal
from asyncio import Event, Task
from collections import defaultdict
from contextlib import AsyncExitStack
from enum import Enum
from itertools import chain
from types import FrameType
from typing import ClassVar

from anyio import CancelScope, create_task_group, get_cancelled_exc_class

from engin._assembler import AssembledDependency, Assembler
from engin._dependency import Invoke, Provide, Supply
from engin._graph import DependencyGrapher, Node
from engin._lifecycle import Lifecycle
from engin._option import Option
from engin._shutdown import ShutdownSwitch
from engin._supervisor import Supervisor
from engin._type_utils import TypeId
from engin.exceptions import EnginError

_OS_IS_WINDOWS = os.name == "nt"
LOG = logging.getLogger("engin")


class _EnginState(Enum):
    IDLE = 0
    """
    Not yet started.
    """

    STARTED = 1
    """
    Engin started via .start() call
    """

    RUNNING = 2
    """
    Engin running via .run() call
    """

    STOPPING = 3
    """
    Engin stopped via .stop() call
    """

    SHUTDOWN = 4
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
    4. The Engin waits for a stop signal, i.e. SIGINT or SIGTERM, or for something to
       set the ShutdownSwitch event.
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

    def __init__(self, *options: Option) -> None:
        """
        Initialise the class with the provided options.

        Examples:
            >>> engin = Engin(Provide(construct_a), Invoke(do_b), Supply(C()), MyBlock())

        Args:
            *options: an instance of Provide, Supply, Invoke, Entrypoint or a Block.
        """
        self._state = _EnginState.IDLE
        self._stop_requested_event = ShutdownSwitch()
        self._stop_complete_event = Event()
        self._exit_stack: AsyncExitStack = AsyncExitStack()
        self._shutdown_task: Task | None = None
        self._run_task: Task | None = None
        self._assembler = Assembler([])

        self._providers: dict[TypeId, Provide] = {
            TypeId.from_type(Assembler): Supply(self._assembler),
            TypeId.from_type(ShutdownSwitch): Supply(self._stop_requested_event),
        }
        self._multiproviders: dict[TypeId, list[Provide]] = defaultdict(list)
        self._invocations: list[Invoke] = []

        # populates the above
        for option in chain(self._LIB_OPTIONS, options):
            option.apply(self)

        multi_providers = [p for multi in self._multiproviders.values() for p in multi]

        for provider in chain(self._providers.values(), multi_providers):
            self._assembler.add(provider)

    @property
    def assembler(self) -> Assembler:
        return self._assembler

    async def run(self) -> None:
        """
        Run the engin.

        The engin will run until it is stopped via an external signal (i.e. SIGTERM or
        SIGINT), the `stop` method is called on the engin, or a lifecycle task errors.
        """
        await self.start()

        # engin failed to start, so exit early
        if self._state != _EnginState.STARTED:
            return

        self._state = _EnginState.RUNNING

        async with create_task_group() as tg:
            tg.start_soon(_stop_engin_on_signal, self._stop_requested_event)
            try:
                await self._stop_requested_event.wait()
                await self._shutdown()
            except get_cancelled_exc_class():
                with CancelScope(shield=True):
                    await self._shutdown()

    async def start(self) -> None:
        """
        Start the engin.

        This is an alternative to calling `run`. This method waits for the startup
        lifecycle to complete and then returns. The caller is then responsible for
        calling `stop`.
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
                return

        lifecycle = await self._assembler.build(Lifecycle)
        supervisor = await self._assembler.build(Supervisor)

        if not supervisor.empty:
            lifecycle.append(supervisor)

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

        LOG.info("startup complete")
        self._state = _EnginState.STARTED

    async def stop(self) -> None:
        """
        Stop the engin.

        This method will wait for the shutdown lifecycle to complete before returning.
        Note this method can be safely called at any point, even before the engin is
        started.
        """
        # If the Engin was ran via `start()` perform shutdown directly
        if self._state == _EnginState.STARTED:
            await self._shutdown()
        # If the Engin was ran via `run()` notify via event
        elif self._state == _EnginState.RUNNING:
            self._stop_requested_event.set()
            await self._stop_complete_event.wait()

    def graph(self) -> list[Node]:
        grapher = DependencyGrapher({**self._providers, **self._multiproviders})
        return grapher.resolve(self._invocations)

    async def _shutdown(self) -> None:
        LOG.info("stopping engin")
        await self._exit_stack.aclose()
        self._stop_complete_event.set()
        LOG.info("shutdown complete")
        self._state = _EnginState.SHUTDOWN


async def _stop_engin_on_signal(stop_requested_event: Event) -> None:
    """
    A task that waits for a stop signal (SIGINT/SIGTERM) and notifies the given event.
    """
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
