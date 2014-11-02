# SpectrumAnalyzer-v01c.py(w)  (26-10-2014)
# For Python version 2.6 or 2.7
# With external module pyaudio (for Python version 2.6 or 2.7); NUMPY module (for used Python version)
# Created by Onno Hoekstra (pa2ohh)
# Launchpad functionality by Siddharth Vadgama (@siddvee)

import pyaudio
import math
import time
import wave
import struct
import launchpad

import tkFont
from Tkinter import *
from tkFileDialog import askopenfilename
from tkSimpleDialog import askstring
from tkMessageBox import *


LP = launchpad.Launchpad()
LP.Open()
LP.Reset()

NUMPYenabled = True         # If NUMPY installed, then the FFT calculations is 4x faster than the own FFT calculation

# Values that can be modified
GRWN = 800                  # Width of the grid
GRHN = 400                  # Height of the grid
X0L = 20                    # Left top X value of grid
Y0T = 25                    # Left top Y value of grid

Vdiv = 8                    # Number of vertical divisions

TRACEmode = 1               # 1 normal mode, 2 max hold, 3 average
TRACEaverage = 10           # Number of average sweeps for average mode
TRACEreset = True           # True for first new trace, reset max hold and averageing 

SAMPLErate = 24000          # Sample rate of the soundcard 24000 48000 96000 192000
UPDATEspeed = 1.1           # Update speed can be increased when problems if PC too slow, default 1.1
ZEROpadding = 1             # ZEROpadding for signal interpolation between frequency samples (0=none)
                            
DBdivlist = [1, 2, 3, 5, 10, 20] # dB per division
DBdivindex = 4              # 10 dB/div as initial value

DBlevel = 0                 # Reference level

SMPfftlist = [64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536] # FFT samples list
SMPfftindex = 5             # index X (start with 0) from SMPfftlist as initial value


# Colors that can be modified
COLORframes = "#000080"     # Color = "#rrggbb" rr=red gg=green bb=blue, Hexadecimal values 00 - ff
COLORcanvas = "#000000"
COLORgrid = "#808080"
COLORtrace1 = "#00ff00"
COLORtrace2 = "#ff8000"
COLORtext = "#ffffff"
COLORsignalband = "#ff0000"
COLORaudiobar = "#606060"
COLORaudiook = "#00ff00"
COLORaudiomax = "#ff0000"


# Button sizes that can be modified
Buttonwidth1 = 12
Buttonwidth2 = 8


# Initialisation of general variables
STARTfrequency = 0.0        # Startfrequency
STOPfrequency = 10000.0     # Stopfrequency

                            
# Other global variables required in various routines
GRW = GRWN                  # Initialize GRW
GRH = GRHN                  # Initialize GRH

CANVASwidth = GRW + 2 * X0L # The canvas width
CANVASheight = GRH + 80     # The canvas height

AUDIOsignal1 = []           # Audio trace channel 1
AUDIOdevin = None           # Audio device for input. None = Windows default
AUDIOdevout = None          # Audio device for output. None = Windows default
WAVinput = 0                # DEFAULT 0 for Audio device input, 1 for WAV file channel 1 input, 2 for WAV file channel 2 input

FFTresult = []              # FFT result
T1line = []                 # Trace line channel 1
T2line = []                 # Trace line channel 2

S1line = []                 # Line for start of signal band indication
S2line = []                 # line for stop of signal band indication

RUNstatus = 1               # 0 stopped, 1 start, 2 running, 3 stop now, 4 stop and restart
AUDIOstatus = 0             # 0 audio off, 1 audio on
STOREtrace = False          # Store and display trace
FFTwindow = 5               # FFTwindow 0=None (rectangular B=1), 1=Cosine (B=1.24), 2=Triangular non-zero endpoints (B=1.33),
                            # 3=Hann (B=1.5), 4=Blackman (B=1.73), 5=Nuttall (B=2.02), 6=Flat top (B=3.77)
AUDIOlevel = 0.0            # Level of audio input 0 to 1

RXbuffer = 0.0              # Data contained in input buffer in %
RXbufferoverflow = False

if NUMPYenabled == True:
    try:
        import numpy.fft
    except:
        NUMPYenabled = False


# =================================== Start widgets routines ========================================
def Bnot():
    print "Routine not made yet"


def BNormalmode():
    global TRACEmode

    TRACEmode = 1
    UpdateScreen()          # Always Update
    

def BMaxholdmode():
    global TRACEmode
    global TRACEreset

    TRACEreset = True       # Reset trace peak and trace average
    TRACEmode = 2
    UpdateScreen()          # Always Update
    

def BAveragemode():
    global TRACEmode
    global TRACEaverage
    global TRACEreset

    TRACEreset = True       # Reset trace peak and trace average
    TRACEmode = 3

    s = askstring("Power averaging", "Value: " + str(TRACEaverage) + "x\n\nNew value:\n(1-n)")

    if (s == None):         # If Cancel pressed, then None
        return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        TRACEaverage = v

    if TRACEaverage < 1:
        TRACEaverage = 1
    UpdateScreen()          # Always Update


