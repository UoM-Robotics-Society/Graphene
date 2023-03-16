class G6Error(Exception):
    pass


class G6StatusNack(G6Error):
    pass


class G6ReportNack(G6Error):
    pass
