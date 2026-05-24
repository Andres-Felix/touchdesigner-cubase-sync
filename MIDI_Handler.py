"""
MIDI Handler for TouchDesigner Cubase Sync
Processes MIDI input from Cubase including MTC timecode
"""

from CubaseSyncExt import cubase_sync

class MIDIHandler:
    """Handle MIDI input processing"""
    
    @staticmethod
    def process_midi_status(status, data1, data2):
        """
        Process MIDI status byte
        Returns True if processed, False otherwise
        """
        status_type = status & 0xF0
        channel = status & 0x0F
        
        # System Common Messages (for MTC)
        if status == 0xF1:  # MTC Quarter Frame
            cubase_sync.parse_mtc_quarter_frame(data1)
            return True
        
        elif status == 0xF0:  # SysEx (for MTC Full Frame)
            # SysEx handling would be done separately
            return True
        
        # Channel Messages
        elif status_type == 0x90:  # Note On
            if data2 > 0:  # velocity > 0
                cubase_sync.process_midi_note_on(data1, data2, channel)
            else:  # velocity = 0 is Note Off
                cubase_sync.process_midi_note_off(data1, channel)
            return True
        
        elif status_type == 0x80:  # Note Off
            cubase_sync.process_midi_note_off(data1, channel)
            return True
        
        elif status_type == 0xB0:  # Control Change
            cubase_sync.process_midi_cc(data1, data2, channel)
            return True
        
        elif status == 0xFA:  # Start
            cubase_sync.process_transport_start()
            return True
        
        elif status == 0xFB:  # Continue
            cubase_sync.process_transport_continue()
            return True
        
        elif status == 0xFC:  # Stop
            cubase_sync.process_transport_stop()
            return True
        
        elif status == 0xF2:  # Song Position Pointer
            position = (data2 << 7) | data1
            cubase_sync.process_song_position_pointer(position)
            return True
        
        return False


def midi_callback(sample, status, data1, data2, sampleoffset, offsetsamples):
    """
    Callback function for TouchDesigner MIDI in CHOP
    Called from a mididevicein operator
    """
    MIDIHandler.process_midi_status(status, data1, data2)


# Example usage with TouchDesigner MIDI in operator:
# In a DAT or EXT operator, use:
# op('mididevicein1').midiCallback = midi_callback