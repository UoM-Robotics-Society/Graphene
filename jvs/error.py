class JVSError(Exception):
    pass


class JVSStatusNack(JVSError):
    pass


class JVSReportNack(JVSError):
    pass
