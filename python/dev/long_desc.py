#!/usr/bin/env python3

with open('../../README.md') as infile:
    readme = infile.read()
    print('_LONG_DESC = """\\')
    print(readme)
    print('"""')
