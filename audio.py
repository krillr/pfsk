import pyaudio, numpy

class Interface:
    def __init__(self, samplerate=44100):
        self.pa = pyaudio.PyAudio()
        self.playback_device  = 2
        self.recording_device = 2
        self.samplerate = samplerate
    def get_devices(self):
        for i in range(self.pa.get_device_count()):
            yield self.pa.get_device_info_by_index(i)
    def set_playback_device(self, index):
        self.playback_device = index
    def set_recording_device(self, index):
        self.recording_device = index
    def play(self, signal_string):
        stream = self.pa.open(format=pyaudio.paFloat32, channels=1, rate=self.samplerate, output=True, output_device_index=self.playback_device)
        stream.write(signal_string)
        stream.close()
    def record(self, seconds=12):
        stream = self.pa.open(format=pyaudio.paFloat32, channels=1, rate=self.samplerate, input=True, output=False, input_device_index=self.recording_device)
        data = stream.read(seconds*self.samplerate)
        stream.close()
        signal = numpy.fromstring(data, dtype=numpy.float32)
        return signal

if __name__ == '__main__':
    import json
    audio = Interface()
    for device in audio.get_devices():
        print json.dumps(device, indent=2)
# vim: ai ts=4 sts=4 et sw=4 ft=python
# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
