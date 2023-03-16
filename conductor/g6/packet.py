from .const import G6_MARK, G6_NODE_MASTER, G6_SYNC


class G6PacketOut:
    def __init__(self, dst: int, *cmds: tuple[int, bytes]):
        self.dst = dst
        self.cmds = cmds

    def __iter__(self):
        return iter(bytes(self))

    def __bytes__(self):
        body = bytearray([self.dst, 0])
        for cmd, data in self.cmds:
            body.append(cmd)
            body += data
        body[1] = len(body)
        body += bytearray([sum(body) % 256])
        escaped = bytearray()
        for i in body:
            if i == G6_SYNC or i == G6_MARK:
                escaped.append(G6_MARK)
                escaped.append(i - 1)
            else:
                escaped.append(i)
        return b"\xE0" + escaped


class G6PacketIn:
    def __init__(self, status: int, data: bytes):
        self.status = status
        self.data = data

    @classmethod
    def from_packet(cls, packet: bytes):
        if len(packet) < 5:
            return None

        if packet[0] != G6_SYNC:
            return None
        if packet[1] != G6_NODE_MASTER:
            return None
        dlen = packet[2]
        status = packet[3]
        data = packet[3:3 + dlen - 2]
        check = packet[3 + dlen - 2]
        if (dlen + status + sum(data)) % 256 != check:
            print("Checksum failed!")
            return None

        return cls(status, data)

    @classmethod
    def _ser_read_one(cls, ser):
        byte = ser.read(1)
        if len(byte) == 0:
            raise TimeoutError
        return byte[0]

    @classmethod
    def from_serial(cls, ser):
        while True:
            while ser.read_one() != G6_SYNC:
                continue
            dest = ser.read_one()
            dlen = ser.read_one()
            status = ser.read_one()

            data = bytearray()
            for _ in range(dlen - 2):
                data.append(ser.read_one())

            calc_sum = (dest + dlen + status + sum(data)) % 256
            try:
                check = ser.read_one()
            except TimeoutError:
                raise
            if calc_sum != check:
                print("W: Checksum failed!")
                print(f"[{dest:02x} {dlen:02x} {status:02x} {data}]  {calc_sum}(exp)!={check:02x}(seen)")
                pass  # continue
            if dest != G6_NODE_MASTER:
                print("W: Packet not for master")
                continue

            return cls(status, data)
