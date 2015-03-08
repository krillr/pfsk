from colorama import init, Fore, Back, Style
import audio, argparse, json, os, select, sys

class Schmetterling:
    options = argparse.ArgumentParser()
    options.add_argument('--interval')
    options.add_argument('--recording-device', type=int)
    options.add_argument('--playback-device', type=int)

    def __init__(self):
        self.options = dict(Schmetterling.options.parse_args()._get_kwargs())
        self.audio = audio.Interface()

    def run(self):
        self.healthcheck()
        missing = [x for x, y in self.options.items() if y == None]
        for x in missing:
            self.options[x] = self.interactive_config(x)
            print Style.RESET_ALL

    def healthcheck(self):
        devices = self.audio.get_devices()
        if not [x for x in self.audio.get_devices() if x['maxInputChannels'] > 0]:
            print Back.RED + "You do not appear to have any recording audio devices. Exiting." + Style.RESET_ALL
            sys.exit(1)
        if not [x for x in self.audio.get_devices() if x['maxOutputChannels'] > 0]:
            print Back.RED + "You do not appear to have any playback audio devices. Exiting." + Style.RESET_ALL
            sys.exit(1)

    def interactive_config(self, option):
        if option == 'interval':
            options = ('odd', 'even')
            choice = raw_input(Style.BRIGHT + 'Please choose an interval (' + Fore.GREEN + 'odd' + Fore.RESET + '/' + Fore.GREEN + 'even' + Fore.RESET +'): ').lower()
            if not choice in options:
                print Fore.RED + 'Invalid choice' + Style.RESET_ALL
                return self.interactive_config(option)
            return choice
        if option == 'recording_device':
            devices = [x for x in self.audio.get_devices() if x['maxInputChannels'] > 0]
            print Style.BRIGHT + "Please choose a device to monitor for transmissions:"
            for x in range(len(devices)):
                print (Style.BRIGHT + Fore.GREEN + "%i)" + Fore.BLUE + " %s" + Style.RESET_ALL) % (x, devices[x]['name'])
            choice = raw_input(Style.BRIGHT + 'Device: ')
            if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(devices):
                print Fore.RED + 'Invalid choice' + Style.RESET_ALL
                return self.interactive_config(option)
            return devices[int(choice)]['index']
        if option == 'playback_device':
            devices = [x for x in self.audio.get_devices() if x['maxOutputChannels'] > 0]
            print Style.BRIGHT + "Please choose a device to use for transmitting:" + Style.RESET_ALL
            for x in range(len(devices)):
                print (Style.BRIGHT + Fore.GREEN + "%i)" + Fore.BLUE + " %s" + Style.RESET_ALL) % (x, devices[x]['name'])
            choice = raw_input(Style.BRIGHT + 'Device: ')
            if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(devices):
                print Fore.RED + 'Invalid choice' + Style.RESET_ALL
                return self.interactive_config(option)
            return devices[int(choice)]['index']

if __name__ == '__main__':
    app = Schmetterling()
    app.run()

# vim: ai ts=4 sts=4 et sw=4 ft=python
# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