def BFFTwindow():
    global FFTwindow
    global TRACEreset
    
    FFTwindow = FFTwindow + 1
    if FFTwindow > 6:
        FFTwindow = 0
    TRACEreset = True       # Reset trace peak and trace average
    UpdateAll()             # Always Update


def BAudiostatus():
    global AUDIOstatus
    global RUNstatus
    
    if AUDIOstatus == 0:
        AUDIOstatus = 1
    else:
        AUDIOstatus = 0
    if RUNstatus == 0:      # Update if stopped
        UpdateScreen()


def BSTOREtrace():
    global STOREtrace
    global T1line
    global T2line
    if STOREtrace == False:
        T2line = T1line
        STOREtrace = True
    else:
        STOREtrace = False
    UpdateTrace()           # Always Update


def BScreensetup():
    global GRWN
    global GRW
    global GRHN
    global GRH
    global STOREtrace
    global Vdiv
    
    if (STOREtrace == True):
        showwarning("WARNING","Clear stored trace first")
        return()

    s = askstring("Screensize", "Give number:\n(1, 2 or 3)")

    # if (s == None):         # If Cancel pressed, then None
    #     return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        if v == 1:
            GRW = int(GRWN / 4)
            GRH = int(GRHN / 4)
        if v == 2:
            GRW = int(GRWN / 2)
            GRH = int(GRHN / 2)
        if v == 3:
            GRW = int(GRWN)
            GRH = int(GRHN)

    s = askstring("Divisions", "Value: " + str(Vdiv) + "\n\nNew value:\n(4-100)")

    if (s == None):         # If Cancel pressed, then None
        return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        Vdiv = v

    if Vdiv < 4:
        Vdiv = 4

    if Vdiv > 100:
        Vdiv = 100
    UpdateTrace()


def BStart():
    global RUNstatus
    
    if (RUNstatus == 0):
        RUNstatus = 1
    UpdateScreen()          # Always Update


def Blevel1():
    global RUNstatus
    global DBlevel

    DBlevel = DBlevel - 1
    
    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def Blevel2():
    global RUNstatus
    global DBlevel

    DBlevel = DBlevel + 1
    
    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def Blevel3():
    global RUNstatus
    global DBlevel

    DBlevel = DBlevel - 10
    
    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def Blevel4():
    global RUNstatus
    global DBlevel

    DBlevel = DBlevel + 10
    
    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def BStop():
    global RUNstatus
    
    if (RUNstatus == 1):
        RUNstatus = 0
    elif (RUNstatus == 2):
        RUNstatus = 3
    elif (RUNstatus == 3):
        RUNstatus = 3
    elif (RUNstatus == 4):
        RUNstatus = 3
    UpdateScreen()          # Always Update


def BSetup():
    global SAMPLErate
    global ZEROpadding
    global RUNstatus
    global AUDIOsignal1
    global T1line
    global TRACEreset
    
    if (RUNstatus != 0):
        showwarning("WARNING","Stop sweep first")
        return()
    
    s = askstring("Sample rate","Sample rate of soundcard.\n\nValue: " + str(SAMPLErate) + "\n\nNew value:\n(6000, 12000, 24000, 48000, 96000, 192000)")

    if (s == None):         # If Cancel pressed, then None
        return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        SAMPLErate = v
        AUDIOsignal1 = []   # Reset Audio trace channel 1    
        T1line = []         # Reset trace line 1
         
    # StartStop = askyesno("Start Stop","Start-Stop mode on?", default = NO)

    s = askstring("Zero padding","For better interpolation of levels between frequency samples.\nBut increases processing time!\n\nValue: " + str(ZEROpadding) + "\n\nNew value:\n(0-5, 0 is no zero padding)")

    if (s == None):         # If Cancel pressed, then None
        return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        if v < 0:
            v = 0
        if v > 5:
            v = 5
        ZEROpadding = v

    TRACEreset = True       # Reset trace peak and trace average
    UpdateScreen()          # Always Update    


def BStartfrequency():
    global STARTfrequency
    global STOPfrequency
    global RUNstatus

    # if (RUNstatus != 0):
    #    showwarning("WARNING","Stop sweep first")
    #    return()
    
    s = askstring("Startfrequency: ","Value: " + str(STARTfrequency) + " Hz\n\nNew value:\n")
    
    if (s == None):         # If Cancel pressed, then None
        return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        STARTfrequency = abs(v)

    if STOPfrequency <= STARTfrequency:
        STOPfrequency = STARTfrequency + 1

    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def BStopfrequency():
    global STARTfrequency
    global STOPfrequency
    global RUNstatus
    
    # if (RUNstatus != 0):
    #    showwarning("WARNING","Stop sweep first")
    #    return()

    s = askstring("Stopfrequency: ","Value: " + str(STOPfrequency) + " Hz\n\nNew value:\n")

    if (s == None):         # If Cancel pressed, then None
        return()

    try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
        v = int(s)
    except:
        s = "error"

    if s != "error":
        STOPfrequency = abs(v)

    if STOPfrequency < 10:  # Minimum stopfrequency 10 Hz
        STOPfrequency = 10
        
    if STARTfrequency >= STOPfrequency:
        STARTfrequency = STOPfrequency - 1

    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def Bsamples1():
    global SMPfftindex
    global RUNstatus
    global TRACEreset
    
    if (SMPfftindex >= 1):
        SMPfftindex = SMPfftindex - 1
        TRACEreset = True   # Reset trace peak and trace average
    if RUNstatus == 0:      # Update if stopped
        UpdateScreen()
    if RUNstatus == 2:      # Restart if running
        RUNstatus = 4


