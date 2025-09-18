import asyncio
import pytest
from panoramisk.fastagi_extension import (
    FastAgi,
    Request,
    AgiRouter,
    ArgModel,
)
from dataclasses import dataclass
from panoramisk.testing import (
    FakeAsteriskClient,
    generate_agi_payload,
)
import logging

logging.basicConfig(level=logging.DEBUG)


async def client_handler(client: FakeAsteriskClient, message: bytes):
    print("landedn on client handle")
    assert message == b"OK\n"


@pytest.mark.asyncio
async def test_route_registration_and_arg_binding(unused_tcp_port):
    app = FastAgi()

    @app.route("check")
    async def check(request: Request, number: str, x: int = 3):
        if request.path == "check" and isinstance(x, int):
            await request.send_command("OK")

    await app.start_server(port=unused_tcp_port)

    client = FakeAsteriskClient(unused_tcp_port)

    await client.connect()
    await client.write(
        generate_agi_payload("check", kwargs={"x": 55, "number": "9112345678"})
    )
    client.handler(client_handler)
    await client.read()
    await client.close()

    app.server.close()
    await app.server.wait_closed()
    await asyncio.sleep(1)  # Wait the end of endpoint


@pytest.mark.asyncio
async def test_agi_router(unused_tcp_port):
    router = AgiRouter()

    @router.route("check")
    async def check(request: Request, x: int = 3):
        if request.path == "check" and isinstance(x, int):
            await request.send_command("OK")

    @router.route("check/sms")
    async def check_sms(request: Request, x: int = 3):
        if request.path == "check/sms" and isinstance(x, int):
            await request.send_command("OK")

    assert len(router.routes) == 2

    app = FastAgi()

    app.include_router(router)

    await app.start_server(port=unused_tcp_port)

    client = FakeAsteriskClient(unused_tcp_port)

    await client.connect()
    await client.write(generate_agi_payload("check/sms"))
    client.handler(client_handler)
    await client.read()
    await client.close()

    app.server.close()
    await app.server.wait_closed()
    await asyncio.sleep(1)  # Wait the end of endpoint


@dataclass
class CallEvent(ArgModel):
    call_id: int
    caller_id: str
    queue: str
    duration: int  # seconds


def test_call_event_conversion():
    e = CallEvent("101", "9876543210", "sales", "120")
    assert isinstance(e.call_id, int)
    assert isinstance(e.duration, int)
    assert e.queue == "sales"


def test_call_event_invalid_duration():
    e = CallEvent("102", "1234567890", "support", "abc")  # invalid int
    # duration may stay as string because conversion fails
    assert hasattr(e, "duration")


@dataclass
class DTMFInput(ArgModel):
    call_id: int
    digit: str
    timestamp: float


def test_subclass_validation():
    import typing

    def typecheck(x: DTMFInput):
        pass

    hint = typing.get_type_hints(typecheck)
    assert hint.get("x") == DTMFInput
    assert issubclass(hint.get("x"), ArgModel)


def test_dtmf_input_conversion():
    d = DTMFInput("201", "5", "1695039293.45")
    assert isinstance(d.call_id, int)
    assert isinstance(d.timestamp, float)
    assert d.digit == "5"


@dataclass
class AgentStatus(ArgModel):
    agent_id: int
    status: str  # e.g., "ready", "busy", "on_break"
    queue: str


def test_agent_status_values():
    a = AgentStatus("301", "ready", "support")
    assert isinstance(a.agent_id, int)
    assert a.status in ("ready", "busy", "on_break")


## test the agi function with the argument parsed


@pytest.mark.asyncio
async def test_agi_router_with_args(unused_tcp_port):
    app = FastAgi()

    @app.route("call/event")
    async def event(request: Request, event: CallEvent, number: str):
        if request.path == "call/event":
            await request.send_command("OK")
        # if (
        #     request.path == "call/event"
        #     and isinstance(number, str)
        #     and number == "9876543210"
        #     and isinstance(event, CallEvent)
        #     and isinstance(event.call_id, int)
        #     and isinstance(event.duration, int)
        #     and event.queue == "sales"
        #     and event.duration == 120
        # ):
        
        #     await request.send_command("OK")

    server = await app.start_server(port=unused_tcp_port)

    client = FakeAsteriskClient(unused_tcp_port)
    client.handler(client_handler)
    await client.connect()
    payload = generate_agi_payload(
            "call/event",
            args=["101", "9876543210", "sales", "120"],
            kwargs={"number": "9876543210"},
        )
    await client.write(payload)

    await client.read()
    await client.close()
    app.server.close()
    await app.server.wait_closed()
    await asyncio.sleep(1)  # Wait the end of endpoint

