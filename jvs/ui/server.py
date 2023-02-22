import socket
import struct
import time

from threading import Thread

from ..node import JVSNode
from ..master import JVSMaster
from .msg import Msg

from ..midiparse import (
    midi_parse,
    MetaEvent, MetaEventType,
    MidiEvent, MidiEventType,
)


HOST = "0.0.0.0"
PORT = 6969


def map_note(note):
    """
    TODO: This exists as a bodge to play music that should not play
    """
    note += 24
    while note < 79:
        note += 12 * 2
    while note > 108:
        note -= 12
    return note


class Server:
    def __init__(self):
        self.jvs = JVSMaster()
        self.playing = False

        # timestamp, node, channel, note, velocity
        self.notes: list[tuple[float, JVSNode, int, int, int]] = []

        # midi channel -> instrument, channel
        self.channel_mapping: dict[int, tuple[str, int]] = {}

    def get_node(self, channel: int) -> None | tuple[JVSNode, int]:
        mapped = self.channel_mapping.get(channel)
        if mapped is None:
            return None
        for node in self.jvs.nodes:
            if node.ioident.split(";")[0] == mapped[0]:
                return node, mapped[1]
        print(f"Warning: Unable to locate a '{mapped[0]}'")
        return None

    def load_midi(self, midi: bytes):
        header, tracks = midi_parse(midi)

    def load_csv_midi(self, csv_midi: str):
        midi_data = csv_midi.strip().split("\n")
        midi_data = [[j.strip() for j in i.split(",")] for i in midi_data]
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
        scale = tempo / (180000 / division)

        self.notes.clear()

        for channel, at, command, *args in midi_data:
            at = int(at)
            channel = int(channel)

            if command == "Note_on_c" or command == "Note_off_c":
                vel = int(args[2])
            else:
                vel = -1

            node = self.get_node(channel)
            if node is None:
                continue
            timestamp = at / scale
            timestamp -= node[0].latency + node[0].offset

            match command:
                case "Note_off_c":
                    note = map_note(int(args[1]))
                    self.notes.append((timestamp, node[0], node[1], note, 0))
                case "Note_on_c":
                    note = map_note(int(args[1]))
                    self.notes.append((timestamp, node[0], node[1], note, vel))

        self.notes.sort(key=lambda x: x[0])

    def play_thread(self):
        if self.playing:
            return
        self.playing = True

        queue = list(self.notes)
        start = time.time()
        while self.playing and queue:
            at, node, channel, note, vel = queue.pop(0)

            dt = at - (time.time() - start)
            if dt > 0:
                time.sleep(dt)

            at = int(at)
            if vel:
                node.note_down(at, channel, note, vel)
            else:
                node.note_up(at, channel, note, 0)

        self.playing = False

    def client_thread(self, conn, addr):
        print(f"Connection from {addr[0]}:{addr[1]}")

        while True:
            while conn.recv(1) != b"\x69":
                continue
            op = Msg(conn.recv(1)[0])

            match op:
                case Msg._ERROR:
                    conn.close()
                    return
                case Msg.ENUMERATE:
                    self.jvs.enumerate_bus()
                    conn.send(bytearray([
                        0x6A, Msg.ENUMERATE.value, 0x00, 0x01,
                        len(self.jvs.nodes)
                    ]))
                case Msg.GET_NODES:
                    conn.send(bytearray([
                        0x6A, Msg.GET_NODES.value, 0x00, 0x01,
                        len(self.jvs.nodes)
                    ]))
                case Msg.GET_NODE:
                    node_no = conn.recv(1)[0]
                    if node_no >= len(self.jvs.nodes):
                        conn.send(bytearray([
                            0x6A, Msg._ERROR.value, 0x00, 0x00
                        ]))
                    else:
                        node = self.jvs.nodes[node_no]
                        resp = (
                            bytearray([
                                node_no,
                                node.cmd_version or 0,
                                node.jvs_version or 0,
                                node.comm_version or 0,
                            ])
                            + struct.pack("<I", int((node.latency or 0) * 1e6))
                            + (node.ioident or "").encode()
                        )
                        resp = (
                            bytearray([0x6A, Msg.GET_NODE.value])
                            + struct.pack("<H", len(resp))
                            + resp
                        )
                        conn.send(resp)
                case Msg.GET_FEATURES:
                    node_no = conn.recv(1)[0]
                    if node_no >= len(self.jvs.nodes):
                        conn.send(bytearray([
                            0x6A, Msg._ERROR.value, 0x00, 0x00
                        ]))
                    else:
                        node = self.jvs.nodes[node_no]
                        resp = (
                            bytearray([
                                node_no,
                            ]) + node.features
                        )
                        resp = (
                            bytearray([0x6A, Msg.GET_FEATURES.value])
                            + struct.pack("<H", len(resp))
                            + resp
                        )
                        conn.send(resp)
                case Msg.LOAD_MIDI:
                    nbytes = struct.unpack("<I", conn.recv(4))[0]
                    # midi_data = conn.recv(nbytes).decode("latin-1")
                    # self.load_csv_midi(midi_data)
                    midi_data = conn.recv(nbytes)
                    self.load_midi(midi_data)

                    conn.send(bytearray([
                        0x6A, Msg.LOAD_MIDI.value, 0x00, 0x00
                    ]))
                case Msg.GET_TRACKS:
                    tracks = [
                        [(1, "T1C1"), (2, "T2C2")],
                        [(3, "T2C3")],
                        [(1, "T3C1"), (6, "T3C6")],
                    ]
                    payload = bytearray([len(tracks)])
                    for track in tracks:
                        payload += bytearray([len(track)])
                        for channel in track:
                            payload += bytearray([channel[0]])
                            payload += channel[1].encode() + b"\0"

                    conn.send(bytearray([
                        0x6A, Msg.GET_TRACKS.value
                    ]) + struct.pack("<H", len(payload)) + payload)
                case Msg.START_PLAYING:
                    Thread(target=self.play_thread, daemon=True).start()
                    conn.send(bytearray([
                        0x6A, Msg.START_PLAYING.value, 0x00, 0x00,
                    ]))
                case Msg.STOP_PLAYING:
                    self.playing = False
                    conn.send(bytearray([
                        0x6A, Msg.STOP_PLAYING.value, 0x00, 0x00,
                    ]))

    def server_thread(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((HOST, PORT))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.listen(10)
        host, port = sock.getsockname()
        print(f"Listening on {host}:{port}")

        print("Loading dummy glock channel map")
        for i in range(64):
            self.channel_mapping[i] = ("GlockOBot", 0)

        while True:
            conn, addr = sock.accept()
            Thread(target=self.client_thread, args=(conn, addr), daemon=True).start()

    def main(self):
        Thread(target=self.server_thread, daemon=True).start()

        while True:
            input()



if __name__ == "__main__":
    Server().main()
