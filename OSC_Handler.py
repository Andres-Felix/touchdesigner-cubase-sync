"""
OSC Handler for TouchDesigner Cubase Sync
Processes OSC messages from Cubase over network
"""

from CubaseSyncExt import cubase_sync
import struct

class OSCHandler:
    """Handle OSC message processing"""
    
    @staticmethod
    def parse_osc_bundle(data):
        """
        Parse OSC bundle format
        Returns list of (address, args) tuples
        """
        messages = []
        
        if data.startswith(b'#bundle\x00'):
            offset = 16  # Skip bundle header and timestamp
            
            while offset < len(data):
                # Get element size
                size = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                
                element = data[offset:offset+size]
                offset += size
                
                if element.startswith(b'#bundle'):
                    # Nested bundle
                    messages.extend(OSCHandler.parse_osc_bundle(element))
                else:
                    # OSC message
                    msg = OSCHandler.parse_osc_message(element)
                    if msg:
                        messages.append(msg)
        
        return messages
    
    @staticmethod
    def parse_osc_message(data):
        """
        Parse single OSC message
        Returns (address, args) tuple or None
        """
        try:
            # Find null-terminated address
            null_pos = data.find(b'\x00')
            if null_pos == -1:
                return None
            
            address = data[:null_pos].decode('utf-8')
            
            # Align to 4-byte boundary
            offset = null_pos + 1
            while offset % 4 != 0:
                offset += 1
            
            # Parse type tag string
            if offset >= len(data) or data[offset:offset+1] != b',':
                return (address, [])
            
            type_start = offset + 1
            type_end = data.find(b'\x00', type_start)
            if type_end == -1:
                return None
            
            types = data[type_start:type_end].decode('utf-8')[1:]  # Skip comma
            
            # Align to 4-byte boundary
            offset = type_end + 1
            while offset % 4 != 0:
                offset += 1
            
            # Parse arguments
            args = []
            for type_char in types:
                if type_char == 'i':  # int32
                    if offset + 4 <= len(data):
                        val = struct.unpack('>i', data[offset:offset+4])[0]
                        args.append(val)
                        offset += 4
                
                elif type_char == 'f':  # float32
                    if offset + 4 <= len(data):
                        val = struct.unpack('>f', data[offset:offset+4])[0]
                        args.append(val)
                        offset += 4
                
                elif type_char == 's':  # string
                    null_pos = data.find(b'\x00', offset)
                    if null_pos != -1:
                        val = data[offset:null_pos].decode('utf-8')
                        args.append(val)
                        offset = null_pos + 1
                        while offset % 4 != 0:
                            offset += 1
                
                elif type_char == 'd':  # float64
                    if offset + 8 <= len(data):
                        val = struct.unpack('>d', data[offset:offset+8])[0]
                        args.append(val)
                        offset += 8
                
                elif type_char == 'b':  # blob
                    if offset + 4 <= len(data):
                        blob_size = struct.unpack('>I', data[offset:offset+4])[0]
                        offset += 4
                        blob = data[offset:offset+blob_size]
                        args.append(blob)
                        offset += blob_size
                        while offset % 4 != 0:
                            offset += 1
                
                elif type_char == 'T':  # True
                    args.append(True)
                
                elif type_char == 'F':  # False
                    args.append(False)
                
                elif type_char == 'N':  # Nil
                    args.append(None)
            
            return (address, args)
        
        except Exception as e:
            print(f"Error parsing OSC message: {e}")
            return None
    
    @staticmethod
    def process_osc_data(data):
        """
        Process raw OSC data (either message or bundle)
        """
        messages = []
        
        if data.startswith(b'#bundle'):
            messages = OSCHandler.parse_osc_bundle(data)
        else:
            msg = OSCHandler.parse_osc_message(data)
            if msg:
                messages = [msg]
        
        # Process each message
        for address, args in messages:
            cubase_sync.process_osc_message(address, *args)
            print(f"OSC: {address} {args}")


# Common Cubase OSC address mappings
CUBASE_OSC_ADDRESSES = {
    '/transport/play': 'Start playback',
    '/transport/stop': 'Stop playback',
    '/transport/continue': 'Continue from pause',
    '/tempo': 'Current tempo in BPM (float)',
    '/beat': 'Current beat (int, int, float)',
    '/bar': 'Current bar (int)',
    '/timecode': 'Timecode (int, int, int, int)',
    '/transport/position': 'Song position in 16th notes',
    '/track/volume': 'Track volume (string track_id, float value)',
    '/track/pan': 'Track pan (string track_id, float value)',
    '/track/mute': 'Track mute (string track_id, bool)',
    '/track/solo': 'Track solo (string track_id, bool)',
}


def osc_receive_callback(dat_ref):
    """
    Callback for TouchDesigner UDP in DAT
    Usage: Create UDP In DAT and set this as callback
    """
    for row_index in range(len(dat_ref.rows)):
        row = dat_ref.row(row_index)
        
        # Assuming first column contains raw OSC data
        if row and row[0]:
            OSCHandler.process_osc_data(row[0])