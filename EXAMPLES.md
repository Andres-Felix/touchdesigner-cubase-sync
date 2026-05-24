# TouchDesigner Cubase Sync - Usage Examples

## Example 1: Basic Timecode Display

```python
from CubaseSyncExt import cubase_sync

def on_timecode_change(data):
    # Display current timecode in text TOP
    op('text1').par.text = cubase_sync.timecode_string

# Register callback
cubase_sync.register_callback('on_timecode_change', on_timecode_change)
```

## Example 2: MIDI Note Triggered Particle Effect

```python
from CubaseSyncExt import cubase_sync

def on_midi_note(data):
    if data['type'] == 'note_on':
        note = data['note']
        velocity = data['velocity']
        
        # Map note to particle type
        particle_type = note % 12
        
        # Spawn particle with velocity
        # op('particle1').par.rate = velocity / 127.0 * 100
        # op('particle1').par.type = particle_type
        
        print(f"Note {note} velocity {velocity}")

cubase_sync.register_callback('on_midi_note', on_midi_note)
```

## Example 3: CC Slider Control

```python
from CubaseSyncExt import cubase_sync

def on_midi_cc(data):
    cc_num = data['cc']
    normalized = data['normalized']  # 0.0 to 1.0
    
    # Map CC 7 (Volume) to opacity
    if cc_num == 7:
        op('geometry1').par.opacity = normalized
    
    # Map CC 11 (Expression) to scale
    elif cc_num == 11:
        op('xform1').par.scale = 1.0 + (normalized * 2.0)
    
    # Map CC 1 (Modulation) to rotation
    elif cc_num == 1:
        op('rotate1').par.ry = normalized * 360

cubase_sync.register_callback('on_midi_cc', on_midi_cc)
```

## Example 4: Sync Animation to Beat

```python
from CubaseSyncExt import cubase_sync

def on_beat(data):
    bar = data['bar']
    beat = data['beat']
    fraction = data['beat_fraction']  # 0.0 to 1.0
    bpm = data['bpm']
    
    # Rotation animation
    rotation = (fraction * 360) % 360
    op('rotate1').par.ry = rotation
    
    # Pulsing scale
    pulse = 1.0 + (math.sin(fraction * 3.14159) * 0.3)
    op('xform1').par.scale = pulse
    
    # Color change per beat
    hue = (beat / 4.0) % 1.0  # Cycle through hues every 4 beats
    op('color1').par.hue = hue
    
    # Print debug info
    print(f"Bar {bar}, Beat {beat}, Fraction {fraction:.3f}, BPM {bpm}")

cubase_sync.register_callback('on_beat', on_beat)
```

## Example 5: Transport State Monitor

```python
from CubaseSyncExt import cubase_sync

def on_transport_change(data):
    state = data.get('state')
    
    if state == 'play':
        print("Transport: PLAY")
        op('indicator_play').par.opacity = 1.0
        op('indicator_stop').par.opacity = 0.0
    
    elif state == 'stop':
        print("Transport: STOP")
        op('indicator_play').par.opacity = 0.0
        op('indicator_stop').par.opacity = 1.0
    
    elif state == 'continue':
        print("Transport: CONTINUE")

cubase_sync.register_callback('on_transport_change', on_transport_change)
```

## Example 6: Multi-Track MIDI Control

```python
from CubaseSyncExt import cubase_sync

# Map MIDI channels to different visual elements
CHANNEL_MAP = {
    0: 'geometry1',    # Channel 1
    1: 'geometry2',    # Channel 2
    2: 'geometry3',    # Channel 3
    3: 'geometry4',    # Channel 4
}

def on_midi_note(data):
    if data['type'] == 'note_on':
        channel = data['channel']
        note = data['note']
        velocity = data['velocity']
        
        if channel in CHANNEL_MAP:
            op_name = CHANNEL_MAP[channel]
            # Apply effect based on note
            scale = 1.0 + (note / 128.0)
            op(op_name).par.scale = scale
            op(op_name).par.opacity = velocity / 127.0

cubase_sync.register_callback('on_midi_note', on_midi_note)
```

## Example 7: Tempo-Based Animation Speed

