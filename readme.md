#Spectrum Analyzer with Launchpad functionality
##Introduction
This is a modification of Onno Hoekstra's Spectrum Analyzer (http://www.qsl.net/pa2ohh/11sa.htm).

The Launchpad porting isn't perfect, and I aim to improve it's mapping accuracy in the future.

##Launchpad Stuff
launchpad() is a function that ports the line graph array produced by Hoekstra's script to the Novation Launchpad. 

The maths involves dividing the T1Line array into eight chunks and getting a peak value for each chunk. The chunks represent a frequency range, and the peak value would be the peak volume of any freqency within the range. Then after a little more value manipulation/mapping it's then ported to the Launchpad.