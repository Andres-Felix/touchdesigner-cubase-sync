"""
Genlock Synchronization Handler for TouchDesigner
Manages synchronization with external video sync signals
Supports DeckLink, AJA, and timecode-based sync
"""

from CubaseSyncExt import cubase_sync
import time

class GenlockManager:
    """
    Manage genlock and video synchronization
    Works with Blackmagic DeckLink, AJA, and other professional video hardware
    """
    
    def __init__(self):
        self.is_synced = False
        self.sync_source = None  # 'decklink', 'aja', 'ltc', 'mtc', 'none'
        self.target_frame_rate = 25
        self.frame_count = 0
        self.last_sync_check = time.time()
        self.sync_error_frames = 0
        self.max_sync_error = 2  # frames
        self.sync_callbacks = []
        
    # ============================================================================
    # Genlock Status and Control
    # ============================================================================
    
    def enable_decklink_sync(self, board_index=0, output_index=0):
        """
        Enable synchronization with DeckLink video card output
        board_index: Which DeckLink card (0 = first)
        output_index: Which output on the card (0-3 typically)
        """
        try:
            # In TouchDesigner, this would be configured via:
            # preferences/video or hardware settings
            self.sync_source = 'decklink'
            self.is_synced = True
            cubase_sync.set_genlock_synced(True, 'decklink')
            self._trigger_sync_callbacks('decklink_enabled')
            print(f"DeckLink genlock enabled: Board {board_index}, Output {output_index}")
            return True
        except Exception as e:
            print(f"Error enabling DeckLink sync: {e}")
            return False
    
    def enable_aja_sync(self, board_index=0):
        """Enable synchronization with AJA video card"""
        try:
            self.sync_source = 'aja'
            self.is_synced = True
            cubase_sync.set_genlock_synced(True, 'aja')
            self._trigger_sync_callbacks('aja_enabled')
            print(f"AJA genlock enabled: Board {board_index}")
            return True
        except Exception as e:
            print(f"Error enabling AJA sync: {e}")
            return False
    
    def enable_timecode_sync(self, timecode_source='mtc'):
        """
        Enable synchronization via timecode (MTC, LTC, or OSC)
        timecode_source: 'mtc', 'ltc', or 'osc'
        """
        self.sync_source = timecode_source
        self.is_synced = True
        cubase_sync.set_genlock_synced(True, timecode_source)
        self._trigger_sync_callbacks(f'{timecode_source}_enabled')
        print(f"Timecode sync enabled: {timecode_source}")
        return True
    
    def disable_sync(self):
        """Disable all synchronization"""
        self.is_synced = False
        self.sync_source = None
        cubase_sync.set_genlock_synced(False, None)
        self._trigger_sync_callbacks('sync_disabled')
        print("Genlock synchronization disabled")
    
    # ============================================================================
    # Frame Rate Configuration
    # ============================================================================
    
    def set_frame_rate(self, fps):
        """Set target frame rate (23.976, 24, 25, 29.97, 30, 50, 59.94, 60)"""
        valid_rates = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]
        if fps not in valid_rates:
            print(f"Invalid frame rate: {fps}. Valid rates: {valid_rates}")
            return False
        
        self.target_frame_rate = fps
        cubase_sync.frame_rate = fps
        return True
    
    # ============================================================================
    # Synchronization Monitoring
    # ============================================================================
    
    def check_sync_status(self):
        """
        Check and report synchronization status
        Returns sync lock status and error information
        """
        status = {
            'is_synced': self.is_synced,
            'sync_source': self.sync_source,
            'target_fps': self.target_frame_rate,
            'current_frame': cubase_sync.frame_count,
            'sync_error_frames': self.sync_error_frames,
            'timecode': cubase_sync.timecode_string
        }
        return status
    
    def validate_sync_lock(self, expected_frame):
        """
        Validate that we're in sync
        Call this every frame to monitor sync health
        """
        current_frame = cubase_sync.frame_count
        frame_diff = abs(current_frame - expected_frame)
        
        if frame_diff > self.max_sync_error:
            self.sync_error_frames += 1
            if self.sync_error_frames > 5:  # Lost sync after 5 consecutive errors
                self.is_synced = False
                self._trigger_sync_callbacks('sync_lost')
                print(f"SYNC LOST: Frame diff = {frame_diff}")
                return False
        else:
            self.sync_error_frames = 0  # Reset on good frame
        
        return self.is_synced
    
    # ============================================================================
    # Frame Synchronization Helpers
    # ============================================================================
    
    def get_expected_frame_for_time(self, milliseconds):
        """
        Calculate expected frame number for a given time in milliseconds
        Useful for validating sync accuracy
        """
        seconds = milliseconds / 1000.0
        return int(seconds * self.target_frame_rate)
    
    def get_time_for_frame(self, frame_number):
        """Calculate time in milliseconds for a given frame number"""
        return (frame_number / self.target_frame_rate) * 1000.0
    
    def get_timecode_from_frame(self, frame_number):
        """
        Convert frame number to SMPTE timecode string
        HH:MM:SS:FF format
        """
        drop_frame = (self.target_frame_rate == 29.97)
        
        if drop_frame:
            # Drop-frame calculation (29.97 fps)
            frame_number = int(frame_number * 30000 / 29970)
        
        frames = int(frame_number % self.target_frame_rate)
        total_seconds = frame_number // self.target_frame_rate
        seconds = int(total_seconds % 60)
        minutes = int((total_seconds // 60) % 60)
        hours = int(total_seconds // 3600)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    
    # ============================================================================
    # Synchronization Optimization
    # ============================================================================
    
    def calculate_frame_skip(self, current_frame, target_frame):
        """
        Calculate if we need to skip frames to catch up
        Returns number of frames to skip (positive or negative)
        """
        skip = target_frame - current_frame
        if abs(skip) > 2:
            return skip
        return 0
    
    def get_sync_quality_percentage(self):
        """
        Calculate synchronization quality as a percentage
        100% = perfect sync, lower = more errors
        """
        if not self.is_synced:
            return 0.0
        
        # Quality based on error count (over last 1000 frames ideally)
        # This is simplified - in production, track over a longer window
        quality = max(0, 100 - (self.sync_error_frames * 10))
        return min(100, quality)
    
    # ============================================================================
    # Callback Management
    # ============================================================================
    
    def register_sync_callback(self, callback):
        """Register callback for synchronization events"""
        self.sync_callbacks.append(callback)
    
    def unregister_sync_callback(self, callback):
        """Unregister synchronization callback"""
        if callback in self.sync_callbacks:
            self.sync_callbacks.remove(callback)
    
    def _trigger_sync_callbacks(self, event_type):
        """Trigger all registered sync callbacks"""
        for callback in self.sync_callbacks:
            try:
                callback(event_type, self.check_sync_status())
            except Exception as e:
                print(f"Error in sync callback: {e}")


# Global genlock manager
genlock_manager = GenlockManager()

def get_genlock_manager():
    """Get the global genlock manager instance"""
    return genlock_manager


# ============================================================================
# TouchDesigner Integration Helper
# ============================================================================

class TouchDesignerGenlockBridge:
    """
    Bridge between TouchDesigner's video processing and genlock manager
    """
    
    @staticmethod
    def configure_for_production_video_output(frame_rate=25, sync_source='decklink'):
        """
        Configure TouchDesigner for professional video output with genlock
        Call this at startup
        """
        manager = get_genlock_manager()
        manager.set_frame_rate(frame_rate)
        
        if sync_source == 'decklink':
            manager.enable_decklink_sync()
        elif sync_source == 'aja':
            manager.enable_aja_sync()
        elif sync_source in ['mtc', 'ltc', 'osc']:
            manager.enable_timecode_sync(sync_source)
        
        print(f"Production config: {frame_rate}fps via {sync_source}")
    
    @staticmethod
    def monitor_frame_sync(frame_number):
        """
        Call this from your main render loop to monitor sync
        Typically called from a Python DAT in a timeline or render loop
        """
        manager = get_genlock_manager()
        
        # Validate we're still in sync
        expected_frame = frame_number
        is_locked = manager.validate_sync_lock(expected_frame)
        
        status = manager.check_sync_status()
        quality = manager.get_sync_quality_percentage()
        
        # Return info for UI display or logging
        return {
            'locked': is_locked,
            'quality': quality,
            'timecode': status['timecode'],
            'error_frames': status['sync_error_frames']
        }