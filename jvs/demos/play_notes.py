import time

from ..node import JVSNode
from ..master import JVSMaster


midi_data = open("jvs/demos/wii.csv").read().strip().split("\n")
midi_data = open("jvs/demos/yr.csv").read().strip().split("\n")
midi_data = open("jvs/demos/pirates.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/ff.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/nyan.csv").read().strip().split("\n")
# midi_data = open("jvs/demos/sims.csv").read().strip().split("\n")
midi_data = [[j.strip() for j in i.split(",")] for i in midi_data]


# Flats: A, B, D, E
C4 = 261.63
Eb4 = 311.13
F4 = 349.23
G4 = 392.00
Ab4 = 415.3
Bb4 = 466.16
C5 = 523.25
Db5 = 554.37
Eb5 = 622.25
F5 = 698.46
G5 = 783.99
Ab5 = 830.61
Bb5 = 932.33
C6 = C5#1046.5
Db6 = Db5#1108.7
F6 = F5#1396.9


tune1 = [
    # Hz
    (F4, 1), (Ab4, .75), (F4, .5), (F4, .25), (Bb4, .5), (F4, .5), (Eb4, .5),
    (F4, 1), (C5, .75), (F4, .5), (F4, .25), (Db5, .5), (C5, .5), (Ab4, .5),

    (F4, .5), (C5, .5), (F5, .5), (F4, .25), (Eb4, .5), (Eb4, .25), (C4, .5), (G4, .5), (F4, 2.5),

    (0, 1),
]
tune2 = [
    # Hz
    (F5, 1), (Ab5, .75), (F5, .5), (F5, .25), (Bb5, .5), (F5, .5), (Eb5, .5),
    (F5, 1), (C6, .75), (F5, .5), (F4, .25), (Db6, .5), (C6, .5), (Ab5, .5),

    (F5, .5), (C6, .5), (F6, .5), (F5, .25), (Eb5, .5), (Eb5, .25), (C5, .5), (G5, .5), (F5, 2.5),

    (0, 1),
]

# tune = [
#     (F4, 1), (Ab4, 1), 
# ]


scale = 2000  # wii
scale = 750  # pirates
# scale = 20000  # fireflies
# scale = 850  # ff
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
# scale = tempo / (180000 / division)
# print(scale)
# scale = 2000

def play(nodes: JVSNode):
    playing = {}

    while 1:
        start = time.time()
        # midi_data.sort(key=lambda x: int(x[1]))
        for channel, at, command, *args in midi_data:
            at = int(at)
            pos = (time.time() - start) * scale

            if command == "Note_on_c" or command == "Note_off_c":
                vel = int(args[2])
            else:
                vel = -1

            if command == "Note_off_c" or vel == 0:
                time.sleep(max(0, (at - pos) / scale))

                note = int(args[1])
                if playing.get(1) == note:
                    del playing[1]
                    nodes[1].note_down(0, 1, 0, 255)
                elif playing.get(0) == note:
                # else:
                    if 0 in playing:
                        del playing[0]
                    nodes[0].note_down(0, 1, 0, 255)
                    if 1 not in playing:
                        nodes[1].note_down(0, 1, 0, 255)
            elif command == "Note_on_c":
                time.sleep(max(0, (at - pos) / scale))
                note = int(args[1])

                # if note > 80:
                # note -= 14
                freq = 440 * (2 ** ((note - 69) / 12))
                freq = int(freq // 4)
                if freq > 255:
                    print("Out of range:", at, note, freq)
                    continue

                # playing = {}
                if 0 in playing:
                    if 1 not in playing:
                        print("1", at, note, freq)
                        nodes[1].note_down(0, 1, freq, 255)
                        playing[1] = note
                else:
                    print("0", at, note, freq)
                    nodes[0].note_down(0, 1, freq, 255)
                    if 1 not in playing:
                        nodes[1].note_down(0, 1, freq, 255)
                    playing[0] = note
                ...


        # for ((freq1, delay1), (freq2, delay2)) in zip(tune1, tune2):
        if False:
            freq1 = int(freq1 // 4)
            # freq2 = int(freq2 // 4)
            nodes[0].note_down(0, 1, freq1, 255)
            nodes[1].note_down(0, 1, freq2, 255)
            print(freq1, freq2)
            assert delay1 == delay2
            time.sleep(delay1 / 2)  # /2
            nodes[0].note_down(0, 1, 0, 255)
            nodes[1].note_down(0, 1, 0, 255)


if __name__ == "__main__":
    jvs = JVSMaster()
    jvs.enumerate_bus()

    if len(jvs.nodes) < 1:
        print("Well shit we ain't got a node to play on!")
        quit()
    if len(jvs.nodes) < 2:
        print(":(")
        # quit()

    # for freq, delay in tune:
    #     freq = int(freq // 4)
    #     jvs.nodes[0].note_down(0, 1, freq, 255)
    #     jvs.nodes[1].note_down(0, 1, freq, 255)
    #     time.sleep(delay / 2)
    #     jvs.nodes[0].note_down(0, 1, 0, 255)
    #     jvs.nodes[1].note_down(0, 1, 0, 255)

    play(jvs.nodes)
