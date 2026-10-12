"""Coverage measurement controls on a throwaway module: counted, missed, excluded and failing cases."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from line_coverage import entry_lines, measure

MODULE = '''def used(x):
    if x:
        return 1
    return 2


def unused():
    return 3


def main():
    return used(1)


if __name__ == '__main__':
    main()
'''
TEST = '''import unittest
from {name} import used


class T(unittest.TestCase):
    def test_used(self):
        self.assertEqual(used(1), {expected})
'''


def workspace(root, name, expected=1):
    (root / f'{name}.py').write_text(MODULE)
    (root / f'test_{name}.py').write_text(TEST.format(name=name, expected=expected))
    return root / f'{name}.py', root / f'test_{name}.py'


class LineCoverageTests(unittest.TestCase):
    def test_counts_missed_lines_and_excludes_entry_points(self):
        with tempfile.TemporaryDirectory() as temp:
            module, test = workspace(Path(temp), 'covmod_a')
            [(hit, total, missed)] = measure([module], [test]).values()
            # used(): def, if, return 1, return 2; unused(): def, return 3. main and the guard are excluded.
            self.assertEqual((hit, total, missed), (4, 6, [4, 8]))
            self.assertEqual(entry_lines(MODULE), set(range(11, 13)) | set(range(15, 17)))

    def test_failing_suite_reports_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            module, test = workspace(Path(temp), 'covmod_b', expected=2)
            with self.assertRaisesRegex(ValueError, 'tests failed'):
                measure([module], [test])

    def test_cli_enforces_the_minimum(self):
        with tempfile.TemporaryDirectory() as temp:
            module, test = workspace(Path(temp), 'covmod_c')
            tool = Path(__file__).resolve().parent / 'line_coverage.py'

            def run(minimum):
                return subprocess.run([sys.executable, str(tool), '--modules', str(module), '--tests', str(test),
                                       '--minimum', str(minimum)], capture_output=True, text=True)
            passed, failed = run(60), run(70)
            self.assertEqual(passed.returncode, 0)
            self.assertIn('covmod_c.py: 4/6 executable lines (66.7%), missed [4, 8]', passed.stdout)
            self.assertEqual(failed.returncode, 1)
            self.assertIn('BELOW 70.0%: covmod_c.py', failed.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
