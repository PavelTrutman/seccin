#!/usr/bin/python3.6

import sys
import argparse
from os.path import normpath
from pathlib import Path

def queryYesNo(question, default=None):
  """
  Ask a yes/no question via raw_input() and return their answer.

  Args:
    question (str): a string that is presented to the user
    default (str): the presumed answer if the user just hits <Enter>. It must be 'yes', 'no' or None (default) (meaning an answer is required of the user)

  Returns:
    bool: True for 'yes' or False for 'no'
  """

  valid = {"yes": True, "y": True, "no": False, "n": False}
  if default is None:
    prompt = " [y/n] "
  elif default == "yes":
    prompt = " [Y/n] "
  elif default == "no":
    prompt = " [y/N] "
  else:
    raise ValueError("invalid default answer: '%s'" % default)

  while True:
    sys.stdout.write(question + prompt)
    choice = input().lower()
    if default is not None and choice == '':
      return valid[default]
    elif choice in valid:
      return valid[choice]

if __name__ == '__main__':
  # argument parsing
  parser = argparse.ArgumentParser()
  parser.prog = 'seccin';
  parser.formatter_class=argparse.RawDescriptionHelpFormatter
  parser.description = 'seccin - Secret in Coffin\n\r  Tool to encrypt passwords and other secret information for different services.';
  parser.add_argument('path', nargs='?', default=Path.cwd().joinpath('coffin'), type=str, help='path to the crypted coffin')
  parser.add_argument('--init', '-i', action='store_true', help='create new crypted coffin')
  args = parser.parse_args()
  
  coffin = Path(normpath(str(args.path))) #libpath workaround
  init = args.init
  
  print(coffin)
  print(type(coffin))
  print(init)
  
  if init:
    
    # check that coffin exists
    if coffin.exists():
      if not queryYesNo('The coffin at ' + str(coffin) + ' already exists. Do you want to overwrite it?', 'no'):
        # not overwriting, exiting
        sys.exit(1)
    
    
  
