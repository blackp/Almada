"""
LocMod (or Location Module - could do with a better name).

This module provides the logic which turns the distance estimates we get 
from the tags into position estimates for each tag.

The basic LocMod interface is simple:
 - add_reading: Add each distance reading one by one. (Should be very lightweight - little computation)
 - update_location: Perform the position estimates. (This is the part that is most computationally intensive)
 - tag_positions: Return the current position estimate for each tag. (Also, lightweight (and is returned by update_locations))

Any object that provides the above three methods can serve as a LocMod, 
but a reference implementation is provided below.

The reference imlementation is made generic by its separation into three parts.
 - Distance Filter: Maintains the history of distance readings for each tag-anchor pair, and provides the best current estimate.
 - Location Engine: Does the main computation of turning the above distance estimates into location estimates.
 - Position Filter: Provides filtering on the location estimates provided by the location engine.

Everything is assumed to be happening as close to real time as possible, so no timestamps are involved in any of the interfaces. 
However, all modules use the clock module to synchronise time, so non-realtime behaviour can be achieved.

The precise interfaces for the three components are listed in their respective files.

The factory method "new_locmod(config)" is responsible for creating a LocMod according to a given configuration

Philip Blackwell - September 2009
"""

import logging

from Almada.location.distance_filter import DistanceFilter
from Almada.location.position_filter import PositionFilter

class LocMod(object):
    """Generic Location Module. Comprising of a Distance Filter, Location Engine, and Position Filter"""
    def __init__(self, anchors, distance_filter, location_engine, position_filter):
        super(LocMod, self).__init__()
        
        self.distance_filter = distance_filter
        self.location_engine = location_engine
        self.position_filter = position_filter
    
        self.tag_ids = set()
        self.anchors = anchors
                                         
    def add_reading(self, anchor_id, tag_id, distance):
        "Add a distance reading: The distance to an anchor as estimated by a tag."

        if not anchor_id in self.anchors:
            logging.warning("Received distance measurement for unknown anchor: %d" % anchor_id)
            return

        self.distance_filter.add_reading(anchor_id, tag_id, distance)
                
        self.tag_ids.add(tag_id)

    def update_locations(self, tag_ids=[]):
        "Perform the location estimates based on the current best distance estimates."
        
        if not tag_ids:
            tag_ids = self.tag_ids
        
        tag_locations = {}

        for tag_id in tag_ids:
            distances = self.distance_filter.distances(tag_id)
            if self.location_engine:
                location = self.location_engine.coordinates(distances)
                tag_locations[tag_id] = location
                logging.info("Estimated location for tag %d: (%.2f %.2f)" % (tag_id, location[0], location[1]))
            
        self.position_filter.add_updates(tag_locations)

        return self.position_filter.tag_locations(tag_ids)

    def tag_positions(self, tag_ids=[]):
        """
        Get the current position estimate for each tag. 
        Lightweight, in that it doesn't go the location_engine (just the position_filter)
        """
        
        if not tag_ids:
            tag_ids = self.tag_ids
            
        return self.position_filter.tag_locations(tag_ids)
        
def new_locmod(config):
    """A new LocMod object (or similar) according to the given configuration (Config object)."""
    
    anchors = config.anchors
    
    if config.location_engine_type == "ParticleFilter":
        from particle_filter import ParticleFilter
        locmod = ParticleFilter(anchors, **config.particle_filter)
        return locmod
        
    distance_filter = DistanceFilter(**config.distance_filter)        
    position_filter = PositionFilter(**config.position_filter)
    
    if config.location_engine_type == "LocationEnginePDF":
        from location_engine_pdf import LocationEnginePDF    
        location_engine = LocationEnginePDF(anchors, **config.location_engine)
    elif config.location_engine_type == "LeDLL":
        from location_engine_ledll import LeDLL
        location_engine = LeDLL(anchors, **config.location_engine)
    elif config.location_engine_type == "LocationEngineMatch":
        from location_engine_match import LocationEngineMatch
        location_engine = LocationEngineMatch(**config.location_engine)
    else:
        raise Exception("Unspecified Location Engine")        

    locmod = LocMod(anchors, distance_filter, location_engine, position_filter)
    return locmod
