# Some basic sounds for operator feed back
# Philip Blackwell January 2010

import sys
import logging

try:
    from AppKit import NSSound
except None:
    logging.error("Error importing from AppKit: " + str(e))
    # We won't be able to get Apple system sounds, but oh well.
    pass

from Almada.experiment.ground_truth import GroundTruthAction

class Sound(object):
    """Simple wrapper for NSSound. Just provides play."""
    
    def __init__(self, filename):
        self._sound = NSSound.alloc()
        self._sound.initWithContentsOfFile_byReference_(filename, True)
        self.filename = filename
        
    def play(self):
        if self._sound.isPlaying():
            print "Playing"
            self._sound.stop()
        self._sound.setCurrentTime_(0.0)
        
        self._sound.play()

class Beep(object):
    """docstring for Beep"""
            
    def play(self):
        print('\a')

try:
    action_sounds = {GroundTruthAction.arrived_code: Sound("/System/Library/Sounds/Ping.aiff"),
                     GroundTruthAction.passed_code: Sound("/System/Library/Sounds/Morse.aiff"),
                     GroundTruthAction.heading_code: Sound("/System/Library/Sounds/Blow.aiff"),
                     GroundTruthAction.abandoned_code: Sound("/System/Library/Sounds/Basso.aiff")}

except Exception, e:
    logging.error("Error loading sounds: " + str(e))
    action_sounds = {GroundTruthAction.arrived_code: Beep(),
                     GroundTruthAction.passed_code: Beep(),
                     GroundTruthAction.heading_code: Beep(),
                     GroundTruthAction.abandoned_code: Beep()}
