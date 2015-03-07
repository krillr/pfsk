import bitarray
import numpy as np
import util

FRAMELENGTH = 0.25
TONESPACING = 4
SAMPLERATE  = 44100.0
CHUNK_LENGTH = int(SAMPLERATE * FRAMELENGTH)
MINIMUM_PHASE = 0
MAXIMUM_PHASE = util.TAU
EXPECTED = bitarray.bitarray('01001011010100100011000101001100010011000101001000100000010000110100111000111000001101010010000000101101001100010011000000110000')

class Modem:
    def __init__(self, carrier=1000, channelcount=2, tonecount=2, phasecount=2):
        self.carrier = carrier
        self.channelcount = channelcount
        self.tonecount = tonecount
        self.phasecount = phasecount

        # calculated values required for basic operation
        self.phasespacing = (MAXIMUM_PHASE - MINIMUM_PHASE) / phasecount
        self.channelwidth = tonecount * TONESPACING
        self.channelbitwidth = util.getPower(tonecount * phasecount)
        self.bitrate = channelcount * self.channelbitwidth

        self.bandwidth = (channelcount+1) * tonecount * TONESPACING + TONESPACING

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
            framesignal = None#util.note(self.carrier, 0, FRAMELENGTH, samplerate=SAMPLERATE) # carrier
            for y in range(0, len(framebits), self.channelbitwidth):
                channelbits = tuple(framebits[y:y+self.channelbitwidth])
                channel = channels.pop(0)
                symbol  = self.bin2symbols[channel][channelbits]

                waveform = util.note(symbol[0], symbol[1], FRAMELENGTH, samplerate=SAMPLERATE)
                if framesignal == None:
                    framesignal = waveform
                else:
                    framesignal += waveform

            signal = np.append(signal, framesignal)
        signal += util.note(self.carrier, 0, len(signal)/SAMPLERATE)
        return signal

    def decode(self, signal):
        signalanalysis = util.SignalAnalyzer(signal, SAMPLERATE)
        signalcarrier = signalanalysis.find_peak()
        bits = bitarray.bitarray()
        c = 0
        for x in range(0, len(signal), CHUNK_LENGTH):
            chunk = signal[x:x+CHUNK_LENGTH]
            chunkanalysis = util.SignalAnalyzer(chunk, SAMPLERATE)
            chunkcarrier = chunkanalysis.find_peak(signalcarrier - TONESPACING/2,
                                                  signalcarrier + TONESPACING/2)
            if not chunkcarrier: continue
            chunkphase = chunkanalysis.get_phase(chunkcarrier)

            channels, symbols2bin, bin2symbols = self.mkchannels(int(chunkcarrier), chunkphase)
            tones = set([x[0] for x in symbols2bin])
            angles = set([x[1] for x in symbols2bin])
            for channel in sorted(channels):
                expected = EXPECTED[c*self.channelbitwidth:c*self.channelbitwidth+self.channelbitwidth]
                expected += [0]*(self.channelbitwidth - len(expected))
                peaks = chunkanalysis.find_peaks_with_angles(*channel)
                scores = []
                for peak in peaks:
                    score = peak[1]
                    angledeltas = [[x, abs(x-peak[2])] for x in angles]
                    for i in range(len(angledeltas)):
                        if angledeltas[i][1] > util.TAU/2:
                            angledeltas[i][1] = abs(angledeltas[i][1] - 6.28)
                    angledeltas.sort(key=lambda x:x[1])
                    score += (util.TAU - angledeltas[0][1])/util.TAU
                    score /= 2
                    scores.append((peak[0], score, angledeltas[0][0]))
                scores.sort()
                tone = scores[0][0]
                angle = scores[0][2]

                if not tone in tones:
                    possibilities = [(x, abs(x-tone)) for x in tones]
                    possibilities.sort(key=lambda x:x[1])
                    tone = possibilities[0][0]

                bits += symbols2bin[(tone, angle)]
                c += 1
        return bytearray(bits.tobytes())

if __name__ == '__main__':
    from scipy.io import wavfile
    import reedsolo, sys, scipy.stats
    
    input = "KR1LLR CN85 -100"
    rs = reedsolo.RSCodec(len(input))

    modem = Modem()

    print "Bandwidth:", modem.bandwidth, "hz"
    print "Bitrate:", modem.bitrate / FRAMELENGTH, "bit/sec"
    print "Efficiency:", float(modem.bitrate) / modem.bandwidth, "bit/hz"
    print "Channel Bitwidth:", modem.channelbitwidth

    if sys.argv[1] == 'encode':
        input = rs.encode(input)
        signal = modem.encode(input)
        wavfile.write(sys.argv[2], SAMPLERATE,  signal.astype(np.float32))
    elif sys.argv[1] == 'decode':
        _, signal = wavfile.read(sys.argv[2])
        print rs.decode(modem.decode(signal))
        #print modem.decode(signal)

# vim: ai ts=4 sts=4 et sw=4 ft=python
# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
