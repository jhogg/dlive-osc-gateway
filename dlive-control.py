#!/usr/bin/python
#
# AHNet dLive test Interface
#
#
# Namespace Map for Sysex/NRPN
#
# f0 0001 001b 001a (Input Channels)
#
#   3000 -> 307f 01 02 Ch 001..128 Fader
#   3080 -> 30ff 01 01 Ch 001..128 Main Out on/off
#   3100 -> 31ff (unknown)
#   3180 -> 31ff 01 01 Ch 001..128 Mute
#   3200 -> 327f 01 01 Ch 001..128 Pan/Balance L/R 00..4a
#   3280 -> 32ff 01 01 Ch 001..128 Pan F/R 00..4a
#   (missing)
#   3d00 -> ???? PAFL control @ 0x0a offsets
#   5a00 -> 79ff 40 01 Ch 001..128 Mix on/off for 64 mixes each
#   7a00 -> 99ff 40 01 Ch 001..128 Mix aux pre/post for 63 mixes each
#   (missing)
#   da00 -> e9ff 20 01 Ch 001..128 DCA Assigns for 24 DCA's (offset 32)
#                          00..23 = DCA Assigns (1..24)
#                          24..31 = Mute Group Assigns (1..8)  
#

import sys, time, socket
import yaml

class BadUri(Exception):
    def __init__(self, uri, msg = ''):
        print "BadURI %s %s" % (uri, msg)
        self._uri = uri
        self._msg = msg

class DataObject(object): pass
        
# ---------------------------------------------------------------------------------------

class dLive_Console(object):
    
    def __init__(self, config = {}):

        self._config = config        
        self._route = {}
        self._route['input']                = dLive_Input(self)
        #self._route['input/*/rawmix']      = dLive_InputMix(self)
        self._route['dca']                  = dLive_DCA(self)
        self._route['fxret']                = dLive_FXReturn(self)
        self._route['fxsend']               = dLive_FXSend(self)
        self._route['group']                = dLive_Mix(self, 'group')
        self._route['stgroup']              = dLive_Mix(self, 'stgroup')
        self._route['aux']                  = dLive_Mix(self, 'aux')
        self._route['staux']                = dLive_Mix(self, 'staux')
        self._route['main']                 = dLive_Mix(self, 'main')
        self._route['matrix']               = dLive_Mix(self, 'matrix')
        self._route['stmatrix']             = dLive_Mix(self, 'stmatrix')
        self._route['mutegroup']            = dLive_MuteGroup(self)

        #self._route['mix']     = LS9_Mix(self)
        #self._route['matrix']  = LS9_Matrix(self)
    
        print self._route

        self._data = []
    
        self._build_mixmap()

        self._range = dict(
            input           = 128, 
            dca             =  24, 
            mutegroup       =   8,
            fxreturn        =  16,
            fxsend          =  16,
            )

        self._open()

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
            ( '*main'           , '*main'       , 0, 0),
            ( 'pafl'            , '*pafl'       , 2, 1),
            ( 'matrix_mono'     , 'matrix'      , 1, 0),
            ( 'matrix_stereo'   , 'stmatrix'    , 2, 0),
        ]

        config = self._config

        self._mixmap = mixmap = {}
        offset = 0x00
        for key, name, channels, minval in build:
            if key == '*main':
                main = config.get('main', 'lr').lower()
                print main
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
            print "0x%04x/%i = %s" % (p[0][0], p[0][1], p[1])

    def _open(self):
        target_ip = self._config.get('ip')
        target_port = self._config.get('port', 51321)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect( (target_ip, target_port) )
        self._socket.setblocking(0)

    def close(self):
        # ... send BYE
        print "dLive_Console.close()"

        self._send([ 0xe0, 0x00, 0x03, 0x42, 0x59, 0x45, 0xe7 ])   # BYE
        time.sleep(1.0)
        self._socket.close()

    def _send(self, data):
        print "Sending: ", data
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
        print "Queue data: [ %s ]" % (fmt_data)
        self._data.append(data)
    
    def handle_message(self, uri, data = None):
        
        uri_text = '/' + '/'.join(uri)

        try:
            if len(uri) < 3:
                raise BadUri(uri_text, 'Too short')
            
            if not uri[0] in self._route:
                raise BadUri(uri_text, 'Unknown route %s' % uri[0])
            
            idx = int(uri[1])
            fn = self._route[uri[0]].__getattribute__(uri[2])
            
            if fn:
                fn(idx, data, uri=uri)
            else:
                raise BadUri(uri_text, 'Unknown Method %s' % uri[2])

        except Exception, e:
            print e

