#!/usr/bin/python
#
#

import sys, time, socket, traceback
import yaml

from lib.consoles.allenheath.dlive.ah_dlive import *
from lib.consoles.allenheath.dlive.util import *            # TEMPORARY - calc_db

VERSION = "0.20"
COPYRIGHT = "(c) 2016, 2017, 2ImagineIt Productions, LLC"

class BadUri(Exception):
    def __init__(self, uri, msg = ''):
        print "BadURI %s %s" % (uri, msg)
        self._uri = uri
        self._msg = msg

class DataObject(object): pass
        
# ---------------------------------------------------------------------------------------

class UDP_Gateway(object):
    
    def __init__(self, config, console):

        self._config = config
        self._console = console

        # FIXME: Console needs to provide a mapping of what it has to Gateway implementation

        self._route = {}
        self._route['input']                = UDP_Input(console)
        self._route['dca']                  = UDP_DCA(console)
        self._route['fxret']                = UDP_FXReturn(console)
        self._route['fxsend']               = UDP_FXSend(console)
        self._route['group']                = UDP_Mix(console, 'group')
        self._route['stgroup']              = UDP_Mix(console, 'stgroup')
        self._route['aux']                  = UDP_Mix(console, 'aux')
        self._route['staux']                = UDP_Mix(console, 'staux')
        self._route['main']                 = UDP_Mix(console, 'main')
        self._route['matrix']               = UDP_Mix(console, 'matrix')
        self._route['stmatrix']             = UDP_Mix(console, 'stmatrix')
        self._route['mutegroup']            = UDP_MuteGroup(console)

        print self._route

        self._open()


    def _open(self):
        # ... this needs to be GATEWAY open
        pass

    def close(self):
        # ... this needs to be GATEWAY close
        pass

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
            print traceback.format_exc()


class UDP_GenericDevice(object):
    
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

    
# =============================================================================
#
# Input Channel
#
# =============================================================================

class UDP_Input(UDP_GenericDevice):
    """Input Channel Control
       Implements:
          mute, fader, balance/pan
          dca exclusive assign
          mute group exclusive assign
          inserta bypass, insertb bypass
          Delay (enable, duration)
       Needs:
          front/back pan
          main controls (send mute, lfe)
          mix sends (mfx, stfx, maux, staux, msubgroup, stsubgroup
          PEQ
          Filter (HPF, LPF)
          Trim control
          HA (gain, 48V, model)
          Comp + models
          Gate + models
          PAFL
          Source input patch
    """
    
    def __init__(self, console):
        self._console = console
 
    def mute(self, channel, data, **kw):
        """Enable or disable channel mute"""
        self._console.get('input', channel).mute(True if data[0] == '1' else False)

    def fader(self, channel, data, **kw):
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('input', channel).fader_abs(float(data[0]))

    def xfader_rel(self, channel, data, **kw):  # TEST
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('input', channel).fader_rel(float(data[0]))

    def balance(self, channel, data, **kw):
        self.pan(channel, data, **kw)
        
    def pan(self, channel, data, **kw):
        """Set pan from L100 to C to R100. Does not support relative change."""
        cmd = data[0].lower()
        if cmd[0] in ['l', 'c', 'r']:
            value = 0  # Center
            if cmd[0] == 'l':
                value = -int(cmd[1:])
            elif cmd[0] == 'r':
                value = int(cmd[1:])
            self._console.get('input', channel).pan(value)
        else:
            print "Bad value: ", cmd

    def dca(self, channel, data, **kw):
        """Assign a channel to DCA's (and unassign from others)
           /input/{channel}/dca=[exclusive list of DCA's]
        """
        self._console.get('input', channel).dca_assign([int(i) for i in data], exclusive=True)

    def mutegroup(self, channel, data, **kw):
        """Assign a channel to mute groups (and unassign from others)"""
        self._console.get('input', channel).mutegroup_assign([int(i) for i in data], exclusive=True)

    def inserta(self, channel, data, **kw):
        """Enable or bypass Insert A"""
        self._console.get('input', channel).inserta_bypass(False if data[0] == '1' else True)

    def insertb(self, channel, data, **kw):
        """Enable or bypass Insert B"""
        self._console.get('input', channel).insertb_bypass(False if data[0] == '1' else True)

    def delay(self, channel, data, **kw):
        """ Set delay
            /input/{}/delay=[0|1, ms]
        """
        enable = True if data[0] == '1' else False
        duration = None

        if len(data) == 2:
            duration = float(data[1])

        self._console.get('input', channel).delay(enable, duration)

    def pafl(self, channel, data, **kw):
        """ Enable PAFL
            /input/{}/pafl=0|1[,PAFL Bus]
        """
        enable = True if data[0] == '1' else False
        bus = None

        if len(data) == 2:
            bus = int(data[1])

        self._console.get('input', channel).pafl(enable, bus)

# =============================================================================
#
# FX Return Channel 
#
# =============================================================================

