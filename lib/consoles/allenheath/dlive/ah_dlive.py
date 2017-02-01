# lib/consols/ah-dlive.py
#
# Console implementation for OSC Gateway
#
# Method Map for Input
#
#   3000 -> 307f 01 02 Ch 001..128 Fader
#   3080 -> 30ff 01 01 Ch 001..128 Main Out on/off
#   3100 -> 317f (unknown)
#   3180 -> 31ff 01 01 Ch 001..128 Mute
#   3200 -> 327f 01 01 Ch 001..128 Pan/Balance L/R 00..4a
#   3280 -> 32ff 01 01 Ch 001..128 Pan F/R 00..4a
#   3300 -> 34ff (unknown)
#   3500 -> 39ff 0A 01 Ch 001..128 PAFL control, 10 per channel @ 0x0a offsets
#   3a00 -> 59ff (unknown)
#   5a00 -> 79ff 40 01 Ch 001..128 Mix on/off for 64 mixes each
#   7a00 -> 99ff 40 01 Ch 001..128 Mix aux pre/post for 64 mixes each
#   9a00 -> d9ff (unknown)
#   da00 -> e9ff 20 01 Ch 001..128 DCA Assigns for 24 DCA's (offset 32)
#                          00..23 = DCA Assigns (1..24)
#                          24..31 = Mute Group Assigns (1..8)  
#   ea99 -> ffff (unknown)
#
# Method map for DCA
#   1000 -> 1017 01 02 DCA 01..24 Fader
#   1018 -> 101f 01 02 (unused - no fader on mute groups)
#   1020 -> 1037 01 01 DCA 01..24 Mute
#   1038 -> 103f 01 01 Mute Groups 1..8 Mute
#   1040 -> 112f 0a 01 DCA 01..24, PAFL for 10 PAFLs
#   1130 -> 117f 0a 01 Mute groups 1..8, PAFL for 10 PAFLs each
#   
# Method map for FX Returns (Current 16 Stereo, address space supports 48 stereo - extra 64 may be Dyn8)
#   1800 -> 181f? 02 02 Fader, 2 channels (L/R) per return
#   1860 -> 18bf? 02 01 Mute,  2 channels (L/R) per return
#   1940 ->       14 01 PAFL,  10 PAFL per channel, 2 channels

from __future__ import print_function

__all__ = ['ah_dLive']

import sys, time, socket

from .util import *
from .rpcproxy import *

# ... Need global exception definitions

