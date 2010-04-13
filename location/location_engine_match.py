"""
Location Engine Match


Philip Blackwell Feb 2010
"""

import os
import logging

from Almada.location.nearest_neighbour import CanonicalObservationDatabase
                
class LocationEngineMatch(object):
    """
    """
        
    def  __init__(self, observation_database="observations.db", error_bound=1.0):
        """        
        """
        
        if not os.path.exists(observation_database):
            raise Exception("Observation file doesn't exist: %s" % observation_database)
        
        self.error_bound = error_bound
        self.observations = CanonicalObservationDatabase(observation_database)
        

    def coordinates(self, distances):
        """
        """
        
        possible_matches = self.observations.possible_locations(distances, self.error_bound)
        
        if not possible_matches:
            return 0.0, 0.0
        
        sum_x, sum_y = 0.0, 0.0
        for x, y in possible_matches:
            sum_x += x
            sum_y += y
        
        n = len(possible_matches)
        
        x = sum_x / n
        y = sum_y / n
        
        logging.debug("Found centroid of % d possible matches: (%.2f, %.2f)" % (n, x, y))
        
        return x, y
