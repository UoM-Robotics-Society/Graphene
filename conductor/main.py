from midiparse import (
    midi_parse, MidiMixer,

    MetaEventType, MidiEventType, MidiTrackEventType
)
from g6 import G6Node, G6Master

import time


# TODO: Fetch from g6
KNOWN_INSTRUMENTS = [
    "Tambourine",
    "Musical Steppers",
    "GlockOBot",
]


MIDI_PROGAM_NAMES = [
    "Acoustic grand piano",
    "Bright acoustic piano",
    "Electric grand piano",
    "Honky tonk piano",
    "Electric piano 1",
    "Electric piano 2",
    "Harpsicord",
    "Clavinet",
    "Celesta",
    "Glockenspiel",
    "Music box",
    "Vibraphone",
    "Marimba",
    "Xylophone",
    "Tubular bell",
    "Dulcimer",
    "Hammond / drawbar organ",
    "Percussive organ",
    "Rock organ",
    "Church organ",
    "Reed organ",
    "Accordion",
    "Harmonica",
    "Tango accordion",
    "Nylon string acoustic guitar",
    "Steel string acoustic guitar",
    "Jazz electric guitar",
    "Clean electric guitar",
    "Muted electric guitar",
    "Overdriven guitar",
    "Distortion guitar",
    "Guitar harmonics",
    "Acoustic bass",
    "Fingered electric bass",
    "Picked electric bass",
    "Fretless bass",
    "Slap bass 1",
    "Slap bass 2",
    "Synth bass 1",
    "Synth bass 2",
    "Violin",
    "Viola",
    "Cello",
    "Contrabass",
    "Tremolo strings",
    "Pizzicato strings",
    "Orchestral strings / harp",
    "Timpani",
    "String ensemble 1",
    "String ensemble 2 / slow strings",
    "Synth strings 1",
    "Synth strings 2",
    "Choir aahs",
    "Voice oohs",
    "Synth choir / voice",
    "Orchestra hit",
    "Trumpet",
    "Trombone",
    "Tuba",
    "Muted trumpet",
    "French horn",
    "Brass ensemble",
    "Synth brass 1",
    "Synth brass 2",
    "Soprano sax",
    "Alto sax",
    "Tenor sax",
    "Baritone sax",
    "Oboe",
    "English horn",
    "Bassoon",
    "Clarinet",
    "Piccolo",
    "Flute",
    "Recorder",
    "Pan flute",
    "Bottle blow / blown bottle",
    "Shakuhachi",
    "Whistle",
    "Ocarina",
    "Synth square wave",
    "Synth saw wave",
    "Synth calliope",
    "Synth chiff",
    "Synth charang",
    "Synth voice",
    "Synth fifths saw",
    "Synth brass and lead",
    "Fantasia / new age",
    "Warm pad",
    "Polysynth",
    "Space vox / choir",
    "Bowed glass",
    "Metal pad",
    "Halo pad",
    "Sweep pad",
    "Ice rain",
    "Soundtrack",
    "Crystal",
    "Atmosphere",
    "Brightness",
    "Goblins",
    "Echo drops / echoes",
    "Sci fi",
    "Sitar",
    "Banjo",
    "Shamisen",
    "Koto",
    "Kalimba",
    "Bag pipe",
    "Fiddle",
    "Shanai",
    "Tinkle bell",
    "Agogo",
    "Steel drums",
    "Woodblock",
    "Taiko drum",
    "Melodic tom",
    "Synth drum",
    "Reverse cymbal",
    "Guitar fret noise",
    "Breath noise",
    "Seashore",
    "Bird tweet",
    "Telephone ring",
    "Helicopter",
    "Applause",
    "Gunshot",
]


def load_midi(filename):
    with open(filename, "rb") as midifile:
        hdr, trks = midi_parse(midifile.read())

    tracks = {}
    for track in trks:
        name = None
        channels = {}
        for _, event in track:
            type_ = event.track_ev_type
            match type_:
                case MidiTrackEventType.Meta:
                    track_ev = event.track_ev
                    if track_ev.ev_type == MetaEventType.TrackName:
                        name = track_ev.tag
                case MidiTrackEventType.Midi:
                    channels.setdefault(event.track_ev.channel, -1)
                    if event.track_ev.ev_type == MidiEventType.ProgramChange:
                        channels[event.track_ev.channel] = event.track_ev.tag

        tracks[track] = (name, channels)

    mixer = MidiMixer.for_track(hdr, trks)
    return tracks, mixer

    for timestamp, evt in mixer:
        if evt.track_ev_type != MidiTrackEventType.Midi:
            continue
        track_ev = evt.track_ev
        print(id(evt.track), track_ev.ev_type, track_ev.channel, track_ev.tag)


def play(g6: G6Master):
    # tracks, mixer = load_midi(r"C:\Users\Nathan\Downloads\Carol-Of-The-Bells-1.mid")
    tracks, mixer = load_midi("../pirates-transposed.mid")
    # tracks, mixer = load_midi("../pirates-reversed.mid")

    # for i in range(76, 108):
    #     g6.nodes[0].note_down(0, 0, i, 255)
    #     time.sleep(0.1)
    #     g6.nodes[0].note_up(0, 0, i, 255)
    #     time.sleep(0.1)

    # quit()

    mappings = {}
    for (track, (name, channels)) in tracks.items():
        for node in g6.nodes:
            if node.name == name:
                break
        else:
            print(f"Unable to allocate track: {name}")
            # node = g6.nodes[0]
            continue

        mappings[track] = node

    start = time.time()

    for timestamp, evt in mixer:
        delta = (timestamp / 1000) - (time.time() - start)
        if delta > 0:
            time.sleep(delta)

        if evt.track_ev_type != MidiTrackEventType.Midi:
            continue
        track_ev = evt.track_ev

        node: G6Node = mappings.get(evt.track)
        if node is None:
            continue

        if track_ev.ev_type == MidiEventType.NoteOn:
            note, vel = track_ev.tag
            if vel == 0:
                print("Up", node.name, track_ev.channel, note)
                node.light(timestamp, track_ev.channel, note, 0)
                node.note_up(timestamp, track_ev.channel, note, vel)
            else:
                print("Down", node.name, track_ev.channel, note)
                node.light(timestamp, track_ev.channel, note, 255)
                node.note_down(timestamp, track_ev.channel, note, vel)
        elif track_ev.ev_type == MidiEventType.NoteOff:
            print("Up", node.name, track_ev.channel, note)
            note, vel = track_ev.tag
            node.light(timestamp, track_ev.channel, note, 0)
            node.note_up(timestamp, track_ev.channel, note, vel)


def main():
    g6 = G6Master()
    g6.enumerate_bus()

    try:
        play(g6)
    except KeyboardInterrupt:
        print("Shutting down")
        g6.reset()


if __name__ == "__main__":
    main()