def Bsamples2():
    global SMPfftlist
    global SMPfftindex
    global RUNstatus
    global TRACEreset
      
    if (SMPfftindex < len(SMPfftlist) - 1):
        SMPfftindex = SMPfftindex + 1
        TRACEreset = True   # Reset trace peak and trace average
    if RUNstatus == 0:      # Update if stopped
        UpdateScreen()
    if RUNstatus == 2:      # Restart if running
        RUNstatus = 4


def BDBdiv1():
    global DBdivindex
    global RUNstatus
    
    if (DBdivindex >= 1):
        DBdivindex = DBdivindex - 1
    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()


def BDBdiv2():
    global DBdivindex
    global DBdivlist
    global RUNstatus
    
    if (DBdivindex < len(DBdivlist) - 1):
        DBdivindex = DBdivindex + 1
    if RUNstatus == 0:      # Update if stopped
        UpdateTrace()




# ============================================ Main routine ====================================================
    
def AUDIOin():   # Read the audio from the stream and store the data into the arrays
    global AUDIOsignal1
    global AUDIOdevin
    global AUDIOdevout
    global RUNstatus
    global AUDIOstatus
    global SMPfftlist
    global SMPfftindex
    global SAMPLErate
    global UPDATEspeed
    global RXbuffer
    global RXbufferoverflow
    
    while (True):                                           # Main loop
        PA = pyaudio.PyAudio()
        FORMAT = pyaudio.paInt16                            # Audio format 16 levels and 2 channels
        CHUNK = int(SMPfftlist[SMPfftindex])

        # RUNstatus = 1 : Open Stream
        if (RUNstatus == 1):
            if UPDATEspeed < 1:
                UPDATEspeed = 1.0

            TRACESopened = 1

            try:
                chunkbuffer = CHUNK
                if chunkbuffer < SAMPLErate / 10:            # Prevent buffer overload if small number of samples
                    chunkbuffer = int(SAMPLErate / 10)

                chunkbuffer = int(UPDATEspeed * chunkbuffer)
                
                stream = PA.open(format = FORMAT,
                    channels = TRACESopened, 
                    rate = SAMPLErate, 
                    input = True,
                    output = True,
                    frames_per_buffer = int(chunkbuffer),
                    input_device_index = AUDIOdevin,
                    output_device_index = AUDIOdevout)
                RUNstatus = 2
            except:                                         # If error in opening audio stream, show error
                RUNstatus = 0
                txt = "Sample rate: " + str(SAMPLErate) + ", try a lower sample rate.\nOr another audio device."
                showerror("Cannot open Audio Stream", txt)

            UpdateScreen()                                  # UpdateScreen() call        

            
        # RUNstatus = 2: Reading audio data from soundcard
        if (RUNstatus == 2):
            buffervalue = stream.get_read_available()       # Buffer reading testroutine
            RXbuffer = 100.0 * float(buffervalue) / chunkbuffer  # Buffer filled in %. Overflow at 2xchunkbuffer
            RXbufferoverflow = False
            try:
                signals = stream.read(chunkbuffer)          # Read samples from the buffer
            except:
                AUDIOsignal1 = []
                RUNstatus = 4
                RXbufferoverflow = True                     # Buffer overflow at 2x chunkbuffer

            if (AUDIOstatus == 1):                          # Audio on
                stream.write(signals, chunkbuffer)


            # Start conversion audio samples to values -32762 to +32767 (one's complement)
            Lsignals = len(signals)                         # Lenght of signals array
            AUDIOsignal1 = []                               # Clear the AUDIOsignal1 array for trace 1

            Sbuffer = Lsignals / 2                          # Sbuffer is number of values (2 bytes per audio sample value, 1 channel is 2 bytes)
            i = 2 * int(Sbuffer - CHUNK)                    # Start value, first part is skipped due to possible distortions

            if i < 0:                                       # Prevent negative values for i
                i = 0
                
            s = Lsignals - 1       
            while (i < s):
                v = ord(signals[i]) + 256 * ord(signals[i+1])
                if v > 32767:                               # One's complement correction
                    v = v - 65535
                AUDIOsignal1.append(v)                      # Append the value to the trace 1 array 
                i = i + 2                                   # 2 bytes per sample value and 1 trace is 2 bytes totally
            UpdateAll()                                     # Update Data, trace and screen


        # RUNstatus = 3: Stop
        # RUNstatus = 4: Stop and restart
        if (RUNstatus == 3) or (RUNstatus == 4):
            stream.stop_stream()
            stream.close()
            PA.terminate()
            if RUNstatus == 3:
                RUNstatus = 0                               # Status is stopped 
            if RUNstatus == 4:          
                RUNstatus = 1                               # Status is (re)start
            UpdateScreen()                                  # UpdateScreen() call

        # print SMPfftlist
        # print RXbuffer

        # Update tasks and screens by TKinter 
        root.update_idletasks()
        root.update()                                       # update screens

    
