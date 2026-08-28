import unittest

from qa_system.services.diarization import Diarizer, SpeakerSegment


class TestDiarizer(unittest.TestCase):
    def test_diarize_with_funasr_maps_fields(self):
        diarizer = Diarizer()
        sentence_info = [
            {"spk": 1, "start": 0, "end": 1200, "text": "你好"},
            {"spk": 2, "start": 1200, "end": 2400, "text": "请问"},
        ]

        segments = diarizer.diarize_with_funasr(sentence_info)

        self.assertEqual(2, len(segments))
        self.assertEqual("speaker1", segments[0].speaker)
        self.assertEqual(0, segments[0].start_ms)
        self.assertEqual(1200, segments[0].end_ms)
        self.assertEqual("你好", segments[0].text)
        self.assertEqual("speaker2", segments[1].speaker)

    def test_merge_adjacent_merges_same_speaker_when_short(self):
        diarizer = Diarizer()
        merged = diarizer.merge_adjacent(
            [
                SpeakerSegment("speaker1", 0, 1000, "短句"),
                SpeakerSegment("speaker1", 1000, 1800, "继续"),
                SpeakerSegment("speaker2", 1800, 2600, "切换"),
            ],
            merge_threshold_chars=10,
        )

        self.assertEqual(2, len(merged))
        self.assertEqual("短句继续", merged[0].text)
        self.assertEqual(1800, merged[0].end_ms)
        self.assertEqual("speaker2", merged[1].speaker)

    def test_merge_adjacent_keeps_long_text_unmerged(self):
        diarizer = Diarizer()
        merged = diarizer.merge_adjacent(
            [
                SpeakerSegment("speaker1", 0, 1000, "这是一条比较长的句子"),
                SpeakerSegment("speaker1", 1000, 1800, "后续"),
            ],
            merge_threshold_chars=4,
        )

        self.assertEqual(2, len(merged))
        self.assertEqual("这是一条比较长的句子", merged[0].text)
        self.assertEqual("后续", merged[1].text)


if __name__ == "__main__":
    unittest.main()