class dLive_GenericDevice(object):
    
    def _check_index(self, idx):
        if (idx < 1) or (idx > self._max_index):
            raise IndexOutOfRange()
    
    def _check_range(self, klass, idx):
        idx = int(idx)
        if idx < 1: raise IndexOutOfRange()
        if idx > self._console._range[klass]: raise IndexOutOfRange()
        return idx
  
    def sysex_send(self, deviceid, addr1, addr2, addr3, data = []):
        # FIXME: This needs to be sysex/f7 safe - REVIEW

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
 
        fmt_data = ' '.join('%02x' % i for i in sysex)
        print "sysex [ %s ]" % (fmt_data)
  
        return sysex

    def calc_db(self, **kw):
        """ Convert db to linear based on straight line calcs
           -oo = 0
        -128db = 1
           0db = 0x8000
        """

        factor = (128.0 / 0x8000)

        # --- Starting Point

        if 'linear' in kw:
            linear = kw.get('linear')
            if linear != None:
                if linear == 0:
                    db = None
                else:
                    db = (linear * factor) - 128.0
        else:
            db = kw.get('db_abs', None)

        print "Starting db", db

        # --- Handle relative adjustment
        if 'db_rel' in kw:
            db_rel = kw.get('db_rel')
            if (db == None):
                db = -128.0
            db += db_rel

        print "After rel", db

        # --- Enforce Limits

        if 'limit_lower' in kw:
            value = kw.get('limit_lower')
            db = max([-129.0, value, db])

        if 'limit_upper' in kw:
            value = kw.get('limit_upper')
            db = min([10.0, value, db])

        # --- Convert db back to linear

        if db < -128.0:
            linear = None
        else:
            linear = int((db + 128.0) / factor)

        return (db, linear)

