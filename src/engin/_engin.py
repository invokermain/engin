import logging
from asyncio import Event
from collections.abc import Iterable
from itertools import chain
from typing import ClassVar, TypeAlias

from engin._assembler import AssembledDependency, Assembler
from engin._dependency import Dependency, Invoke, Provide, Supply
from engin._lifecycle import Lifecycle
from engin._module import Module
from engin._type_utils import TypeId

LOG = logging.getLogger(__name__)

Option: TypeAlias = Invoke | Provide | Supply | Module
_Opt: TypeAlias = Invoke | Provide | Supply


class Engin:
    _LIB_OPTIONS: ClassVar[list[Option]] = [Provide(Lifecycle)]

    def __init__(self, *options: Option) -> None:
        self._providers: dict[TypeId, Provide] = {}
        self._invokables: list[Invoke] = []
        self._stop_event = Event()

        self._destruct_options(options)
        self._assembler = Assembler(self._providers.values())

    @property
    def assembler(self) -> Assembler:
        return self._assembler

    async def run(self):
        await self.start()

        # lifecycle startup

        # wait till stop signal recieved
        await self._stop_event.wait()

        # lifecycle shutdown

    async def start(self) -> None:
        LOG.info("starting ngyn")
        assembled_invocations: list[AssembledDependency] = [
            await self._assembler.assemble(invocation) for invocation in self._invokables
        ]
        for invocation in assembled_invocations:
            await invocation()

        lifecycle = await self._assembler.get(Lifecycle)
        await lifecycle.startup()
        self._stop_event = Event()

    async def stop(self) -> None:
        self._stop_event.set()

    def _destruct_options(self, options: Iterable[Option]):
        for opt in chain(self._LIB_OPTIONS, options):
            if isinstance(opt, Module):
                self._destruct_options(opt)
            if isinstance(opt, (Provide, Supply)):
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
            if overwrites.module_name:
                extra += f" [{overwrites.module_name}]"
        else:
            extra = ""
        if isinstance(opt, Provide):
            LOG.debug(f"PROVIDE {str(opt.return_type_id):<35} <- {opt.name}() {extra}")
        elif isinstance(opt, Supply):
            LOG.debug(f"SUPPLY  {str(opt.return_type_id):<35}{extra}")
        elif isinstance(opt, Invoke):
            LOG.debug(f"INVOKE {opt.name:<40}")
