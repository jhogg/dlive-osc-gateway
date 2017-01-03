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

The AH-NET protocol does not implement any security and minimal data validation, which can result in invalid
information being sent to the mix rack.  

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

| URI | Values | Notes |
| ----- | ----- | ------------ |
| /input/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /input/{range}/fader | 0..32768 | Need to sort out log scale
| /input/{range}/pan | L100->L0, C, R0->R100
| /input/{range}/dca | {list of dca's} | Exclusively assigns channel to designated DCA's.  Adds new before removing old.
| /input/{range}/mutegroup | {list of mutegroups 1-8} | Exclusively assigns channel to designated mute groups. Adds new before removing old.
| /input/{range}/inserta | 0,1 | Bypass or enable Insert A
| /input/{range}/insertb | 0,1 | Bypass or enable Insert B
| /input/{range}/delay | 0,1 | Delay in ms  xx.xx
| /input/{range}/send/... | | Not Implemented


### DCA
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /dca/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /dca/{range}/fader | 0..32768 | Need to sort out log scale
| /dca/{range}/assign/input/{range} | 0,1 |


### FX Return
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /fxret/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /fxret/{range}/fader | 0..32768 | Need to sort out log scale
| /fxret/{range}/pan | L100->L0, C, R0->R100
| /fxret/{range}/send/... | | Not Implemented

### FX Send
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /fxsend/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /fxsend/{range}/fader | 0..32768 | Need to sort out log scale

### Group & Stereo Group
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /[st]group/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /[st]group/{range}/fader | 0..32768 | Need to sort out log scale
| /[st]group/{range}/pan | | Not Implemented
| /[st]group/{range}/delay | | Not Implemented
| /[st]group/{range}/send/... | | Not Implemented

### Aux & Stereo Aux
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /[st]aux/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /[st]aux/{range}/fader | 0..32768 | Need to sort out log scale
| /[st]aux/{range}/pan | | Not Implemented
| /[st]aux/{range}/delay | | Not Implemented
| /[st]aux/{range}/send/... | | Not Implemented

### Main

| Channel | Target |
| --- | --- |
| 1 | Main Left/Right
| 2 | Mono or Center
| 3 | LFE for Surround
| 4 | Surround LR

| URI | Values | Notes |
| ----- | ----- | ------------ |
| /main/{range}/mute | 0,1 |  Mutes or unmutes a channel
| /main/{range}/fader | 0..32768 | Need to sort out log scale
| /main/{range}/pan | | Not Implemented
| /main/{range}/delay | | Not Implemented
| /main/{range}/send/... | | Not Implemented

### Matrix & Stereo Matrix
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /[st]matrix/{range}/mute | 0,1 |  Mutes or unmutes a matrix
| /[st]matrix/{range}/fader | 0..32768 | Need to sort out log scale
| /[st]matrix/{range}/pan | | Not Implemented
| /[st]matrix/{range}/delay | | Not Implemented


### Mute Group
| URI | Values | Notes |
| ----- | ----- | ------------ |
| /mutegroup/{range}/mute | 0,1 |  Mutes or unmutes a group


(c) 2016, Jay Hogg.  All rights reserved.
