#!/usr/bin/env python3
import zlib

with open('../../README.md') as infile:
    readme = infile.read()
    print('_LONG_DESC = """\\')
    print(readme)
    print('"""')

