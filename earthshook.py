#!/usr/bin/python
#
#  earthshook.py
#  pyanalysis
#
#  Created by Brian Baughman on 1/23/10.
#  Copyright (c) 2010 Brian Baughman. All rights reserved.
#
try:
  import re, sys, time
  from os import environ, _exit
except:
  print 'Failed to load base modules'
  sys.exit(-1)

try:
  from bitly import shorten
  import tweepy
  # Home directory
  homedir = environ['HOME']
  curtime = time.strftime('%Y-%m-%d %H:%M:%S')
# stop if something looks wrong
except:
  print 'Failed to load modules'
  _exit(-1)

# Define input files and output log file
try:
  quakelog = environ['QUAKELOG']
except:
  quakelog = '%s/logs/quakealert.log'%homedir

try:
  twapi = environ['TWAPI']
except:
  twapi = '%s/.twapi'%homedir

try:
  twusr = environ['TWUSR']
except:
  twusr = '%s/.twusr'%homedir

# Define some regular expressions
anglere = '\([0-9\.\-]+ degrees\)'
milesre = '\([0-9\.\-]+ miles\)'
bitlyre = '"shortCNAMEUrl":\s*"([^"]+)"'
# Define stuff to find links
linktag = 'For subsequent updates, maps, and technical information, see:'
linkbase = 'http://earthquake.usgs.gov'

try:
  log = open(quakelog, 'a')
except:
  log = sys.stdout
  log.write('%s: Cannot open log file: %s\n'%(curtime,quakelog))
################################################################################
# Useful functions
################################################################################
def easy_exit(eval):
  '''
    Function to clean up before exiting and exiting itself
  '''
  try:
    log.close()
  except:
    _exit(eval)
  _exit(eval)

try:
  twapif = open(twapi,'r')
  consumer_key, consumer_secret = twapif.readlines()
  consumer_key = consumer_key.strip()
  consumer_secret = consumer_secret.strip()
  twapif.close()
except:
  log.write('Failed to load twitter API info!\n')
  easy_exit(-2)

try:
  twusrf = open(twusr,'r')
  usrs = twusrf.readlines()
  key, secret  = usrs[0].split()
  key = key.strip()
  secret = secret.strip()
  twusrf.close()
except:
  log.write('Failed to load twitter user info!\n')
  easy_exit(-3)

def clean(lines):
  rv = []
  for l in lines:
    if l.strip()=='':
      continue
    else:
      rv.append(l.strip())
  return rv

def gettbody(lines):
  try:
    lines
  except:
    return None
  if lines is None:
    return None
  start=-1
  end=len(lines)
  for i in range(end):
    cline = lines[i]
    if cline.find('== PRELIMINARY EARTHQUAKE REPORT ==')>=0:
      start=i
    elif cline.find('DISCLAIMER:')>=0:
      if start==-1:
        return None
      else:
        return lines[start:i+1]
  return None

def getlink(lines):
  try:
    lines
  except:
    return None
  if lines is None:
    return None
  end = len(lines)
  for i in range(end):
    if lines[i]==linktag:
      if lines[i+1].find(linkbase)>=0:
        return lines[i+1]
  return None

class evtinfo:
  def __init__(self):
    self.mag = None
    self.lat = None
    self.long = None
    self.localtime = None
    self.utctime = None
    self.nearby = None

def prepinfo(info):
  rv = evtinfo()
  try:
    info
  except:
    return rv
  if info is None:
    return rv
  end = len(info)
  for i in range(end):
    s = info[i]
    sloc = s.find(':')
    if sloc<0:
      continue
    nm = s[0:sloc].strip()
    dt = s[sloc+1:].strip()
    if nm=='Magnitude':
      rv.mag=dt
    elif nm=='Universal Time (UTC)':
      rv.utctime='%s UTC'%dt
    elif nm=='Time near the Epicenter':
      rv.localtime=dt
    elif nm=='Geographic coordinates':
      try:
        tlat,tlong = dt.split(',')
        tlat = tlat.strip()
        tlong = tlong.strip()
        if tlat.find('N')>=0:
          rv.lat = '+%s'%tlat.replace('N','')
        elif tlat.find('S')>=0:
          rv.lat = '-%s'%tlat.replace('S','')
        if tlong.find('E')>=0:
          rv.long = '+%s'%tlong.replace('E','')
        elif tlong.find('W')>=0:
          rv.long = '-%s'%tlong.replace('W','')
      except:
        continue
    elif nm=='Location with respect to nearby cities':
      csub = re.sub(anglere,'',info[i+1].strip())
      csub = re.sub(milesre,'',csub)
      rv.nearby = csub.replace('  ',' ')
  return rv

def formate(pinfo):
  rv=''
  if pinfo.mag!=None:
    rv='%s earthquake '%pinfo.mag
  if pinfo.utctime!=None:
    rv='%soccurred at %s'%(rv,pinfo.utctime)
  if pinfo.nearby!=None:
    rv='%s, %s'%(rv,pinfo.nearby)
  return rv

def toascii(s):
  rv = []
  for c in s:
    try:
      c.decode('ascii')
      rv.append(c)
    except:
      continue
  rv = ''.join(rv)
  return rv

# Read in data from standard input
ogdata = sys.stdin.readlines()

sdata = clean(ogdata)
lk = getlink(sdata)
tb = gettbody(sdata)
pio = prepinfo(tb)
fmttw = formate(pio)

if lk!=None:
  shrtlk = shorten(lk)
  fmttw='%s. %s'%(fmttw,shrtlk)
else:
  log.write('Failed to find link.\n')

fmttw = fmttw.strip().replace('  ',' ').decode('unicode_escape')

try:
  # Create twitter authentication handler
  auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
  auth.set_access_token(key, secret)
  # Create interface to twitter API
  api = tweepy.API(auth)
except:
  log.write('Failed TAuth: %s\n'%fmttw)

if len(fmttw)>140:
  fmttw = fmttw.replace(' earthquake occurred',' quake')
if fmttw!=None and fmttw!='' and fmttw!='.' and pio.lat is not None and len(fmttw)<140:
  try:
    stt = api.update_status(status=fmttw,lat=float(pio.lat),long=float(pio.long))
    log.write('%s\n'%toascii(fmttw))
  except:
    log.write('Failed Send: %s\n'%fmttw)
else:
  log.write('Failed!\n')

easy_exit(0)
