from Almada.clock import shared_clock as clock
import clock_test_b
import time

if __name__ == "__main__":
    b = clock_test_b.B()
    
    for i in range(10):
        start_time = clock.get_time()
        b.advance_time(i)
        time.sleep(1)
        wait_time = clock.get_time() - start_time
        print "Slept for %.2f seconds" % (wait_time)
        