class UDP_FXReturn(UDP_GenericDevice):
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
        """Enable or disable channel mute"""
        self._console.get('fxreturn', channel).mute(True if data[0] == '1' else False)

    def fader(self, channel, data, **kw):
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('fxreturn', channel).fader_abs(float(data[0]))

    def xfader_rel(self, channel, data, **kw):  # TEST
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('fxreturn', channel).fader_rel(float(data[0]))

    def balance(self, channel, data, **kw):
        self.pan(channel, data, **kw)

    def pan(self, channel, data, **kw):
        """Set pan from L100 to C to R100. Does not support relative change."""
        cmd = data[0].lower()
        if cmd[0] in ['l', 'c', 'r']:
            value = 0  # Center
            if cmd[0] == 'l':
                value = -int(cmd[1:])
            elif cmd[0] == 'r':
                value = int(cmd[1:])
            self._console.get('fxreturn', channel).pan(value)
        else:
            print "Bad value: ", cmd

# =============================================================================
#
# DCA Channel 
#
# =============================================================================

class UDP_DCA(UDP_GenericDevice):
    """ Implement NRPN Channel Control"""
    
    def __init__(self, console):
        self._console = console
        
    def mute(self, channel, data, **kw):
        """Enable or disable channel mute"""
        self._console.get('dca', channel).mute(True if data[0] == '1' else False)

    def fader(self, channel, data, **kw):
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('dca', channel).fader_abs(float(data[0]))

    def xfader_rel(self, channel, data, **kw):  # TEST
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('dca', channel).fader_rel(float(data[0]))

    def pafl(self, channel, data, **kw):
        """ Enable PAFL
            /dca/{}/pafl=0|1[,PAFL Bus]
        """
        enable = True if data[0] == '1' else False
        bus = None

        if len(data) == 2:
            bus = int(data[1])

        self._console.get('dca', channel).pafl(enable, bus)

    def assign(self, dca, data, **kw):
        """Non-exclsive assignment of DCA's
           /dca/X/assign/input/[X] = 1|0
        """

        uri = kw['uri']
        dca = self._check_range('dca', dca)
        value = 0x01 if data[0] == '1' else 0x00

        if uri[3] == 'input':
            channel = int(uri[4])
            if value:
                self._console.get('input', channel).dca_assign([dca])
            else:
                self._console.get('input', channel).dca_remove([dca])
        else:
            raise BadUri('/dca/{}/assign/* only support input currently')

# =============================================================================
#
# FX Send Channel 
#
# =============================================================================

class UDP_FXSend(UDP_GenericDevice):

    def __init__(self, console):
        self._console = console

    def mute(self, channel, data, **kw):
        """Enable or disable channel mute"""
        self._console.get('fxsend', channel).mute(True if data[0] == '1' else False)

    def fader(self, channel, data, **kw):
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('fxsend', channel).fader_abs(float(data[0]))

    def xfader_rel(self, channel, data, **kw):  # TEST
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get('fxsend', channel).fader_rel(float(data[0]))


# =============================================================================
#
# Mix (Group, Aux, Main, Matrix) 
#
# =============================================================================

class UDP_Mix(UDP_GenericDevice):

    def __init__(self, console, device):
        self._console = console
        self._device  = device

    def mute(self, channel, data, **kw):
        """Enable or disable channel mute"""
        self._console.get(self._device, channel).mute(True if data[0] == '1' else False)

    def fader(self, channel, data, **kw):
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get(self._device, channel).fader_abs(float(data[0]))

    def xfader_rel(self, channel, data, **kw):  # TEST
        """Set fader level.  Currently does NOT support db or relative"""
        self._console.get(self._device, channel).fader_rel(float(data[0]))

    # pan/balance depending on type
    # delay depending on type

# =============================================================================
#
# Mute Group
#
# =============================================================================

class UDP_MuteGroup(UDP_GenericDevice):
    """ Implement NRPN Channel Control
        
        Note: Assignment are handled via channel types since MuteGroups span
        input, main, mix, fx and others.

    """
    
    def __init__(self, console):
        self._console = console
        
    def mute(self, channel, data, **kw):
        """Enable or disable channel mute"""
        self._console.get('mutegroup', channel).mute(True if data[0] == '1' else False)
          

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
        print "%s %s" % (VERSION, COPYRIGHT)
    
        # --- Parse command line options
        options = DataObject()
        options.config = 'config.yaml'
    
        # --- Load Configuration
        print "Loading Configuration"
        config = yaml.load(open(options.config, 'r'))
                
        print "Load Tag data"
        self._parser = URIExpander()
        self._parser.loadtags(config.get('tags', []))

        self._gateway = None
        self._console = None

        try:

            print "Creating Console"
            self._console = ah_dLive(config['console'])
        
            print "Creating UDP Gateway"
            self._gateway = UDP_Gateway(config['gateway'], self._console)

            if True:
                self.ListenMode()
            else:
                self.TestMode()

        except KeyboardInterrupt, e:
            pass

        finally:

            if self._gateway:
                self._gateway.close()

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
                self._gateway.handle_message(path, data)

        self._gateway.flush()

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
                        self._gateway.handle_message(path, data)
                except Exception, e:
                    print traceback.format_exc()
                    
            self._console.flush()
        
if __name__ == '__main__':
    Application().run()

