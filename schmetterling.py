from colorama import init, Fore, Back, Style
from scipy.io import wavfile
import audio, argparse, json, os, pfsk, select, sys, time, warnings

warnings.simplefilter('ignore')

class Schmetterling:
    options = argparse.ArgumentParser()
    options.add_argument('--interval', choices=['odd','even'])
    options.add_argument('--recording-device', type=int)
    options.add_argument('--playback-device', type=int)
    options.add_argument('--encode-wav', action='store_true', default=False)
    options.add_argument('--decode-wav', action='store_true', default=False)
    options.add_argument('--file')
    options.add_argument('--msg')

    def __init__(self):
        self.options = dict(Schmetterling.options.parse_args()._get_kwargs())
        self.audio = audio.Interface()
        self.pfsk = pfsk.Modem()

    def run(self):
        if self.options['encode_wav'] or self.options['decode_wav']:
            if not self.options['file']:
                print Fore.RED + "You must specify a filename to encode/decode with --file." + Style.RESET_ALL
                sys.exit(1)
            if self.options['encode_wav']:
                if not self.options['msg']:
                    print Fore.RED + "You must specify a msg to encode with --msg." + Style.RESET_ALL
                    sys.exit(1)
                self.encode()
            if self.options['decode_wav']:
                self.decode()
            return
            
        self.healthcheck()
        missing = [x for x, y in self.options.items() if y == None]
        for x in missing:
            self.options[x] = self.interactive_config(x)
            print Style.RESET_ALL + '\n'
        self.audio.set_playback_device(self.options['playback_device'])
        self.audio.set_recording_device(self.options['recording_device'])

    def encode(self):
        print Style.BRIGHT + "Encoding..." + Style.RESET_ALL
        t = time.time()
        signal = self.pfsk.encode(self.options['msg'])
        print (Style.BRIGHT + "Done! (%.2f seconds)" + Style.RESET_ALL) % (time.time()-t)
        print Style.BRIGHT + "Writing..." + Style.RESET_ALL
        wavfile.write(self.options['file'], pfsk.SAMPLERATE, signal)

    def decode(self):
        print Style.BRIGHT + "Reading..." + Style.RESET_ALL
        _, signal = wavfile.read(self.options['file'])
        print Style.BRIGHT + "Decoding..." + Style.RESET_ALL
        t = time.time()
        print (Style.BRIGHT + Fore.BLUE + "Message: " + Fore.GREEN + "%s" + Style.RESET_ALL) % self.pfsk.decode(signal)
        print (Style.BRIGHT + "Done! (%.2f seconds)" + Style.RESET_ALL) % (time.time()-t)

    def healthcheck(self):
        devices = self.audio.get_devices()
        playback  = { x['index']: x for x in self.audio.get_devices() if x['maxOutputChannels'] > 0 }
        recording = { x['index']: x for x in self.audio.get_devices() if x['maxInputChannels'] > 0 }

        if not recording:
            print Back.RED + Fore.BLACK + "You do not appear to have any recording audio devices. Exiting." + Style.RESET_ALL
            sys.exit(1)
    
        if not playback:
            print Back.RED + Fore.BLACK + "You do not appear to have any playback audio devices. Exiting." + Style.RESET_ALL
            sys.exit(1)

        if self.options['recording_device'] != None and self.options['recording_device'] not in recording:
            print Back.RED + Fore.BLACK + "Your chosen recording device either does not exist, or cannot record. Exiting." + Style.RESET_ALL
            sys.exit(1)

        if self.options['playback_device'] != None and self.options['playback_device'] not in playback:
            print Back.RED + Fore.BLACK + "Your chosen playback device either does not exist, or cannot play. Exiting." + Style.RESET_ALL
            sys.exit(1)

    def interactive_config(self, option):
        if option in ['encode_wav', 'decode_wav', 'file']: return
        if option == 'interval':
            options = ('odd', 'even')
            choice = raw_input(Style.BRIGHT + 'Please choose an interval (' + Fore.GREEN + 'odd' + Fore.RESET + '/' + Fore.GREEN + 'even' + Fore.RESET +'): ' + Style.RESET_ALL).lower()
            if not choice in options:
                print Fore.RED + 'Invalid choice' + Style.RESET_ALL
                return self.interactive_config(option)
            return choice

        if option == 'recording_device':
            devices = [x for x in self.audio.get_devices() if x['maxInputChannels'] > 0]
            print Style.BRIGHT + "Please choose a device to monitor for transmissions:"
            for x in range(len(devices)):
                print (Style.BRIGHT + Fore.GREEN + "%i)" + Fore.BLUE + " %s" + Style.RESET_ALL) % (x, devices[x]['name'])
            choice = raw_input(Style.BRIGHT + 'Device: ' + Style.RESET_ALL)
            if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(devices):
                print Fore.RED + 'Invalid choice' + Style.RESET_ALL
                return self.interactive_config(option)
            return devices[int(choice)]['index']

        if option == 'playback_device':
            devices = [x for x in self.audio.get_devices() if x['maxOutputChannels'] > 0]
            print Style.BRIGHT + "Please choose a device to use for transmitting:" + Style.RESET_ALL
            for x in range(len(devices)):
                print (Style.BRIGHT + Fore.GREEN + "%i)" + Fore.BLUE + " %s" + Style.RESET_ALL) % (x, devices[x]['name'])
            choice = raw_input(Style.BRIGHT + 'Device: ' + Style.RESET_ALL)
            if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(devices):
                print Fore.RED + 'Invalid choice' + Style.RESET_ALL
                return self.interactive_config(option)
            return devices[int(choice)]['index']

if __name__ == '__main__':
    app = Schmetterling()
    app.run()

# vim: ai ts=4 sts=4 et sw=4 ft=python
# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
