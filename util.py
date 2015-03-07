import numpy as np, math

TAU = np.pi * 2

def getPower (num, base=2):
    if base == 1 and num != 1: return False
    if base == 1 and num == 1: return True
    if base == 0 and num != 1: return False
    power = int (math.log (num, base) + 0.5)
    if base ** power == num: return power

def note(freq, phase=0, length=0.25, samplerate=44100):
    t = np.linspace(0, length, length * samplerate)
    data = np.cos((TAU * freq * t) + (phase % 6.28))
    return envelope(data, 1)

def envelope (samples, channels):
    '''Add an envelope to np array samples to prevent clicking.'''    
    
    attack = 800
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
        self.signal = signal / signal.max()
        self.samplerate = samplerate
        self.fft = None
        self.amplitudes = None
        self.freqs = None
    def preprocess(self):
        self.fft    = np.fft.fft(self.signal)
        self.amps   = np.abs(self.fft)
        self.amps  /= self.amps.max()
        self.freqs  = np.around(np.fft.fftfreq(len(self.fft), 1.0/(self.samplerate)))
        self.angles = np.angle(self.fft) % TAU
        self.angle_lookup = dict(zip(self.freqs, self.angles))
    def find_peak(self, minfreq=250, maxfreq=2500):
        peaks = self.find_peaks(minfreq, maxfreq)
        if not peaks: return
        peak  = max(peaks, key=lambda x: x[1])
        return peak[0]
    def find_peaks(self, minfreq=250, maxfreq=2500):
        if self.fft == None: self.preprocess()
        y = np.indices(self.freqs.shape)
        locs = y[:, (self.freqs >= minfreq) & (self.freqs <= maxfreq)]
        freqs = self.freqs[locs][0]
        amps = self.amps[locs][0]
        return zip(freqs, amps)
    def find_peak_with_angle(self, minfreq=250, maxfreq=250):
        peak = self.find_peak(minfreq, maxfreq)
        return peak, self.get_phase(peak)
    def get_phase(self, frequency):
        if frequency in self.angle_lookup: return self.angle_lookup[frequency]

if __name__ == '__main__':
    from scipy.io import wavfile
    import sys
    wavfile.write(sys.argv[1], 44100, note(500, 0))

# vim: ai ts=4 sts=4 et sw=4 ft=python
# # vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
