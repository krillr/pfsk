import argparse, os, select

class Schmetterling:
    options = argparse.ArgumentParser()
    options.addargument('--interval')
    options.addargument('--recording-device', type=int)
    options.addargument('--playback-device', type=int)

    def __init__(self):
        self.options = Schmetterling.parse_args()


# vim: ai ts=4 sts=4 et sw=4 ft=python
# vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
