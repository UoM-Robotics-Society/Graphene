import time

from ..node import JVSNode
from ..master import JVSMaster


# midi_data = open("jvs/demos/wii.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/yr.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/pirates.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/ff.csv").read().strip().split("\n")
midi_data = open("jvs/demos/nyan.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/sims.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/koopa.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/smb.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/zelda.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/lt.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/wonderwall.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/uefa.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/tears.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/nigeria.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/mariah.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/viva.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/badapple.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/sandstorm.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/bumblebee.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/axelf.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/despacito.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/angel.csv").read().strip().split("\n")
midi_data = open("jvs/demos/megalovania.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/batman.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/shooting.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/hedwig.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/caramelldansen.csv").read().strip().split("\n")
midi_data = [[j.strip() for j in i.split(",")] for i in midi_data]


# scale = 2000  # wii
# scale = 750  # pirates
# scale = 20000  # fireflies
# scale = 850  # ff
# scale = 1485  # ff
# scale = 227  # nyan
# scale = 3000  # sims

midi_data.sort(key=lambda x: (int(x[1]), 0 if x[2] != "Note_on_c" else -int(x[4])))

tempo = 300000
division = 100
for i in midi_data:
    if i[2] == "Tempo":
        tempo = int(i[3])
        break
for i in midi_data:
    if i[2] == "Header":
        division = int(i[5])
        break
print(tempo / (180000 / division))
scale = tempo / (180000 / division)
# print(scale)
# scale = 2000

scale *= 2

# scale = 850  # ff
# scale = 1485  # ff
# scale = 750  # pirates

# scale = 1100 # nigeria

# scale /= 2  # mariah
# scale *= 4  # megalovania


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
    for channel, at, command, *args in midi_data:
        print(channel, at, command, args)
        at = int(at)
        pos = (time.time() - start) * scale

        if command == "Note_on_c" or command == "Note_off_c":
            vel = int(args[2])
        else:
            vel = -1

        if command == "Note_off_c" or vel == 0:
            time.sleep(max(0, (at - pos) / scale))

            note = map_note(int(args[1]))

            nodes[0].send(
                JVSNode.cmd_light(0, 0, note, 0),
            )
        elif command == "Note_on_c":
            time.sleep(max(0, (at - pos) / scale))
            note = map_note(int(args[1]))

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
