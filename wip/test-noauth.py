#!/usr/bin/python

import socket, time

TARGET_IP = '192.168.1.70'
TARGET_PORT = 51321
#TARGET_IP = '127.0.0.1'
#TARGET_PORT = 51325

BUFFER_SIZE = 20


TEST_MUTE1  = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x80, 0x00, 0x01, 0x01, 0xf7 ]
TEST_MUTE1x = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x80, 0x00, 0x01, 0x00, 0xf7 ]

TEST_MUTE2  = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x81, 0x00, 0x01, 0x01, 0xf7 ]
TEST_MUTE2x = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x81, 0x00, 0x01, 0x00, 0xf7 ]

TEST_MUTE3  = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x82, 0x00, 0x01, 0x01, 0xf7 ]
TEST_MUTE3x = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x82, 0x00, 0x01, 0x00, 0xf7 ]

TEST_MUTE4  = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x83, 0x00, 0x01, 0x01, 0xf7 ]
TEST_MUTE4x = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x31, 0x83, 0x00, 0x01, 0x00, 0xf7 ]

# PAFL
TEST_DATA1 = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x35, 0x00, 0x00, 0x01, 0x01, 0xf7 ]
TEST_DATA2 = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x35, 0x0a, 0x00, 0x01, 0x01, 0xf7 ]
TEST_DATA3 = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x35, 0x14, 0x00, 0x01, 0x01, 0xf7 ]
TEST_DATA4 = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x35, 0x1e, 0x00, 0x01, 0x01, 0xf7 ]
TEST_DATA5 = [ 0xf0, 0x00, 0x01, 0x00, 0x1b, 0x00, 0x1a, 0x35, 0x1e, 0x00, 0x01, 0x00, 0xf7 ]

SERIES = [
   (1, TEST_MUTE1    ),
   (0, TEST_MUTE1x   ),
   (1, TEST_MUTE2    ),
   (0, TEST_MUTE2x   ),
   (1, TEST_MUTE3    ),
   (0, TEST_MUTE3x   ),
   (1, TEST_MUTE4    ),
   (0, TEST_MUTE4x   ),
   (1, TEST_DATA1    ),
   (1, TEST_DATA2    ),
   (1, TEST_DATA3    ),
   (1, TEST_DATA4    ),
   (0, TEST_DATA5    )
]

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect ( (TARGET_IP, TARGET_PORT) )

while True:

   for x, (dly, data) in enumerate(SERIES):
      print "Set ", x

      s.send(''.join(chr(x) for x in data))
      time.sleep(dly)

#data = s.recv(BUFFER_SIZE)
#print data

s.close()

