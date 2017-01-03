#!/usr/bin/python

import socket, time, select
import sys
from types import StringType

from mixrackstate import dLiveMessageRouter
from util import *

TARGET_IP = '192.168.1.70'
TARGET_PORT = 51321
#TARGET_IP = '127.0.0.1'
#TARGET_PORT = 51325

BUFFER_SIZE = 65536 * 16

MixRackRouter = dLiveMessageRouter()


def make_msg(deviceid, addr1, addr2, addr3, data = []):

   if type(data) == StringType:
      data = [ord(x) for x in data]

   len1  = len(data) / 256
   len2  = len(data) % 256

   sysex = [ 0xf0, 
               deviceid/256, deviceid%256, 
               addr1/256, addr1%256, 
               addr2/256, addr2%256,    # Typically addr1 - 0x0001
               addr3/256, addr3%256,
               len1, len2]
   sysex.extend(data)
   sysex.append(0xf7)  
   return sysex

 
# get Rack Bus Config  
GET_BUSCONFIG1 = make_msg(0x0001, 0x0004, 0x0002, 0x0006, [ 0x00, 0x00, 0x50, 0xf9, 0x10, 0x02, 0x10, 0x03, 0x00, 0xff])
GET_BUSCONFIG2 = make_msg(0x0001, 0x0004, 0x0002, 0x0006, [ 0x00, 0x00, 0x50, 0xf9, 0x10, 0x01, 0x10, 0x02, 0x00, 0xff])
GET_BUSCONFIG3 = make_msg(0x0001, 0x0000, 0x0002, 0x0004, 'Channel Mapper\0' )

GET_INPUT_NAMES1 = \
   make_msg(0x0001, 0x000b, 0x0002, 0x0006, [ 0x00, 0x00, 0x00, 0x0a, 0x10, 0xfd, 0x10, 0xfd, 0x00, 0x01]) + \
   make_msg(0x0001, 0x000b, 0x000a, 0x0008, []) + \
   make_msg(0x0001, 0x000b, 0x0002, 0x0006, [ 0x00, 0x00, 0x00, 0x0a, 0x10, 0xfe, 0x10, 0xfe, 0x00, 0x01]) + \
   make_msg(0x0001, 0x000b, 0x000a, 0x0008, []) + \
   make_msg(0x0001, 0x000b, 0x0002, 0x0006, [ 0x00, 0x00, 0x00, 0x0a, 0x10, 0xff, 0x10, 0xff, 0x00, 0x01]) + \
   make_msg(0x0001, 0x000b, 0x000a, 0x0008, [])

GET_INPUT_NAMES2 = make_msg(0x0001, 0x0000, 0x0002, 0x0004, 'Mono Group Channel Name Colour Manager\0')

# Unknown   f000 0100 0700 0601 0500 0200 04f7
#DUMP_MSG1   = [ 0xf0, 0x00, 0x01, 0x00, 0x07, 0x00, 0x06, 0x01, 0x05, 0x00, 0x02, 0x00, 0x04, 0xf7 ]
DUMP_MSG1   = make_msg(0x0001, 0x0007, 0x0006, 0x0105, [0x00, 0x04])

# Unknwon   f000 0100 0700 0601 0500 0200 0af7  -- Has channel names and colors
#DUMP_MSG2   = [ 0xf0, 0x00, 0x01, 0x00, 0x07, 0x00, 0x06, 0x01, 0x05, 0x00, 0x02, 0x00, 0x0a, 0xf7 ]
DUMP_MSG2   = make_msg(0x0001, 0x0007, 0x0006, 0x0105, [0x00, 0x0a])

# Disconnect Messages - Cancel Subscriptions?
# f0 0001 000a 50fc 0009 0000 f7
#
# f0 0001 17f5 50fa 0009 0000 f7
# f0 0001 0037 50fa 0009 0000 f7
# f0 0001 17f3 50fa 0009 0000 f7
# f0 0001 0004 50fa 0009 0000 f7 
#
# f0 0001 0003 2a2b 0009 0000 f7
# f0 0001 0003 2a5a 0009 0000 f7
#

#
# Final disconnect - close MixRack connection
# e000 0342 5945 e7                 BYE
DISC_MSG10 = [ 0xe0, 0x00, 0x03, 0x42, 0x59, 0x45, 0xe7 ]


from ctypes import (
   Structure, Union, addressof, sizeof,
   c_ubyte, c_byte, c_ushort)





SERIES = [
   (0, DUMP_MSG1     ),
   (0, DUMP_MSG2     ),
#   (0, GET_INPUT_NAMES1),
#   (0, GET_INPUT_NAMES2),
#   (0, GET_BUSCONFIG1),
#   (0, GET_BUSCONFIG2),
#   (0, GET_BUSCONFIG3),
]

def to_array(data):
   print "DATA_XXX = ["
   for idx in xrange(0, len(data)/16 + 1):
      hex_str = ''
      for byte in data[idx*16:idx*16+16]:
         ch = ord(byte)
         hex_str += '0x%02x, ' % ch

      print hex_str

   print "]\n"


def dump_ahnet(mode, data):

   rawdata = data

   if type(data) == StringType:
      data = [ord(x) for x in data]
   idx = 0

   while idx < len(data) and mode == 'request':

      # This is sysex
      if data[idx] == 0xf0:
         # ... parse sysex
         deviceid = data[idx+1] * 256 + data[idx+2]
         addr1    = data[idx+3] * 256 + data[idx+4]
         addr2    = data[idx+5] * 256 + data[idx+6]
         addr3    = data[idx+7] * 256 + data[idx+8]
         length   = data[idx+9] * 256 + data[idx+10]
         print "%-8.8s F0 0x%04x 0x%04x 0x%04x 0x%04x Len=0x%04x" % (mode, deviceid, addr1, addr2, addr3, length)
         dump_binary(data[idx+11:idx+11+length])

         idx += 12 + length

      else:
         print "Unexpected data at sysex start (0xf0) @ %i has 0x%02x" % (idx, data[idx])
         dump_binary(data[idx:])
         idx += len(data[idx:])

   if mode == 'response':
      msgs = MixRackRouter.process(rawdata)
      # ... process messages


#from packet_002 import *

#STR_001 = ''.join(chr(x) for x in DATA_001)
#dump_binary(STR_001)

#sys.exit(0)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect ( (TARGET_IP, TARGET_PORT) )
s.setblocking(0)


while True:

   for x, (dly, data) in enumerate(SERIES):
      print "Series ", x

      dump_ahnet("request", data)
      s.send(''.join(chr(x) for x in data))

      while True:
         ready = select.select([s], [], [], 2)
         if ready[0]:
            data = s.recv(BUFFER_SIZE)
            #dump_binary(data)
            dump_ahnet("response", data)
            #to_array(data)
            continue
         break

   break


print "Sending Bye"
s.send(''.join(chr(x) for x in DISC_MSG10))
time.sleep(1)

print "Closing connection"
s.close()


