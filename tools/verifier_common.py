#!/usr/bin/env python3
"""Shared pieces of the verifier idiom: derive from pinned sources, run negative controls, reproduce a receipt.

A verifier defines `derive(inputs)` (pure; raises its own error class when a check fails), a list of
controls (label, mutate) that each make `derive` raise on a copy of the inputs, and calls `finish`.
CODING_STANDARDS.md states the idiom; tools/verify_vu_dispatch_map.py is the reference use.
"""
import copy
import hashlib
import json
import re


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def make_need(error):
    """A `need(condition, message)` that raises the verifier's own error class."""
    def need(condition, message):
        if not condition:
            raise error(message)
    return need


def normalise(text):
    """Numbers (hex or decimal) become decimal and whitespace collapses, so two renderings of one instruction compare equal."""
    text = re.sub(r'(?<![\w.])(-?0x[0-9a-f]+)(?![\w])', lambda m: str(int(m.group(1), 16)), text.strip())
    return re.sub(r'\s+', ' ', text)


def run_controls(inputs, controls, derive, error, clone=copy.deepcopy, baseline=None):
    """Apply each (label, mutate) to a copy of the inputs; every mutation must be rejected.

    Rejected means `derive` raised `error`. With `baseline` (the clean receipt) a mutation that derives a
    different receipt also counts, and each result records which way it was caught ('by')."""
    results = []
    for label, mutate in controls:
        mutated = clone(inputs)
        mutate(mutated)
        try:
            derived = derive(mutated)
        except error as e:
            results.append({'mutation': label, 'rejected': True, **({'by': 'derivation error'} if baseline is not None else {}), 'reason': str(e)})
            continue
        if baseline is None or derived == baseline:
            raise AssertionError('mutation escaped: ' + label)
        results.append({'mutation': label, 'rejected': True, 'by': 'receipt differs', 'reason': 'the derived receipt differs from the clean one'})
    return results


def finish(receipt, path, argv, root, summary):
    """Write the receipt with --write, otherwise require it to reproduce byte for byte. Returns the exit code."""
    text = json.dumps(receipt, indent=1) + '\n'
    if '--write' in argv:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    elif not path.exists() or path.read_text() != text:
        print('RECEIPT MISMATCH: %s does not reproduce from the pinned sources (re-run with --write only after reading the diff)' % path.relative_to(root))
        return 1
    print(json.dumps(summary))
    print('VERIFY OK')
    return 0
