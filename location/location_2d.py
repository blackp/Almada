"""
Utility maths for working with 2D locations.
"""

import math
import numpy

class Grid(object):
    "Partition a rectangular region into a grid of square cells with a given size"
    
    def __init__(self, min_x, max_x, min_y, max_y, size=0.25):
        super(Grid, self).__init__()
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.size = size
        
        self.range_x = max_x - min_x
        self.range_y = max_y - min_y
        assert (self.range_x > 0 and self.range_y > 0), "Max bounds should be greater than min bounds"
        
        self.n_x = int(math.ceil(self.range_x / size))
        self.n_y = int(math.ceil(self.range_y / size))
        
    def coordinate_to_index(self, x, y):
        "What grid index does x, y fall in?"
        
        ix = (x - self.min_x) / self.size
        iy = (y - self.min_y) / self.size
    
        return int(ix), int(iy)
        
    def index_to_coordinate(self, grid_x, grid_y, alpha_x=0.5, alpha_y=0.5):
        "x, y coordinates for grid indices (position within cell defaults to centre, defined by alphas)"
        
        x = self.min_x + (grid_x + alpha_x) * self.size
        y = self.min_y + (grid_y + alpha_y) * self.size
        
        return x, y
        
    def divmod(self, i):
        return divmod(i, self.n_y)
        
    def cell_indices(self):
        
        return [(ix, iy) for ix in range(self.n_x) for iy in range(self.n_y)]
        
    def array(self, ones=False):
        "A 2D numpy array of the appropriate size, set to zeros by default (otherwise ones)."
        
        size = (self.n_x, self.n_y)
        if ones:
            return numpy.ones(size)
        else:
            return numpy.zeros(size)

def distance(a, b):
    "Distance between two points."
    xa, ya = a
    xb, yb = b
    return math.hypot(xa - xb, ya - yb)
    
def expected_distances(x, y, anchors, perturb_function=None):
    """
    A dictionary of expected distances as measured by a tag at 'x', 'y' amongst 'anchors'.
    """

    distances = {}

    for anchor_id, location in anchors.iteritems():
        ax, ay = location
        d = math.hypot(ax - x, ay - y)
        if perturb_function:
            d = perturb_function(d)
        distances[anchor_id] = d
        
    return distances

