"""
Location Engine PDF

A brute force location module that calculates the entire probability density function 
for each measurement and combines them together.

Currently, it is too slow to use in real time - but it may be useful for visually observing 
underlying probability models used in more efficient location modules.

Philip Blackwell on 2009-09-16.
"""

import math

from Almada.location.location_2d import Grid
from Almada.location.distance_model import DistanceModel, UniformDistanceModel
                
class LocationEnginePDF(object):
    """
    Location Engine based on probability distributions
    """
        
    def  __init__(self, anchors, distance_model=None, edge_length=0.25):
        """
        Initialise with a dictionary of anchors (id->(x,y), and other parameters)
        """
        super(LocationEnginePDF, self).__init__()
        
        self.anchors = anchors
        self.edge_length = edge_length
        if distance_model == None:
            distance_model = DistanceModel()
        self.distance_model = distance_model
        self.pdfs = {}
        
        # Find the range in x and y of the anchor positions
        x, y = anchors.values()[0]
        min_x, min_y = x, y
        max_x, max_y = x, y
        for anchor_id, location in anchors.iteritems():
            x, y = location
            min_x = min(x, min_x)
            max_x = max(x, max_x)
            min_y = min(y, min_y)
            max_y = max(y, max_y)
        
        self.grid = Grid(min_x - 1, max_x + 1, min_y - 1, max_y + 1)                
        
        self.combine_pdfs = self.multiply_pdfs
            
    def set_standard(self):
        self.distance_model = DistanceModel()
        self.combine_pdfs = self.multiply_pdfs
        self.pdfs = {}
            
    def set_uniform(self):
        self.distance_model = UniformDistanceModel()
        self.combine_pdfs = self.add_pdfs
        self.pdfs = {}
    
    def generate_pdf(self, anchor_id, estimated_distance):
        "A numpy array representing the probability of a tag being at each grid cell, given the distance from a particular base station."
        
        ax, ay = self.anchors[anchor_id]
        
        array = self.grid.array()
        for ix, iy in self.grid.cell_indices():
            x, y = self.grid.index_to_coordinate(ix, iy)
            d = math.hypot(x - ax, y - ay)
            array[ix][iy] = self.distance_model.distance_probability(d, estimated_distance)
            
        return array
        
    def round_distance(self, distance):
        
        return float("%.1f" % distance)
        
    def pdf(self, anchor_id, estimated_distance):
        
        estimated_distance = self.round_distance(estimated_distance)
        key = anchor_id, estimated_distance
        if not self.pdfs.has_key(key):
            self.pdfs[key] = self.generate_pdf(*key)
        return self.pdfs[key]
        
    def add_pdfs(self, distances):
        ""
        pdf = self.grid.array(ones=False)
        
        for anchor_id, estimated_distance in distances.iteritems():
            pdf += self.pdf(anchor_id, estimated_distance)
        return pdf
            
    def multiply_pdfs(self, distances):
        
        pdf = self.grid.array(ones=True)
        
        for anchor_id, estimated_distance in distances.iteritems():
            pdf *= self.pdf(anchor_id, estimated_distance)
        return pdf
                
    def coordinates(self, distances):
        """
        The coordinates of the most likely tag location (x,y) that would give rise to the given distance measurements
        Distances can either be a dictionary (base_id -> d) or a list of distances (in order of base id).
        """
        
        pdf = self.combine_pdfs(distances)
        i = pdf.argmax()
        ix, iy = self.grid.divmod(i)
        x, y = self.grid.index_to_coordinate(ix, iy)
        
        return x, y

            
if __name__ == "__main__":
    
    # Run a quick test.
    from almada import Config
    from location_2d import expected_distances
    config = Config()
    config.load_file("almada.cfg")
    location_engine = LocationEnginePDF(config.anchors)
    distances = expected_distances(5, 5, config.anchors)
    n09 = 8, 9
    n09_distances = {1: 9.76, 2:5.41, 4:21.05, 5: 4.12, 6:11.02, 7:17.66, 8:14.51}
    t05 = 14, 5
    t05_distances = {2:12.93, 3:12.74, 4:18.57, 6:9.25, 8:14.47}
    
    print n09, location_engine.coordinates(n09_distances)
    print t05, location_engine.coordinates(t05_distances)
    
    location_engine.set_uniform()
    print n09, location_engine.coordinates(n09_distances)
    print t05, location_engine.coordinates(t05_distances)
    