#!/usr/bin/env python
# encoding: utf-8

"""
Created by Philip Blackwell on 2009-09-22.
"""

import math
import logging
import random

from Almada.location.distance_filter import DistanceFilter
from Almada.clock import shared_clock as clock
from Almada.location.distance_model import DistanceModel

class ParticleGenerator(object):
    """docstring for ParticleGenerator"""
    def __init__(self, min_x, max_x, min_y, max_y):
        super(ParticleGenerator, self).__init__()
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        
    def new_particle(self):
        """Randomly generate a new """
        
        x = random.uniform(self.min_x, self.max_x)
        y = random.uniform(self.min_y, self.max_y)
        return x, y

class Particle(object):
    """docstring for Particle"""
    def __init__(self, location, errors):
        super(Particle, self).__init__()
        self.location = location
        self.errors = errors
        self.cluster = None
        self.score = None
        
    def perturb(self, period):
        "Change the location by some random amount according to how long it's been."
    
        
class ParticleCloud(object):
    """
    
    """
        
    def  __init__(self, anchors, particle_count=100, discard_ratio=0.2):
        """
        
        """

        super(ParticleCloud, self).__init__()
        self.anchors = anchors
        self.discard_ratio = discard_ratio
        self.particle_count = particle_count
        self.min_distances = 3
        self.last_perturb_time = 0.0
        self.particles = []
        self.distances = {} # The current estimated distance to each anchor.
        #self.score_function = self.score_best_errors() # A function which takes a single particle, and returns a score based on its errors (lower is better)
        self.score_function = self.score_p()
        self.score_function = self.score_best_p()
      

    def set_distances(self, distances):
        """Update each of the particles for the new distance measurements."""
        
        if len(distances) >= self.min_distances:
            # If there are sufficient numbers in the new distances, just use them and discard the old.
           self.distances = distances
        else:
            # Otherwise, update the new ones, but hold on to the old ones too.
            for anchor_id, distance in distances.iteritems():
                self.distances[anchor_id] = distance
        
        for particle in self.particles:
            particle.errors = self.errors(particle.location)
                
    def errors(self, location):
        """What are the errors, for this location according to the current distance measurements."""
        x, y = location
        
        result = []
        for anchor_id, distance in self.distances.iteritems():
            ax, ay = self.anchors[anchor_id]
            d = math.hypot(ax - x, ay - y)
            result.append(distance - d)
            
        return result
        
    def cull_particle(self, particle):
        "Based on the errors, should this particle be culled?"
        
        if min(particle.errors) < 0:
            return True
            
        return False
        
    def cull(self):
        "Cull particles"
        original_len = len(self.particles)
        self.particles = filter(lambda x: not self.cull_particle(x), self.particles)
        logging.info("Culled %d (out of %d) particles" % (len(self.particles) - original_len, original_len))
            
    def score(self):
        "Set the score for each particle."
        
        for particle in self.particles:
            particle.score = self.score_function(particle)

    def discard(self):
        """Sort the particles by their score, then remove the worst"""
        self.particles.sort(lambda x, y: cmp(x.score, y.score))
        keep = int(self.particle_count * (1 - self.discard_ratio))
        self.particles = self.particles[:keep]
        
        logging.debug("Particles after discard: %d" % len(self.particles))
        
    def perturb(self):
        """Perturb each of the particles in the cloud according to the given perturbation function"""
        
        now = clock.get_time()
        
        period = now - self.last_perturb_time
        for particle in self.particles:
            particle.perturb(period)
            
    def generate_new(self, particle_generator):
        """Generate new particles up to 'particle_count', such that """
        
        i = 0
        while len(self.particles) < self.particle_count:
            i += 1
            if i > 100:
                break
            location = particle_generator.new_particle()
            particle = Particle(location, self.errors(location))
            if not self.cull_particle(particle):
                self.particles.append(particle)
    
    def location(self):
        """
        The representitive location of the particle cloud.
        
        
        For now, geometric average location of all particles in order of score. 
        """
        
        rx, ry = self.particles[0].location
        #for particle in self.particles:
        #    x, y = particle.location
        #    rx = (rx + x) / 2.0
        #    ry = (ry + y) / 2.0
        
        logging.debug("Location for particle cloud: (%.2f, %.2f)" % (rx, ry))
        return rx, ry
          
    def score_best_p(self, n=3):

        distance_model = DistanceModel()

        def f(particle):
            
            probabilities = [distance_model.error_probability(e) for e in particle.errors]

            probabilities.sort()
            probabilities.reverse()

            probability = 1
            
            for p in probabilities[:n]:
                probability *= p

            return 1 - p

        return f



    def score_p(self):

        distance_model = DistanceModel()

        def f(particle):
            
            p = 1

            for error in particle.errors:
                p *= distance_model.error_probability(error)
         
            return 1 - p

        return f

    def score_best_errors(self, n=3):
        "The sum of the N minimum errors"

        def f(particle):

            if n > len(self.distances):
                raise Exception("Not enough distance measurements: %d > %d" % (n, len(self.distances)))

            particle.errors.sort()
            return sum(particle.errors[:n])

        return f
        
    
        
class ParticleFilter(object):
    """docstring for LocationEngineParticleFilter"""
    def __init__(self, anchors):
        super(ParticleFilter, self).__init__()
        self.anchors = anchors
        self.particle_clouds = {} # By tag ID
        self.distance_filter = DistanceFilter()
        self.set_particle_generator()
        
    def set_particle_generator(self, particle_generator=None):
        
        x, y = self.anchors.values()[0]
        
        if particle_generator == None:
            min_x, min_y = x, y
            max_x, max_y = x, y
            for anchor_id, location in self.anchors.iteritems():
                x, y = location
                min_x = min(x, min_x)
                max_x = max(x, max_x)
                min_y = min(y, min_y)
                max_y = max(y, max_y)
            self.particle_generator = ParticleGenerator(min_x, max_x, min_y, max_y)
        else:
            self.particle_generator = particle_generator
                                                                 
    def add_reading(self, anchor_id, tag_id, distance):
        "FIXME: Docstring"

        if not anchor_id in self.anchors:
            logging.warning("Received distance measurement for unknown anchor: %d" % anchor_id)
            return

        self.distance_filter.add_reading(anchor_id, tag_id, distance)
        if not self.particle_clouds.has_key(tag_id):
            self.particle_clouds[tag_id] = ParticleCloud(self.anchors)
                
    def update_locations(self, tag_ids=[]):
        
        if not tag_ids:
            tag_ids = self.particle_clouds.keys()

        result = {}
                
        for tag_id in tag_ids:
            if not self.particle_clouds.has_key(tag_id):
                continue
            particle_cloud = self.particle_clouds[tag_id]
            particle_cloud.set_distances(self.distance_filter.distances(tag_id))
            particle_cloud.perturb()
            particle_cloud.cull()
            particle_cloud.generate_new(self.particle_generator)
            particle_cloud.score()
            particle_cloud.discard()
            try:
                result[tag_id] = particle_cloud.location()
            except Exception, e:
                logging.error("Error getting location for cloud with particles")
                
        return result
