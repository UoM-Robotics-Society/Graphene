import threading
import serial
import serial.tools.list_ports
import time

from .error import G6Error
from .const import COM_PORT_VID_PID, G6_NODE_BROADCAST, G6_CMD_RESET, G6_RESET_DELAY, G6_CMD_RESET_CHECK, G6_CMD_ASSIGN_ADDR, G6_POST_RESET_DELAY
from .packet import G6PacketOut
from .util import wait_resp
from .node import G6Node


MIN_SEND_DELAY = 0
# MIN_SEND_DELAY = 0.01


class G6Com:
    def __init__(self, port, baud):
        self.com = serial.Serial(port, baud)
        time.sleep(2)
        self.com.timeout = 0.1
        self.timeout = 1

    def write(self, data):
        data = bytes(data)

        self.com.write(b"\0")
        self.com.write(bytearray([len(data) >> 8, len(data) & 0xff]))

        self.com.write(data)
        self.com.flush()

        if self.com.read(1) != b"\xE0":
            raise TimeoutError

    def read_one(self):
        self.com.write(b"\1")
        timeout = int(self.timeout * 1000)
        self.com.write(bytearray([timeout >> 8, timeout & 0xff]))
        status = self.com.read(1)
        if not status:
            print("HW timeout(1)!")
            raise TimeoutError
        if status[0] != 0x00:
            print("SW timeout!")
            raise TimeoutError

        read = self.com.read(1)
        if not read:
            print("HW timeout(2)!")
            raise TimeoutError
        return read[0]

    def read_n(self, n):
        return bytearray(self.read_one() for _ in range(n))

    def flush(self):
        pass


class G6Master:
    def __init__(self, port=None, baud=115200):
        if port is None:
            port = self.locate_port()
        print(f"[+] Connecting to conductor using {port}")
        self.nodes: list[G6Node] = []
        # self.com = serial.Serial(port, baud)
        self.com = G6Com(port, baud)
        self.lock = threading.Lock()
        self._last_send = 0

    def exchange(self, data: bytes):
        self.write(data)
        with self.lock:
            ret = wait_resp(self.com)
            return ret

    def write(self, data: bytes):
        with self.lock:
            now = time.time()
            delta = now - self._last_send
            if delta < MIN_SEND_DELAY:
                time.sleep(delta)
            self._last_send = now

            self.com.write(data)

    def locate_port(self):
        devices = serial.tools.list_ports.comports()

        for i in devices:
            if (i.vid, i.pid) in COM_PORT_VID_PID:
                return i.name
        raise G6Error("No serial ports found")

    def reset(self, count=2):
        self.nodes.clear()
        for _ in range(count):
            self.com.write(G6PacketOut(G6_NODE_BROADCAST, (G6_CMD_RESET, bytearray([G6_CMD_RESET_CHECK]))))
            time.sleep(G6_RESET_DELAY)
        time.sleep(G6_POST_RESET_DELAY)

    def enumerate_bus(self, retries=5):
        self.reset(5)

        print("Enumerating bus...")
        next_id = 1
        while True:
            retry = False

            print(".", end="", flush=True)
            # Set ID
            self.com.write(G6PacketOut(G6_NODE_BROADCAST, (G6_CMD_ASSIGN_ADDR, bytearray([next_id]))))
            time.sleep(0.1)
            try:
                wait_resp(self.com)
            except TimeoutError:
                print("\nEnumeration done!")
                break
            except G6Error:
                retry = True
            else:
                self.nodes.append(G6Node(self, next_id))
                next_id += 1

            if retry:
                print("\nRestarting bus enumeration")
                if retries == 0:
                    break
                self.reset(2)
                self.com.flush()
                next_id = 1
                retries -= 1

        print(f"\nFound {next_id - 1} device{'s' if next_id != 2 else ''}")
        for i in self.nodes:
            for _ in range(5):
                try:
                    i.request_info()
                    i.measure_latency()
                except TimeoutError:
                    print("TO")
                    continue
                except G6Error:
                    print("G6E")
                    continue
                else:
                    break
            else:
                print("Crap")
                quit()

            print(i)
