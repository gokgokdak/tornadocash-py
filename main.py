from time import sleep

from components import log, util
from components.core import TornadoManager
from components.executor import Job, Pool
from components.mytype import Second
import config


if __name__ == '__main__':
    log.init(config.LOG_DIR)
    log.set_level(log.Level.INFO)
    log.set_console_enable(True)
    manager = TornadoManager()
    pool = Pool(1)
    pool.start()
    pool.run_async(Job('test', lambda: manager.init(sync_only=False)))
    # while True:
    #     try:
    #         util.wait(Second(1))
    #     except KeyboardInterrupt:
    #         log.info('main', 'Ctrl+C')
    #         manager.un_init()
    #         break
    sleep(3)
    manager.un_init()
    pool.stop()
    log.un_init()
