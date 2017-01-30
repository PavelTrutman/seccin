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
import readline

def queryYesNo(question, default=None):
  """
  Asks a yes/no question via raw_input() and return their answer.

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

def inputSuggest(prompt, prefill=''):
   """
   Asks user for input with prefilled text.

   Args:
     promp(str): text before input
     prefill (str): prefilled text in the input

   Returns:
     str: typed text
   """

   readline.set_startup_hook(lambda: readline.insert_text(prefill))
   try:
      return input(prompt)
   finally:
      readline.set_startup_hook()

def parseCommandLineArguments():
  """
  Parses command line arguments.

  Args:
    namespace object: parsed arguments

  Returns:
    None
  """

  parser = argparse.ArgumentParser(add_help=False)
  parser.prog = 'seccin';
  parser.formatter_class=argparse.RawDescriptionHelpFormatter
  parser.description = 'seccin - Secret in Coffin\n  Tool to encrypt passwords and other secret information for different services.';

  parser.add_argument('--help', '-h', action='help', help='service from coffin to see or edit')
  parser.add_argument('service', nargs='?', type=str, help='service from coffin to see or edit')
  parser.add_argument('path', nargs='?', default=Path.cwd().joinpath('coffin'), type=str, help='path to the crypted coffin')

  group = parser.add_mutually_exclusive_group()
  group.add_argument('--init', '-i', action='store_true', help='create a new coffin')
  group.add_argument('--open', '-o', action='store_true', help='open and see content of the coffin')
  group.add_argument('--edit', '-e', action='store_true', help='edit the content of the coffin')

  return parser.parse_args()

def initCoffin(coffin):
  """
  Initializes the coffin.

  Args:
    coffin (str): path to the coffin

  Returns:
    None
  """

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
  dbConn.commit()
  dbConn.close()
  encfs.terminate()
  encfs.wait()
  visibleDir.cleanup()

  # zip the files
  coffinZip = zipfile.ZipFile(str(coffin), mode='w')
  coffinZip.write(str(Path(cryptedDir.name).joinpath('db')), 'db')
  coffinZip.write(str(Path(cryptedDir.name).joinpath('.encfs6.xml')), 'meta')

  # clean up
  coffinZip.close()
  cryptedDir.cleanup()

def openCoffin(coffin, service):
  """
  Opens and prints content related to the given service of the coffin.

  Args:
    coffin (str): path to the coffin
    service (str): service to print

  Returns:
    None
  """

  # create temp dirs for encfs
  cryptedDir = tempfile.TemporaryDirectory()
  visibleDir = tempfile.TemporaryDirectory()

  # unarchive
  coffinZip = zipfile.ZipFile(str(coffin), mode='r')
  coffinZip.extract('db', cryptedDir.name)
  coffinZip.extract('meta', cryptedDir.name)

  # clean up
  coffinZip.close()

  password = getpass.getpass('Type your password: ')
  encfs = subprocess.Popen(['encfs', '-i 1', '-f', '-S', cryptedDir.name, visibleDir.name], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, env={'ENCFS6_CONFIG': str(Path(cryptedDir.name).joinpath('meta'))})
  encfs.stdin.write(password.encode('utf-8') + b'\n')
  encfs.stdin.flush()
  # wait until mounts
  while not Path(visibleDir.name).joinpath('db').exists():
    time.sleep(0.1)

  # read db
  dbPath = Path(visibleDir.name).joinpath('db')
  dbConn = sqlite3.connect(str(dbPath))
  db = dbConn.cursor()
  db.execute('PRAGMA foreign_keys = ON')
  db.execute('SELECT * FROM services WHERE name=?', (service, ))
  data = db.fetchone()
  if data == None:
    print('No data for this service.')
  else:
    print(data[2])

  # clean up
  dbConn.commit()
  dbConn.close()
  encfs.terminate()
  encfs.wait()

  # clean up
  cryptedDir.cleanup()
  visibleDir.cleanup()

def editCoffin(coffin, service):
  """
  Opens and allows user to edit content related to the given service of the coffin.

  Args:
    coffin (str): path to the coffin
    service (str): service to print

  Returns:
    None

  """

  # create temp dirs for encfs
  cryptedDir = tempfile.TemporaryDirectory()
  visibleDir = tempfile.TemporaryDirectory()

  # unarchive
  coffinZip = zipfile.ZipFile(str(coffin), mode='r')
  coffinZip.extract('db', cryptedDir.name)
  coffinZip.extract('meta', cryptedDir.name)
  coffinZip.close()

  password = getpass.getpass('Type your password: ')
  encfs = subprocess.Popen(['encfs', '-i 1', '-f', '-S', cryptedDir.name, visibleDir.name], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, env={'ENCFS6_CONFIG': str(Path(cryptedDir.name).joinpath('meta'))})
  encfs.stdin.write(password.encode('utf-8') + b'\n')
  encfs.stdin.flush()
  # wait until mounts
  while not Path(visibleDir.name).joinpath('db').exists():
    time.sleep(0.1)

  # read db
  dbPath = Path(visibleDir.name).joinpath('db')
  dbConn = sqlite3.connect(str(dbPath))
  db = dbConn.cursor()
  db.execute('PRAGMA foreign_keys = ON')
  db.execute('SELECT * FROM services WHERE name=?', (service, ))
  oldData = db.fetchone()
  if oldData == None:
    print('No data for this service. New service will be created.')
  else:
    print(oldData[2])

  # insert new data
  if oldData == None:
    newData = input('Input string: ')
    db.execute('INSERT INTO services(name, data) values(?, ?)', (service, newData))
  else:
    newData = inputSuggest('Input string: ', prefill=oldData[2])
    db.execute('UPDATE services SET data=? WHERE id=?', (newData, oldData[0]))

  # clean up
  dbConn.commit()
  dbConn.close()

  # save coffin
  coffinZip = zipfile.ZipFile(str(coffin), mode='w')
  coffinZip.write(str(Path(cryptedDir.name).joinpath('db')), 'db')
  coffinZip.write(str(Path(cryptedDir.name).joinpath('meta')), 'meta')
  coffinZip.close()
  encfs.terminate()
  encfs.wait()

  # clean up
  cryptedDir.cleanup()
  visibleDir.cleanup()


if __name__ == '__main__':

  args = parseCommandLineArguments()

  if Path(args.path).is_absolute():
    coffin = Path(normpath(str(args.path))) #libpath workaround
  else:
    coffin = Path(normpath(str(Path.cwd().joinpath(args.path)))) #libpath workaround

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
  
  # init coffin
  if args.init:
    initCoffin(coffin)

  # open coffin
  elif args.open or args.edit:
    # check if coffin exists, if not ask user and create it
    if not coffin.exists():
      if queryYesNo('The coffin at ' + str(coffin) + ' does not exist. Do you want to create it?', 'yes'):
        initCoffin(coffin)
      else:
        # not creating, exiting
        sys.exit(1)

    # check service
    if args.service == None:
      sys.stderr.write('Service name not specified.\n')
      sys.exit(1)

    if args.open:
      # open existing coffin
      openCoffin(coffin, args.service)

    elif args.edit:
      # edit existing coffin
      editCoffin(coffin, args.service)
