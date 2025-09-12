import asyncio
from panoramisk import utils
from panoramisk.exceptions import AGIException


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

def generate_payload(path: str, args: list = None, kwargs: dict = None) -> bytes:
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


def test_parse_agi_valid_result():
    res = try_parse_agi_result('200 result=0')
    assert res == {'msg': '', 'result': ('0', ''), 'status_code': 200}

    res = try_parse_agi_result('200 result=1')
    assert res == {'msg': '', 'result': ('1', ''), 'status_code': 200}

    res = try_parse_agi_result('200 result=1234')
    assert res == {'msg': '', 'result': ('1234', ''), 'status_code': 200}

    res = try_parse_agi_result('200 result= (timeout)')
    assert res == {'msg': '', 'result': ('', 'timeout'), 'status_code': 200}


def test_parse_agi_invalid_result():
    res = try_parse_agi_result('510 Invalid or unknown command')
    assert res == {'msg': '510 Invalid or unknown command',
                   'error': 'AGIInvalidCommand',
                   'status_code': 510}

    res = try_parse_agi_result('520 Use this')
    assert res == {'msg': '520 Use this',
                   'error': 'AGIUsageError',
                   'status_code': 520}


def try_parse_agi_result(result):
    try:
        res = utils.parse_agi_result(result)
    except AGIException as err:
        res = err.items
        res['error'] = err.__class__.__name__
        res['msg'] = err.args[0]

    return res
