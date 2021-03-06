import numpy as np, math, time
from numpy.fft import fft as FFT_FUNC

TAU = np.pi * 2

def isEven(num):
    return num % 2 == 0

def getPower (num, base=2):
    if base == 1 and num != 1: return False
    if base == 1 and num == 1: return True
    if base == 0 and num != 1: return False
    power = int (math.log (num, base) + 0.5)
    if base ** power == num: return power

def note(freq, phase=0, length=0.25, samplerate=44100):
    t = np.linspace(0, length, length * samplerate)
    data = np.cos((TAU * freq * t) + (phase % 6.28)) * 12750
    data /= data.max()
    return envelope(data, 1)

def envelope (samples, channels):
    '''Add an envelope to np array samples to prevent clicking.'''    
    attack = 200
    if len(samples) < 3 * attack:
        attack = int(len(samples) * 0.05)
    line1 = np.linspace (0, 1, attack * channels)
    line2 = np.ones (len(samples) * channels - 2 * attack * channels)
    line3 = np.linspace (1, 0, attack * channels)
    envelope = np.concatenate ((line1, line2, line3))
    if channels == 2:
        envelope.shape = (len(envelope) / 2, 2)
    samples *= envelope
    return samples

class SignalAnalyzer:
    def __init__(self, signal, samplerate):
        self.signal = signal
        self.samplerate = samplerate
        self.fft = None
        self.amplitudes = None
        self.freqs = None
        self.processed = False
    def process(self):
        self.fft    = FFT_FUNC(self.signal)#, planner_effort='FFTW_ESTIMATE')
        self.amps   = np.abs(self.fft)
        self.freqs  = np.around(np.fft.fftfreq(len(self.fft), 1.0/(self.samplerate)))
        self.freq_indices = np.indices(self.freqs.shape)
        self.angles = np.angle(self.fft) % TAU
        self.processed  = True
    def find_peak(self, minfreq=250, maxfreq=2500):
        peaks = self.find_peaks(minfreq, maxfreq)
        if not peaks: return
        peak  = max(peaks, key=lambda x: x[1])
        return peak[0]
    def find_peaks(self, minfreq=250, maxfreq=2500):
        if not self.processed: self.process()
        locs = self.freq_indices[:, (self.freqs >= minfreq) & (self.freqs <= maxfreq)]
        freqs = self.freqs[locs][0]
        amps = self.amps[locs][0]
        amps /= amps.max()
        peaks = zip(freqs, amps)
        peaks = filter(lambda x: x[1]>0.95, peaks)
        return peaks
    def find_peaks_with_angles(self, minfreq=250, maxfreq=2500):
        peaks = [(x, y, self.get_phase(x)) for x, y in self.find_peaks(minfreq, maxfreq)]
        return peaks

    def find_peak_with_angle(self, minfreq=250, maxfreq=2500):
        peak = self.find_peak(minfreq, maxfreq)
        return peak, self.get_phase(peak)
    def get_phase(self, frequency):
        i = self.freq_indices[:, (self.freqs == frequency)]
        return self.angles[i][0][0]

if __name__ == '__main__':
    from scipy.io import wavfile
    import sys
    signal = note(500, 0, 5)
    signal /= signal.max()
    signal *= 2147483647
    signal = signal.astype(np.int32)
    wavfile.write(sys.argv[1], 44100, signal)
    _, signal2 = wavfile.read(sys.argv[1])
    print (signal == signal2).all()

# vim: ai ts=4 sts=4 et sw=4 ft=python
# # vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
