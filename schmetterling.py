from colorama import init, Fore, Back, Style
from scipy.io import wavfile
import audio, argparse, json, ntplib, numpy as np, os, pfsk, reedsolo, select, sys, time, util, warnings

warnings.simplefilter('ignore')

TX_LENGTH = 16

class Schmetterling:
    options = argparse.ArgumentParser()
    options.add_argument('--interval', choices=['odd','even'])
    options.add_argument('--recording-device', type=int)
    options.add_argument('--playback-device', type=int)
    options.add_argument('--encode-wav', action='store_true', default=False)
    options.add_argument('--decode-wav', action='store_true', default=False)
    options.add_argument('--fec', action='store_true', default=False)
    options.add_argument('--file')
    options.add_argument('--msg')

    def __init__(self):
        self.options = dict(Schmetterling.options.parse_args()._get_kwargs())
        self.audio = audio.Interface()
        self.pfsk = pfsk.Modem()
        self.ntpclient = ntplib.NTPClient()
        self.timeoffset = self.ntpclient.request('time.nist.gov', version=3).offset
        self.tx_msg = ''
        self.tx_length = int((TX_LENGTH * (self.pfsk.bitrate/pfsk.FRAMELENGTH))/16)
        self.rs = reedsolo.RSCodec(self.tx_length)

    def time(self):
        return time.time() + self.timeoffset

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

        self.run_client()

    def next_cycle(self):
        t = self.time()
        d = 30-(t % 30)
        n = int(t + d)
        typ = 'rx'
        even = util.isEven(int(t+d)/2)
        if even and self.options['interval'] == 'even' \
        or not even and self.options['interval'] == 'odd':
            typ = 'tx'
        return typ, d

    def run_client(self):
        typ, til = self.next_cycle()
        if typ == 'tx':
            til += 30
            typ = 'rx'
        print (Style.BRIGHT + 'Waiting until next rx cycle (%.2fs)' + Style.RESET_ALL) % til
        time.sleep(til)
        while 1:
            if typ == 'tx':
                self.do_tx()
            else:
                self.do_rx()
            typ, til = self.next_cycle()
            print (Style.BRIGHT + "Sleeping until the prophecy is fulfilled (%.2fs)" + Style.RESET_ALL) % til
            time.sleep(til)

    def do_tx(self):
        if not self.tx_msg:
            print (Fore.RED + 'Nothing to TX, waiting until RX cycle' + Style.RESET_ALL)
            return
        print (Style.BRIGHT + Fore.BLUE + "Transmitting" + Style.RESET_ALL)
        self.audio.play(self.tx_signal)
        print (Style.BRIGHT + Fore.BLUE + "DONE!" + Style.RESET_ALL)

        
    def do_rx(self):
        print (Style.BRIGHT + Fore.BLUE + "Receiving" + Style.RESET_ALL)
        signal = self.audio.record(TX_LENGTH)
        wavfile.write('lol.wav', 44100, signal)
        print (Style.BRIGHT + Fore.BLUE + "Decoding" + Style.RESET_ALL)
        msg = self.pfsk.decode(signal)
        try:
            msg = self.rs.decode(msg)
        except:
            msg = Fore.RED + "UNRELIABLE DECODE: " + msg
        if not msg:
            print (Fore.RED + "No message decoded." + Style.RESET_ALL)
        else:
            print (Style.BRIGHT + Fore.GREEN + msg + Style.RESET_ALL)
        print (Style.BRIGHT + Fore.BLUE + "DONE!" + Style.RESET_ALL)
        typ, til = self.next_cycle()
        timeout = til-2
        self.tx_msg = self.timed_input(timeout)
        if self.tx_msg:
            self.tx_msg += " "*(self.tx_length-(len(self.tx_msg)%self.tx_length))
            self.tx_msg = self.rs.encode(self.tx_msg)
            self.tx_signal = self.pfsk.encode(self.tx_msg)
            self.tx_signal = self.tx_signal.astype(np.float32)
            wavfile.write('lol2.wav', 44100, self.tx_signal)
            self.tx_signal = self.tx_signal.tostring()

    def timed_input(self, timeout):
        sys.stdout.write("Please input a message to transmit next cycle (%.2fs):\n" % timeout)
        i, o, e = select.select( [sys.stdin], [], [], timeout )
        if i:
            i = sys.stdin.readline().strip()[:self.tx_length]
        if not i:
            print (Fore.RED + "No message input, not transmitting next cycle..." + Style.RESET_ALL)
        return i

    def encode(self):
        if self.options['fec']:
            rs = reedsolo.RSCodec(len(self.options['msg']))
            self.options['msg'] = rs.encode(self.options['msg'])
        print Style.BRIGHT + "Encoding..." + Style.RESET_ALL
        t = time.time()
        signal = self.pfsk.encode(self.options['msg'])
        print (Style.BRIGHT + "Done! (%.2f seconds)" + Style.RESET_ALL) % (time.time()-t)
        print Style.BRIGHT + "Writing..." + Style.RESET_ALL
        wavfile.write(self.options['file'], pfsk.SAMPLERATE, signal.astype(np.int32))

    def decode(self):
        print Style.BRIGHT + "Reading..." + Style.RESET_ALL
        _, signal = wavfile.read(self.options['file'])
        print Style.BRIGHT + "Decoding..." + Style.RESET_ALL
        t = time.time()
        msg = self.pfsk.decode(signal)
        if self.options['fec']:
            print 'doing fec'
            rs = reedsolo.RSCodec(len(msg)/2)
            msg = rs.decode(msg)
        print (Style.BRIGHT + Fore.BLUE + "Message: " + Fore.GREEN + "%s" + Style.RESET_ALL) % msg
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
        if option in ['encode_wav', 'decode_wav', 'file', 'fec']: return
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
