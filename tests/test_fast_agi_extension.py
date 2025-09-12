import asyncio
import pytest
from panoramisk.exceptions import AGIAppError
from panoramisk.fastagi_extension import FastAgi, Request
from .test_utils import FakeAsteriskClient, generate_payload
import logging

logging.basicConfig(level=logging.DEBUG)

@pytest.mark.asyncio
async def test_route_registration_and_arg_binding(unused_tcp_port):

    app = FastAgi()

    @app.route('check')
    async def check(request: Request, x: int='3'):
        if request.path == 'check' and isinstance(x, int) :
            await request.send_command('OK')

    async def client_handler(client: FakeAsteriskClient, message: bytes):
        assert message == b'OK\n'
        
    await app.start_server(port=unused_tcp_port)

    client = FakeAsteriskClient(unused_tcp_port)

    await client.connect()
    await client.write(generate_payload('check'))
    client.handler(client_handler)
    msg = await client.read()
    print(msg)
    await client.close()

    app.server.close()
    await app.server.wait_closed()
    await asyncio.sleep(1)  # Wait the end of endpoint