class ah_dLive(object):
    
    def __init__(self, config = {}):

        self._config = config        

        self._open()

        # ... use static config since we aren't reading console config yet
        self._console_data = config['console_data']

        self._init_rpc()
        self._build_mixmap()
   
        self._range = dict(
            input           = 128, 
            dca             =  24, 
            mutegroup       =   8,
            fxreturn        =  16,
            fxsend          =  16,
            )

        # ... Build Targets
        self._target = target = {}
        for idx in range(0,self._range['input']):     target[ ('input', idx+1)] = dLive_Input(idx, self)
        for idx in range(0,self._range['dca']):       target[ ('dca', idx+1)] = dLive_DCA(idx, self)
        for idx in range(0,self._range['fxsend']):    target[ ('fxsend', idx+1)] = dLive_FXSend(idx, self)
        for idx in range(0,self._range['fxreturn']):  target[ ('fxreturn', idx+1)] = dLive_FXReturn(idx, self)
        for idx in range(0,self._range['mutegroup']): target[ ('mutegroup', idx+1)] = dLive_MuteGroup(idx, self)

        for k,v in self._mixmap.iteritems():
            if k[0] != '*':
                target[k] = dLive_Mix(k[0], k[1], self)

        self._data = []
        
    def _init_rpc(self):

        init_rpc_proxy(self, self._console_data['version_string'])

    def _build_mixmap(self):

        # ... FIXME: Need to add pan/balance/delay capabilities into build matrix

        # Order matters here - this is the order the DMxx assigns mix buses
        # Note some busses are burned in LRM/LCR modes
        build = [
            ( 'group_mono'      , 'group'       , 1, 0),
            ( 'group_stereo'    , 'stgroup'     , 2, 0),
            ( 'fx_mono'         , '*fx'         , 1, 0),   # In the mixmap, managed via different NRPN interface
            ( 'aux_mono'        , 'aux'         , 1, 0), 
            ( 'fx_stereo'       , '*stfx'       , 2, 0),   # In the mixmap, managed via different NRPN interface
            ( 'aux_stereo'      , 'staux'       , 2, 0),
            ( '*main'           , 'main'        , 0, 0),
            ( 'pafl'            , '*pafl'       , 2, 1),
            ( 'matrix_mono'     , 'matrix'      , 1, 0),
            ( 'matrix_stereo'   , 'stmatrix'    , 2, 0),
        ]

        config = self._console_data

        self._mixmap = mixmap = {}
        offset = 0x00
        for key, name, channels, minval in build:
            if key == '*main':
                main = config.get('main', 'lr').lower()
                mixmap[ ( 'main', 1) ] = (offset, 2)
                offset += 0x0002
                if main in ['lr']:
                    pass
                elif main in ['lrm']:
                    mixmap[ ( 'main', 2 ) ] = (offset, 1)
                    mixmap[ ( 'main', '*burn' ) ] = (offset + 0x0001, 1)
                    offset += 0x0002   # Burn odd mix
                elif main in ['lcm']:
                    mixmap[ ( 'main', 2 ) ] = (offset, 1)
                    mixmap[ ( 'main', '*burn' ) ] = (offset + 0x0001, 1)
                    offset += 0x0002   # Burn odd mix
                elif main in ['surround5.1']:
                    mixmap[ ( 'main', 2 ) ]   = (offset, 1)
                    mixmap[ ( 'main', 3 ) ] = (offset + 0x0001, 1)
                    mixmap[ ( 'main', 4 ) ] = (offset + 0x0002, 2)
                    offset += 0x0004
                else:
                    raise BadMode()
            else:
                count = max(config.get(key, minval), minval)
                for idx in range(0, count):
                    mixmap[ (name, idx+1) ] = (offset, channels)
                    offset += channels

        tosort = [ (v,k) for k,v in mixmap.iteritems()]
        tosort.sort()
        for p in tosort:
            print("0x%04x/%i = %s" % (p[0][0], p[0][1], p[1]))

    def _open(self):
    	print("ah_dlive._open()")
        target_ip = self._config.get('ip')
        target_port = self._config.get('port', 51321)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect( (target_ip, target_port) )
        self._socket.setblocking(0)

    def close(self):
        # ... send BYE
        print("ah_dLive._close()")

        self._send([ 0xe0, 0x00, 0x03, 0x42, 0x59, 0x45, 0xe7 ])   # BYE
        time.sleep(1.0)
        self._socket.close()

    def _send(self, data):
        print("Sending: %s" % str(data))
        data_str = ''.join([chr(ch) for ch in data])
        self._socket.send(data_str)
        
        # Dummy non-blocking receive
        try:
            self._socket.recv(4096) 
        except Exception, e:
            #print e
            pass

    def flush(self):
        
        while True:
            try:
                cmd = self._data.pop(0)
                self._send(cmd)
            except IndexError, e:
                break

    def queue_command(self, data):
        # ... Need to implement scheduled sends
        fmt_data = ' '.join('%02x' % i for i in data)
        print( "Queue data: [ %s ]" % (fmt_data))
        self._data.append(data)

    def get(self, target_type, target_index):
        return self._target[ (target_type, target_index) ]



class dLive_GenericTarget(object):
    pass


# =============================================================================
#
# Input Channel 
#
# =============================================================================

