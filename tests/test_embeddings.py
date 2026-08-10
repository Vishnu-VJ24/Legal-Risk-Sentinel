import unittest

from src.embeddings import build_embedding_batches


class EmbeddingBatchTests(unittest.TestCase):
    def test_packs_records_by_item_count(self):
        batches = build_embedding_batches(["a", "b", "c", "d", "e"], max_items=2, max_chars=100)
        self.assertEqual([[index for index, _ in batch] for batch in batches], [[0, 1], [2, 3], [4]])

    def test_splits_before_payload_budget_and_preserves_indexes(self):
        batches = build_embedding_batches(["a" * 7, "b" * 7, "c" * 7], max_items=64, max_chars=13)
        self.assertEqual([[index for index, _ in batch] for batch in batches], [[0], [1], [2]])

    def test_skips_blank_payloads_without_reindexing_later_records(self):
        batches = build_embedding_batches(["first", " ", "second"], max_items=64, max_chars=100)
        self.assertEqual([[index for index, _ in batch] for batch in batches], [[0, 2]])


if __name__ == "__main__":
    unittest.main()
