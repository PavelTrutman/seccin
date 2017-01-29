#!/usr/bin/python3

import argparse
from pathlib import Path

# argument parsing
parser = argparse.ArgumentParser()
parser.prog = 'seccin';
parser.formatter_class=argparse.RawDescriptionHelpFormatter
parser.description = 'seccin - Secret in Coffin\n\r  Tool to encrypt passwords and other secret information for different services.';
parser.add_argument('path', nargs='?', default=Path.cwd().joinpath('coffin'), type=str, help='path to the crypted coffin')
parser.add_argument('--init', '-i', action='store_true', help='create new crypted coffin')
args = parser.parse_args()
print(args)
