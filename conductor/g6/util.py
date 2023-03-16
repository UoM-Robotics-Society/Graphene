from .packet import G6PacketIn
from .const import G6_TIMEOUT, G6_RESEND_RETRIES, G6_STATUS_OK, G6_STATUS_SUM
from .error import G6StatusNack


def wait_resp(com_or_node, timeout=G6_TIMEOUT, retries=G6_RESEND_RETRIES) -> G6PacketIn:
    from .node import G6Node

    if isinstance(com_or_node, G6Node):
        com = com_or_node.master.com
        node = com_or_node
    else:
        com = com_or_node
        node = None

    if com.timeout != timeout:
        com.timeout = timeout
    pkt = G6PacketIn.from_serial(com)
    if pkt.status != G6_STATUS_OK:
        if pkt.status == G6_STATUS_SUM and node is not None and retries:
            node.resend()
            return wait_resp(com_or_node, timeout, retries - 1)
        raise G6StatusNack(pkt)
    return pkt


def get_sense():
    raise NotImplementedError
