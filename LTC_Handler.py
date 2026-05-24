"""
LTC (Linear Timecode) Handler for TouchDesigner Cubase Sync
Decodes LTC audio signal from Cubase
"""

from CubaseSyncExt import cubase_sync
import numpy as np

class LTCDecoder:
    """Decode LTC timecode from audio signal"""
    
    def __init__(self, sample_rate=48000):
        self.sample_rate = sample_rate
        self.frame_rate = 25
        self.bit_buffer = []
        self.sync_word = 0xBFFC  # LTC sync word (16 bits)
        self.frame_counter = 0
        self.ltc_lock = False
        
    def process_audio_samples(self, audio_data):
        """
        Process audio samples looking for LTC signal
        audio_data should be numpy array or list of floats (-1.0 to 1.0)
        """
        # Simple frequency detection for LTC
        # LTC uses 1200 Hz for bit 0 and 2400 Hz for bit 1
        for sample in audio_data:
            self._process_sample(sample)
    
    def _process_sample(self, sample):
        """Process single audio sample"""
        # Threshold detection
        threshold = 0.1
        if abs(sample) > threshold:
            self.bit_buffer.append(1 if sample > 0 else 0)
        else:
            self.bit_buffer.append(0)
        
        # Check for complete frame (80 bits)
        if len(self.bit_buffer) >= 80:
            self._try_parse_frame()
    
    def _try_parse_frame(self):
        """Try to parse an 80-bit LTC frame"""
        frame_data = self.bit_buffer[-80:]
        
        # Check sync word in last 16 bits
        sync_bits = frame_data[-16:]
        sync_val = self._bits_to_int(sync_bits)
        
        if sync_val == self.sync_word:
            # Valid frame found
            self._decode_ltc_frame(frame_data)
            self.ltc_lock = True
        
        # Keep buffer size manageable
        if len(self.bit_buffer) > 160:
            self.bit_buffer = self.bit_buffer[-80:]
    
    def _decode_ltc_frame(self, bits):
        """
        Decode 80-bit LTC frame
        Bit layout (SMPTE 12M format):
        """
        try:
            # Extract binary groups (each contains 4 bits of data)
            def extract_group(start_bit):
                """Extract 4 data bits from binary group with parity"""
                group_bits = [
                    bits[start_bit],
                    bits[start_bit + 1],
                    bits[start_bit + 2],
                    bits[start_bit + 3]
                ]
                return self._bits_to_int(group_bits)
            
            # Parse BCD (Binary Coded Decimal) values
            units_frames = extract_group(0)
            tens_frames = extract_group(8)
            units_seconds = extract_group(16)
            tens_seconds = extract_group(24)
            units_minutes = extract_group(32)
            tens_minutes = extract_group(40)
            units_hours = extract_group(48)
            tens_hours = extract_group(56)
            
            # Convert BCD to decimal
            frames = units_frames + (tens_frames * 10)
            seconds = units_seconds + (tens_seconds * 10)
            minutes = units_minutes + (tens_minutes * 10)
            hours = units_hours + (tens_hours * 10)
            
            # Validate ranges
            if frames < 30 and seconds < 60 and minutes < 60 and hours < 24:
                cubase_sync.hours = hours
                cubase_sync.minutes = minutes
                cubase_sync.seconds = seconds
                cubase_sync.frames = frames
                cubase_sync._update_timecode_string()
                cubase_sync._trigger_callback('on_timecode_change')
                
                self.frame_counter += 1
                
                # Print debug every 25 frames
                if self.frame_counter % 25 == 0:
                    print(f"LTC: {cubase_sync.timecode_string}")
        
        except Exception as e:
            print(f"Error decoding LTC frame: {e}")
            self.ltc_lock = False
    
    @staticmethod
    def _bits_to_int(bits):
        """Convert list of bits to integer"""
        result = 0
        for bit in bits:
            result = (result << 1) | (1 if bit else 0)
        return result


class LTCProcessor:
    """Process LTC from TouchDesigner audio"""
    
    def __init__(self, sample_rate=48000):
        self.decoder = LTCDecoder(sample_rate)
        self.sample_rate = sample_rate
    
    def process_chop_samples(self, chop_ref):
        """
        Process samples from a CHOP audio input
        
        Usage in TouchDesigner:
        - Connect audio input to a CHOP (e.g., audio in device)
        - In EXT script, call: ltc_proc.process_chop_samples(op('audiosource1'))
        """
        if not chop_ref:
            return
        
        # Get audio data from CHOP
        # Assuming single channel or first channel
        try:
            channel_index = 0
            if len(chop_ref.chans) > 0:
                audio_samples = [chop_ref[channel_index, i] for i in range(len(chop_ref))]
                
                # Normalize if needed
                max_val = max(abs(s) for s in audio_samples) if audio_samples else 1.0
                if max_val > 1.0:
                    audio_samples = [s / max_val for s in audio_samples]
                
                # Process through LTC decoder
                self.decoder.process_audio_samples(audio_samples)
        
        except Exception as e:
            print(f"Error processing CHOP samples: {e}")


# Global LTC processor instance
ltc_processor = None

def init_ltc_processor(sample_rate=48000):
    """Initialize LTC processor"""
    global ltc_processor
    ltc_processor = LTCProcessor(sample_rate)
    return ltc_processor

def get_ltc_processor():
    """Get global LTC processor"""
    global ltc_processor
    if ltc_processor is None:
        ltc_processor = LTCProcessor()
    return ltc_processor