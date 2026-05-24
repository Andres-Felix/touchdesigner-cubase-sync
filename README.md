# TouchDesigner Cubase Synchronization Plugin

A comprehensive synchronization plugin for TouchDesigner that enables seamless integration with Cubase, supporting multiple synchronization protocols and timecode standards.

## Features

### Synchronization Methods
- **MTC (MIDI Timecode)** - Frame-accurate synchronization via MIDI
- **LTC (Linear Timecode)** - Audio-based timecode from Cubase
- **OSC (Open Sound Control)** - Network-based synchronization
- **Genlock** - Hardware video synchronization (DeckLink, AJA)

### MIDI Integration
- Note On/Off events
- Control Change (CC) messages
- Transport control (Play, Stop, Continue)
- Song Position Pointer

### Sync Features
- Real-time tempo/BPM tracking
- Bar and beat synchronization
- Transport state monitoring
- Beat fraction tracking (0.0-1.0)
- Time signature support
- Sync quality monitoring
- Frame skip detection

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Andres-Felix/touchdesigner-cubase-sync.git
```

2. Copy the plugin files to your TouchDesigner project:
```
CubaseSyncExt.py
MIDI_Handler.py
OSC_Handler.py
LTC_Handler.py
GenlockSync.py
```

## Quick Start

### Basic Setup

```python
from CubaseSyncExt import cubase_sync, get_sync_manager
from GenlockSync import get_genlock_manager

# Get sync manager
sync = get_sync_manager()

# Register for timecode changes
def on_timecode_change(data):
    print(f"Timecode: {data['timecode']}")

sync.register_callback('on_timecode_change', on_timecode_change)

# Check current status
status = sync.get_sync_status()
print(status)
```

### MTC Setup (via MIDI)

1. In TouchDesigner, create a **MIDI In** CHOP operator
2. Connect it to your MIDI interface
3. Set the callback:

```python
from MIDI_Handler import midi_callback

op('mididevicein1').midiCallback = midi_callback
```

### OSC Setup (via Network)

1. Create a **UDP In** DAT operator in TouchDesigner
2. Set it to listen on port 9000 (or your choice)
3. Process incoming data:

```python
from OSC_Handler import OSCHandler

OSCHandler.process_osc_data(incoming_data)
```

### LTC Setup (Audio-based)

```python
from LTC_Handler import get_ltc_processor

ltc = get_ltc_processor()
ltc.process_chop_samples(op('audiosource1'))
```

### Genlock Setup

```python
from GenlockSync import get_genlock_manager, TouchDesignerGenlockBridge

# Configure for 25fps DeckLink output
TouchDesignerGenlockBridge.configure_for_production_video_output(
    frame_rate=25, 
    sync_source='decklink'
)

# Monitor sync in render loop
genlock = get_genlock_manager()
sync_info = genlock.check_sync_status()
print(sync_info)
```

## Architecture

### Core Components

#### **CubaseSyncExt.py**
Main synchronization engine that manages:
- MTC/LTC timecode parsing
- MIDI note and CC processing
- Transport state management
- Callback system
- Sync status reporting

#### **MIDI_Handler.py**
Processes MIDI input:
- Note On/Off events
- Control Changes
- MTC Quarter Frames
- Transport messages
- Song Position Pointer

#### **OSC_Handler.py**
Handles OSC message protocol:
- OSC message parsing
- Bundle support
- Type conversion (int, float, string, blob, bool)
- Cubase OSC address routing

#### **LTC_Handler.py**
Decodes audio-based timecode:
- SMPTE 12M format support
- Audio sample processing
- BCD (Binary Coded Decimal) parsing
- Lock detection

#### **GenlockSync.py**
Manages video synchronization:
- DeckLink support
- AJA support
- Timecode-based sync
- Frame rate management
- Sync quality monitoring

## Callback Events

Register callbacks for these events:

```python
# Timecode changed
sync.register_callback('on_timecode_change', callback)

# Transport state changed (play/stop/continue)
sync.register_callback('on_transport_change', callback)

# MIDI note event
sync.register_callback('on_midi_note', callback)

# MIDI CC changed
sync.register_callback('on_midi_cc', callback)

# Beat changed
sync.register_callback('on_beat', callback)

# Bar changed
sync.register_callback('on_bar', callback)

# Tempo changed
sync.register_callback('on_tempo_change', callback)

# OSC message received
sync.register_callback('on_osc_message', callback)

# Genlock sync status changed
sync.register_callback('on_sync_lock', callback)
```

## Example: Triggering Visuals from MIDI

```python
from CubaseSyncExt import cubase_sync

def on_midi_note(data):
    if data['type'] == 'note_on':
        note = data['note']
        velocity = data['velocity']
        
        # Trigger visual based on note
        if note == 60:  # Middle C
            op('geometry1').par.tx = velocity / 127.0

sync = cubase_sync
sync.register_callback('on_midi_note', on_midi_note)
```

## Example: Syncing Animation to Beat

```python
def on_beat(data):
    bar = data['bar']
    beat = data['beat']
    fraction = data['beat_fraction']
    bpm = data['bpm']
    
    # Animate rotation based on beat
    op('rotate1').par.ry = (fraction * 360)
    
    # Scale pulse on beat
    scale = 1.0 + (0.1 * (1.0 - fraction))
    op('xform1').par.scale = scale

cubase_sync.register_callback('on_beat', on_beat)
```

## Cubase OSC Configuration

For OSC synchronization, configure Cubase to send OSC messages to TouchDesigner:

**Cubase OSC Addresses:**
- `/transport/play` - Start playback
- `/transport/stop` - Stop playback
- `/transport/continue` - Continue from pause
- `/tempo` - Current BPM (float)
- `/beat` - Bar, beat, fraction (int, int, float)
- `/timecode` - HH, MM, SS, FF (int, int, int, int)

## Frame Rate Support

Supported frame rates:
- 23.976 fps (NTSC film)
- 24 fps (cinema)
- 25 fps (PAL)
- 29.97 fps (NTSC drop-frame)
- 30 fps
- 50 fps
- 59.94 fps
- 60 fps

## Troubleshooting

### MTC Not Syncing
1. Verify MIDI cable connection
2. Check TouchDesigner MIDI input device selection
3. Enable MIDI output in Cubase (Devices > MIDI Output)
4. Verify frame rate matches in both applications

### OSC Connection Issues
1. Check network connectivity
2. Verify Cubase OSC is enabled
3. Ensure UDP port is not blocked by firewall
4. Monitor incoming messages with packet sniffer

### Genlock Not Locking
1. Verify video card driver is up to date
2. Check sync source is connected to video input
3. Confirm frame rate matches sync signal
4. Check TouchDesigner preferences for video card settings

## Performance Considerations

- **MTC** - Minimal CPU overhead, excellent timing
- **OSC** - Network latency dependent, typically <10ms
- **LTC** - More CPU intensive, requires audio processing
- **Genlock** - Hardware-dependent, most accurate

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please submit issues and pull requests.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Resources

- [TouchDesigner Documentation](https://docs.derivative.ca/)
- [Cubase MIDI/OSC Documentation](https://helpcenter.steinberg.de/)
- [SMPTE Timecode Standard](https://en.wikipedia.org/wiki/Timecode)
- [OSC Specification](http://opensoundcontrol.org/)
