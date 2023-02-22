import struct
import time

from .error import JVSReportNack
from .packet import JVSPacketOut
from .const import (
    JVS_CMD_GRAPHENE_DOWN, JVS_CMD_READ_ID, JVS_CMD_GET_CMD_VERSION, JVS_CMD_GET_COMM_VERSION,
    JVS_CMD_GET_FEATURES, JVS_CMD_GET_JVS_VERSION, JVS_CMD_GRAPHENE_CNTR, JVS_CMD_GRAPHENE_INCR,
    JVS_CMD_GRAPHENE_PING, JVS_FEATURE_NOTE_CHANNEL, JVS_FEATURE_EOF, JVS_CMD_GRAPHENE_UP,
    JVS_PING_DELAY, JVS_CMD_GRAPHENE_LIGHT, JVS_CMD_GRAPHENE_CONTROL, JVS_REPORT_OK,
    JVS_FEATURE_LIGHT_CHANNEL, JVS_FEATURE_CONTROL_CHANNEL, JVS_FEATURE_OFFSET
)


class JVSNode:
    def __init__(self, master, address):
        from .master import JVSMaster

        self.master: JVSMaster = master

        self.address = address
        self.features = bytearray([JVS_FEATURE_EOF])
        self.ioident = ""
        self.cmd_version = 0x00
        self.jvs_version = 0x00
        self.comm_version = 0x00
        self.latency = 0.0

    def request_info(self):
        self.ioident = self.exchange_one((JVS_CMD_READ_ID, b"")).decode("latin-1")
        self.cmd_version = self.exchange_one((JVS_CMD_GET_CMD_VERSION, b""))[0]
        self.jvs_version = self.exchange_one((JVS_CMD_GET_JVS_VERSION, b""))[0]
        self.comm_version = self.exchange_one((JVS_CMD_GET_COMM_VERSION, b""))[0]
        self.features = self.exchange_one((JVS_CMD_GET_FEATURES, b""))

    def resend(self):
        if self._last is not None:
            if self._last[1]:
                return self.master.exchange(self._last[0])
            else:
                self.master.write(self._last[0])

    def send(self, *cmds: tuple[int, bytes]):
        pkt = JVSPacketOut(self.address, *cmds)
        self._last = (bytes(pkt), False)
        return self.master.write(self._last[0])

    def exchange(self, *cmds: tuple[int, bytes]):
        pkt = JVSPacketOut(self.address, *cmds)
        self._last = (bytes(pkt), True)
        return self.master.exchange(self._last[0])

    def exchange_one(self, cmd: tuple[int, bytes]):
        pkt = JVSPacketOut(self.address, cmd)
        self._last = (bytes(pkt), True)
        response = self.master.exchange(self._last[0])
        if response.data[0] != JVS_REPORT_OK:
            raise JVSReportNack()
        return response.data[1:]

    def incr(self):
        self.send((JVS_CMD_GRAPHENE_INCR, b""))

    def cntr(self):
        return self.send((JVS_CMD_GRAPHENE_CNTR, b""))

    def ping(self):
        return self.exchange((JVS_CMD_GRAPHENE_PING, b""))

    @staticmethod
    def cmd_note_down(time, channel, note, vel):
        return (JVS_CMD_GRAPHENE_DOWN, struct.pack(
            "<IBBB", time, channel, note, vel
        ))

    @staticmethod
    def cmd_note_up(time, channel, note, vel):
        return (JVS_CMD_GRAPHENE_UP, struct.pack(
            "<IBBB", time, channel, note, vel
        ))

    @staticmethod
    def cmd_light(time, channel, light, value):
        return (JVS_CMD_GRAPHENE_LIGHT, struct.pack(
            "<IBBB", time, channel, light, value
        ))

    @staticmethod
    def cmd_control(time, channel, control, value):
        return (JVS_CMD_GRAPHENE_CONTROL, struct.pack(
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
            time.sleep(JVS_PING_DELAY)
        avg = sum(measurements) / len(measurements)
        self.latency = avg / 2

    def _features_str(self):
        ret = ""
        features = bytearray(self.features)
        while features:
            op = features.pop(0)
            if op == JVS_FEATURE_EOF:
                break
            elif op == JVS_FEATURE_NOTE_CHANNEL:
                ret += f"   - Note    | Channel {features.pop(0)}, min:{features.pop(0)}/max:{features.pop(0)}\n"
            elif op == JVS_FEATURE_LIGHT_CHANNEL:
                ret += f"   - Light   | Channel {features.pop(0)}, min:{features.pop(0)}/max:{features.pop(0)}\n"
            elif op == JVS_FEATURE_CONTROL_CHANNEL:
                ret += f"   - Control | Channel {features.pop(0)}, min:{features.pop(0)}/max:{features.pop(0)}\n"
            elif op == JVS_FEATURE_OFFSET:
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
            if op == JVS_FEATURE_EOF:
                break
            elif op == JVS_FEATURE_OFFSET:
                requested = struct.unpack(">h", features[:2])[0] / 1000
            features.pop(0)
            features.pop(0)
            features.pop(0)

        return requested + self.latency

    def __str__(self):
        return (
            f"JVS Node {self.address}:\n"
            f"  Identification: {self.ioident}\n"
            f"  CMD Version:    {self.cmd_version >> 4}.{self.cmd_version & 0x0f}\n"
            f"  JVS Version:    {self.jvs_version >> 4}.{self.jvs_version & 0x0f}\n"
            f"  Comm Version:   {self.comm_version >> 4}.{self.comm_version & 0x0f}\n"
            f"  Latency:       ~{self.latency * 1000:.02f}ms\n"
            f"  Offset:         {abs(self.offset) * 1000:.02f}ms {'ahead' if self.offset > 0 else '' if self.offset == 0 else 'behind'}\n"
            f"  Features:       \n"
            + self._features_str()
        )

    def __repr__(self):
        return f"<JVSNode: {self.address} {self.ioident}>"
