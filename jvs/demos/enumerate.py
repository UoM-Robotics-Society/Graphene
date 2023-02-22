import time

from ..master import JVSMaster
from ..node import JVSNode


if __name__ == "__main__":
    jvs = JVSMaster()
    jvs.enumerate_bus()

    while True:
        for i in range(30):
            note = i + 79

            # Play note 0
            jvs.nodes[0].send(
                JVSNode.cmd_light(0, 0, note, 255),
                JVSNode.cmd_note_down(0, 0, note, 255),
            )
            time.sleep(0.25)
        # Send led clear command
        jvs.nodes[0].send(
            JVSNode.cmd_control(0, 0, 1, 0)
        )
