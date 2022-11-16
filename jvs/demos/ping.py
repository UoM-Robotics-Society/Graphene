import time

from ..master import JVSMaster


if __name__ == "__main__":
    jvs = JVSMaster()
    jvs.enumerate_bus()

    if len(jvs.nodes) == 0:
        quit()

    tot = suc = 0
    counter = 0
    C_MAX = 25

    # while True:
    #     for _ in range(C_MAX):
    #         jvs.nodes[0].incr()
    #         time.sleep(0.0001)
    #     time.sleep(0.001)
    #     cntr = jvs.nodes[0].cntr().data[0]
    #     time.sleep(0.0001)
    #     if cntr != C_MAX:
    #         print(f"!! {cntr}")
        # else:
            # print(cntr)
#    quit()

    start = last = time.perf_counter()
    delta = 0
    while True:
        
        for n, node in enumerate(jvs.nodes):
            perc = 0
            if tot:
                perc = (suc / tot) * 100
            print(f"{perc:03.02f}%\t {tot / (time.perf_counter() - start):03.02f}pkt/s\t {delta*1000:.01f}\t Ping: {n}: ", end="", flush=True)
            try:
                node.ping()
            except TimeoutError:
                print("TO")
                # raise
            except Exception:
                print("KO")
                raise
            else:
                print("OK")
                suc += 1
            tot += 1

            now = time.perf_counter()
            delta = now - last
            last = now

    while True:
        for n, node in enumerate(jvs.nodes):
            perc = 0
            if tot:
                perc = (suc / tot) * 100
            print(f"{perc:03.02f}%\t Ping: {n}: ", end="", flush=True)
            try:
                if counter == C_MAX:
                    tot += counter
                    counter = 0
                    pkt = node.cntr()
                    suc += pkt.data[0]
                    if pkt.data[0] != C_MAX:
                        print(pkt.data)
                        # quit()
                        raise Exception
                else:
                    node.incr()
                    if n == len(jvs.nodes) - 1:
                        counter += 1
                node.ping()
            except TimeoutError:
                print("TO")
            except Exception:
                print("KO")
                raise
            else:
                print("OK")
            #     suc += 1
            # tot += 1
            time.sleep(0.001)