```python
from CubaseSyncExt import cubase_sync

def on_tempo_change(data):
    bpm = data['bpm']
    beat_duration_ms = data['beat_duration_ms']
    
    # Convert BPM to animation speed
    # At 120 BPM = 1 beat per second = animation speed 1.0
    animation_speed = bpm / 120.0
    
    # Apply to all animation operators
    op('animate1').par.speed = animation_speed
    op('animate2').par.speed = animation_speed
    
    # Display current tempo
    op('text_bpm').par.text = f"BPM: {bpm:.1f}"
    
    print(f"Tempo changed: {bpm:.2f} BPM, Beat duration: {beat_duration_ms:.0f}ms")

cubase_sync.register_callback('on_tempo_change', on_tempo_change)
```

## Example 8: Complete Live Performance Setup

```python
from CubaseSyncExt import cubase_sync
from GenlockSync import get_genlock_manager
import math

class LivePerformanceController:
    def __init__(self):
        self.sync = cubase_sync
        self.genlock = get_genlock_manager()
        
        # Register all callbacks
        self.sync.register_callback('on_transport_change', self.on_transport)
        self.sync.register_callback('on_beat', self.on_beat)
        self.sync.register_callback('on_midi_note', self.on_note)
        self.sync.register_callback('on_midi_cc', self.on_cc)
        self.sync.register_callback('on_tempo_change', self.on_tempo)
    
    def on_transport(self, data):
        if data['state'] == 'play':
            # Start background animation
            op('timeline1').play()
        else:
            # Stop background animation
            op('timeline1').pause()
    
    def on_beat(self, data):
        # Visual pulse on beat
        beat = data['beat']
        
        if beat == 1:  # First beat of measure
            op('flash1').par.intensity = 1.0
    
    def on_note(self, data):
        if data['type'] == 'note_on':
            note = data['note']
            velocity = data['velocity']
            
            # Use lower notes for effects, higher for melodies
            if note < 60:  # Bass notes
                op('bass_effect').par.intensity = velocity / 127.0
            else:  # Higher notes
                op('geometry_main').par.scale = velocity / 127.0
    
    def on_cc(self, data):
        cc = data['cc']
        normalized = data['normalized']
        
        # CC 74 = Filter (common on keyboards)
        if cc == 74:
            op('blur1').par.amount = normalized * 10
    
    def on_tempo(self, data):
        bpm = data['bpm']
        # Adjust effect speeds based on tempo
        speed = bpm / 120.0
        op('effect1').par.speed = speed

# Initialize
controller = LivePerformanceController()
print("Live Performance Controller initialized")
```

## Example 9: Genlock Sync Monitoring

```python
from GenlockSync import get_genlock_manager

def setup_genlock():
    genlock = get_genlock_manager()
    
    # Configure for 25fps DeckLink
    genlock.set_frame_rate(25)
    genlock.enable_decklink_sync(board_index=0, output_index=0)
    
    # Register callback for sync events
    def on_sync_event(event_type, status):
        print(f"Sync Event: {event_type}")
        print(f"Status: {status}")
        print(f"Quality: {genlock.get_sync_quality_percentage():.1f}%")
    
    genlock.register_sync_callback(on_sync_event)

setup_genlock()
```

## Example 10: OSC Data Visualization

```python
from CubaseSyncExt import cubase_sync

def on_osc_message(data):
    address = data['address']
    args = data['args']
    
    # Display OSC data
    msg = f"{address}: {args}"
    op('text_osc').par.text = msg
    
    # Map specific addresses
    if address == '/track/volume':
        track_id, volume = args
        print(f"Track {track_id} volume: {volume}")
    
    elif address == '/track/pan':
        track_id, pan = args
        # Apply pan to audio (if processing audio)
        print(f"Track {track_id} pan: {pan}")

cubase_sync.register_callback('on_osc_message', on_osc_message)
```

## Example 11: Saving/Loading Performance State

```python
from CubaseSyncExt import cubase_sync
import json

def save_performance_state(filename):
    state = {
        'timecode': cubase_sync.timecode_string,
        'tempo': cubase_sync.tempo_bpm,
        'bar': cubase_sync.bar,
        'beat': cubase_sync.beat,
        'is_playing': cubase_sync.is_playing,
        'active_notes': cubase_sync.get_midi_note_names()
    }
    
    with open(filename, 'w') as f:
        json.dump(state, f, indent=2)
    
    print(f"Performance state saved to {filename}")

def display_sync_status():
    status = cubase_sync.get_sync_status()
    for key, value in status.items():
        op('text_status').par.text += f"{key}: {value}\n"

# Call periodically
print(cubase_sync.debug_info())
```

These examples demonstrate the flexibility of the TouchDesigner Cubase Sync plugin. Adapt them to your specific needs!
