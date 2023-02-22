import time
import os

from ..node import JVSNode
from ..master import JVSMaster

from ..midiparse import (
    midi_parse,
    MetaEvent, MetaEventType,
    MidiEvent, MidiEventType,
)
# from ..midiparse import *


data = open(os.path.join(os.path.dirname(__file__), "happy-birthday.mid"), "rb").read()


hdr, trks = midi_parse(data)
output = []

tempo = 500_000 / 1000_000
tracks = list(trks)
for track in (tracks[0], tracks[6]):
    print(track)
    divs = track.header.division

    time_ = 0
    for (deltaTicks, event) in track:
        # print(deltaTicks, event.ev_type, event.tag)
        if isinstance(event, MetaEvent):
            match event.ev_type:
                case MetaEventType.Tempo:
                    # event.tag = microseconds per midi_quarter
                    print("tempo=", event.tag)
                    tempo = event.tag / 1000_000
                    print(tempo)

        elif isinstance(event, MidiEvent):
            if isinstance(divs, tuple):
                # divs = (frames per second, ticks per frame)
                deltaTime = (deltaTicks / divs[1]) / divs[0]
            else:
                # divs = ticks
                deltaTime = (deltaTicks / divs) * tempo
                if event.ev_type == MidiEventType.NoteOn:
                    print(time_, event.tag, deltaTime, tempo, deltaTicks)

            time_ += deltaTime
            match event.ev_type:
                case MidiEventType.NoteOn:
                    # print("Lol")
                    key, vel = event.tag
                    output.append((time_, event.channel, key, vel))
                case MidiEventType.NoteOff:
                    # print("Lolnt")
                    key, _ = event.tag
                    output.append((time_, event.channel, key, 0))


# print(output)
# output.sort(key=lambda x: x[0])


def map_note(note):
    note += 24
    while note < 79:
        note += 12 * 2
    while note > 108:
        note -= 12
    return note


def play(nodes: list[JVSNode]):
    start = time.time()
    # midi_data.sort(key=lambda x: int(x[1]))
    for at, channel, key, vel in output:
        print(at, channel, key, vel)
        pos = time.time() - start
        time.sleep(max(0, at - pos))
        # continue
        note = map_note(key)

        if vel == 0:
            nodes[0].send(
                JVSNode.cmd_light(0, 0, note, 0),
            )
        else:
            if note < 79 or note > 108:
                print(f"Note out of range!", note)
            else:
                print(f"Play: {channel} {note}")
            nodes[0].send(
                JVSNode.cmd_light(0, 0, note, 255),
                JVSNode.cmd_note_down(0, 0, note, vel),
            )


if __name__ == "__main__":
    jvs = JVSMaster()
    jvs.enumerate_bus()

    if len(jvs.nodes) < 1:
        print("Well shit we ain't got a node to play on!")
        quit()

    play(jvs.nodes)
