import threading
import time
import unittest

from components import rpc
from components.mytype import ChainID


def start_queue_only(connection: rpc.Connection) -> None:
    with connection.condition:
        connection.turn_off = False
        connection.worker = threading.Thread(target=connection.work_loop)
        connection.worker.start()


class TestRpcConnectionThreadSafety(unittest.TestCase):

    def test_run_sync_returns_error_when_stopped(self):
        connection = rpc.Connection(ChainID.SEPOLIA, 'http://localhost')

        result = connection.run_sync(lambda: 1, 'test()', ())

        self.assertIsInstance(result, rpc.Error)
        self.assertEqual(rpc.ErrorCode.RPC_NOT_STARTED, result.code)

    def test_stop_drains_accepted_sync_task(self):
        connection = rpc.Connection(ChainID.SEPOLIA, 'http://localhost')
        start_queue_only(connection)
        action_started = threading.Event()
        action_can_finish = threading.Event()
        result = []

        def action():
            action_started.set()
            action_can_finish.wait(1)
            return 42

        worker = threading.Thread(target=lambda: result.append(connection.run_sync(action, 'test()', ())))
        worker.start()
        self.assertTrue(action_started.wait(1))

        stopper = threading.Thread(target=connection.stop)
        stopper.start()
        time.sleep(0.05)
        action_can_finish.set()

        worker.join(1)
        stopper.join(1)
        self.assertFalse(worker.is_alive())
        self.assertFalse(stopper.is_alive())
        self.assertEqual([42], result)
        self.assertFalse(connection.started())
        self.assertIsNone(connection.worker)

    def test_worker_callback_can_call_run_sync(self):
        connection = rpc.Connection(ChainID.SEPOLIA, 'http://localhost')
        start_queue_only(connection)
        done = threading.Event()
        result = []

        def callback(_):
            result.append(connection.run_sync(lambda: 'nested', 'nested()', ()))
            done.set()

        try:
            self.assertIsNone(connection.run_async(lambda: 'outer', 'outer()', (), callback))
            self.assertTrue(done.wait(1))
            self.assertEqual(['nested'], result)
        finally:
            connection.stop()

    def test_worker_cannot_wait_for_its_own_restart(self):
        connection = rpc.Connection(ChainID.SEPOLIA, 'http://localhost')
        start_queue_only(connection)
        done = threading.Event()
        result = []

        def callback(_):
            connection.stop()
            result.append(connection.start())
            done.set()

        self.assertIsNone(connection.run_async(lambda: 'outer', 'outer()', (), callback))
        self.assertTrue(done.wait(1))
        self.assertEqual([False], result)
        for _ in range(100):
            if connection.worker is None:
                break
            time.sleep(0.01)
        self.assertIsNone(connection.worker)

    def test_start_returns_false_while_stop_pending(self):
        connection = rpc.Connection(ChainID.SEPOLIA, 'http://localhost')
        start_queue_only(connection)
        action_started = threading.Event()
        action_can_finish = threading.Event()
        result = []

        def action():
            action_started.set()
            action_can_finish.wait(1)
            return 1

        worker = threading.Thread(target=lambda: connection.run_sync(action, 'test()', ()))
        worker.start()
        self.assertTrue(action_started.wait(1))

        stopper = threading.Thread(target=connection.stop)
        stopper.start()
        for _ in range(100):
            with connection.condition:
                if connection.turn_off and connection.worker is not None:
                    break
            time.sleep(0.01)

        starter = threading.Thread(target=lambda: result.append(connection.start()))
        starter.start()
        starter.join(0.2)
        self.assertFalse(starter.is_alive())
        self.assertEqual([False], result)

        action_can_finish.set()
        worker.join(1)
        stopper.join(1)
        self.assertFalse(stopper.is_alive())
        self.assertIsNone(connection.worker)


if __name__ == '__main__':
    unittest.main()
