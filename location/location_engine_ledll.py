#!/usr/bin/env python
# encoding: utf-8

"""
Wrapper for the Nanotron Location Engine dll (ledll.dll)

Created by Philip Blackwell on 2009-08-24.
"""

import math
import ctypes
import logging
from ctypes.util import find_library

class LeDLL(object):
    """
    Wrapper for the Nanotron Location Engine dll
    """
    
    le_dll_file = find_library("ledll.dll")
    logging.info("loading dll: %s" % le_dll_file)
    le_dll = ctypes.cdll.LoadLibrary (le_dll_file)
    
    # Describe function prototypes
    le_create_proto = ctypes.CFUNCTYPE (ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_byte, ctypes.POINTER(ctypes.c_double))
    le_coordinates_proto = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_ubyte, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double))
    le_destroy_proto = ctypes.CFUNCTYPE(None, ctypes.c_int)
    
    # Map function calls    
    le_create = le_create_proto (("le_create", le_dll))
    le_coordinates = le_coordinates_proto(("le_coordinates", le_dll))
    le_destroy = le_destroy_proto(("le_destroy", le_dll))
    
    def  __init__(self, anchors, edge_length=0.25, distance_margin=1.5):
        """
        Initialise with a dictionary of anchors (id->(x,y), and other parameters)
        """
        super(LeDLL, self).__init__()
        
        self.anchors = anchors
        self.edge_length = edge_length
        self.distance_margin = distance_margin
        
        anchors_array_type = ctypes.c_double * (len(anchors) * 2)
        anchors_array = anchors_array_type()
        
        distances_array_type = ctypes.c_double * len(anchors)
        self.distances_array = distances_array_type()
        self.n_distance = ctypes.c_ubyte(len(anchors))
        
        location_array_type = ctypes.c_double * 2
        self.location_array = location_array_type()
        
        anchor_ids = anchors.keys()
        anchor_ids.sort()
        self.anchor_ids = anchor_ids
        
        for i, anchor_id in enumerate(anchor_ids):
            x, y = anchors[anchor_id]
            anchors_array[i * 2] = x
            anchors_array[i * 2 + 1] = y

        handle = self.le_create(ctypes.c_double(edge_length), 
                                ctypes.c_double(distance_margin), 
                                ctypes.c_byte(len(anchors)), 
                                anchors_array)
        self.handle = ctypes.c_int(handle)

#    def __del__(self):
#        "Destroy the underlying location engine."        
#        
#        self.le_destroy(self.handle)

    def coordinates(self, distances):
        """
        The coordinates of the most likely tag location (x,y) that would give rise to the given distance measurements
        Distances can either be a dictionary (base_id -> d) or a list of distances (in order of base id).
        """
        
        for i, anchor_id in enumerate(self.anchor_ids):
            if distances.has_key(anchor_id):
                self.distances_array[i] = distances[anchor_id]
            else:
                self.distances_array[i] = -1.0

        self.le_coordinates(self.handle, self.n_distance, self.distances_array, self.location_array)
        x, y = self.location_array
        
        return x, y

    def expected_distances_for_tag_location(self, x, y, include_margin=False):
        """
        A dictionary giving the expected distances as measured by a tag at 'x', 'y'.
        """

        distances = {}

        for anchor_id in self.anchor_ids:
            ax, ay = self.anchors[anchor_id]
            distances[anchor_id] = math.hypot(ax - x, ay - y)
            
        return distances
            
            
if __name__ == "__main__":
    
    # Run a quick test.
    
    l, b, t, r = 0.0, 0.0, 10.0, 10.0 
    anchors = {1:(l, b), 2:(l, t), 3:(r,b), 4:(r,t)}
    le = LocationEngine(anchors)
    for x, y in [(l,b), (l, (b + t) / 2.0), ((l + r) / 2.0, (b + t) / 2.0)]:
        distances = le.expected_distances_for_tag_location(x, y)
        cx, cy = le.coordinates(distances)
        print "(%.2f, %.2f) expected (%.2f, %.2f) error: %.2f" % (cx, cy, x, y, (math.hypot(cx - x, cy - y)))
    
    
