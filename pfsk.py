import bitarray
import numpy as np
import util

FRAMELENGTH = 0.25
TONESPACING = 4
SAMPLERATE  = 44100
CHUNK_LENGTH = int(SAMPLERATE * FRAMELENGTH)
MINIMUM_PHASE = 0
MAXIMUM_PHASE = util.TAU

class Modem:
    def __init__(self, carrier=500, channelcount=2, tonecount=2, phasecount=2):
        self.carrier = carrier
        self.channelcount = channelcount
        self.tonecount = tonecount
        self.phasecount = phasecount

        # calculated values required for basic operation
        self.phasespacing = (MAXIMUM_PHASE - MINIMUM_PHASE) / phasecount
        self.channelwidth = tonecount * TONESPACING
        self.channelbitwidth = util.getPower(tonecount * phasecount)
        self.bitrate = channelcount * self.channelbitwidth

        # magic to create a list of all the possible symbol values
        self.symbolvalues = [
            tuple(
                map(bool, map(
                    int, tuple(
                        "{0:b}".format(x).zfill(self.channelbitwidth)
                        )
                    )
                )
            ) for x in range(self.tonecount*self.phasecount)
        ]

        self.channels, self.symbols2bin, self.bin2symbols = self.mkchannels(carrier)

    def mkchannels(self, carrier, phaseoffset=0):
        """
        creates the channels, including their boundaries and symbols
        """
        lowerbound = carrier - ((self.channelcount/2)* self.channelwidth)
        upperbound = carrier + ((self.channelcount/2) * self.channelwidth)

        channels, symbols2bin, bin2symbols = {}, {}, {}

        for center in range(lowerbound, upperbound+1, self.channelwidth):
            if center == carrier: continue
            channelrange = (center - self.channelwidth/2 - TONESPACING/2,
                            center + self.channelwidth/2 + TONESPACING/2)
            symbols = dict(self.mksymbols(center, phaseoffset))
            channels[channelrange] = symbols
            bin2symbols[channelrange] = {}
            for symbol, value in symbols.iteritems():
                bin2symbols[channelrange][value] = symbol
                symbols2bin[symbol] = value
        return channels, symbols2bin, bin2symbols

    def mksymbols(self, channel, phaseoffset=0):
        """
        creates the (tone, phase) symbols and associates them with a tuple of bit states
        """
        values = list(self.symbolvalues)
        minphase = int(MINIMUM_PHASE * 100000000000)
        maxphase = int((MAXIMUM_PHASE - self.phasespacing) * 100000000000)
        phasespacing = int(self.phasespacing * 100000000000)
        phases = [x/100000000000.0 for x in range(minphase, maxphase+1, phasespacing)]
        lowerbound = channel - (self.channelwidth/2)
        upperbound = channel + (self.channelwidth/2)
        for tone in range(lowerbound, upperbound, TONESPACING):
            for phase in phases:
                phase %= util.TAU
                yield (tone, (phase + phaseoffset) % util.TAU), values.pop()

    def encode(self, data):
        bits = bitarray.bitarray()
        bits.frombytes(bytes(data))

        signal = np.array([])

        for x in range(0, len(bits), self.bitrate):
            framebits = bits[x:x+self.bitrate]
            framebits += [0] * (self.bitrate-len(framebits))

            channels = list(sorted(self.channels))
            framesignal = util.note(self.carrier, 0, FRAMELENGTH, samplerate=SAMPLERATE) # carrier
            frame = []
            for y in range(0, len(framebits), self.channelbitwidth):
                channelbits = tuple(framebits[y:y+self.channelbitwidth])
                channel = channels.pop(0)
                symbol  = self.bin2symbols[channel][channelbits]
                frame.append(symbol)

                framesignal += util.note(symbol[0], symbol[1], FRAMELENGTH, samplerate=SAMPLERATE)

            signal = np.append(signal, framesignal)

        return signal

    def decode(self, signal):
        signalanalysis = util.SignalAnalyzer(signal, SAMPLERATE)
        signalcarrier = signalanalysis.find_peak()
        bits = bitarray.bitarray()

        for x in range(0, len(signal), CHUNK_LENGTH):
            chunk = signal[x:x+CHUNK_LENGTH]
            chunkanalysis = util.SignalAnalyzer(chunk, SAMPLERATE)
            chunkcarrier = chunkanalysis.find_peak(signalcarrier - TONESPACING/2,
                                                  signalcarrier + TONESPACING/2)
            chunkphase = chunkanalysis.get_phase(chunkcarrier)

            channels, symbols2bin, bin2symbols = self.mkchannels(int(chunkcarrier), chunkphase)
            tones = [x[0] for x in symbols2bin]
            angles = set([x[1] for x in symbols2bin])
            frame = []
            for channel in sorted(channels):
                tone, angle = chunkanalysis.find_peak_with_angle(*channel)
                if not tone in tones:
                    possibilities = [(x, abs(tone-x)) for x in tones]
                    possibilities.sort(key=lambda x:x[1])
                    tone = possibilities[0][0]
                if not angle in angles:
                    possibilities = [[x, abs(angle-x)] for x in angles]
                    possibilities.sort(key=lambda x:x[1])
                    for possibility in possibilities:
                        if possibility[1] > util.TAU/2:
                            possibility[1] = abs(possibility[1] - 6.28)
                    angle = possibilities[0][0]
                frame.append((tone, angle))
                bits += symbols2bin[(tone, angle)]
        return bits.tobytes()

if __name__ == '__main__':
    from scipy.io import wavfile
    import sys
    
    modem = Modem()

    if sys.argv[1] == 'encode':
        signal = modem.encode("KR1LLR CN85 -100")
        wavfile.write(sys.argv[2], SAMPLERATE,  signal.astype(np.float32))
    elif sys.argv[1] == 'decode':
        _, signal = wavfile.read(sys.argv[2])
        print modem.decode(signal)

# vim: ai ts=4 sts=4 et sw=4 ft=python
# # # vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
