import logging
import numpy

from Almada.clock import shared_clock as clock

class DistanceFilterTypes(object):
    
    null = "null"
    median_filter = "median_filter"
    most_recent = "most_recent"
    types = [null, median_filter, most_recent]

class DistanceReading(object):
    """Simple class for keeping the attributes of a distance reading."""
    
    def __init__(self, anchor_id, tag_id, distance, timestamp=None):
        super(DistanceReading, self).__init__()
        self.anchor_id = anchor_id
        self.tag_id = tag_id
        self.distance = distance
        if timestamp == None:
            timestamp = clock.get_time()
        self.timestamp = timestamp
        
class DistanceFilter(object):
    """docstring for DistanceFilter"""
        
    max_readings = 10 # The maximum number of readings to keep (per pair)
    
    def __init__(self, name=None):
        super(DistanceFilter, self).__init__()
            
        if name == None:
            name = DistanceFilterTypes.null
    
        if not name in DistanceFilterTypes.types:
            logging.error("Unexpected name for distance filter: %s" % name)
            name = DistanceFilterTypes.null
        self.name = name
        self.readings = {}

        logging.debug("Initialised distance filter: %s" % self.name)

    def add_reading(self, anchor_id, tag_id, distance):
        "FIXME: Docstring"

        pair = (anchor_id, tag_id)
        if not self.readings.has_key(pair):
            self.readings[pair] = []
        
        self.readings[pair].insert(0, DistanceReading(anchor_id, tag_id, distance))
        
        # Ensure we aren't keeping too many.
        while len(self.readings[pair]) > self.max_readings:
            self.readings[pair].pop()
        
    def most_recent_distance(self, distance_readings):
        "The distance of the most recent reading."
        if distance_readings:
            distance_reading = distance_readings[0]
            return distance_reading.distance
        else:
            return None

    def median_distance(self, distance_readings, max_age=2.0):
        "Return the median distance of all the readings within max_age"
        
        now = clock.get_time()
        distances = [r.distance for r in distance_readings if now - r.timestamp < max_age]
        if distances:
            logging.debug("Returning median of %d distances" % len(distances))
            return numpy.median(distances)
        else:
            return None
            
    def distances(self, tag_id):
        "Current distance readings for the given tag."
        result = {}
        
        for pair, distance_readings in self.readings.iteritems():
            anchor_id, tid = pair
            if not tid == tag_id:
                continue
            
            # Establish the distance
            if self.name == DistanceFilterTypes.median_filter:
                distance = self.median_distance(distance_readings)
            else:
                distance = self.most_recent_distance(distance_readings)
            
            if distance != None:
                result[anchor_id] = distance

            # We want to clear all old readings for a null filter.
            if self.name == DistanceFilterTypes.null:
                self.readings[pair] = []
            
        return result
        
        
if __name__ == "__main__":
    filter = DistanceFilter(DistanceFilterTypes.null)