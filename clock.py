"""
Keeps everything in sync.

No other code should call time.time(). All other modules use shared_clock.get_time()

To replay an experiment, we only need one module to keep the shared_clock at the right time. 
Other modules can assume things are happening in real time.


Example import statement:
from clock import shared_clock as clock

Philip Blackwell 2009-09-18
"""

import time

class Clock(object):
    """docstring for Clock"""
    
    def __init__(self):
        super(Clock, self).__init__()
        self.live = True
        self.time_offset = 0.0
        self.current_time = 0.0
        
    def get_time(self):
        "Main function that calling functions should use."
        if self.live:
            return time.time() - self.time_offset
        else:
            return self.current_time
        
    def set_time(self, timestamp):
        "Set the time such that get_time() == timestamp"
    
        if self.live:
            self.time_offset = time.time() - timestamp
        else:
            self.current_time = timestamp
        
    def pause(self, timestamp=None):
        "Pause the clock, optionally at a set time"
    
        if timestamp == None:
            self.current_time = self.get_time()
        else:
            self.current_time = timestamp
        
        self.live = False
    
    def resume(self, timestamp=None):
        "Restart the clock, optionally at a set time"
        
        self.live = True
    
        if timestamp == None:
            self.set_time(self.current_time)
        else:
            self.set_time(timestamp)
            
# The module keeps a singleton clock object.
# Importing modules can rename, but calling it shared_clock implies the appropriate use.
shared_clock = Clock()

