"""
Various 2D geometry functions
"""

import math

def distance_2d(a, b):
    xa, ya = a
    xb, yb = b
    
    return math.hypot(xa - xb, ya - yb)