class dLive_Input(dLive_GenericTarget):

    _track_data_init = dict(
        fader = None,
        pafl  = None)

    def __init__(self, index, console):
        print('Creating: dLiveInput(%i)' % (index))
        self._index = index
        self._console = console
        self._track = dict(dLive_Input._track_data_init)

    def mute(self, state):
        print('dLive_Input(%i).mute(%s)' % (self._index, state))
        value = 1 if state else 0
        self._console.proxyInput.set(0x3180 + self._index, [value])

    def fader_abs(self, db):
        print('dLive_Input(%i).fader_abs(%s)' % (self._index, db))
        value = calc_db(db_abs=db, limit_lower=-128.0, limit_upper=10.0)[1]
        self._track['fader'] = value
        self._console.proxyInput.set(0x3000 + self._index, [value/256, value%256])

    # This is dangerous until we are fully tracking console state from other devices!
    def fader_rel(self, db):
        print('dLive_Input(%i).fader_rel(%s)' % (self._index, db))
        if self._track['fader'] != None:
            value = calc_db(linear=self._track['fader'], db_rel=db, limit_lower=-128.0, limit_upper=10.0)[1]
            self._track['fader'] = value
            self._console.proxyInput.set(0x3000 + self._index, [value/256, value%256])
        else:
            print("No tracking information!")

    def pan(self, position):
        """Set pan from -100 (L) to 0 (C) to +100 (R). Does not support relative change."""
        print('dLive_Input(%i).pan(%s)' % (self._index, position))

        value = 37  # Center (0x00 .. 0x4a range)

        if position < 0:
            value = value - (37 * min(-position, 100)) / 100
        elif position > 0:
            value = value + (37 * min(position, 100)) / 100

        self._console.proxyInput.set(0x3200 + self._index, [0x00, value])

    def dca_assign(self, dcas, exclusive=False):
        print('dLive_Input(%i).dca_assign(%s)' % (self._index, str(dcas)))

        method = 0xda00 + 0x20 * self._index

        for dca in dcas: # Add DCA's first
            # FIXME: Need to range check DCA #
            self._console.proxyInput.set(method + (dca-1), [0x01])

        if exclusive:        
            for dca in range(1,25):  # FIXME - This shouldn't be a static range
                if dca not in dcas:
                   self._console.proxyInput.set(method + (dca-1), [0x00])

    def dca_remove(self, dcas):
        print('dLive_Input(%i).dca_remove(%s)' % (self._index, str(dcas)))

        method = 0xda00 + 0x20 * self._index

        for dca in dcas: # Add DCA's first
            # FIXME: Need to range check DCA #
            self._console.proxyInput.set(method + (dca-1), [0x00])

    def mutegroup_assign(self, mutegroups, exclusive=False):
        print('dLive_Input(%i).mutegroup_assign(%s)' % (self._index, str(mutegroups)))

        method = 0xda18 + 0x20 * self._index

        for mg in mutegroups: # Add MuteGroup's first
            # FIXME: Need to range check Mute Group #
            self._console.proxyInput.set(method + (mg-1), [0x01])

        if exclusive:        
            for mg in range(1,9):  # FIXME - This shouldn't be a static range
                if mg not in mutegroups:
                   self._console.proxyInput.set(method + (mg-1), [0x00])

    def mutegroup_remove(self, mutegroups):
        print('dLive_Input(%i).mutegroup_remove(%s)' % (self._index, str(mutegroups)))

        method = 0xda18 + 0x20 * self._index

        for mg in mutegroups: # Add MuteGroup's first
            # FIXME: Need to range check Mute Group #
            self._console.proxyInput.set(method + (mg-1), [0x00])

    def inserta_bypass(self, state):
        print('dLive_Input(%i).inserta_bypass(%s)' % (self._index, str(state)))
        value = 0x01 if state else 0x00
        self._console.proxyInputProcessing.inserta(self._index, 0x1001, [value])

    def insertb_bypass(self, state):
        print('dLive_Input(%i).insertb_bypass(%s)' % (self._index, str(state)))
        value = 0x01 if state else 0x00
        self._console.proxyInputProcessing.insertb(self._index, 0x1001, [value])

    def delay(self, state=None, duration=None):
        print('dLive_Input(%i).delay(%s %s)' % (self._index, str(state), str(duration)))

        if state != None:
            value = 0x00 if state else 0x01
            self._console.proxyInputProcessing.delay(self._index, 0x1001, [value])

        if duration != None:
            delay = int(float(duration) * 0x60)   # 60h per ms   FIXME: Always rounds down
            self._console.proxyInputProcessing.delay(self._index, 0x1000, [delay/256, delay%256])

    def pafl(self, state, bus = None):
        print('dLive_Input(%i).pafl(%s %s)' % (self._index, str(state), str(bus)))

        # FIXME need to validate bus range
        bus = bus or (self._console._config.get('pafl', 1))

        method = 0x3500 + 0x0a * self._index + (bus-1)
        self._console.proxyInput.set(method, [0x01 if state else 0x00])

        self._track['pafl'] = bus if state else None


