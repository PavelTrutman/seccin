#!/usr/bin/python3.6

import sys
import argparse
from os.path import normpath
from pathlib import Path
import subprocess
import tempfile
import getpass
import sqlite3
import time
import zipfile

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
  parser.description = 'seccin - Secret in Coffin\n  Tool to encrypt passwords and other secret information for different services.';
  parser.add_argument('path', nargs='?', default=Path.cwd().joinpath('coffin'), type=str, help='path to the crypted coffin')
  parser.add_argument('--init', '-i', action='store_true', help='create new crypted coffin')
  args = parser.parse_args()

  if Path(args.path).is_absolute():
    coffin = Path(normpath(str(args.path))) #libpath workaround
  else:
    coffin = Path(normpath(str(Path.cwd().joinpath(args.path)))) #libpath workaround
  init = args.init
  
  print(coffin)
  print(type(coffin))
  print(init)

  # check encfs version
  try:
    encfs = subprocess.run(['encfs', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except FileNotFoundError:
    # no encfs
    sys.stderr.write('ENCFS is not installed. Please install it first.\n')
    sys.exit(1)
  if encfs.returncode:
    # no encfs
    sys.stderr.write('ENCFS is not installed. Please install it first.\n')
    sys.exit(1)
  

  if init:
    
    # check that coffin exists
    if coffin.exists():
      if not queryYesNo('The coffin at ' + str(coffin) + ' already exists. Do you want to overwrite it?', 'no'):
        # not overwriting, exiting
        sys.exit(1)

    # select password
    
    while True:
      pass1 = getpass.getpass('Choose password: ')
      pass2 = getpass.getpass('Retype password: ')
      if pass1 == pass2:
        password = pass1
        break
      else:
        print('Passwords do not match.')

    # create temp dirs for encfs
    cryptedDir = tempfile.TemporaryDirectory()
    visibleDir = tempfile.TemporaryDirectory()
    print(cryptedDir.name)
    print(visibleDir.name)
    encfs = subprocess.Popen(['encfs', '-i 1', '-f', '-S', cryptedDir.name, visibleDir.name], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
    encfs.stdin.write(b'x\n1\n256\n1024\n3\ny\ny\ny\ny\n8\ny\n' + password.encode('utf-8') + b'\n')
    encfs.stdin.flush()
    # wait until mounts
    while not Path(visibleDir.name).joinpath('.encfs6.xml').exists():
      time.sleep(0.1)

    # create db
    dbPath = Path(visibleDir.name).joinpath('db')
    dbConn = sqlite3.connect(str(dbPath))
    db = dbConn.cursor()
    db.execute('PRAGMA foreign_keys = ON')
    db.execute('CREATE TABLE services(id INTEGER PRIMARY KEY autoincrement, name TEXT, data TEXT)')

    # clean up
    dbConn.close()
    encfs.terminate()
    encfs.wait()
    visibleDir.cleanup()

    # zip the files
    coffinZip = zipfile.ZipFile(str(coffin), mode='w')
    coffinZip.write(str(Path(cryptedDir.name).joinpath('db')), 'db')
    coffinZip.write(str(Path(cryptedDir.name).joinpath('.encfs6.xml')), 'meta')

    coffinZip.close()
    cryptedDir.cleanup()
