#!/usr/bin/env python3
"""Compatibility entry point: rebuild the dealership from its editable copies."""
from build_dealership import OUTPUT, build

if __name__ == '__main__':
    cars = build()
    print(f'{len(cars)} dealership cars -> {OUTPUT}; editable models preserved')