def WAVin():   # Read the audio from the WAV file and store the data into the array and read data from the array
    global WAVinput
    global WAVframes
    global WAVchannels
    global WAVsamplewidth
    global WAVframerate
    global WAVsignal1
    global WAVsignal2
    global WAVfilename

    global AUDIOsignal1
    global AUDIOdevin
    global AUDIOdevout
    global RUNstatus
    global AUDIOstatus
    global SMPfftlist
    global SMPfftindex
    global SAMPLErate
    global UPDATEspeed
    global RXbuffer
    global RXbufferoverflow
    
    while (True):                                           # Main loop
        CHUNK = int(SMPfftlist[SMPfftindex])

        # RUNstatus = 1 : Open WAV file
        if (RUNstatus == 1):
            chunkbuffer = CHUNK

            WAVfilename = ASKWAVfilename()

            if (WAVfilename == None): # No input, cancel or error
                WAVfilename = ""

            if (WAVfilename == ""):
                RUNstatus = 0
            else:
                WAVf = wave.open(WAVfilename, 'rb')
                WAVframes = WAVf.getnframes()
                # print "frames: ", WAVframes
                WAVchannels = WAVf.getnchannels()
                # print "channels: ", WAVchannels
                WAVsamplewidth = WAVf.getsampwidth()
                # print "samplewidth: ", WAVsamplewidth
                WAVframerate = WAVf.getframerate()
                # print "framerate: ", WAVframerate
                SAMPLErate = WAVframerate

                signals = WAVf.readframes(WAVframes)        # Read the data from the WAV file and convert to WAVsignalx[]
                
                i = 0
                f = 0
                s = ""

                WAVsignal1 = []
                WAVsignal2 = []

                if (WAVsamplewidth == 1) and (WAVchannels == 1):
                    while (f < WAVframes):
                        s = str(struct.unpack('B', signals[i:(i+1)]))
                        v = int(s[1:-2]) - 128
                        WAVsignal1.append(v) 
                        WAVsignal2.append(0) 
                        i = i + 1
                        f = f + 1
                    
                if (WAVsamplewidth == 1) and (WAVchannels == 2):
                    while (f < WAVframes):
                        s = str(struct.unpack('B', signals[i:(i+1)]))
                        v = int(s[1:-2]) - 128
                        WAVsignal1.append(v) 
                        s = str(struct.unpack('B', signals[(i+1):(i+2)]))
                        v = int(s[1:-2])
                        WAVsignal2.append(v) 
                        i = i + 2
                        f = f + 1

                if (WAVsamplewidth == 2) and (WAVchannels == 1):
                    while (f < WAVframes):
                        s = str(struct.unpack('h', signals[i:(i+2)]))
                        v = int(s[1:-2])
                        WAVsignal1.append(v) 
                        WAVsignal2.append(0) 
                        i = i + 2
                        f = f + 1

                if (WAVsamplewidth == 2) and (WAVchannels == 2):
                    while (f < WAVframes):
                        s = str(struct.unpack('h', signals[i:(i+2)]))
                        v = int(s[1:-2])
                        WAVsignal1.append(v) 
                        s = str(struct.unpack('h', signals[(i+2):(i+4)]))
                        v = int(s[1:-2])
                        WAVsignal2.append(v) 
                        i = i + 4
                        f = f + 1

            WAVf.close()
            WAVpntr = 0                                     # Pointer to WAV array that has to be read
            UpdateScreen()                                  # UpdateScreen() call
            if RUNstatus == 1:
                RUNstatus = 2

            
        # RUNstatus = 2: Reading audio data from WAVsignalx array
        if (RUNstatus == 2):
            RXbuffer = 0                                    # Buffer filled in %. No overflow for WAV mode
            RXbufferoverflow = False

            AUDIOsignal1 = []
            n = 0

            if WAVinput == 1:
                while n < chunkbuffer:
                    v = WAVsignal1[WAVpntr]
                    AUDIOsignal1.append(v)

                    WAVpntr = WAVpntr + 1
                    if WAVpntr >= len(WAVsignal1):
                        WAVpntr = 0

                    n = n + 1

            if WAVinput == 2:
                while n < chunkbuffer:
                    v = WAVsignal2[WAVpntr]
                    AUDIOsignal1.append(v)

                    WAVpntr = WAVpntr + 1
                    if WAVpntr >= len(WAVsignal2):
                        WAVpntr = 0

                    n = n + 1

            UpdateAll()                                     # Update Data, trace and screen


        if (RUNstatus == 3) or (RUNstatus == 4):
            RUNstatus = 0                                   # Status is stopped 
            UpdateScreen()                                  # UpdateScreen() call


        # Update tasks and screens by TKinter 
        root.update_idletasks()
        root.update()                                       # update screens


def UpdateAll():        # Update Data, trace and screen
    DoFFT()             # Fast Fourier transformation
    MakeTrace()         # Update the traces
    UpdateScreen()      # Update the screen 


def UpdateTrace():      # Update trace and screen
    MakeTrace()         # Update traces
    UpdateScreen()      # Update the screen


