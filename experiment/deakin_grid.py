#!/usr/bin/env python

"""
The grid that makes up the fake ceiling in the Deakin office is very convenient for reference locations.

We have labelled the external corner of the meeting room as the origin.
Along the long wall we have alphabetical labels, from A to R, along the short wall we have numerical labels starting from 1 to 13.
The (internal) measurements for the whole office is 20.53m by 7.50m.

Philip Blackwell December 2009
"""

startLetter = 'A'
endLetter = 'R'
startNumber = 1
endNumber = 13

# Size of the grid rectangles in metres
sizeX = 1.20
sizeY = 0.60

# Measure the offset of the first bar from the wall in each direction
startOffsetX = 0.87 # 'A'
startOffsetY = 0.44 # '1'
endOffsetX = 0.45 # 'R'
endOffsetY = 0.43 # '13'

def xFromLetter(letter):
    "The distance in metres from the origin to the centre of the grid at the given letter"

    letter = letter.upper()
    
    n = ord(letter) - ord(startLetter) - 1  
    
    if not startLetter <= letter <= endLetter:
        raise
    
    if letter == startLetter:
        result = startOffsetX / 2
    elif letter == endLetter:
        result = startOffsetX + n * sizeX + endOffsetX / 2
    else:
        result = startOffsetX + (n + 0.5) * sizeX
                
    return result
    
def yFromNumber(number):
    "The distance in metres from the origin to the centre of the grid at the given number"

    n = number - startNumber - 1
    
    if not 1 <= number <= 13:
        raise
    
    if number == startNumber:
        result = startOffsetY / 2
    elif number == endNumber:
        result = startOffsetY + n * sizeY + endOffsetX / 2
    else:
        result = startOffsetY + (n + 0.5) * sizeY
        
    return result

def referencePoints(start=None, letterSpan=1, numberSpan=1):

    if start == None:
        startL, startN = startLetter, startNumber
    else:
        startL, startN = start

    letter = startL
    while letter <= endLetter:
    
        number = startN
        while number <= endNumber:
            print "Reference: %s%02d; %.2f, %.2f" % (letter, number, xFromLetter(letter), yFromNumber(number))
            number += numberSpan
    
        letter = chr(ord(letter) + letterSpan)

def test():
    
    letter = startLetter
    while letter <= endLetter:
        print "%s %.2f" % (letter, xFromLetter(letter))
        letter = chr(ord(letter) + 1)
    
    number = startNumber
    while number <= endNumber:
        print "%d %.2f" % (number, yFromNumber(number))
        number += 1
    
    yFromNumber(13)
from optparse import OptionParser

##############################
# Command line options.
##############################


option_parser = OptionParser()
options, args = option_parser.parse_args()

if len(args) == 2:
    letter, number = args
    number = int(number)
    x = xFromLetter(letter)
    y = yFromNumber(number)
    
    print "%.2f %.2f" % (x, y)


else:
    #referencePoints(("B", 2), 2, 3)
    referencePoints()