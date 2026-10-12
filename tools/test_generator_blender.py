"""Generate both learned methods, then prove Blender edit/export/rebuild on temporary copies."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(blender):
    with tempfile.TemporaryDirectory(prefix='generator-blender-') as folder:
        root = Path(folder)
        for method in ['shape space', 'network']:
            work = root / method.replace(' ', '-')
            (work / 'models').mkdir(parents=True)
            (work / 'catalog.json').write_text('[]\n')
            # Generation runs in the pinned numerical environment, separate from Blender.
            program = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tools'))
from car_generator import Generator
source = Generator()
result = source.generate(method=sys.argv[1], seed=35, novelty=.35)
target = Generator(Path(sys.argv[2]), source.assets)
work = Path(sys.argv[2])
target.save(result, output=work.parent / (work.name + '-display') / 'cars.json')
'''
            subprocess.run([str(ROOT / '.venv-generator/bin/python'), '-c', program, method, str(work)],
                           cwd=ROOT, check=True)
            subprocess.run([str(blender), '--background', '--python-exit-code', '1', '--python',
                            str(ROOT / 'tools/generator_blender_fixture.py'), '--', str(work)],
                           cwd=ROOT, check=True)
        print('PASS generated Blender roundtrip: ' + json.dumps({'methods': ['shape space', 'network'],
              'claim_limits': ['Pinned Blender 4.5.14, seed 35, two temporary models; not all DCC exporters.']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', type=Path, required=True)
    run(parser.parse_args().blender)