def UpdateScreen():     # Update screen with trace and text
    MakeScreen()        # Update the screen
    root.update()       # Activate updated screens    


def DoFFT():            # Fast Fourier transformation
    global AUDIOsignal1
    global TRACEmode
    global TRACEaverage
    global TRACEreset
    global ZEROpadding
    global FFTresult
    global AUDIOlevel
    global FFTwindow
    global NUMPYenabled
    
    T1 = time.time()                        # For time measurement of FFT routine
    
    REX = []
    IMX = []

    fftsamples = len(AUDIOsignal1)
    if fftsamples < 64:                     # No FFT if empty or too short array of audio samples
        return

    n = 0
    AUDIOlevel = 0.0
    v = 0.0
    m = 0                                   # For calculation of correction factor 
    while n < fftsamples:
        v = float(AUDIOsignal1[n]) / 16000  # Convert to values between -1 and +1 (should be / 32000 for a good soundcard)

        # Check for overload
        va = abs(v)                         # Check for too high audio input level
        if va > AUDIOlevel:
            AUDIOlevel = va

        # Cosine window function
        # medium-dynamic range B=1.24
        if FFTwindow == 1:
            w = math.sin(math.pi * n / (fftsamples - 1))
            v = w * v * 1.571

        # Triangular non-zero endpoints
        # medium-dynamic range B=1.33
        if FFTwindow == 2:
            w = (2.0 / fftsamples) * ((fftsamples / 2.0) - abs(n - (fftsamples - 1) / 2.0))
            v = w * v * 2.0

        # Hann window function
        # medium-dynamic range B=1.5
        if FFTwindow == 3:
            w = 0.5 - 0.5 * math.cos(2 * math.pi * n / (fftsamples - 1))
            v = w * v * 2.000

        # Blackman window, continuous first derivate function
        # medium-dynamic range B=1.73
        if FFTwindow == 4:
            w = 0.42 - 0.5 * math.cos(2 * math.pi * n / (fftsamples - 1)) + 0.08 * math.cos(4 * math.pi * n / (fftsamples - 1))
            v = w * v * 2.381

        # Nuttall window, continuous first derivate function
        # high-dynamic range B=2.02
        if FFTwindow == 5:
            w = 0.355768 - 0.487396 * math.cos(2 * math.pi * n / (fftsamples - 1)) + 0.144232 * math.cos(4 * math.pi * n / (fftsamples - 1))- 0.012604 * math.cos(6 * math.pi * n / (fftsamples - 1))
            v = w * v * 2.811

        # Flat top window, 
        # medium-dynamic range, extra wide bandwidth B=3.77
        if FFTwindow == 6:
            w = 1.0 - 1.93 * math.cos(2 * math.pi * n / (fftsamples - 1)) + 1.29 * math.cos(4 * math.pi * n / (fftsamples - 1))- 0.388 * math.cos(6 * math.pi * n / (fftsamples - 1)) + 0.032 * math.cos(8 * math.pi * n / (fftsamples - 1))
            v = w * v * 1.000
        
        # m = m + w / fftsamples                # For calculation of correction factor
        REX.append(v)                           # Append the value to the REX array
        IMX.append(0.0)                         # Append 0 to the imagimary part

        n = n + 1

    # if m > 0:                               # For calculation of correction factor
    #     print 1/m                           # For calculation of correction factor

    # Zero padding of array for better interpolation of peak level of signals
    ZEROpaddingvalue = int(math.pow(2,ZEROpadding) + 0.5)
    fftsamples = ZEROpaddingvalue * fftsamples       # Add zero's to the arrays


    # The FFT calculation with NUMPY if NUMPYenabled == True or with the FFT calculation below
    if NUMPYenabled == True: 
        fftresult = numpy.fft.fft(REX, n=fftsamples)# Do FFT+zeropadding till n=fftsamples with NUMPY if NUMPYenabled == True
        REX=fftresult.real
        IMX=fftresult.imag
    else:                                           # Else use the FFT calculation here below
        while len(REX) < fftsamples:                # Zeropadding (add zeros till len(REX) = fftsamples
            REX.append(0)
            IMX.append(0)
        
        Pi = math.pi
        NM1 = 0
        ND2 = 0
        M = 0
        j = 0
        K = 0
        L = 0
        LE = 0
        LE2 = 0
        JM1 = 0
        i = 0
        IP = 0
        TR = 0.0
        TI = 0.0
        UR = 0.0
        UI = 0.0
        SR = 0.0
        SI = 0.0
        
        N = int(fftsamples)
        NM1 = N - 1
        ND2 = N / 2
        M = int(math.log(N,2) + 0.5)
        j = ND2

        i = 1
        while i <= (N - 2):                 # Bit reversal sorting
            if i < j:
                TR = REX[j]
                TI = IMX[j]
                REX[j] = REX[i]
                IMX[j] = IMX[i]
                REX[i] = TR
                IMX[i] = TI
            K = ND2

            while K <= j:
                j = j - K
                K = K / 2

            j = j + K
            i = i + 1

        L = 1
        while L <= M:                       # Loop for each stage
            LE = int(math.pow(2,L) + 0.5)
            LE2 = LE / 2
            UR = 1
            UI = 0
            SR = math.cos(Pi / LE2)         # Calculate sine & cosine values
            SI = -1 * math.sin(Pi / LE2)

            j = 1
            while j <= LE2:                 # Loop for each sub DFT
                JM1 = j - 1

                i = JM1
                while i <= NM1:             # Loop for each butterfly
                    IP = i + LE2
                    TR = REX[IP] * UR - IMX[IP] * UI   #Butterfly calculation
                    TI = REX[IP] * UI + IMX[IP] * UR
                    REX[IP] = REX[i] - TR
                    IMX[IP] = IMX[i] - TI
                    REX[i] = REX[i] + TR
                    IMX[i] = IMX[i] + TI
                    i = i + LE
                    
                TR = UR
                UR = TR * SR - UI * SI
                UI = TR * SI + UI * SR
                j = j + 1

            L = L + 1


    # Make FFT result array
    Totalcorr = float(ZEROpaddingvalue)/ fftsamples         # For VOLTAGE!
    Totalcorr = Totalcorr * Totalcorr                       # For POWER!

    FFTmemory = FFTresult
    FFTresult = []
    
    n = 0
    while (n <= fftsamples / 2):
        # For relative to voltage: v = math.sqrt(REX[n] * REX[n] + IMX[n] * IMX[n])    # Calculate absolute value from re and im
        v = REX[n] * REX[n] + IMX[n] * IMX[n]               # Calculate absolute value from re and im relative to POWER!
        v = v * Totalcorr                                   # Make level independent of samples and convert to display range

        if TRACEmode == 1:                                  # Normal mode, do not change v
            pass

        if TRACEmode == 2 and TRACEreset == False:          # Max hold, change v to maximum value
            if v < FFTmemory[n]:
                v = FFTmemory[n]

        if TRACEmode == 3 and TRACEreset == False:          # Average, add difference / TRACEaverage to v
            v = FFTmemory[n] + (v - FFTmemory[n]) / TRACEaverage

        FFTresult.append(v)                                 # Append the value to the FFTresult array

        n = n + 1

    TRACEreset = False                                      # Trace reset done

    # print len(FFTresult)
    #launchpad()
    T2 = time.time()
    # print (T2 - T1)                                         # For time measurement of FFT routine

