import threading
import time
import unittest

from src.key_pool import NvidiaKeyPool


class KeyPoolTests(unittest.TestCase):
    def test_initial_work_rotates_across_available_keys(self):
        pool = NvidiaKeyPool(("one", "two", "three"), 1, 0.01)
        leases = [pool.acquire(0.1) for _ in range(3)]
        self.assertEqual([lease.slot for lease in leases], [0, 1, 2])
        for lease in leases:
            pool.release(lease)

    def test_reuses_first_finished_slot(self):
        pool = NvidiaKeyPool(("one", "two"), 1, 0.01)
        first = pool.acquire(0.1)
        second = pool.acquire(0.1)
        pool.release(second)
        third = pool.acquire(0.1)
        self.assertEqual(third.slot, second.slot)
        pool.release(first)
        pool.release(third)

    def test_cooldown_moves_work_to_another_key(self):
        pool = NvidiaKeyPool(("one", "two"), 1, 0.05)
        first = pool.acquire(0.1)
        pool.release(first, retryable_failure=True)
        second = pool.acquire(0.1)
        self.assertNotEqual(first.slot, second.slot)
        pool.release(second)

    def test_per_key_limit_blocks_until_release(self):
        pool = NvidiaKeyPool(("only",), 1, 0.01)
        lease = pool.acquire(0.1)
        result = []
        thread = threading.Thread(target=lambda: result.append(pool.acquire(0.5)))
        thread.start()
        time.sleep(0.02)
        self.assertEqual(result, [])
        pool.release(lease)
        thread.join(0.5)
        self.assertEqual(len(result), 1)
        pool.release(result[0])


if __name__ == "__main__":
    unittest.main()
