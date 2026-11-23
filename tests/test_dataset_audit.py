import csv
from datetime import datetime, timedelta
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.dataset_audit import audit, ensure_file


class DatasetAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, offsets=(0, 2000, 4000), **overrides):
        header = self.root / "test.hea"
        header.write_text(f"test 2 500 {overrides.get('count', len(offsets))}\n")
        path = self.root / "test.csv"
        with path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time", "ecg", "pleth_3", "peaks"])
            for i, offset in enumerate(offsets):
                timestamp = datetime(2021, 1, 1) + timedelta(microseconds=offset)
                writer.writerow([timestamp.isoformat(), overrides.get("ecg", i), i + 2,
                                 overrides.get("peak", int(i == 1))])
        return path, header

    def test_regular_timeline(self):
        result, _ = audit(*self.fixture())
        self.assertTrue(result["raw_timestamp_timeline_accepted"])
        self.assertEqual(result["annotated_peak_count"], 1)
        self.assertEqual(result["nominal_last_sample_s"], 0.004)

    def test_wrap_flagged_without_rewriting_time(self):
        result, signals = audit(*self.fixture((0, 2000, 4000 - 2**32)))
        self.assertFalse(result["raw_timestamp_timeline_accepted"])
        self.assertTrue(result["timestamp_anomalies"][0]["consistent_with_32bit_us_wrap"])
        self.assertLess(signals[2][-1], 0)
        self.assertEqual(result["nominal_last_sample_s"], 0.004)

    def test_other_backward_jump_not_labelled_wrap(self):
        result, _ = audit(*self.fixture((0, 2000, 1000)))
        self.assertFalse(result["timestamp_anomalies"][0]["consistent_with_32bit_us_wrap"])

    def test_duplicate_and_gap_rejected(self):
        for offsets in ((0, 2000, 2000), (0, 2000, 6000)):
            with self.subTest(offsets=offsets):
                result, _ = audit(*self.fixture(offsets))
                self.assertFalse(result["raw_timestamp_timeline_accepted"])

    def test_one_microsecond_rounding_tolerance(self):
        result, _ = audit(*self.fixture((0, 2000, 4001)))
        self.assertTrue(result["raw_timestamp_timeline_accepted"])

    def test_nonfinite_and_invalid_annotations_fail(self):
        for overrides in ({"ecg": "nan"}, {"ecg": "inf"}, {"peak": 2}, {"count": 4}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                audit(*self.fixture(**overrides))

    def test_missing_columns_fail(self):
        path, header = self.fixture()
        path.write_text("time,ecg\n2021-01-01,1\n")
        with self.assertRaisesRegex(ValueError, "Required columns"):
            audit(path, header)

    def test_existing_bad_checksum_preserved(self):
        path = self.root / "file"
        path.write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            ensure_file(path, hashlib.sha256(b"good").hexdigest(), "unused", True)
        self.assertEqual(path.read_bytes(), b"bad")

    def test_download_verified_and_bad_temporary_removed(self):
        path = self.root / "file"
        digest = hashlib.sha256(b"good").hexdigest()
        with patch("urllib.request.urlopen", return_value=BytesIO(b"bad")):
            with self.assertRaises(ValueError):
                ensure_file(path, digest, "unused", True)
        self.assertFalse(path.exists())
        self.assertFalse(path.with_name("file.part").exists())
        with patch("urllib.request.urlopen", return_value=BytesIO(b"good")):
            ensure_file(path, digest, "unused", True)
        self.assertEqual(path.read_bytes(), b"good")
        ensure_file(path, digest, "unused")

    def test_offline_missing_file_fails(self):
        with self.assertRaises(FileNotFoundError):
            ensure_file(self.root / "absent", "unused", "unused")

    def test_audit_reproducible(self):
        inputs = self.fixture()
        self.assertEqual(audit(*inputs), audit(*inputs))