def launchpad():

    #print "launchpad"
    global FFTresult
    global T1line

    localFFT = FFTresult

    aggregateFFT = []

    localIndex = 0

    for (i, item) in enumerate(T1line):


        if (i % 2 == 0): #even 
            pass
        else:

            localMax = 0

            localIndex += 1
            if item > localMax:
                localMax = item
            if localIndex >= 212:
                aggregateFFT.append(localMax)
                localIndex = 0

    print aggregateFFT
    #print len(T1line)
    
    for (i, item) in enumerate(aggregateFFT):

        item = item/60
        bar = math.floor(item)
        bar = int(bar)
        bar = 8-bar

        if bar > 8:
            bar = 8
        if bar < 0:
            bar = 0

        #print bar
        for x in range(1, 9):
            if x <= bar:
                if x <= 2:
                    LP.LedCtrlXY(i, 9-x, 0, 4)
                if x > 2 and x <= 4:
                    LP.LedCtrlXY(i, 9-x, 2, 4)
                if x > 4:
                    LP.LedCtrlXY(i, 9-x, 4, 0)
            else:
                LP.LedCtrlXY(i, 9-x, 0, 0)
    

    aggregateFFT = []





def MakeTrace():        # Update the grid and trace
    global FFTresult
    global T1line
    global T2line
    global STOREtrace
    global X0L          # Left top X value
    global Y0T          # Left top Y value
    global GRW          # Screenwidth
    global GRH          # Screenheight
    global Vdiv         # Number of vertical divisions
    global STARTfrequency
    global STOPfrequency
    global DBdivlist    # dB per division list
    global DBdivindex   # Index value
    global DBlevel      # Reference level
    global SAMPLErate


    # Set the TRACEsize variable
    TRACEsize = len(FFTresult)      # Set the trace length

    if TRACEsize == 0:              # If no trace, skip rest of this routine
        return()


    # Vertical conversion factors (level dBs) and border limits
    Yconv = float(GRH) / (Vdiv * DBdivlist[DBdivindex])     # Conversion factors from dBs to screen points 10 is for 10 * log(power)
    Yc = float(Y0T) + GRH + Yconv * (DBlevel -90)           # Zero postion and -90 dB for in grid range
    Ymin = Y0T                                              # Minimum position of screen grid (top)
    Ymax = Y0T + GRH                                        # Maximum position of screen grid (bottom)


    # Horizontal conversion factors (frequency Hz) and border limits
    Fpixel = float(STOPfrequency - STARTfrequency) / GRW    # Frequency step per screen pixel
    Fsample = float(SAMPLErate / 2) / (TRACEsize - 1)       # Frequency step per sample   

    T1line = []
    n = 0
    Slevel = 0.0            # Signal level
    Nlevel = 0.0            # Noise level
    while n < TRACEsize:
        F = n * Fsample

        if F >= STARTfrequency and F <= STOPfrequency:
            x = X0L + (F - STARTfrequency)  / Fpixel
            T1line.append(int(x + 0.5))
            try:
                y =  Yc - Yconv * 10 * math.log10(float(FFTresult[n]))  # Convert power to DBs, except for log(0) error
            except:
                y = Ymax
                
            if (y < Ymin):
                y = Ymin
            if (y > Ymax):
                y = Ymax
            T1line.append(int(y + 0.5))

        n = n + 1               

    launchpad()

