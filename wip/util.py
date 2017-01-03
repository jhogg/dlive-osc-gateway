# util.py
#

__all__ = [ 'dump_binary' ]

from types import StringType

def dump_binary(data):
   if type(data) == StringType:
      data = [ord(x) for x in data]
   for idx in xrange(0, len(data)/16 + 1):
      hex_str = ''
      ascii_str = ''
      for byte in data[idx*16:idx*16+16]:
         hex_str += '%02x ' % byte
         ascii_str += chr(byte if byte > 31 and byte < 127 else 0x2e)

      print "%05x: %-48.48s %-17.17s" % (idx*16, hex_str, ascii_str)

