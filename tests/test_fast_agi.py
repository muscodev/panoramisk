import asyncio
import pytest
from panoramisk.exceptions import AGIAppError
from panoramisk.fast_agi import Application

FAST_AGI_PAYLOAD = b'''agi_network: yes
agi_network_script: call_waiting
agi_request: agi://127.0.0.1:4574/call_waiting
agi_channel: SIP/xxxxxx-00000000
agi_language: en_US
agi_type: SIP
agi_uniqueid: 1437920906.0
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
agi_arg_1: answered

'''

FAST_AGI_ERROR_PAYLOAD = b'''agi_network: yes
agi_network_script: invalid
agi_request: agi://127.0.0.1:4574/invalid
agi_channel: SIP/xxxxxx-00000000
agi_language: en_US
agi_type: SIP
agi_uniqueid: 1437920906.0
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
agi_arg_1: answered

'''


async def call_waiting(request):
    r = await request.send_command('ANSWER')
    v = {'msg': '', 'result': ('0', ''),
         'status_code': 200}
    assert r == v


async def invalid(request):
    with pytest.raises(AGIAppError) as excinfo:
        await request.send_command('EXEC Dial something')
    assert excinfo.result == {'msg': '', 'status_code': 200, 'result': ('-1', '')}


async def fake_asterisk_client(unused_tcp_port, err=False):
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', unused_tcp_port)
    # send headers
    if err:
        writer.write(FAST_AGI_ERROR_PAYLOAD)
    else:
        writer.write(FAST_AGI_PAYLOAD)
    # read it back
    msg = await reader.readline()
    if msg == b'ANSWER\n':
        writer.write(b'100 Trying...\n')
        writer.write(b'200 result=0\n')
    elif msg == b'EXEC Dial something\n':
        writer.write(b'200 result=-1\n')
    writer.close()
    return msg


@pytest.mark.asyncio
async def test_fast_agi_application(unused_tcp_port):
    event_loop = asyncio.get_event_loop()
    fa_app = Application(loop=event_loop)
    fa_app.add_route('call_waiting', call_waiting)

    server = await asyncio.start_server(fa_app.handler, '127.0.0.1',
                                        unused_tcp_port)

    msg_back = await fake_asterisk_client(unused_tcp_port)
    assert msg_back == b'ANSWER\n'

    server.close()
    await server.wait_closed()
    await asyncio.sleep(1)  # Wait the end of endpoint


@pytest.mark.asyncio
async def test_fast_agi_application_error( unused_tcp_port):
    event_loop = asyncio.get_event_loop()
    fa_app = Application(loop=event_loop, raise_on_error=True)
    fa_app.add_route('invalid', invalid)

    server = await asyncio.start_server(fa_app.handler, '127.0.0.1',
                                        unused_tcp_port)

    await fake_asterisk_client(unused_tcp_port, err=True)

    server.close()
    await server.wait_closed()
    await asyncio.sleep(1)  # Wait the end of endpoint
