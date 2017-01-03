# mixrackstate.py - dLive MixRack state
#
#
#

_all_ = ['dLiveMessageRouter']

from ctypes import (
    BigEndianStructure, Union, addressof, sizeof,
    c_ubyte, c_byte, c_ushort,
    memmove)

from util import *

# -----------------------------------------------------------------------------
#
# Message Routing Definitions
#
# -----------------------------------------------------------------------------

MESSAGES = []

def maskkey(bits, data):
    d = [ None, None, None, None ]
    if bits & 0x08:  d[0] = data[0]
    if bits & 0x04:  d[1] = data[1]
    if bits & 0x02:  d[2] = data[2]
    if bits & 0x01:  d[3] = data[3]
    return tuple(d)

class _dLiveRouteEntry(object):
    
    def __init__(self, code, desc, request, responses):
        self.code = code
        self.desc = desc
        self.request = request
        self.responses = responses

    def __repr__(self):
        msg = "%s: %s\n" % (self.code, self.request)
        return msg

class _dLiveSysex(object):

    def __init__(self, deviceid, addr1, addr2, addr3, data = None, mask = 0x0f):
        self._deviceid = deviceid
        self._addr1 = addr1
        self._addr2 = addr2
        self._addr3 = addr3
        self._data  = data
        self._mask  = mask      # Match all 4 parts

    def match(self):
        return maskkey(self._mask, [self._deviceid, self._addr1, self._addr2, self._addr3])

# -----------------------------------------------------------------------------
#
# Binary structure definitions for AH-NET & dLive
#
# -----------------------------------------------------------------------------

class dLiveStructure(BigEndianStructure):

    def receive(self, bytes, sysex_msg):
        offset = 0 #sizeof(_sysex_prefix)  # Skip sysex header
        length = min(len(bytes)-offset, sizeof(self), sysex_msg.length + sizeof(sysex_msg))
        memmove(addressof(self), bytes[offset:], length)
        return self

    def __repr__(self):
        output = ''
        for (name, datatype) in self._fields_:
            output += '%s=%s ' % (name, self.__getattribute__(name)) 
        return output

class _sysex_prefix(dLiveStructure):
    _pack_ = 1
    _fields_ = [
        ('f0'         , c_ubyte),
        ('deviceid'	  , c_ushort),
        ('addr1'      , c_ushort),
        ('addr2'      , c_ushort),
        ('addr3'      , c_ushort),
        ('length'     , c_ushort),
        # ('data'       , c_ubyte*1)		# Variable length data or 0xf7 end marker
    ]

    def receive(self, bytes):
        # validate 0xf0 & f7!
        length = min(len(bytes), sizeof(self))
        memmove(addressof(self), bytes, length)
        return self

    def create_matchkey(self, mask):
        all = [ self.deviceid, self.addr1, self.addr2, self.addr3 ]
        return maskkey(mask, all)

    def __repr__(self):
        return "(id=0x%04x a1=0x%04x a2=0x%04x a3=0x%04x L=0x%04x)" % \
            (self.deviceid, self.addr1, self.addr2, self.addr3, self.length)

# ---
# Empty Response
# ---

class _dlive_resp_empty(dLiveStructure):
    _pack = 1
    _fields_ = [
        ('_sysex'       , _sysex_prefix),
    ]

# ---
# Bus Config 1 - Bus type counts
#
# Sample response data:
# (1) F0 0x000b 0x50f9 0x0004 0x0008 Len=0x0000
# 
# (2) F0 0x000b 0x50f9 0x0004 0x1001 Len=0x000c
# 00 01 04 04 08 08 02 02 05 01 02 ff
#
# ---
#GET_BUSCONFIG1 = make_msg(0x0001, 0x0004, 0x0002, 0x0006, [ 0x00, 0x00, 0x50, 0xf9, 0x10, 0x01, 0x10, 0x02, 0x00, 0xff])
TEST_BUSCONFIG1_RESP = [ 0x00, 0x01, 0x04, 0x04, 0x08, 0x08, 0x02, 0x02, 0x05, 0x01, 0x02, 0xff]

class _dlive_resp_busconfig1(dLiveStructure):
	_pack_ = 1
	_fields_ = [
        ('_sysex'       , _sysex_prefix),
        ('group_mono'	, c_ubyte),
        ('group_stereo'	, c_ubyte),
        ('fx_mono'		, c_ubyte),
        ('fx_stereo'	, c_ubyte),
        ('aux_mono'		, c_ubyte),
        ('aux_stereo'	, c_ubyte),
        ('matrix_mono'	, c_ubyte),
        ('matrix_stereo', c_ubyte),
        ('mains'		, c_ubyte),
        ('mains_lfe'	, c_ubyte),
        ('pafl'			, c_ubyte),
        ('unknown1'		, c_ubyte)
    ]

