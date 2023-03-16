#!/usr/bin/env python3

from __future__ import annotations

import pprint
import sys

from . import midi

def main():
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <midi-file>', file=sys.stderr)
        quit()

    with open(sys.argv[1], 'rb') as f:
        hdr, trks = midi.midi_parse(f.read())

        print(f'MIDI Header: fmt={hdr.fmt}, tracks={hdr.tracks}, division={hdr.division}')

        for trk in trks:
            print(f'MIDI Events:')
            pprint.pprint(list(trk))

        pprint.pprint(list(midi.MidiMixer.for_track(hdr, trks)))


if __name__ == '__main__':
    main()

