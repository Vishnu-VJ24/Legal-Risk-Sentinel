import unittest

from src.normalization import normalize_pages
from src.sections import (
    canon_id_from_heading,
    extract_sections_from_text,
    map_sections_to_pages,
    recover_subclauses_deterministically,
)


class SectionExtractionTests(unittest.TestCase):
    def test_rejects_section_cross_reference_with_comma(self):
        node_id, title, level, raw = canon_id_from_heading(
            "Section 2.1, or termination, pursuant to Section 2.2"
        )

        self.assertIsNone(node_id)
        self.assertIsNone(title)
        self.assertEqual(level, -1)
        self.assertEqual(raw, "")

    def test_accepts_explicit_section_heading(self):
        node_id, title, level, raw = canon_id_from_heading("Section 2.1 Term of Agreement")

        self.assertEqual(node_id, "2.1")
        self.assertEqual(title, "Term of Agreement")
        self.assertEqual(level, 2)
        self.assertEqual(raw, "Section 2.1 Term of Agreement")

    def test_duplicate_sample_keeps_one_section_id(self):
        text = "\n".join(
            [
                "2.1 Term of Agreement Except as otherwise provided herein, the term of this Agreement is three (3) years from the Execution Date",
                "(\"Cooperation Period\"). The Parties may negotiate for an extension.",
                "Section 2.1, or termination, pursuant to Section 2.2; provided, however, that Sections 2.2, 2.3, 3.1 and 3.9 shall survive.",
                "2.2 Early Termination This Agreement may be terminated as follows:",
                "Either party may terminate under the stated conditions.",
            ]
        )

        sections = extract_sections_from_text(text)
        section_ids = [section.node_id for section in sections]

        self.assertEqual(section_ids.count("2.1"), 1)
        self.assertEqual(section_ids.count("2.2"), 1)
        self.assertIn("Section 2.1, or termination", sections[0].text)

    def test_recovers_lettered_subclauses_without_losing_intro(self):
        text = "1. Services\nIntroductory promise.\n(a) First duty.\n(b) Second duty.\n"
        sections = recover_subclauses_deterministically(extract_sections_from_text(text))
        active = [section for section in sections if section.is_analysis_unit]
        self.assertEqual([section.node_id for section in active], ["1__intro", "1(a)", "1(b)"])
        self.assertEqual("".join(section.text for section in active).replace("\n", ""), text.replace("\n", ""))

    def test_normalized_page_offsets_remain_correct(self):
        pages = normalize_pages([
            {"page_num": 1, "text": "1. One\nbody\n"},
            {"page_num": 2, "text": "2. Two\nbody\n"},
        ])
        text = "".join(page["text"] for page in pages)
        offsets = []
        cursor = 0
        for page in pages:
            offsets.append({"page_num": page["page_num"], "start": cursor, "end": cursor + len(page["text"])})
            cursor += len(page["text"])
        sections = map_sections_to_pages(extract_sections_from_text(text), offsets)
        self.assertEqual([section.page_start for section in sections], [1, 2])


if __name__ == "__main__":
    unittest.main()
