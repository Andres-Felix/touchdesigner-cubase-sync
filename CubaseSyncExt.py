"""
TouchDesigner Cubase Synchronization Extension
Handles MTC, MIDI, OSC, and transport control synchronization
"""

import struct
import time
from datetime import datetime

class CubaseSyncManager:
    """
    Main synchronization manager for Cubase ↔ TouchDesigner integration
    Supports: MTC timecode, MIDI CC/Notes, OSC, Transport control, Genlock sync
    """
    
    def __init__(self):
        # Timecode state
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.frames = 0
        self.frame_rate = 25  # 24, 25, 29.97, 30 fps
        self.timecode_string = "00:00:00:00"
        self.frame_count = 0
        
        # Transport state
        self.is_playing = False
        self.is_recording = False
        self.play_position = 0  # in frames
        
        # Sync state
        self.tempo_bpm = 120.0
        self.beat = 0
        self.bar = 0
        self.beat_fraction = 0.0  # 0.0 to 1.0 within a beat
        self.time_signature_numerator = 4
        self.time_signature_denominator = 4
        
        # MIDI state
        self.midi_notes = {}  # {note_number: velocity}
        self.midi_cc = {}     # {cc_number: value}
        self.last_note_on = None
        self.last_cc_change = None
        
        # OSC state
        self.osc_data = {}
        self.last_osc_message = None
        
        # Genlock state
        self.genlock_synced = False
        self.genlock_source = None  # 'ltc', 'mtc', 'osc', 'none'
        
        # Callbacks
        self.callbacks = {
            'on_transport_change': [],
            'on_timecode_change': [],
            'on_midi_note': [],
            'on_midi_cc': [],
            'on_beat': [],
            'on_bar': [],
            'on_tempo_change': [],
            'on_osc_message': [],
            'on_sync_lock': []
        }
        
    # ============================================================================
    # MTC (MIDI Timecode) Processing
    # ============================================================================
    
    def parse_mtc_quarter_frame(self, data_byte):
        """
        Parse MTC quarter frame messages
        MTC sends 8 quarter frames per timecode frame
        Format: 0xF1 (status) + data byte with sequence and value
        """
        sequence = (data_byte >> 4) & 0x0F
        value = data_byte & 0x0F
        
        if sequence == 0:      # Frames low nibble (0-3)
            self.frames = (self.frames & 0xF0) | value
        elif sequence == 1:    # Frames high nibble (0-1)
            self.frames = (self.frames & 0x0F) | ((value & 0x01) << 4)
        elif sequence == 2:    # Seconds low nibble (0-9)
            self.seconds = (self.seconds & 0xF0) | value
        elif sequence == 3:    # Seconds high nibble (0-5)
            self.seconds = (self.seconds & 0x0F) | ((value & 0x07) << 4)
        elif sequence == 4:    # Minutes low nibble (0-9)
            self.minutes = (self.minutes & 0xF0) | value
        elif sequence == 5:    # Minutes high nibble (0-5)
            self.minutes = (self.minutes & 0x0F) | ((value & 0x07) << 4)
        elif sequence == 6:    # Hours low nibble (0-9)
            self.hours = (self.hours & 0xF0) | value
        elif sequence == 7:    # Hours high nibble (0-2), frame rate
            self.hours = (self.hours & 0x0F) | ((value & 0x03) << 4)
            frame_rate_bits = (value >> 2) & 0x03
            self.frame_rate = self._get_frame_rate_from_bits(frame_rate_bits)
        
        # Update timecode string after complete frame
        if sequence == 7:
            self._update_timecode_string()
            self._trigger_callback('on_timecode_change')
    
    def parse_mtc_full_frame(self, mtc_data):
        """
        Parse MTC full frame message (0xF0 0x7F ... 0xF7)
        Provides complete timecode in one message
        """
        if len(mtc_data) < 5:
            return False
        
        # mtc_data[0] = hours (bit 7-6 = frame rate)
        frame_rate_bits = (mtc_data[0] >> 5) & 0x03
        self.hours = mtc_data[0] & 0x1F
        self.minutes = mtc_data[1]
        self.seconds = mtc_data[2]
        self.frames = mtc_data[3]
        self.frame_rate = self._get_frame_rate_from_bits(frame_rate_bits)
        
        self._update_timecode_string()
        self._trigger_callback('on_timecode_change')
        return True
    
    def _get_frame_rate_from_bits(self, bits):
        """Convert frame rate bits to fps value"""
        rates = {0: 24, 1: 25, 2: 29.97, 3: 30}
        return rates.get(bits, 25)
    
    def _update_timecode_string(self):
        """Update timecode string representation"""
        self.timecode_string = f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}:{self.frames:02d}"
        self.frame_count = (self.hours * 3600 * self.frame_rate + 
                           self.minutes * 60 * self.frame_rate + 
                           self.seconds * self.frame_rate + 
                           self.frames)
    
    # ============================================================================
    # MIDI Processing
    # ============================================================================
    
    def process_midi_note_on(self, note, velocity, channel=0):
        """Process MIDI Note On message"""
        self.midi_notes[note] = velocity
        self.last_note_on = {
            'note': note,
            'velocity': velocity,
            'channel': channel,
            'timestamp': time.time()
        }
        self._trigger_callback('on_midi_note', {
            'type': 'note_on',
            'note': note,
            'velocity': velocity,
            'channel': channel
        })
    
    def process_midi_note_off(self, note, channel=0):
        """Process MIDI Note Off message"""
        if note in self.midi_notes:
            del self.midi_notes[note]
        self._trigger_callback('on_midi_note', {
            'type': 'note_off',
            'note': note,
            'channel': channel
        })
    
    def process_midi_cc(self, cc_number, value, channel=0):
        """Process MIDI Control Change message"""
        self.midi_cc[cc_number] = value
        self.last_cc_change = {
            'cc': cc_number,
            'value': value,
            'channel': channel,
            'timestamp': time.time()
        }
        self._trigger_callback('on_midi_cc', {
            'cc': cc_number,
            'value': value,
            'channel': channel,
            'normalized': value / 127.0
        })
    
    def get_midi_note_names(self):
        """Get currently active MIDI notes by name"""
        note_names = {
            0: 'C', 1: 'C#', 2: 'D', 3: 'D#', 4: 'E', 5: 'F',
            6: 'F#', 7: 'G', 8: 'G#', 9: 'A', 10: 'A#', 11: 'B'
        }
        active_notes = []
        for note, velocity in self.midi_notes.items():
            octave = (note // 12) - 1
            note_name = note_names[note % 12]
            active_notes.append(f"{note_name}{octave}")
        return active_notes
    
    # ============================================================================
    # Transport Control
    # ============================================================================
    
    def process_transport_start(self):
        """Process transport START message"""
        self.is_playing = True
        self.is_recording = False
        self._trigger_callback('on_transport_change', {
            'state': 'play',
            'is_playing': True,
            'is_recording': False
        })
    
    def process_transport_stop(self):
        """Process transport STOP message"""
        self.is_playing = False
        self.is_recording = False
        self._trigger_callback('on_transport_change', {
            'state': 'stop',
            'is_playing': False,
            'is_recording': False
        })
    
    def process_transport_continue(self):
        """Process transport CONTINUE message"""
        self.is_playing = True
        self._trigger_callback('on_transport_change', {
            'state': 'continue',
            'is_playing': True,
            'is_recording': self.is_recording
        })
    
    def process_song_position_pointer(self, position):
        """
        Process Song Position Pointer (SPP)
        Position is in 16th note increments
        """
        self.play_position = position * (self.frame_rate / 4)  # Convert to frames
        self._trigger_callback('on_transport_change', {
            'type': 'position',
            'position_16th_notes': position,
            'position_frames': self.play_position
        })
    
    # ============================================================================
    # Tempo and Beat Synchronization
    # ============================================================================
    
    def update_tempo(self, bpm):
        """Update tempo from Cubase"""
        if abs(self.tempo_bpm - bpm) > 0.01:  # Only trigger if changed
            self.tempo_bpm = bpm
            self._trigger_callback('on_tempo_change', {
                'bpm': bpm,
                'beat_duration_ms': (60000.0 / bpm)
            })
    
    def update_beat_info(self, bar, beat, beat_fraction=0.0):
        """Update beat/bar information from Cubase"""
        beat_changed = (self.bar != bar) or (self.beat != beat)
        bar_changed = (self.bar != bar)
        
        self.bar = bar
        self.beat = beat
        self.beat_fraction = beat_fraction
        
        if beat_changed:
            self._trigger_callback('on_beat', {
                'bar': bar,
                'beat': beat,
                'beat_fraction': beat_fraction,
                'bpm': self.tempo_bpm
            })
        
        if bar_changed:
            self._trigger_callback('on_bar', {
                'bar': bar,
                'time_sig': f"{self.time_signature_numerator}/{self.time_signature_denominator}"
            })
    
    def set_time_signature(self, numerator, denominator):
        """Set time signature"""
        self.time_signature_numerator = numerator
        self.time_signature_denominator = denominator
    
    # ============================================================================
    # OSC Processing
    # ============================================================================
    
    def process_osc_message(self, address, *args):
        """
        Process OSC message from Cubase
        Common Cubase OSC addresses:
        /transport/play, /transport/stop, /tempo, /beat, /bar, etc.
        """
        self.osc_data[address] = args
        self.last_osc_message = {
            'address': address,
            'args': args,
            'timestamp': time.time()
        }
        
        # Route to appropriate handlers based on OSC address
        if address == '/transport/play':
            self.process_transport_start()
        elif address == '/transport/stop':
            self.process_transport_stop()
        elif address == '/transport/continue':
            self.process_transport_continue()
        elif address == '/tempo':
            if args:
                self.update_tempo(float(args[0]))
        elif address == '/beat':
            if len(args) >= 2:
                self.update_beat_info(int(args[0]), int(args[1]), 
                                     float(args[2]) if len(args) > 2 else 0.0)
        elif address == '/timecode':
            if len(args) >= 4:
                self.hours, self.minutes, self.seconds, self.frames = [int(a) for a in args[:4]]
                self._update_timecode_string()
        
        self._trigger_callback('on_osc_message', {
            'address': address,
            'args': args
        })
    
    # ============================================================================
    # Genlock and Sync Status
    # ============================================================================
    
    def set_genlock_synced(self, synced, source=None):
        """Update genlock synchronization status"""
        if self.genlock_synced != synced or self.genlock_source != source:
            self.genlock_synced = synced
            self.genlock_source = source
            self._trigger_callback('on_sync_lock', {
                'synced': synced,
                'source': source,
                'timecode': self.timecode_string
            })
    
    def get_sync_status(self):
        """Get current synchronization status"""
        return {
            'timecode': self.timecode_string,
            'frame_rate': self.frame_rate,
            'is_playing': self.is_playing,
            'tempo_bpm': self.tempo_bpm,
            'bar': self.bar,
            'beat': self.beat,
            'beat_fraction': self.beat_fraction,
            'genlock_synced': self.genlock_synced,
            'genlock_source': self.genlock_source,
            'active_notes': self.get_midi_note_names(),
            'midi_cc_count': len(self.midi_cc)
        }
    
    # ============================================================================
    # Callback Management
    # ============================================================================
    
    def register_callback(self, event_name, callback):
        """Register a callback for an event"""
        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback)
    
    def unregister_callback(self, event_name, callback):
        """Unregister a callback"""
        if event_name in self.callbacks:
            self.callbacks[event_name].remove(callback)
    
    def _trigger_callback(self, event_name, data=None):
        """Trigger all callbacks for an event"""
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in callback for {event_name}: {e}")
    
    # ============================================================================
    # Debug and Utility Methods
    # ============================================================================
    
    def get_timecode(self):
        """Get current timecode string"""
        return self.timecode_string
    
    def get_frame_number(self):
        """Get current frame number"""
        return self.frame_count
    
    def format_time(self, milliseconds):
        """Format milliseconds to MM:SS.MS"""
        seconds = milliseconds // 1000
        ms = milliseconds % 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}.{ms:03d}"
    
    def debug_info(self):
        """Get debug information"""
        return f"""
        === Cubase Sync Debug Info ===
        Timecode: {self.timecode_string}
        Frame Rate: {self.frame_rate} fps
        Transport: {'PLAYING' if self.is_playing else 'STOPPED'}
        Tempo: {self.tempo_bpm:.2f} BPM
        Bar: {self.bar}, Beat: {self.beat}, Fraction: {self.beat_fraction:.3f}
        Active MIDI Notes: {len(self.midi_notes)}
        MIDI CCs: {len(self.midi_cc)}
        Genlock: {'SYNCED' if self.genlock_synced else 'NOT SYNCED'} ({self.genlock_source})
        """


# Global instance
cubase_sync = CubaseSyncManager()

def get_sync_manager():
    """Get the global sync manager instance"""
    return cubase_sync