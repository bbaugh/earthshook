#!/usr/bin/python
#
#  earthshook.py
#  pyanalysis
#
#  Created by Brian Baughman on 1/23/10.
#  Copyright (c) 2010 Brian Baughman. All rights reserved.
#
import re, sys, os
# Define input files and output log file
homedir = os.getenv('HOME')
logfile = '%s/log/quakealert.log'%homedir #'%s/tmp/tmp.log'%homedir #
cachedir = '%s/.cache'%homedir
twapi = '%s/.twapi'%homedir
twusr = '%s/.twusr'%homedir
bitlyapi = '%s/.bitlyapi'%homedir
# Define some regular expressions
anglere = '\([0-9\.\-]+ degrees\)'
milesre = '\([0-9\.\-]+ miles\)'
bitlyre = '"shortCNAMEUrl":\s*"([^"]+)"'
# Define stuff to find links
linktag = 'For subsequent updates, maps, and technical information, see:'
linkbase = 'http://earthquake.usgs.gov'

try:
  f = open(logfile, 'a')
except:
  sys.exit(-5)

try:
  twapif = open(twapi,'r')
  consumer_key, consumer_secret = twapif.readlines()
  consumer_key = consumer_key.strip()
  consumer_secret = consumer_secret.strip()
  twapif.close()
except:
  f.write('Failed to load twitter API info!\n')
  sys.exit(-2)

try:
  twusrf = open(twusr,'r')
  usrs = twusrf.readlines()
  key, secret  = usrs[0].split()
  key = key.strip()
  secret = secret.strip()
  twusrf.close()
except:
  f.write('Failed to load twitter user info!\n')
  sys.exit(-3)

try:
  bitlyapif = open(bitlyapi,'r')
  busr,bapi = bitlyapif.readlines()
  busr = busr.strip()
  bapi = bapi.strip()
  bitlyapif.close()
except:
  f.write('Failed to load j.mp API info!\n')
  sys.exit(-4)


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
    rv='%soccured at %s'%(rv,pinfo.utctime)
  if pinfo.nearby!=None:
    rv='%s, %s'%(rv,pinfo.nearby)
  return rv

def getbitly(content):
  lines = content.split('\n')
  for l in lines:
    mtc = re.findall(bitlyre,l)
    if len(mtc)==1:
      return mtc[0]
  return None

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

#try:
# Read in data from standard input
ogdata = sys.stdin.readlines()
##############################
# if testing use following
#df = homedir+'/tmp/txtfmt.eml'
#ogdataf = open(df,'r')
#ogdata = ogdataf.readlines()
#ogdataf.close()
##############################
sdata = clean(ogdata)
lk = getlink(sdata)
tb = gettbody(sdata)
pio = prepinfo(tb)
fmttw = formate(pio)
# Load twitter, j.mp stuff
import httplib2
import tweepy
if lk!=None:
  burl = 'http://api.j.mp/shorten?version=2.0.1&longUrl=%s&login=%s&apiKey=%s'%(lk,busr,bapi)
  h = httplib2.Http(cachedir)
  resp, ct = h.request(burl, "GET",headers={'cache-control':'no-cache'})
  surl = getbitly(ct)
  if surl!=None:
    fmttw='%s. %s'%(fmttw,surl)
  else:
    f.write('Failed to get j.mp info\n')
else:
  f.write('Failed to find link.n')
# Create twitter authentication handler
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(key, secret)
# Create interface to twitter API
api = tweepy.API(auth)
fmttw = fmttw.strip().replace('  ',' ').decode('unicode_escape')
if len(fmttw)>140:
  fmttw = fmttw.replace(' earthquake occured',' quake')
if fmttw!=None and fmttw!='' and fmttw!='.' and pio.lat is not None and len(fmttw)<140:
  stt = api.update_status(status=fmttw,lat=float(pio.lat),long=float(pio.long))
  f.write('%s\n'%toascii(fmttw))
else:
  f.write('Failed!\n')
f.close()
sys.exit(1)
#except:
#  f.write('Failed with exception!\n')
#  f.close()
#  sys.exit(-1)