def MakeScreen():       # Update the screen with traces and text
    global X0L          # Left top X value
    global Y0T          # Left top Y value
    global GRW          # Screenwidth
    global GRH          # Screenheight
    global T1line
    global T2line
    global S1line
    global S2line
    global STOREtrace
    global Vdiv         # Number of vertical divisions
    global RUNstatus    # 0 stopped, 1 start, 2 running, 3 stop now, 4 stop and restart
    global AUDIOstatus  # 0 audio off, 1 audio on
    global UPDATEspeed
    global STARTfrequency
    global STOPfrequency
    global DBdivlist    # dB per division list
    global DBdivindex   # Index value
    global DBlevel      # Reference level
    global SAMPLErate
    global TRACEmode    # 1 normal 2 max 3 average
    global TRACEaverage # Number of traces for averageing
    global AUDIOlevel   # Level of audio input 0 to 1
    global FFTwindow
    global COLORgrid    # The colors
    global COLORtrace1
    global COLORtrace2
    global COLORtext
    global COLORsignalband
    global COLORaudiobar
    global COLORaudiook 
    global COLORaudiomax
    global CANVASwidth
    global CANVASheight
    global RXbuffer
    global RXbufferoverflow

    # Delete all items on the screen
    de = ca.find_enclosed ( 0, 0, CANVASwidth+1000, CANVASheight+1000)    
    for n in de: 
        ca.delete(n)
 

    # Draw horizontal grid lines
    i = 0
    x1 = X0L
    x2 = X0L + GRW
    while (i <= Vdiv):
        y = Y0T + i * GRH/Vdiv
        Dline = [x1,y,x2,y]
        ca.create_line(Dline, fill=COLORgrid)            
        i = i + 1


    # Draw vertical grid lines
    i = 0
    y1 = Y0T
    y2 = Y0T + GRH
    while (i < 11):
        x = X0L + i * GRW/10
        Dline = [x,y1,x,y2]
        ca.create_line(Dline, fill=COLORgrid)
        i = i + 1


    # Draw traces
    if len(T1line) > 4:                                     # Avoid writing lines with 1 coordinate    
        ca.create_line(T1line, fill=COLORtrace1)            # Write the trace 1

    if STOREtrace == True and len(T2line) > 4:              # Write the trace 2 if active
        ca.create_line(T2line, fill=COLORtrace2)            # and avoid writing lines with 1 coordinate


    # General information on top of the grid
    if (AUDIOstatus == 1):
        txt = "Audio on "
    else:
        txt = "Audio off"

    txt = txt + "    Sample rate: " + str(SAMPLErate)
    txt = txt + "    FFT samples: " + str(SMPfftlist[SMPfftindex])

    if FFTwindow == 0:
        txt = txt + "    Rectangular (no) window (B=1) "
    if FFTwindow == 1:
        txt = txt + "    Cosine window (B=1.24) "
    if FFTwindow == 2:
        txt = txt + "    Triangular window (B=1.33) "
    if FFTwindow == 3:
        txt = txt + "    Hann window (B=1.5) "
    if FFTwindow == 4:
        txt = txt + "    Blackman window (B=1.73) "
    if FFTwindow == 5:
        txt = txt + "    Nuttall window (B=2.02) "
    if FFTwindow == 6:
        txt = txt + "    Flat top window (B=3.77) "
        
    x = X0L
    y = 12
    idTXT = ca.create_text (x, y, text=txt, anchor=W, fill=COLORtext)


    # Start and stop frequency and dB/div and trace mode
    txt = str(STARTfrequency) + " to " + str(STOPfrequency) + " Hz"
    txt = txt +  "    " + str(DBdivlist[DBdivindex]) + " dB/div"
    txt = txt + "    Level: " + str(DBlevel) + " dB "

    if TRACEmode == 1:
        txt = txt + "    Normal mode "

    if TRACEmode == 2:
        txt = txt + "    Maximum hold mode "
    
    if TRACEmode == 3:
        txt = txt + "    Power average  mode (" + str(TRACEaverage) + ") " 

    x = X0L
    y = Y0T+GRH+12
    idTXT = ca.create_text (x, y, text=txt, anchor=W, fill=COLORtext)


    # Soundcard level bargraph
    txt1 = "||||||||||||||||||||"   # Bargraph
    le = len(txt1)                  # length of bargraph
        
    t = int(math.sqrt(AUDIOlevel) * le)

    n = 0
    txt = ""
    while(n < t and n < le):
        txt = txt + "|"
        n = n + 1

    x = X0L
    y = Y0T+GRH+32

    IDtxt = ca.create_text (x, y, text=txt1, anchor=W, fill=COLORaudiobar)

    if AUDIOlevel >= 1.0:
        IDtxt = ca.create_text (x, y, text=txt, anchor=W, fill=COLORaudiomax)
    else:
        IDtxt = ca.create_text (x, y, text=txt, anchor=W, fill=COLORaudiook)


    # Runstatus and level information
    if (RUNstatus == 0) or (RUNstatus == 3):
        txt = "Sweep stopped"
    else:
        txt = "Sweep running"

    # txt = txt + "    Buffer (%): " + str(int (RXbuffer))

    # if RXbufferoverflow == True:
    #    txt = txt + " OVERFLOW"

    if RXbuffer > 100:
        txt = txt + "."
    
    x = X0L + 100
    y = Y0T+GRH+32
    IDtxt  = ca.create_text (x, y, text=txt, anchor=W, fill=COLORtext)