class dLive_Input(dLive_GenericDevice):
    """Input Channel Control
       Implements:
          mute, fader, balance/pan
          dca exclusive assign
          mute group exclusive assign
          inserta bypass, insertb bypass
          Delay (enable, duration)
       Needs:
          front/back
          main controls (send mute, lfe)
          mix sends (mfx, stfx, maux, staux, msubgroup, stsubgroup
          PEQ
          Filter (HPF, LPF)
          Trim control
          HA (gain, 48V, model)
          Comp + models
          Gate 
          PAFL
          Source input patch
    """
    
    def __init__(self, console):
        self._console = console
        
    def mute(self, channel, data, **kw):
        """Enable or disable channel mute"""
        self._check_range('input', channel)
        value = 0x01 if data[0] == '1' else 0x00
        self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, 0x3180 + channel-1, [value]))

    # fader - need to sort out log scale for console
    def fader(self, channel, data, **kw):
        """Set fader level.  Currently does NOT support db or relative"""
        self._check_range('input', channel)
        value = self.calc_db(db_abs=float(data[0]), limit_lower=-128.0, limit_upper=10.0)
        self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, 0x3000 + channel-1, [value/256, value%256]))


    def balance(self, channel, data, **kw):
        self.pan(channel, data, **kw)
        
    def pan(self, channel, data, **kw):
        """Set pan from L100 to C to R100. Does not support relative change."""
        self._check_range('input', channel)
        cmd = data[0].lower()
        if cmd[0] in ['l', 'c', 'r']:
            value = 37  # Center
            if cmd[0] == 'l':
                value = value - (37 * min(int(cmd[1:]), 100)) / 100
            elif cmd[0] == 'r':
                value = value + (37 * min(int(cmd[1:]), 100)) / 100
            self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, 0x3200 + channel-1, [0x00, value]))
        else:
            print "Bad value: ", cmd

    def dca(self, channel, data, **kw):
        """Assign a channel to DCA's (and unassign from others)
           /input/{channel}/dca=[exclusive list of DCA's]
        """
        self._check_range('input', channel)
        addr3 = 0xda00 + 0x20 * (channel-1)
        dcas = [int(i) for i in data]
        for dca in dcas: # Add DCA's first
            self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, addr3 + (dca-1), [0x01]))
        for dca in range(1,25):
            if dca not in dcas:
               self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, addr3 + (dca-1), [0x00]))

    def mutegroup(self, channel, data, **kw):
        """Assign a channel to mute groups (and unassign from others)"""
        self._check_range('input', channel)
        addr3 = 0xda18 + 0x20 * (channel-1)
        mutegroups = [int(i) for i in data]
        for idx in mutegroups: # Add MG's first
            self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, addr3 + (idx-1), [0x01]))
        for idx in range(1,9):
            if idx not in mutegroups:
               self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, addr3 + (idx-1), [0x00]))

    def inserta(self, channel, data, **kw):
        """Enable or bypass Insert A"""
        self._check_range('input', channel)
        value = 0x00 if data[0] == '1' else 0x01
        addr1 = 0x010c + (0x10 * (channel-1))
        self._console.queue_command(self.sysex_send(0x0001, addr1, addr1-1, 0x1001, [value]))

    def insertb(self, channel, data, **kw):
        """Enable or bypass Insert B"""
        self._check_range('input', channel)
        value = 0x00 if data[0] == '1' else 0x01
        addr1 = 0x010d + (0x10 * (channel-1))
        self._console.queue_command(self.sysex_send(0x0001, addr1, addr1-1, 0x1001, [value]))

    def delay(self, channel, data, **kw):
        """ Set delay
            /input/{}/delay=[0|1, ms]
        """
        self._check_range('input', channel)
        addr1 = 0x0111 + 0x10 * (channel-1)
        enable = 0x00 if data[0] == '1' else 0x01
        self._console.queue_command(self.sysex_send(0x0002, addr1, addr1-1, 0x1001, [enable]))

        if len(data) == 2:
            delay = int(float(data[1]) * 0x60)   # 60h per ms   FIXME: Always rounds down
            self._console.queue_command(self.sysex_send(0x0002, addr1, addr1-1, 0x1000, [delay/256, delay%256]))


class dLive_FXReturn(dLive_GenericDevice):
    """FX Return Channel Control - Inputs with less capabilities
       Implements:
          mute, fader, balance/pan
       Needs:
          front/back
          main controls (send mute, lfe)
          mix sends (mfx, stfx, maux, staux, msubgroup, stsubgroup
          PEQ
          PAFL
    """
    
    def __init__(self, console):
        self._console = console
        
    def mute(self, channel, data, **kw):
        self._check_range('fxreturn', channel)
        value = 0x01 if data[0] == '1' else 0x00
        self._console.queue_command(self.sysex_send(0x0002, 0x001c, 0x001b, 0x1860 + (channel-1)*2, [value]))

    # fader - need to sort out log scale for console
    # data = abs[[,rel],upper limit]

    def fader(self, channel, data, **kw):
        self._check_range('fxreturn', channel)
        value = self.calc_db(db_abs=float(data[0]), limit_lower=-128.0, limit_upper=10.0)
        self._console.queue_command(self.sysex_send(0x0002, 0x001c, 0x001b, 0x1800 + (channel-1)*2, [value/256, value%256]))
 
    def balance(self, channel, data, **kw):
        self.pan(channel, data, **kw)

    def pan(self, channel, data, **kw):
        """Set pan from L100 to C to R100. Does not support relative change."""
        self._check_range('fxreturn', channel)
        cmd = data[0].lower()
        if cmd[0] in ['l', 'c', 'r']:
            value = 37  # Center
            if cmd[0] == 'l':
                value = value - (37 * min(int(cmd[1:]), 100)) / 100
            elif cmd[0] == 'r':
                value = value + (37 * min(int(cmd[1:]), 100)) / 100
            self._console.queue_command(self.sysex_send(0x0002, 0x001c, 0x001b, 0x1880 + (channel-1)*2, [0x00, value]))
        else:
            print "Bad value: ", cmd

