# dlive-osc-gateway
Allen &amp; Heath dLive OSC-like gateway for qLab via AH-NET

## DISCLAIMER

This software talks directly to the dLive system over TCP using Allen & Heath's undocumented AH-NET
protocol.  While the capabilities are siginficantly greater than the MIDI-based interface, it is 
fully unsupported and may cause problems:
* Your system may lock up or perform incorrectly;
* You may cause damage to your hardware, software or saved show;
* You may cause hearing damage;
* You may cause individual hearing damage to IEM users.

The AH-NET protocol does not implement any security or data validation, which can result in invalid
information being sent to the mixer.  

**USE OF THIS SOFTWARE IS FOR EVALUATION PURPOSES ONLY AND AT YOUR OWN RISK**

## Background on what drove the development

## Background on AH-NET Protocol

## The OSC-Like Gateway Interface

## Installation

## Configuration

### Mixer
### Tags

## Use in qLab

## Supported URI's
### Input
/channel/{range}/mute=0|1

/channel/{range}/fader=0..32768  (Need to sort out log scale)

/channel/{range}/pan=L100->L0 | C | R0->R100

/channel/{range}/dca={list of dca's}  ** exclusive

/channel/{range}/mutegroup={list of mutegroups}  ** exclusive

/channel/{range}/inserta=0|1

/channel/{range}/insertb=0|1

/channel/{range}/delay=0|1[,delay in ms.xx]

### DCA
### FX Return
### FX Send
### Group & Stereo Group
### Aux & Stereo Aux
### Main
### Matrix & Stereo Matrix
### MuteGroup

(c) 2016, Jay Hogg.  All rights reserved.
