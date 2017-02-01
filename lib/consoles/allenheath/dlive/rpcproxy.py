# rpcproxy.py - A&H RPC Proxies
#
#
# General RPC Mapping groups (addr1)
#
#  Target               1.30        1.40
#  MixRack Config*                  0001
#
#  Name/Color Input	 				000d
#  Name/Color M Grp 				000e
#  Name/Color St Grp 				000f
#  Name/Color M Aux					0010
#  Name/Color St Aux				0011
#  Name/Color M FX S 				0012
#  Name/Color St FX S 				0013
#  Name/Color Main 					0014
#  Name/Color M Matrix 				0015
#  Name/Color St Matrix 			0016
#  Name/Color FX Return 			0017
#  Name/Color DCA 					0018
#  Name/Color Wedge/IEM 			0019
#  (unknown)						001a
# +DCA/Mute             0019		001b
#  Ganging              001a        001c
# +Input                001b        001d
# +FX Return            001c 		001e
# +FX Send              001d        001f
# +Mix                  001e        0020
#  PAFL Talkback dim				0021
#									0022
#									0023
#  Signal Generator					0024
#									0025
#									0026
#  Talkback HPF						0027
#  									0028
#  FX (16)							0029-0038
#  Input Source Select              0039 			* Also talkback assign
#									003a
#									003b
#  Dyn8 (64)            n/a         003c-007b
#  Mixrack Sock In (64)             007c-00bb
#
#  (90 undefined)
#
#  Input Processing (2048 addresses from 0145 to 0944)
#    Base (Blocks/16)   0102        0145
#	 Input Model					  00  ** This is probably the start of the block
#	 Input Width/Mode				  01
#	 Input Trim/Pol					  02
#    Input/HPF                        03
# 	 Input/LPF						  04
#	 Input/Gate Filter				  05
#	 Input/Gate						  06
#	 Input/PEQ						  07
#	 Input/Comp						  08
#    Input/Direct Out				  09
#   +Input/Insert A       0a          0a        
#   +Input/Insert B       0b          0b
#	 (unknown)   					  0c
#	 (unknown)						  0d
#	 (unknown)						  0e
#   +Input/Delay          0f          0f
#
#
#
#  0fe5  Mix Trim for Ext In
#  0fe6  Mix PEQ
#  0fe7  Mix GEQ
#  0fe8  Mix Comp
#  0fea  Mix Ins A
#  0feb  Mix Delay
#
#  1253  Talkback Trim
#  18b9  Midi Controls




from __future__ import print_function

__all__ = ['init_rpc_proxy']

#
# Map MixRack version string to internal proxy versions
#

class ProxyConfig(object):
	def __init__(self, **kw):
		self.__dict__.update(kw)
	def get(self, key, default=None):
		return self.__dict__.get(key, default)

CONFIG_130 = [
	ProxyConfig(name='proxyDCA', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x0019, _addr2=0x0019-1,
				),
	ProxyConfig(name='proxyInput', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001b, _addr2=0x001b-1, 
				),
	ProxyConfig(name='proxyFXReturn', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001c, _addr2=0x001c-1,
				),
	ProxyConfig(name='proxyFXSend', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001d, _addr2=0x001d-1,
				),
	ProxyConfig(name='proxyMix', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001e, _addr2=0x001e-1,
				),
	ProxyConfig(name='proxyInputProcessing', klass='proxyInputProcessing',
					_deviceid=0x0001, _addr1=0x0102, _addr2=0x0102-1, 
					inserta_ofs = 0x000a,
					insertb_ofs = 0x000b,
					delay_ofs   = 0x000f,
				),
]

