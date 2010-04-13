import numpy
import logging

from Almada.clock import shared_clock as clock

class PositionFilterTypes(object):

    most_recent = "most_recent"
    median_filter = "median"
    mean_filter = "mean"

class PositionUpdate(object):
    """Simple class for the data relating to a single position update"""
    def __init__(self, x, y):
        super(PositionUpdate, self).__init__()
        self.x = x
        self.y = y
        self.timestamp = clock.get_time()

class PositionFilter(object):
    """A filter for the x, y location estimates."""
    
    def __init__(self, name=None, update_rate=None, max_age=2.0):
        super(PositionFilter, self).__init__()
        if name == None:
            name = PositionFilterTypes.most_recent
        self.name = name
        self.update_rate = update_rate
        self.last_updates = {} # tag_id -> timestamp
        self.max_age = max_age
        self.tag_updates = {} # tag_id -> list(PositionUpdate)
        
        if name == PositionFilterTypes.most_recent:
            self.filter_function = self.most_recent_filter
        elif name == PositionFilterTypes.median_filter:
            self.filter_function = self.median_filter
        elif name == PositionFilterTypes.mean_filter:
            self.filter_function = self.mean_filter
        else:
            raise Exception("Unrecognised Position Filter type: %s" % name)
            
        logging.debug("Initialised position filter: %s" % self.name)
            
                        
    def add_updates(self, tags):
        "Add the location information given in the dictionary 'tags': tag_id -> (x,y)"
                
        # Add these tag updates to our history
        for tag_id, location in tags.iteritems():
            x, y = location
            if not self.tag_updates.has_key(tag_id):
                self.tag_updates[tag_id] = []
            self.tag_updates[tag_id].append(PositionUpdate(x, y))
        
    def cull_old(self):
        "Delete any position updates older than 'max_age'"
        oldest = clock.get_time() - self.max_age
        
        for tag_id, position_updates in self.tag_updates.iteritems():
            i = 0
            while i < len(position_updates):
                if position_updates[i].timestamp < oldest:
                    del position_updates[i]
                else:
                    i += 1
                
    def tag_locations(self, tag_ids=[]):
        "A dictionary of tag locations: tag_id -> (x,y)"

        now = clock.get_time()
        result = {}
                        
        self.cull_old()
                        
        for tag_id in tag_ids:
            if self.update_rate and (now - self.last_updates[tag_id] < self.update_rate):
                continue
            position_updates = self.tag_updates.get(tag_id)
            if position_updates:
                result[tag_id] = self.filter_function(position_updates)
                self.last_updates[tag_id] = now
            
        return result

    def most_recent_filter(self, position_updates):
        "Return the most recent position (x, y)"
        
        if position_updates:
            most_recent = position_updates[-1]
            return most_recent.x, most_recent.y

    def median_filter(self, position_updates):
        "Return the median position (x, y)"

        logging.info("Calculating median position from %d" % len(position_updates))

        x = numpy.median([update.x for update in position_updates])
        y = numpy.median([update.y for update in position_updates]) 

        return x, y

    def mean_filter(self, position_updates):
        "Return the mean position (x, y)"

        logging.info("Calculating mean position from %d" % len(position_updates))

        xs = [update.x for update in position_updates]
        ys = [update.y for update in position_updates]
        
        x = numpy.mean(xs)
        y = numpy.mean(ys)
        
        logging.debug("Min x: %05.2f Mean x: %05.2f Max x: %05.2f" % (min(xs), x, max(xs)))
        logging.debug("Min y: %05.2f Mean y: %05.2f Max y: %05.2f" % (min(ys), y, max(ys)))
        
        return x, y