class dLive_DCA(dLive_GenericDevice):
    """ Implement NRPN Channel Control"""
    
    def __init__(self, console):
        self._console = console
        
    def mute(self, dca, data, **kw):
        self._check_range('dca', dca)
        value = 0x01 if data[0] == '1' else 0x00
        self._console.queue_command(self.sysex_send(0x0001, 0x0019, 0x0018, 0x1020 + dca-1, [value]))

    # fader - need to sort out log scale for console
    def fader(self, dca, data, **kw):
        self._check_range('dca', dca)
        value = self.calc_db(db_abs=float(data[0]), limit_lower=-128.0, limit_upper=10.0)
        self._console.queue_command(self.sysex_send(0x0001, 0x0019, 0x0018, 0x1000 + dca-1, [value/256, value%256]))
 
    def assign(self, dca, data, **kw):
        """Non-exclsive assignment of DCA's
           /dca/X/assign/input/[X] = 1|0
        """

        uri = kw['uri']
        dca = self._check_range('dca', dca)
        value = 0x01 if data[0] == '1' else 0x00

        if uri[3] == 'input':
            input = self._check_range('input', uri[4])
            addr3 = 0xda00 + 0x20 * (input-1)
            self._console.queue_command(self.sysex_send(0x0001, 0x001b, 0x001a, addr3 + (dca-1), [value]))
        else:
            raise BadUri('/dca/{}/assign/* only support input currently')

class dLive_FXSend(dLive_GenericDevice):

    def __init__(self, console):
        self._console = console

    def mute(self, channel, data, **kw):
        self._check_range('fxsend', channel)
        value = 0x01 if data[0] == '1' else 0x00
        self._console.queue_command(self.sysex_send(0x0002, 0x001d, 0x001c, 0x1010 + channel-1, [value]))

    # fader - need to sort out log scale for console
    def fader(self, channel, data, **kw):
        self._check_range('fxsend', channel)
        value = self.calc_db(db_abs=float(data[0]), limit_lower=-128.0, limit_upper=10.0)
        self._console.queue_command(self.sysex_send(0x0002, 0x001d, 0x001c, 0x1000 + channel-1, [value/256, value%256]))
 
class dLive_Mix(dLive_GenericDevice):

    def __init__(self, console, device):
        self._console = console
        self._device  = device

    def mute(self, channel, data, **kw):
        offset, channelct = self._console._mixmap[ (self._device, channel) ]
        value = 0x01 if data[0] == '1' else 0x00
        self._console.queue_command(self.sysex_send(0x0002, 0x001e, 0x001d, 0x2040 + offset, [value]))

    # fader - need to sort out log scale for console
    def fader(self, channel, data, **kw):
        offset, channelct = self._console._mixmap[ (self._device, channel) ]
        value = self.calc_db(db_abs=float(data[0]), limit_lower=-128.0, limit_upper=10.0)
        self._console.queue_command(self.sysex_send(0x0002, 0x001e, 0x001d, 0x2000 + offset, [value/256, value%256]))

    # pan/balance depending on type
    # delay depending on type

class dLive_MuteGroup(dLive_GenericDevice):
    """ Implement NRPN Channel Control
        
        Note: Assignment are handled via channel types since MuteGroups span
        input, main, mix, fx and others.

    """
    
    def __init__(self, console):
        self._console = console
        
    def mute(self, channel, data):
        self._check_range('mutegroup', channel)
        value = 0x01 if data[0] == '1' else 0x00
        self._console.queue_command(self.sysex_send(0x0001, 0x0019, 0x0018, 0x1038 + channel-1, [value]))
            

# ---------------------------------------------------------------------------------------

