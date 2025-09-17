from __future__ import unicode_literals
import asyncio
from unittest import mock

from . import manager
from . import utils


MagicMock = mock.MagicMock
patch = mock.patch
call = mock.call


class AMIProtocol(manager.AMIProtocol):

    debug_count = [0]

    def connection_made(self, transport):
        super(AMIProtocol, self).connection_made(transport)
        self.transport = MagicMock()

    def send(self, data, as_list=False):
        utils.IdGenerator.reset(uid='transaction_uid')
        future = super(AMIProtocol, self).send(data, as_list=as_list)
        if getattr(self.factory, 'stream', None) is not None:
            with open(self.factory.stream, 'rb') as fd:
                for resp in fd.read().split(b'\n\n'):
                    self.data_received(resp + b'\n\n')
                    if future.done():
                        break
            if not future.done():  # pragma: no cover
                print(self.responses)
                raise AssertionError("Future's result was never set")
        return future


class Manager(manager.Manager):

    fixtures_dir = None
    defaults = manager.Manager.defaults.copy()

    def __init__(self, **config):
        self.defaults.update(
            protocol_factory=AMIProtocol,
            stream=None)
        super(Manager, self).__init__(**config)

        self.stream = self.config.get('stream')

        if self.loop is None:
            self.loop = asyncio.get_event_loop()

        protocol = AMIProtocol()
        protocol.factory = manager
        protocol.connection_made(mock.MagicMock())
        future = self.loop.create_future()
        future.set_result((mock.MagicMock(), protocol))
        self.protocol = protocol
        self.connection_made(future)

        utils.IdGenerator.reset(uid='transaction_uid')
        utils.EOL = '\n'


class FakeAsteriskClient:
    def __init__(self, port: int , host: str = '127.0.0.1'):
        self.host = host
        self.port = port

        self.read_handler = None
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def write(self, payload: bytes):
        self.writer.write(payload)
        await self.writer.drain()

    def handler(self, handler: callable):
        self.read_handler = handler


    async def read(self) -> bytes:
        msg = await self.reader.readline()
        if asyncio.iscoroutinefunction(self.read_handler):
            await self.read_handler(self, msg)
        else:
            self.read_handler(self, msg)
        return msg

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

def generate_agi_payload(path: str, args: list = None, kwargs: dict = None) -> bytes:
    args = args or []
    kwargs = kwargs or {}

    # Format kwargs safely (handle special characters if needed)
    args_formatted = '&'.join(f"{k}={v}" for k, v in kwargs.items())

    # Format args
    arg_content = '\n'.join(f'agi_arg_{i + 1}: {args[i]}' for i in range(len(args)))

    payload = f"""agi_network: yes
agi_network_script: {path}
agi_request: agi://127.0.0.1:4574/{path}?{args_formatted}
agi_channel: SIP/xxxxxx-00000000
agi_language: en_US
agi_type: SIP
agi_version: asterisk
agi_callerid: 201
agi_calleridname: user 201
agi_callingpres: 0
agi_callingani2: 0
agi_callington: 0
agi_callingtns: 0
agi_dnid: 9011
agi_rdnis: unknown
agi_context: default
agi_extension: 9011
agi_priority: 2
agi_enhanced: 0.0
agi_accountcode: default
agi_threadid: -1260881040
{arg_content}
"""

    return payload.encode('utf-8')
