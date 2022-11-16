from .packet import JVSPacketIn
from .const import JVS_TIMEOUT, JVS_RESEND_RETRIES, JVS_REPORT_OK, JVS_STATUS_OK, JVS_STATUS_SUM
from .error import JVSStatusNack, JVSReportNack


def wait_resp(com_or_node, timeout=JVS_TIMEOUT, retries=JVS_RESEND_RETRIES):
    from .node import JVSNode

    if isinstance(com_or_node, JVSNode):
        com = com_or_node.master.com
        node = com_or_node
    else:
        com = com_or_node
        node = None

    if com.timeout != timeout:
        com.timeout = timeout
    pkt = JVSPacketIn.from_serial(com)
    if pkt.status != JVS_STATUS_OK:
        if pkt.status == JVS_STATUS_SUM and node is not None and retries:
            node.resend()
            return wait_resp(com_or_node, timeout, retries - 1)
        raise JVSStatusNack(pkt)
    if pkt.report != JVS_REPORT_OK:
        raise JVSReportNack(pkt)
    return pkt


def get_sense():
    raise NotImplementedError
