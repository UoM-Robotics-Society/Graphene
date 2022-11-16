import threading
import serial
import serial.tools.list_ports
import time

from .error import JVSError
from .const import COM_PORT_VID_PID, JVS_NODE_BROADCAST, JVS_CMD_RESET, JVS_RESET_DELAY, JVS_CMD_RESET_CHECK, JVS_CMD_ASSIGN_ADDR, JVS_POST_RESET_DELAY
from .packet import JVSPacketOut
from .util import wait_resp
from .node import JVSNode


MIN_SEND_DELAY = 0
# MIN_SEND_DELAY = 0.01


class JVSMaster:
    def __init__(self, port=None, baud=115200):
        if port is None:
            port = self.locate_port()
        print(f"Using {port}")
        self.nodes: list[JVSNode] = []
        self.com = serial.Serial(port, baud)
        self.lock = threading.Lock()
        self._last_send = 0

    def write(self, node, data: bytes, response=False):
        with self.lock:
            # print("Got lock")
            now = time.time()
            delta = now - self._last_send
            if delta < MIN_SEND_DELAY:
                time.sleep(delta)
            self._last_send = now

            self.com.write(data)
            if response:
                ret = wait_resp(node)
                # print("unlock")
                return ret
            # print("unlock")

    def locate_port(self):
        devices = serial.tools.list_ports.comports()

        for i in devices:
            if (i.vid, i.pid) in COM_PORT_VID_PID:
                return i.name
        raise JVSError("No serial ports found")

    def reset(self, count=2):
        self.nodes.clear()
        for _ in range(count):
            self.com.write(JVSPacketOut(JVS_NODE_BROADCAST, JVS_CMD_RESET, bytearray([JVS_CMD_RESET_CHECK])))
            time.sleep(JVS_RESET_DELAY)
        time.sleep(JVS_POST_RESET_DELAY)

    def enumerate_bus(self, retries=5):
        self.reset(5)

        print("Enumerating bus...")
        next_id = 1
        while True:
            retry = False

            print(".", end="", flush=True)
            # Set ID
            self.com.write(JVSPacketOut(JVS_NODE_BROADCAST, JVS_CMD_ASSIGN_ADDR, bytearray([next_id])))
            time.sleep(0.1)
            try:
                wait_resp(self.com)
            except TimeoutError:
                print("\nEnumeration done!")
                break
            except JVSError:
                retry = True
            else:
                self.nodes.append(JVSNode(self, next_id))
                next_id += 1

            if retry:
                print("\nRestarting bus enumeration")
                if retries == 0:
                    break
                self.reset(2)
                self.com.read_all()
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
                except JVSError:
                    print("JVSE")
                    continue
                else:
                    break
            else:
                print("Crap")
                quit()

            print(i)
