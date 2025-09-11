from typing import Any
from unittest.mock import Mock

import pytest

from engin import Engin, Provide, Supply
from engin.extensions.asgi import ASGIEngin, ASGIType, engin_to_lifespan


class MockASGIApp:
    def __init__(self, state: Any = None) -> None:
        self.state = state or Mock()

    async def __call__(self, scope, receive, send):
        pass


@pytest.fixture
def mock_asgi_app():
    return MockASGIApp()


async def test_init_requires_asgi_type_provider():
    with pytest.raises(
        LookupError, match="A provider for `ASGIType` was expected, none found"
    ):
        ASGIEngin()


async def test_init_with_asgi_type_provider():
    def asgi_factory() -> ASGIType:
        return MockASGIApp()

    engin = ASGIEngin(Provide(asgi_factory))
    assert engin is not None


async def test_lifespan_startup_success():
    def asgi_factory() -> ASGIType:
        return MockASGIApp()

    engin = ASGIEngin(Provide(asgi_factory))

    startup_message = {"type": "lifespan.startup"}
    receive_calls = [startup_message]
    receive_call_count = 0

    async def mock_receive():
        nonlocal receive_call_count
        if receive_call_count < len(receive_calls):
            msg = receive_calls[receive_call_count]
            receive_call_count += 1
            return msg
        return {"type": "lifespan.disconnect"}

    sent_messages = []

    async def mock_send(message):
        sent_messages.append(message)

    scope = {"type": "lifespan"}

    await engin(scope, mock_receive, mock_send)

    # Should not send any failure messages
    assert not any(msg.get("type") == "lifespan.startup.failed" for msg in sent_messages)


async def test_lifespan_startup_failure():
    """Test lifespan startup failure handling."""

    def failing_startup() -> int:
        raise Exception("Startup failed")

    def asgi_factory() -> ASGIType:
        return MockASGIApp()

    engin = ASGIEngin(Provide(asgi_factory), Provide(failing_startup))
    # Mock the _startup method to raise an exception
    original_startup = engin._startup

    async def failing_startup_method():
        await original_startup()
        raise Exception("Startup failed")

    engin._startup = failing_startup_method

    startup_message = {"type": "lifespan.startup"}
    receive_calls = [startup_message]
    receive_call_count = 0

    async def mock_receive():
        nonlocal receive_call_count
        if receive_call_count < len(receive_calls):
            msg = receive_calls[receive_call_count]
            receive_call_count += 1
            return msg
        return {"type": "lifespan.disconnect"}

    sent_messages = []

    async def mock_send(message):
        sent_messages.append(message)

    scope = {"type": "lifespan"}

    with pytest.raises(Exception, match="Startup failed"):
        await engin(scope, mock_receive, mock_send)

    # Should send startup failed message
    failure_msgs = [
        msg for msg in sent_messages if msg.get("type") == "lifespan.startup.failed"
    ]
    assert len(failure_msgs) == 1
    assert "message" in failure_msgs[0]
    assert "Startup failed" in failure_msgs[0]["message"]


async def test_lifespan_shutdown():
    """Test lifespan shutdown handling."""

    def asgi_factory() -> ASGIType:
        return MockASGIApp()

    engin = ASGIEngin(Provide(asgi_factory))
    await engin._startup()

    shutdown_message = {"type": "lifespan.shutdown"}
    receive_calls = [shutdown_message]
    receive_call_count = 0

    async def mock_receive():
        nonlocal receive_call_count
        if receive_call_count < len(receive_calls):
            msg = receive_calls[receive_call_count]
            receive_call_count += 1
            return msg
        return {"type": "lifespan.disconnect"}

    sent_messages = []

    async def mock_send(message):
        sent_messages.append(message)

    scope = {"type": "lifespan"}

    # Mock the stop method to verify it was called
    stop_called = False
    original_stop = engin.stop

    async def mock_stop():
        nonlocal stop_called
        stop_called = True
        await original_stop()

    engin.stop = mock_stop

    await engin(scope, mock_receive, mock_send)

    assert stop_called


async def test_non_lifespan_request():
    """Test handling of non-lifespan requests."""
    app_called = False

    class TestASGIApp:
        async def __call__(self, scope, receive, send):
            nonlocal app_called
            app_called = True

    def asgi_factory() -> ASGIType:
        return TestASGIApp()

    engin = ASGIEngin(Provide(asgi_factory))

    # Initialize the app first
    await engin._startup()

    async def mock_receive():
        return {"type": "http.request"}

    async def mock_send(message):
        pass

    scope = {"type": "http"}

    await engin(scope, mock_receive, mock_send)

    assert app_called


async def test_graph_method():
    """Test the graph method returns dependency nodes."""

    def asgi_factory() -> ASGIType:
        return MockASGIApp()

    engin = ASGIEngin(Provide(asgi_factory))

    nodes = engin.graph()
    assert isinstance(nodes, list)
    assert len(nodes) > 0


async def test_engin_to_lifespan_success(mock_asgi_app):
    """Test successful lifespan with engin_to_lifespan."""

    def some_service() -> str:
        return "service"

    engin = Engin(Provide(some_service))
    lifespan_func = engin_to_lifespan(engin)

    # Track start/stop calls
    start_called = False
    stop_called = False

    original_start = engin.start
    original_stop = engin.stop

    async def mock_start():
        nonlocal start_called
        start_called = True
        await original_start()

    async def mock_stop():
        nonlocal stop_called
        stop_called = True
        await original_stop()

    engin.start = mock_start
    engin.stop = mock_stop

    async with lifespan_func(mock_asgi_app):
        # Verify app was added to assembler
        assert hasattr(mock_asgi_app.state, "assembler")
        assert mock_asgi_app.state.assembler is engin.assembler
        assert start_called

    assert stop_called


async def test_engin_to_lifespan_with_existing_app_supply(mock_asgi_app):
    """Test lifespan when app is already supplied to engin."""

    def some_service() -> str:
        return "service"

    # Pre-supply the app
    engin = Engin(Provide(some_service), Supply(mock_asgi_app))
    lifespan_func = engin_to_lifespan(engin)

    async with lifespan_func(mock_asgi_app):
        # Should still work without errors
        assert hasattr(mock_asgi_app.state, "assembler")


async def test_engin_to_lifespan_handles_value_error_gracefully(mock_asgi_app):
    """Test that ValueError from adding duplicate supply is suppressed."""

    def some_service() -> str:
        return "service"

    engin = Engin(Provide(some_service))

    # Mock the add method to raise ValueError
    original_add = engin.assembler.add

    def mock_add(option):
        if isinstance(option, Supply):
            raise ValueError("Duplicate supply")
        return original_add(option)

    engin.assembler.add = mock_add

    lifespan_func = engin_to_lifespan(engin)

    # Should not raise ValueError
    async with lifespan_func(mock_asgi_app):
        assert hasattr(mock_asgi_app.state, "assembler")
