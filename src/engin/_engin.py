import logging
from asyncio import Event
from collections.abc import Iterable
from itertools import chain
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


class Engin:
    _LIB_OPTIONS: ClassVar[list[Option]] = [Provide(Lifecycle)]

    def __init__(self, *options: Option) -> None:
        self._providers: dict[TypeId, Provide] = {TypeId.from_type(Engin): Provide(self._self)}
        self._invokables: list[Invoke] = []
        self._stop_event = Event()

        self._destruct_options(chain(self._LIB_OPTIONS, options))
        self._assembler = Assembler(self._providers.values())

    @property
    def assembler(self) -> Assembler:
        return self._assembler

    async def run(self) -> None:
        await self.start()

        # wait till stop signal recieved
        await self._stop_event.wait()

        await self.stop()

    async def start(self) -> None:
        LOG.info("starting engin")
        assembled_invocations: list[AssembledDependency] = [
            await self._assembler.assemble(invocation) for invocation in self._invokables
        ]
        for invocation in assembled_invocations:
            await invocation()

        lifecycle = await self._assembler.get(Lifecycle)
        await lifecycle.startup()
        self._stop_event = Event()
        LOG.info("startup complete")

    async def stop(self) -> None:
        self._stop_event.set()
        lifecycle = await self._assembler.get(Lifecycle)
        await lifecycle.shutdown()

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
