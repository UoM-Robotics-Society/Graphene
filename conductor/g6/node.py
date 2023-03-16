import struct
import time

from .error import G6ReportNack
from .packet import G6PacketOut
from .const import (
    G6_CMD_GRAPHENE_DOWN, G6_CMD_READ_ID, G6_CMD_GET_CMD_VERSION, G6_CMD_GET_COMM_VERSION,
    G6_CMD_GET_FEATURES, G6_CMD_GET_G6_VERSION, G6_CMD_GRAPHENE_CNTR, G6_CMD_GRAPHENE_INCR,
    G6_CMD_GRAPHENE_PING, G6_FEATURE_NOTE_CHANNEL, G6_FEATURE_EOF, G6_CMD_GRAPHENE_UP,
    G6_PING_DELAY, G6_CMD_GRAPHENE_LIGHT, G6_CMD_GRAPHENE_CONTROL, G6_REPORT_OK,
    G6_FEATURE_LIGHT_CHANNEL, G6_FEATURE_CONTROL_CHANNEL, G6_FEATURE_OFFSET
)


class G6Node:
    def __init__(self, master, address):
        from .master import G6Master

        self.master: G6Master = master

        self.address = address
        self.features = bytearray([G6_FEATURE_EOF])
        self.ioident = ""
        self.cmd_version = 0x00
        self.g6_version = 0x00
        self.comm_version = 0x00
        self.latency = 0.0

    def _get_ioident(self, n):
        split = self.ioident.split(";")
        if n < len(split):
            return split[n]
        return n

    def get_features(self):
        print(self.features)
        features = bytearray(self.features)
        json_features = []

        while features:
            op = features.pop(0)
            if op == G6_FEATURE_EOF:
                break
            elif op == G6_FEATURE_NOTE_CHANNEL:
                json_features.append({
                    "type": "note",
                    "channel": features.pop(0),
                    "min": features.pop(0),
                    "max": features.pop(0),
                })
            elif op == G6_FEATURE_LIGHT_CHANNEL:
                json_features.append({
                    "type": "light",
                    "channel": features.pop(0),
                    "min": features.pop(0),
                    "max": features.pop(0),
                })
            elif op == G6_FEATURE_CONTROL_CHANNEL:
                json_features.append({
                    "type": "control",
                    "channel": features.pop(0),
                    "min": features.pop(0),
                    "max": features.pop(0),
                })
            elif op == G6_FEATURE_OFFSET:
                offset = struct.unpack(">h", features[:2])[0]
                features.pop(0)
                features.pop(0)
                features.pop(0)
                json_features.append({
                    "type": "offset",
                    "offset": offset,
                })
            else:
                json_features.append({
                    "type": "?",
                    "0": features.pop(0),
                    "1": features.pop(0),
                    "2": features.pop(0),
                })

        return json_features

    @property
    def feature_offset(self):
        for i in self.get_features():
            if i["type"] == "offset":
                return i["offset"]
        return 0

    def _channels(self, type_):
        channels = {}
        for i in self.get_features():
            if i["type"] == type_:
                channels[i["channel"]] = (i["min"], i["max"])
        return channels

    @property
    def channels(self):
        return self._channels("note")

    @property
    def light_channels(self):
        return self._channels("light")

    @property
    def contorl_channels(self):
        return self._channels("control")

    @property
    def name(self):
        return self._get_ioident(0)

    @property
    def version(self):
        return self._get_ioident(1)

    def request_info(self):
        self.ioident = self.exchange_one((G6_CMD_READ_ID, b"")).decode("latin-1")
        self.cmd_version = self.exchange_one((G6_CMD_GET_CMD_VERSION, b""))[0]
        self.g6_version = self.exchange_one((G6_CMD_GET_G6_VERSION, b""))[0]
        self.comm_version = self.exchange_one((G6_CMD_GET_COMM_VERSION, b""))[0]
        self.features = self.exchange_one((G6_CMD_GET_FEATURES, b""))

    def resend(self):
        if self._last is not None:
            if self._last[1]:
                return self.master.exchange(self._last[0])
            else:
                self.master.write(self._last[0])

    def send(self, *cmds: tuple[int, bytes]):
        pkt = G6PacketOut(self.address, *cmds)
        self._last = (bytes(pkt), False)
        return self.master.write(self._last[0])

    def exchange(self, *cmds: tuple[int, bytes]):
        pkt = G6PacketOut(self.address, *cmds)
        self._last = (bytes(pkt), True)
        return self.master.exchange(self._last[0])

    def exchange_one(self, cmd: tuple[int, bytes]):
        pkt = G6PacketOut(self.address, cmd)
        self._last = (bytes(pkt), True)
        response = self.master.exchange(self._last[0])
        if response.data[0] != G6_REPORT_OK:
            raise G6ReportNack()
        return response.data[1:]

    def incr(self):
        self.send((G6_CMD_GRAPHENE_INCR, b""))

    def cntr(self):
        return self.send((G6_CMD_GRAPHENE_CNTR, b""))

    def ping(self):
        return self.exchange((G6_CMD_GRAPHENE_PING, b""))

    @staticmethod
    def cmd_note_down(time, channel, note, vel):
        return (G6_CMD_GRAPHENE_DOWN, struct.pack(
            "<IBBB", time, channel, note, vel
        ))

    @staticmethod
    def cmd_note_up(time, channel, note, vel):
        return (G6_CMD_GRAPHENE_UP, struct.pack(
            "<IBBB", time, channel, note, vel
        ))

    @staticmethod
    def cmd_light(time, channel, light, value):
        return (G6_CMD_GRAPHENE_LIGHT, struct.pack(
            "<IBBB", time, channel, light, value
        ))

    @staticmethod
    def cmd_control(time, channel, control, value):
        return (G6_CMD_GRAPHENE_CONTROL, struct.pack(
            "<IBBB", time, channel, control, value
        ))

    def note_down(self, time, channel, note, vel):
        self.send(self.cmd_note_down(time, channel, note, vel))

    def note_up(self, time, channel, note, vel):
        self.send(self.cmd_note_up(time, channel, note, vel))

    def light(self, time, channel, light, value):
        self.send(self.cmd_light(time, channel, light, value))

    def control(self, time, channel, control, value):
        self.exchange_one(self.cmd_control(time, channel, control, value))

    def measure_latency(self):
        measurements = []
        for _ in range(5):
            start = time.time()
            self.ping()
            measurements.append(time.time() - start)
            time.sleep(G6_PING_DELAY)
        avg = sum(measurements) / len(measurements)
        self.latency = avg / 2

    def _features_str(self):
        ret = ""
        features = bytearray(self.features)
        while features:
            op = features.pop(0)
            if op == G6_FEATURE_EOF:
                break
            elif op == G6_FEATURE_NOTE_CHANNEL:
                ret += f"   - Note    | Channel {features.pop(0)}, min:{features.pop(0)}/max:{features.pop(0)}\n"
            elif op == G6_FEATURE_LIGHT_CHANNEL:
                ret += f"   - Light   | Channel {features.pop(0)}, min:{features.pop(0)}/max:{features.pop(0)}\n"
            elif op == G6_FEATURE_CONTROL_CHANNEL:
                ret += f"   - Control | Channel {features.pop(0)}, min:{features.pop(0)}/max:{features.pop(0)}\n"
            elif op == G6_FEATURE_OFFSET:
                offset = struct.unpack(">h", features[:2])[0]
                features.pop(0)
                features.pop(0)
                features.pop(0)
                if offset > 0:
                    ret += f"   - Requested offset: {offset}ms ahead\n"
                elif offset == 0:
                    ret += "   - Requested offset: none\n"
                else:
                    ret += f"   - Requested offset: {-offset}ms behind\n"
            else:
                ret += f"   - Unk feature {op:02x} ({features.pop(0):02x} {features.pop(0):02x} {features.pop(0):02x})\n"
        return ret

    @property
    def offset(self):
        requested = 0
        features = bytearray(self.features)
        while features:
            op = features.pop(0)
            if op == G6_FEATURE_EOF:
                break
            elif op == G6_FEATURE_OFFSET:
                requested = struct.unpack(">h", features[:2])[0] / 1000
            features.pop(0)
            features.pop(0)
            features.pop(0)

        return requested + self.latency

    def __str__(self):
        return (
            f"G6 Node {self.address}:\n"
            f"  Identification: {self.ioident}\n"
            f"  CMD Version:    {self.cmd_version >> 4}.{self.cmd_version & 0x0f}\n"
            f"  G6 Version:    {self.g6_version >> 4}.{self.g6_version & 0x0f}\n"
            f"  Comm Version:   {self.comm_version >> 4}.{self.comm_version & 0x0f}\n"
            f"  Latency:       ~{self.latency * 1000:.02f}ms\n"
            f"  Offset:         {abs(self.offset) * 1000:.02f}ms {'ahead' if self.offset > 0 else '' if self.offset == 0 else 'behind'}\n"
            f"  Features:       \n"
            + self._features_str()
        )

    def __repr__(self):
        return f"<G6Node: {self.address} {self.ioident}>"
