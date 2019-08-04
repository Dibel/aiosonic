
import asyncio
from concurrent import futures
from datetime import datetime
from datetime import timedelta
import json
import random
from time import sleep
from urllib.request import urlopen
from urllib.error import URLError

from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from uvicorn.main import Server
from uvicorn.main import Config

from multiprocessing import Process

import aiosonic
from aiosonic.connectors import TCPConnector
from aiohttp import ClientSession
import requests

APP = Starlette(debug=True)


@APP.route('/')
async def homepage(_request):
    return HTMLResponse('foo')


async def start_dummy_server(loop, port):
    """Start dummy server."""
    host = '0.0.0.0'

    config = Config(APP, host=host, port=port, workers=2, log_level='warning')
    server = Server(config=config)

    await server.serve()


async def timeit_coro(func, *args, **kwargs):
    """To time stuffs."""
    repeat = kwargs.pop('repeat', 1000)
    before = datetime.now()
    for _ in range(repeat):
        await func(*args, **kwargs)
    after = datetime.now()
    return (after - before) / timedelta(milliseconds=1)


async def performance_aiohttp(url, concurrency):
    """Test aiohttp performance."""
    async with ClientSession() as session:
        print('aiohttp')
        return await timeit_coro(session.get, (url))


async def performance_aiosonic(url, concurrency):
    """Test aiohttp performance."""
    print('aiosonic')
    return await timeit_coro(
        aiosonic.get, url, connector=TCPConnector(pool_size=concurrency))


def timeit_requests(url, concurrency, repeat=1000):
    """Timeit requests."""
    print('requests')
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=concurrency,
        pool_maxsize=concurrency
    )
    session.mount('http://', adapter)
    with futures.ThreadPoolExecutor(concurrency) as executor:
        to_wait = []
        before = datetime.now()
        for _ in range(repeat):
            to_wait.append(executor.submit(session.get, url))
        for fut in to_wait:
            fut.result()
        after = datetime.now()
    return (after - before) / timedelta(milliseconds=1)


def do_tests(url):
    """Start benchmark."""
    print('doing testss...')
    concurrency = 25
    loop = asyncio.get_event_loop()

    # aiohttp
    res1 = loop.run_until_complete(performance_aiohttp(url, concurrency))

    # aiosonic
    res2 = loop.run_until_complete(performance_aiosonic(url, concurrency))

    # requests
    res3 = timeit_requests(url, concurrency)
    print(json.dumps({
        'aiohttp': '%.2f ms' % res1,
        'requests': '%.2f ms' % res3,
        'aiosonic': '%.2f ms' % res2,
    }, indent=True))


def start_server(port):
    """Start server."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_dummy_server(loop, port))


def main():
    """Start."""
    port = random.randint(1000, 9000)
    url = 'http://0.0.0.0:%d' % port
    process = Process(target=start_server, args=(port,))
    process.start()

    max_wait = datetime.now() + timedelta(seconds=5)
    while True:
        try:
            with urlopen(url) as response:
                print(response.read())
                break
        except URLError:
            sleep(1)
            if datetime.now() > max_wait:
                raise
    do_tests(url)
    process.terminate()


main()