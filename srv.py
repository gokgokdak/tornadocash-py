import argparse
import copy
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from components.mytype import MBytes, Second
from www.ws import Server

import config
from components import log

server: Server = Server()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    server.init()
    server.start()
    try:
        yield
    finally:
        server.stop()
        server.un_init()


app: FastAPI = FastAPI(lifespan=lifespan)
server.register(app)


@app.get('/health')
def health() -> dict[str, bool]:
    return {'ok': True}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Start the TornadoCash WebSocket service.')
    parser.add_argument('--host', default='127.0.0.1', help='Bind host. Defaults to 127.0.0.1.')
    parser.add_argument('--port', default=8000, type=int, help='Bind port. Defaults to 8000.')
    return parser.parse_args()


def uvicorn_log_config() -> dict:
    log_config = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)
    for formatter in ('default', 'access'):
        if formatter in log_config['formatters']:
            log_config['formatters'][formatter]['use_colors'] = False
    return log_config


def main() -> None:
    args = parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_config=uvicorn_log_config())


if __name__ == '__main__':
    log.init(config.LOG_DIR)
    log.set_level(log.Level.INFO)
    log.set_console_enable(True)
    main()
    log.un_init()