def SELECTaudiodevice():        # Select an audio device
    global AUDIOdevin
    global AUDIOdevout

    PA = pyaudio.PyAudio()
    ndev = PA.get_device_count()

    n = 0
    ai = ""
    ao = ""
    while n < ndev:
        s = PA.get_device_info_by_index(n)
        # print n, s
        if s['maxInputChannels'] > 0:
            ai = ai + str(s['index']) + ": " + s['name'] + "\n"
        if s['maxOutputChannels'] > 0:
            ao = ao + str(s['index']) + ": " + s['name'] + "\n"
        n = n + 1
    PA.terminate()

    AUDIOdevin = None
    
    s = askstring("Device","Select audio INPUT device:\nPress Cancel for Windows Default\n\n" + ai + "\n\nNumber: ")
    if (s != None):             # If Cancel pressed, then None
        try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
            v = int(s)
        except:
            s = "error"

        if s != "error":
            if v < 0 or v > ndev:
                v = 0
            AUDIOdevin = v

    AUDIOdevout = None

    s = askstring("Device","Select audio OUTPUT device:\nPress Cancel for Windows Default\n\n" + ao + "\n\nNumber: ")
    if (s != None):             # If Cancel pressed, then None
        try:                    # Error if for example no numeric characters or OK pressed without input (s = "")
            v = int(s)
        except:
            s = "error"

        if s != "error":
            if v < 0 or v > ndev:
                v = 0
            AUDIOdevout = v


def ASKWAVfilename():

    filename = askopenfilename(filetypes=[("WAVfile","*.wav"),("allfiles","*")])

    if (filename == None):              # No input, cancel pressed or an error
        filename = ""

    if (filename == ""):
        return(filename)
    
    if filename[-4:] != ".wav":
        filename = filename + ".wav"

    return(filename)


# ================ Make Screen ==========================

root=Tk()
root.title("SpectrumanalyzerV01b.py(w) (29-04-2012): Audio Spectrum Analyzer")

root.minsize(100, 100)

frame1 = Frame(root, background=COLORframes, borderwidth=5, relief=RIDGE)
frame1.pack(side=TOP, expand=1, fill=X)

frame2 = Frame(root, background="black", borderwidth=5, relief=RIDGE)
frame2.pack(side=TOP, expand=1, fill=X)

frame3 = Frame(root, background=COLORframes, borderwidth=5, relief=RIDGE)
frame3.pack(side=TOP, expand=1, fill=X)

ca = Canvas(frame2, width=CANVASwidth, height=CANVASheight, background=COLORcanvas)
ca.pack(side=TOP)

b = Button(frame1, text="Normal mode", width=Buttonwidth1, command=BNormalmode)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame1, text="Max hold", width=Buttonwidth1, command=BMaxholdmode)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame1, text="Average", width=Buttonwidth1, command=BAveragemode)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame1, text="FFTwindow", width=Buttonwidth1, command=BFFTwindow)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame1, text="Store trace", width=Buttonwidth1, command=BSTOREtrace)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame1, text="Screen setup", width=Buttonwidth1, command=BScreensetup)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame1, text="Setup", width=Buttonwidth1, command=BSetup)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame1, text="Audio on/off", width=Buttonwidth1, command=BAudiostatus)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="Start", width=Buttonwidth2, command=BStart)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame3, text="Stop", width=Buttonwidth2, command=BStop)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame3, text="Startfreq", width=Buttonwidth2, command=BStartfrequency)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame3, text="Stopfreq", width=Buttonwidth2, command=BStopfrequency)
b.pack(side=LEFT, padx=5, pady=5)

b = Button(frame3, text="+Samples", width=Buttonwidth2, command=Bsamples2)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="-Samples", width=Buttonwidth2, command=Bsamples1)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="+dB/div", width=Buttonwidth2, command=BDBdiv2)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="-dB/div", width=Buttonwidth2, command=BDBdiv1)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="LVL+10", width=Buttonwidth2, command=Blevel4)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="LVL-10", width=Buttonwidth2, command=Blevel3)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="LVL+1", width=Buttonwidth2, command=Blevel2)
b.pack(side=RIGHT, padx=5, pady=5)

b = Button(frame3, text="LVL-1", width=Buttonwidth2, command=Blevel1)
b.pack(side=RIGHT, padx=5, pady=5)

# ================ Call main routine ===============================
root.update()               # Activate updated screens

if WAVinput == 0:
    SELECTaudiodevice()
    AUDIOin()
else:                       # Input from WAV file instead of audio device
    WAVin()
 


