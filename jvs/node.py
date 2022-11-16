import struct
import time

from .packet import JVSPacketOut
from .const import JVS_CMD_GRAPHENE_DOWN, JVS_CMD_READ_ID, JVS_CMD_GET_CMD_VERSION, JVS_CMD_GET_COMM_VERSION, JVS_CMD_GET_FEATURES, JVS_CMD_GET_JVS_VERSION, JVS_CMD_GRAPHENE_CNTR, JVS_CMD_GRAPHENE_INCR, JVS_CMD_GRAPHENE_PING, JVS_FEATURE_CHANNEL, JVS_FEATURE_EOF, JVS_CMD_GRAPHENE_UP, JVS_PING_DELAY


class JVSNode:
    def __init__(self, master, address):
        from .master import JVSMaster

        self.master: JVSMaster = master

        self.address = address
        self.features = None
        self.ioident = None
        self.cmd_version = None
        self.jvs_version = None
        self.comm_version = None
        self.latency = None

    def request_info(self):
        self.iodent = self.send(JVSPacketOut(self.address, JVS_CMD_READ_ID)).data.decode("latin-1")
        self.cmd_version = self.send(JVSPacketOut(self.address, JVS_CMD_GET_CMD_VERSION)).data[0]
        self.jvs_version = self.send(JVSPacketOut(self.address, JVS_CMD_GET_JVS_VERSION)).data[0]
        self.comm_version = self.send(JVSPacketOut(self.address, JVS_CMD_GET_COMM_VERSION)).data[0]
        self.features = self.send(JVSPacketOut(self.address, JVS_CMD_GET_FEATURES)).data[0]
    
    def resend(self):
        if self._last is not None:
            return self.master.write(self, *self._last)

    def send(self, pkt, response=True):
        self._last = (bytes(pkt), response)
        return self.master.write(self, *self._last)

    def incr(self):
        self.send(JVSPacketOut(self.address, JVS_CMD_GRAPHENE_INCR))

    def cntr(self):
        return self.send(JVSPacketOut(self.address, JVS_CMD_GRAPHENE_CNTR))

    def ping(self):
        return self.send(JVSPacketOut(self.address, JVS_CMD_GRAPHENE_PING))
    
    def note_down(self, time, channel, note, vel):
        self.send(JVSPacketOut(self.address, JVS_CMD_GRAPHENE_DOWN, struct.pack(
            "<IBBB", time, channel, note, vel
        )), response=False)

    def note_up(self, time, channel, note, vel):
        self.send(JVSPacketOut(self.address, JVS_CMD_GRAPHENE_UP, struct.pack(
            "<IBBB", time, channel, note, vel
        )), response=False)

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
            elif op == JVS_FEATURE_CHANNEL:
                ret += f"   - Channels: {features.pop(0)}\n"
                features.pop(0)
                features.pop(0)
            else:
                ret += f"   - Unk feature {op:02x} ({features.pop(0):02x} {features.pop(0):02x} {features.pop(0):02x})\n"
        return ret

    def __str__(self):
        return (
            f"JVS Node {self.address}:\n"
            f"  Identification: {self.ioident}\n"
            f"  CMD Version:    {self.cmd_version >> 4}.{self.cmd_version & 0x0f}\n"
            f"  JVS Version:    {self.jvs_version >> 4}.{self.jvs_version & 0x0f}\n"
            f"  Comm Version:   {self.comm_version >> 4}.{self.comm_version & 0x0f}\n"
            f"  Features:       \n"
            + self._features_str() +
            f"  Latency:       ~{self.latency * 1000:.02f}ms\n"
        )

    def __repr__(self):
        return f"<JVSNode: {self.address} {self.ioident}>"
