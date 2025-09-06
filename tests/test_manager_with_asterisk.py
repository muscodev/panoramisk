import asyncio
import subprocess

import pytest

from panoramisk import Manager

try:
    subprocess.check_call(
        ['docker-compose', 'version'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    compose_available = True
except Exception:
    compose_available = False

pytestmark = pytest.mark.skipif(
    not compose_available,
    reason='Compose is not available'
)


@pytest.mark.asyncio
async def test_reconnection_without_lost(asterisk):
    event_loop = asyncio.get_event_loop()    
    manager = Manager(loop=event_loop,
                      username='username',
                      secret='mysecret')
    asterisk.start()
    pid = asterisk.proc.pid

    await manager.connect()
    await manager.send_action({'Action': 'Ping'})

    asterisk.stop()

    manager.send_action({'Action': 'Ping'})
    f = manager.send_action({'Action': 'Status'})

    await asyncio.sleep(.1)
    assert manager.awaiting_actions
    asterisk.start()
    assert pid != asterisk.proc.pid
    assert manager.awaiting_actions
    await asyncio.sleep(.5)
    assert not manager.awaiting_actions
    messages = []
    async for message in f:
        messages.append(message)
        assert message.eventlist.lower() in ("start", "complete"), message
    assert len(messages)
