import inspect
import threading
import traceback
from typing import Callable

import log
from mytype import Second


class Job:

    def __init__(self, name: str, task: Callable[[int], None] | Callable[[], None]) -> None:
        self.done: threading.Event                                   = threading.Event()
        self.name: str                                               = name
        self.task: Callable[[int | None], None] | Callable[[], None] = task


class Queue:

    def __init__(self, queue_id: int | None = None) -> None:
        self.tag     : str                      = __class__.__name__
        self.queue_id: int | None               = queue_id
        self.turn_off: bool                     = True
        self.cond    : threading.Condition      = threading.Condition()
        self.worker  : threading.Thread | None  = None
        self.queue   : list[Job]                = []

    def start(self) -> None:
        if not self.turn_off:
            log.warn(self.tag, 'start() already started')
            return
        self.turn_off = False
        self.worker = threading.Thread(target=self.loop)
        self.worker.start()
        self.run_sync(Job('TaskQueue', lambda: log.debug(self.tag, 'start()')))

    def stop(self) -> None:
        if self.turn_off:
            log.warn(self.tag, 'stop() already stopped')
            return
        log.debug(self.tag, 'stop() shutting down')
        self.turn_off = True
        with self.cond:
            self.cond.notify_all()
        self.worker.join()
        self.worker = None
        log.debug(self.tag, 'stop() done')

    def queue_size(self, lock: bool) -> int:
        if lock:
            with self.cond:
                return len(self.queue)
        else:
            return len(self.queue)

    def loop(self) -> None:
        while True:
            # Get task
            job: Job | None = None
            with self.cond:
                # Stop loop if turn off and queue is empty
                if 0 == len(self.queue) and self.turn_off:
                    break
                # Wait for task
                while 0 == len(self.queue) and not self.turn_off:
                    try:
                        self.cond.wait(0.01)  # 10ms
                    except KeyboardInterrupt:
                        pass
                if len(self.queue) > 0:
                    job = self.queue.pop(0)
            # Execute task
            if job is not None:
                try:
                    sig = inspect.signature(job.task)
                    params = sig.parameters
                    if len(params) == 0:
                        job.task()
                    else:
                        job.task(self.queue_id)
                except Exception as e:
                    stack: str = traceback.format_exc()
                    text: str = str(e)
                    lines: list[str] = [f'Exception in task {job.name}: {text}']
                    lines.extend(stack.split('\n'))
                    log.error(self.tag, lines)
                job.done.set()

    def run_sync(self, job: Job) -> bool:
        if self.turn_off:
            log.warn(self.tag, 'run_sync() queue is turned off')
            return False
        with self.cond:
            self.queue.append(job)
            self.cond.notify_all()
        wait_time: Second = Second(0)
        while not job.done.is_set():
            try:
                job.done.wait(10)  # 10 seconds
                if not job.done.is_set():
                    wait_time += Second(10)
                    log.warn(self.tag, f'run_sync() waiting for task \'{job.name}\' for {wait_time} seconds')
            except KeyboardInterrupt:
                log.warn(self.tag, f'run_sync() interrupted by SIGINT during task \'{job.name}\', will continue waiting')
        return True

    def run_async(self, job: Job) -> bool:
        if self.turn_off:
            log.warn(self.tag, 'run_async() queue is turned off')
            return False
        with self.cond:
            self.queue.append(job)
            self.cond.notify_all()
        return True


class Pool(object):

    def __init__(self, workers: int) -> None:
        self.TAG: str = __class__.__name__
        self.turn_off: bool = True
        self.workers : list[Queue] = [Queue(_) for _ in range(workers)]

    def start(self) -> None:
        if not self.turn_off:
            log.warn(self.TAG, 'start() already started')
            return
        self.turn_off = False
        for worker in self.workers:
            worker.start()
        log.info(self.TAG, 'start()')

    def stop(self) -> None:
        if self.turn_off:
            log.warn(self.TAG, 'stop() already stopped')
            return
        log.info(self.TAG, 'stop() shutting down')
        self.turn_off = True
        for worker in self.workers:
            worker.stop()
        log.info(self.TAG, 'stop() done')

    def run_sync(self, job: Job, queue_id: int | None = None) -> bool:
        if self.turn_off:
            log.warn(self.TAG, 'run_sync() queue is turned off')
            return False
        queue_id = self.select_queued_id() if queue_id is None else queue_id
        return self.workers[queue_id].run_sync(job)

    def run_async(self, job: Job, queue_id: int | None = None) -> bool:
        if self.turn_off:
            log.warn(self.TAG, 'run_async() queue is turned off')
            return False
        queue_id = self.select_queued_id() if queue_id is None else queue_id
        return self.workers[queue_id].run_async(job)

    def select_queued_id(self) -> int:
        min_queued_size: int = -1
        qid: int = -1
        for i, worker in enumerate(self.workers):
            size: int = worker.queue_size(False)
            if min_queued_size < 0 or size < min_queued_size:
                min_queued_size = size
                qid = i
        return qid

    def pool_size(self) -> int:
        return len(self.workers)

    def queue_size(self, lock: bool) -> int:
        total: int = 0
        for worker in self.workers:
            total += worker.queue_size(lock)
        return total