CONFIG_140 = [
	ProxyConfig(name='proxyDCA', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001b, _addr2=0x001b-1,
				),
	ProxyConfig(name='proxyInput', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001d, _addr2=0x001d-1,
				),
	ProxyConfig(name='proxyFXReturn', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001e, _addr2=0x001e-1,
				),
	ProxyConfig(name='proxyFXSend', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x001f, _addr2=0x001f-1,
				),
	ProxyConfig(name='proxyMix', klass='proxyBasic',
					_deviceid=0x0001, _addr1=0x0020, _addr2=0x0020-1,
				),
	ProxyConfig(name='proxyInputProcessing', klass='proxyInputProcessing',
					_deviceid=0x0001, _addr1=0x0145, _addr2=0x0145-1,
					inserta_ofs = 0x000a,
					insertb_ofs = 0x000b,
					delay_ofs   = 0x000f,
				),

]

VERSION_MAPPING = {
	'V1.30 - Rev. 27648':  CONFIG_130,
	'V1.31 - Rev. XXXXX':  CONFIG_130,   # FIXME: Need 1.31 Build #
	'V1.40 - Rev. 30551':  CONFIG_140,
}

def init_rpc_proxy(console, version):
	print("init_rpc_proxy(%s)" % version)

	# --- Verify firmware version is recognized
	if not version in VERSION_MAPPING:
		raise UnknownFirmwareVersion(version)

	# --- Dynamically create proxies
	for entry in VERSION_MAPPING[version]:
		obj = globals()[entry.get('klass')](console, entry)
		console.__dict__[entry.get('name')] = obj


# -----------------------------------------------------------------------------

class proxyBase(object):
    
    def configure(self, console, config):
    	self._console = console
    	self._config  = config
    	for key in ['_deviceid', '_addr1', '_addr2', '_method']:
    		self.__dict__[key] = config.get(key, None)
		
		#self._deviceid, self._addr1, self._addr2 = 0x0001, 0x001d, 0x001c  # 1.40 TEST

    def sysex_send(self, deviceid=None, addr1=None, addr2=None, method=None, data = [], **kw):

    	deviceid 	= deviceid or self._deviceid
    	addr1 		= (addr1 or self._addr1) + kw.get('addr1_ofs', 0)
    	addr2 		= (addr2 or self._addr2) + kw.get('addr2_ofs', kw.get('addr1_ofs', 0))
    	method 		= (method or self._method) + kw.get('method_ofs', 0)

        len1  = len(data) / 256
        len2  = len(data) % 256

        sysex = [ 0xf0, 
                  deviceid/256, deviceid%256, 
                  addr1/256, addr1%256, 
                  addr2/256, addr2%256,    # Typically addr1 - 0x0001
                  method/256, method%256,
                  len1, len2]
        sysex.extend(data)
        sysex.append(0xf7)  
 
        fmt_data = ' '.join('%02x' % i for i in sysex)
        print("sysex [ %s ]" % (fmt_data))
  
        return sysex

class proxyBasic(proxyBase):

	def __init__(self, console, config):
		self.configure(console, config)

	def set(self, method, data):
		self._console.queue_command(self.sysex_send(method=method, data=data))

class proxyInputProcessing(proxyBase):

	def __init__(self, console, config):
		self.configure(console, config)
		self._inserta_ofs = config.get('inserta_ofs')
		self._insertb_ofs = config.get('insertb_ofs')
		self._delay_ofs   = config.get('delay_ofs')

	def inserta(self, channel_idx, method, data):
		addr1_ofs = (channel_idx) * 0x10 + self._inserta_ofs
		self._console.queue_command(self.sysex_send(addr1_ofs=addr1_ofs, method=method, data=data))

	def insertb(self, channel_idx, method, data):
		addr1_ofs = (channel_idx) * 0x10 + self._insertb_ofs
		self._console.queue_command(self.sysex_send(addr1_ofs=addr1_ofs, method=method, data=data))

	def delay(self, channel_idx, method, data):
		addr1_ofs = (channel_idx) * 0x10 + self._delay_ofs
		self._console.queue_command(self.sysex_send(addr1_ofs=addr1_ofs, method=method, data=data))