class URIExpander(object):
	
    def __init__(self):
        self._tags = {}

    def loadtags(self, taglist):
        for td in taglist:
            klass = td.get('class', None)
            index = td.get('index', None)
            name = td.get('name', None)
            tags = td.get('tags', [])
            
            if not klass or not index:
                print 'Bad tag data: %s' % str(td)
                continue
                
            if name:
                tags.append('name:%s' % name)
            
            for tag in tags:
                tag = tag.replace(' ', '_').lower()
                key = (klass.lower(),tag)
                if not key in self._tags:  self._tags[key] = set()
                self._tags[key].update([index])
                    
        for k,v in self._tags.iteritems():  print k,v
        
    def parse(self, uri, tags = {}):
		
        final = []
        self._result = []
    
        uri_str, data_str = uri.split('=', 1)
        
        if data_str:
            data = data_str.split(',')
        else:
            data = []

    	print "Data = ", data

        for idx,part in enumerate(uri_str.split('/')):
			
            if idx == 0 and len(part) == 0:		# Skip initial blank
                continue
			
            if len(final) == 0:					# We never expand first entry
                final.append([part])
                continue
			
            if part[0] == '[' and part[-1] ==']':
                final.append(self._expand_tags(final[0][0], part))
            elif ('-' in part) or (',' in part):
                final.append(self._expand_value(part))
            else:
                final.append([part])
		
        print final
		
        self._flatten_iter(final, [])
        return (data, self._result)
	
    def _expand_tags(self, root, args):
        result_incl = set()
        result_excl = set()
        for tag in args[1:-1].split(','):
            t = result_excl if tag[0] == '!' else result_incl
            key = (root.lower(), tag.replace(' ','_').replace('!','').lower())
            print key
            if key in self._tags:
                t.update(self._tags[key])
            else:
                raise BadUri('', 'Unknown tag/class: %s' % str(key))    
        result_incl.difference_update(result_excl)
        return sorted(result_incl)
        
    def _expand_value(self, args):
		result_incl = set()
		result_excl = set()
		for part in args.split(','):
			t = result_excl if part[0] == '!' else result_incl
			x = part.replace('!','').split('-')
			t.update(range(int(x[0]), int(x[-1])+1))
		result_incl.difference_update(result_excl)
		return sorted(result_incl)
	
    def _flatten_iter(self, final, partial=[]):
		parts = final[0]
		for p in parts:
			partial_next = list(partial)
			partial_next.append(str(p))
			if len (final) > 1:
				self._flatten_iter(final[1:], partial_next)
			else:
				self._result.append(partial_next)

# ---------------------------------------------------------------------------------------

class Application(object):
    
    def __init__(self):
        pass
        
    def run(self):

        print "dLive OSC Gateway"
        print "v 0.10  (c) 2016, Jay Hogg\n"
    
        # --- Parse command line options
        options = DataObject()
        options.config = 'config.yaml'
    
        # --- Load Configuration
        print "Loading Configuration"
        config = yaml.load(open(options.config, 'r'))
                
        print "Load Tag data"
        self._parser = URIExpander()
        self._parser.loadtags(config.get('tags', []))

        self._console = None

        try:

            print "Creating Console"
            self._console = dLive_Console(config['console'])
        
            if True:
                self.ListenMode()
            else:
                self.TestMode()

        except KeyboardInterrupt, e:
            pass

        finally:

            if self._console:
                self._console.close()

        print "Exiting"

    def TestMode(self):

        print "Running in TEST mode"
        
        test = [
    #        '/channel/12/mute',
            '/channel/1-4,120/mute=0',
            '/dca/1-8/mute=1',
    #       '/channel/40-42/dca/4,5/unassign'
    #       '/channel/35/unmute',
    #       '/channel/1-18,22,31-42/unmute',
    #       '/channel/1-18,22,31-42,!35,!12-14/unmute',
        ]
    
        for uri in test:
            print 'Test URI ', uri
            data, paths = self._parser.parse(uri)
            for path in paths:
                print data, path
                self._console.handle_message(path, data)

        self._console.flush()

    def ListenMode(self):
    
        print "Running in LISTEN mode"

        listen_addr = ('localhost', 55000)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(listen_addr)

        while True:
            data, address = sock.recvfrom(4096)
            print data
            sys.stdout.flush()
    
            for uri in data.split('|'):
                try:
                    data, paths = self._parser.parse(uri)
                    for path in paths:
                        print data, path
                        self._console.handle_message(path, data)
                except Exception, e:
                    print e
                    
            self._console.flush()

    def update_console(self):
        for mc in self._console._midi:
            #print mc
            self._md.write_short(mc[0], mc[1], mc[2])
            time.sleep(0.005)
        self._console._midi = []    # FIXME
        
if __name__ == '__main__':
    Application().run()

