from Almada.clock import shared_clock as clock

class B(object):
    """docstring for B"""
    
    def advance_time(self, interval):
        now = clock.get_time()
        should_be = now + interval
        clock.set_time(should_be)
        print "Error: %.2f" % (clock.get_time() - should_be)
    
        