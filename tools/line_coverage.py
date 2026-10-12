#!/usr/bin/env python3
"""Line coverage of repo modules under their unittest modules, using only the stdlib `trace` module.

Executable lines come from `trace`'s own line table; a module's `main()` and its
`if __name__ == '__main__':` block are excluded because tests import modules rather than run them.
Exits 1 when any module is below --minimum percent. Coverage shows which lines ran, not that they are right.
"""
import argparse
import ast
from pathlib import Path
import sys
import trace
import unittest


def entry_lines(source):
    """Line numbers of `def main` and the `if __name__ == '__main__'` guard."""
    skipped = set()
    for node in ast.walk(ast.parse(source)):
        is_main = isinstance(node, ast.FunctionDef) and node.name == 'main'
        is_guard = (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                    and isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__')
        if is_main or is_guard:
            skipped.update(range(node.lineno, node.end_lineno + 1))
    return skipped


def measure(modules, tests):
    """{module path: (covered lines, executable lines, missed line numbers)} after running the tests."""
    modules = [Path(m).resolve() for m in modules]
    for directory in {str(m.parent) for m in modules} | {str(Path(t).resolve().parent) for t in tests}:
        if directory not in sys.path:
            sys.path.insert(0, directory)
    names = [Path(t).stem for t in tests]
    tracer = trace.Trace(count=1, trace=0)
    outcome = {}

    def run():
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        with open(Path('/dev/null'), 'w') as sink:
            outcome['result'] = unittest.TextTestRunner(stream=sink, verbosity=0).run(suite)
    tracer.runfunc(run)
    if not outcome['result'].wasSuccessful():
        raise ValueError('tests failed under coverage; coverage is not reported for a failing suite')
    counts = tracer.results().counts
    report = {}
    for module in modules:
        path = str(module)
        executable = {line for line in trace._find_executable_linenos(path) if isinstance(line, int) and line > 0}
        executable -= entry_lines(module.read_text())
        if not executable:
            raise ValueError('no executable lines in ' + path)
        hit = {line for (name, line), n in counts.items() if name == path and n} & executable
        report[path] = (len(hit), len(executable), sorted(executable - hit))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modules', nargs='+', required=True)
    parser.add_argument('--tests', nargs='+', required=True)
    parser.add_argument('--minimum', type=float, default=0.0)
    args = parser.parse_args()
    try:
        report = measure(args.modules, args.tests)
    except (ValueError, OSError, SyntaxError) as error:
        print('ERROR:', error)
        return 1
    below = []
    for path, (hit, total, missed) in report.items():
        percent = 100 * hit / total
        print(f'{Path(path).name}: {hit}/{total} executable lines ({percent:.1f}%), missed {missed}')
        if percent < args.minimum:
            below.append(Path(path).name)
    if below:
        print(f'BELOW {args.minimum}%: ' + ', '.join(below))
        return 1
    print(f'ALL MODULES AT OR ABOVE {args.minimum}%')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