# =============================================================================
#
# FX Return 
#
# =============================================================================

class dLive_FXReturn(dLive_GenericTarget):

    _track_data_init = dict(
        fader = None,
        pafl  = None)

    def __init__(self, index, console):
        print('Creating: dLive_FXReturn(%i)' % (index))
        self._index = index
        self._console = console
        self._track = dict(dLive_FXReturn._track_data_init)

    def mute(self, state):
        print('dLive_FXReturn(%i).mute(%s)' % (self._index, state))
        value = 1 if state else 0
        self._console.proxyFXReturn.set(0x1860 + (self._index * 2), [value])

    def fader_abs(self, db):
        print('dLive_FXReturn(%i).fader_abs(%s)' % (self._index, db))
        value = calc_db(db_abs=db, limit_lower=-128.0, limit_upper=10.0)[1]
        self._track['fader'] = value
        self._console.proxyFXReturn.set(0x1800 + (self._index*2), [value/256, value%256])

    # This is dangerous until we are fully tracking console state from other devices!
    def fader_rel(self, db):
        print('dLive_FXReturn(%i).fader_rel(%s)' % (self._index, db))
        if self._track['fader'] != None:
            value = calc_db(linear=self._track['fader'], db_rel=db, limit_lower=-128.0, limit_upper=10.0)[1]
            self._track['fader'] = value
            self._console.proxyFXReturn.set(0x1800 + (self._index*2), [value/256, value%256])
        else:
            print("No tracking information!")

    def pan(self, position):
        """Set pan from -100 (L) to 0 (C) to +100 (R). Does not support relative change."""
        print('dLive_FXReturn(%i).pan(%s)' % (self._index, position))

        value = 37  # Center (0x00 .. 0x4a range)

        if position < 0:
            value = value - (37 * min(-position, 100)) / 100
        elif position > 0:
            value = value + (37 * min(position, 100)) / 100

        self._console.proxyFXReturn.set(0x1880 + self._index, [0x00, value])



# =============================================================================
#
# DCA
#
# =============================================================================

class dLive_DCA(dLive_GenericTarget):

    _track_data_init = dict(
        fader = None,
        pafl  = None)

    def __init__(self, index, console):
        print('Creating: dLive_DCA(%i)' % (index))
        self._index = index
        self._console = console
        self._track = dict(dLive_DCA._track_data_init)

    def mute(self, state):
        print('dLive_DCA(%i).mute(%s)' % (self._index, state))
        value = 1 if state else 0
        self._console.proxyDCA.set(0x1020 + self._index, [value])

    def fader_abs(self, db):
        print('dLive_DCA(%i).fader_abs(%s)' % (self._index, db))
        value = calc_db(db_abs=db, limit_lower=-128.0, limit_upper=10.0)[1]
        self._track['fader'] = value
        self._console.proxyDCA.set(0x1000 + self._index, [value/256, value%256])

    # This is dangerous until we are fully tracking console state from other devices!
    def fader_rel(self, db):
        print('dLive_DCA(%i).fader_rel(%s)' % (self._index, db))
        if self._track['fader'] != None:
            value = calc_db(linear=self._track['fader'], db_rel=db, limit_lower=-128.0, limit_upper=10.0)[1]
            self._track['fader'] = value
            self._console.proxyDCA.set(0x1000 + self._index, [value/256, value%256])
        else:
            print("No tracking information!")

    def pafl(self, state, bus = None):
        print('dLive_DCA(%i).pafl(%s %s)' % (self._index, str(state), str(bus)))

        # FIXME need to validate bus range
        bus = bus or (self._console._config.get('pafl', 1))

        method = 0x1040 + (0x0a * self._index) + (bus-1)
        self._console.proxyDCA.set(method, [0x01 if state else 0x00])

        self._track['pafl'] = bus if state else None