MESSAGES.append(_dLiveRouteEntry(
    code = 'BUSCONFIG1',
    desc = '',
    request  = _dLiveSysex(0x0001, 0x0004, 0x0002, 0x0006, [ 0x00, 0x00, 0x50, 0xf9, 0x10, 0x01, 0x10, 0x02, 0x00, 0xff]),
    responses = [
        (0, _dLiveSysex(0x0010, 0x50f9, 0x0004, 0x0008, mask=0x07), _dlive_resp_empty),
        (1, _dLiveSysex(0x0010, 0x50f9, 0x0004, 0x1001, mask=0x07), _dlive_resp_busconfig1),
        ]
))

# ---
# Bus Config 2 - # of busses allocated
#
# (1) F0 0x000b 0x0002 0x0000 0x0002 Len=0x0002
# 00 37
#
# ---
#GET_BUSCONFIG3 = make_msg(0x0001, 0x0000, 0x0002, 0x0004, 'Channel Mapper\0' )
TEST_BUSCONFIG2_RESP = [ 0x00, 0x37 ]

class _dlive_resp_busconfig2(dLiveStructure):
	_pack_ = 1
	_fields_ = [
        ('_sysex'               , _sysex_prefix),
        ('busses_configured'	, c_ushort),
    ]

MESSAGES.append(_dLiveRouteEntry(
    code = 'BUSCONFIG2',
    desc = '',
    request  = _dLiveSysex(0x0001, 0x0004, 0x0002, 0x0004, 'Channel Mapper\0' ),
    responses = [
        (0, _dLiveSysex(0x0010, 0x0002, 0x0000, 0x0002, mask=0x07), _dlive_resp_busconfig2),
        ]
))

# -----------------------------------------------------------------------------

class dLiveMessageRouter(object):
    """

    TODO: 
    -- bytebuffer needs to be a static 64k with offset/shifts to minimize the
       GC involved with the slicing/appending
    -- Handled messages other than 0xf0 sysex

    """

    def __init__(self):
        self._routes = {}
        self._msgqueue = []
        self._bytebuffer = ''

        for msg in MESSAGES:
            self._build_routes(msg)

    def _build_routes(self, msg):
        for idx, entry in enumerate(msg.responses):
            print "Route: %s:%i " % (msg.code, entry[0])
            key = entry[1].match()
            print "--> %s maps to %i" % (key, idx)
            if key in self._routes:
                raise DuplicateRoute()
            else:
                self._routes[key] = (msg, idx)

    def process(self, byte_data):

        print "len(byte_data) %i" % (len(byte_data))
        bb = self._bytebuffer

        # --- Sanity check for existing buffer
        if bb and bb[0] != '\xf0':
            print "Flush buffer - unknown start"
            bb = ''

        self._bytebuffer = bb = bb + byte_data

        while bb and bb[0] == '\xf0':

            if self._process_f0() == False:
                break

            bb = self._bytebuffer

        return len(self._msgqueue)

    def _process_f0(self):
        bb = self._bytebuffer
        
        # --- Make sure we at least have sysex header + terminator
        if len(bb) < sizeof(_sysex_prefix) + 1:
            print "--> Too short (sysex) %i/%i" % (len(bb), sizeof(_sysex_prefix)+1)
            return False

        # --- Cast it to sysex and see if we have enough length
        hdr = _sysex_prefix().receive(bb)
        ttl = sizeof(_sysex_prefix) + hdr.length + 1
        print "bb len(0x%04x) ttl(0x%04x)" % (len(bb), ttl)
        if len(bb) < ttl:
            print "--> Too short (sysex+data)"
            return False

        self._route(hdr, bb)

        self._bytebuffer = bb[ttl:]

        return True

    def _route(self, sysex, byte_data):
        masks = [ 0x0f, 0x07, 0x0e ]
        #sysex = _sysex_prefix().receive(byte_data
        print "Routing: ", sysex
        dump_binary(byte_data[11:11+sysex.length])
        for mask in masks:
            key = sysex.create_matchkey(mask)
            print "Checking: ", key
            route = self._routes.get(key, None)
            if route:
                entry = route[0].responses[route[1]]
                key  = '%s:%s' % (route[0].code, entry[0]) 
                data = entry[2]().receive(byte_data, sysex)
                print key, data
                self._msgqueue.append( (key, data) )
                return

        print "No Route"

if __name__ == '__main__':

    FULL_MSG = [ 0xf0, 0x00, 0x10, 0x50, 0xf9, 0x00, 0x04, 0x10, 0x01, 0x00, 0x0c ]
    FULL_MSG.extend(TEST_BUSCONFIG1_RESP)
    FULL_MSG.append(0xf7)

    byte_data = ''.join([chr(x) for x in FULL_MSG])

    p1 = _sysex_prefix().receive(byte_data)
    p2 = _dlive_resp_busconfig1().receive(byte_data, p1)

    router = dLiveMessageRouter()
    router.process(byte_data)