# =============================================================================
#
# FX Send 
#
# =============================================================================

class dLive_FXSend(dLive_GenericTarget):

    _track_data_init = dict(
        fader = None,
        pafl  = None)

    def __init__(self, index, console):
        print('Creating: dLive_FXSend(%i)' % (index))
        self._index = index
        self._console = console
        self._track = dict(dLive_FXSend._track_data_init)

    def mute(self, state):
        print('dLive_FXSend(%i).mute(%s)' % (self._index, state))
        value = 1 if state else 0
        self._console.proxyFXSend.set(0x1010 + self._index, [value])

    def fader_abs(self, db):
        print('dLive_FXSend(%i).fader_abs(%s)' % (self._index, db))
        value = calc_db(db_abs=db, limit_lower=-128.0, limit_upper=10.0)[1]
        self._track['fader'] = value
        self._console.proxyFXSend.set(0x1000 + self._index, [value/256, value%256])

    # This is dangerous until we are fully tracking console state from other devices!
    def fader_rel(self, db):
        print('dLive_FXSend(%i).fader_rel(%s)' % (self._index, db))
        if self._track['fader'] != None:
            value = calc_db(linear=self._track['fader'], db_rel=db, limit_lower=-128.0, limit_upper=10.0)[1]
            self._track['fader'] = value
            self._console.proxyFXSend.set(0x1000 + self._index, [value/256, value%256])
        else:
            print("No tracking information!")



# =============================================================================
#
# Mix 
#
# =============================================================================

class dLive_Mix(dLive_GenericTarget):

    _track_data_init = dict(
        fader = None,
        pafl  = None)

    def __init__(self, key, index, console):
        print('Creating: dLive_Mix(%i %s)' % (index, key))
        self._index = index
        self._key   = key
        self._console = console
        self._mixid, self._channels = console._mixmap[ (key, index) ]
        self._track = dict(dLive_Mix._track_data_init)
        print('--> Actual mix %i ch %i' % (self._mixid, self._channels))

    def mute(self, state):
        print('dLive_Mix(%s %i).mute(%s)' % (self._key, self._index, state))
        value = 1 if state else 0
        self._console.proxyMix.set(0x2040 + self._mixid, [value])

    def fader_abs(self, db):
        print('dLive_Mix(%s %i).fader_abs(%s)' % (self._key, self._index, db))
        value = calc_db(db_abs=db, limit_lower=-128.0, limit_upper=10.0)[1]
        self._track['fader'] = value
        self._console.proxyMix.set(0x2000 + self._mixid, [value/256, value%256])

    # This is dangerous until we are fully tracking console state from other devices!
    def fader_rel(self, db):
        print('dLive_Mix(%s %i).fader_rel(%s)' % (self._key, self._index, db))
        if self._track['fader'] != None:
            value = calc_db(linear=self._track['fader'], db_rel=db, limit_lower=-128.0, limit_upper=10.0)[1]
            self._track['fader'] = value
            self._console.proxyMix.set(0x2000 + self._mixid, [value/256, value%256])
        else:
            print("No tracking information!")


# =============================================================================
#
# Mute Group 
#
# =============================================================================

class dLive_MuteGroup(dLive_GenericTarget):

    _track_data_init = dict(
        fader = None,
        pafl  = None)

    def __init__(self, index, console):
        print('Creating: dLive_MuteGroup(%i)' % (index))
        self._index = index
        self._console = console
        self._track = dict(dLive_MuteGroup._track_data_init)

    def mute(self, state):
        print('dLive_MuteGroup(%i).mute(%s)' % (self._index, state))
        value = 1 if state else 0
        self._console.proxyDCA.set(0x1038 + self._index, [value])


