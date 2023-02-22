from .msg import Msg
import socket
import struct
import flask

from ..const import (
    JVS_FEATURE_NOTE_CHANNEL, JVS_FEATURE_EOF,
    JVS_FEATURE_LIGHT_CHANNEL, JVS_FEATURE_CONTROL_CHANNEL, JVS_FEATURE_OFFSET
)


app = flask.Flask(__name__)


def get_sock():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 6969))
    return s


def get_resp(s):
    while s.recv(1) != b"\x6A":
        continue
    cmd = s.recv(1)[0]
    nbytes = struct.unpack("<H", s.recv(2))[0]
    return cmd, s.recv(nbytes)


def sock_end(s):
    s.send(bytearray([0x69, Msg._ERROR.value]))
    s.close()


@app.route("/enumerate")
def enumerate_nodes():
    s = get_sock()
    s.send(bytearray([0x69, Msg.ENUMERATE.value]))
    cmd, r = get_resp(s)
    sock_end(s)

    if cmd != Msg.ENUMERATE.value:
        return flask.jsonify({
            "cmd": cmd,
        })
    return flask.jsonify({
        "cmd": cmd,
        "nodes": r[0],
    })


@app.route("/nodes")
def get_nodes():
    s = get_sock()
    s.send(bytearray([0x69, Msg.GET_NODES.value]))
    cmd, r = get_resp(s)
    sock_end(s)

    if cmd != Msg.GET_NODES.value:
        return flask.jsonify({
            "cmd": cmd,
        })
    return flask.jsonify({
        "cmd": cmd,
        "nodes": r[0],
    })


def sock_get_node(node_id, s=None):
    newsock = s is None
    if s is None:
        s = get_sock()
    s.send(bytearray([0x69, Msg.GET_NODE.value, node_id]))
    cmd, r = get_resp(s)
    if newsock:
        sock_end(s)

    if cmd != Msg.GET_NODE.value:
        return cmd, None
    return cmd, {
        "node": r[0],
        "ver": {
            "cmd": r[1],
            "jvs": r[2],
            "comm": r[3]
        },
        "latency": struct.unpack("<I", r[4:8])[0] / 1e3,
        "ident": r[8:].decode("latin-1"),
    }


def sock_get_features(node_id, s=None):
    newsock = s is None
    if s is None:
        s = get_sock()
    s.send(bytearray([0x69, Msg.GET_FEATURES.value, node_id]))
    cmd, r = get_resp(s)
    if newsock:
        sock_end(s)

    if cmd != Msg.GET_FEATURES.value:
        return cmd, None

    json_features = []
    features = bytearray(r[1:])
    while features:
        op = features.pop(0)
        if op == JVS_FEATURE_EOF:
            break
        elif op == JVS_FEATURE_NOTE_CHANNEL:
            json_features.append({
                "type": "note",
                "channel": features.pop(0),
                "min": features.pop(0),
                "max": features.pop(0),
            })
        elif op == JVS_FEATURE_LIGHT_CHANNEL:
            json_features.append({
                "type": "light",
                "channel": features.pop(0),
                "min": features.pop(0),
                "max": features.pop(0),
            })
        elif op == JVS_FEATURE_CONTROL_CHANNEL:
            json_features.append({
                "type": "control",
                "channel": features.pop(0),
                "min": features.pop(0),
                "max": features.pop(0),
            })
        elif op == JVS_FEATURE_OFFSET:
            offset = struct.unpack(">h", features[:2])[0]
            features.pop(0)
            features.pop(0)
            features.pop(0)
            json_features.append({
                "type": "offset",
                "offset": offset,
            })
        else:
            json_features.append({
                "type": "?",
                "0": features.pop(0),
                "1": features.pop(0),
                "2": features.pop(0),
            })

    return cmd, {
        "node": r[0],
        "features":json_features
    }


@app.route("/node/all")
def get_all_nodes():
    s = get_sock()
    s.send(bytearray([0x69, Msg.GET_NODES.value]))
    cmd, r = get_resp(s)
    if cmd != Msg.GET_NODES.value:
        sock_end(s)
        return flask.jsonify({
            "cmd": cmd,
        })

    nodes = []
    for node_id in range(r[0]):
        cmd, node = sock_get_node(node_id, s)
        if cmd != Msg.GET_NODE.value:
            sock_end(s)
            return flask.jsonify({
                "cmd": cmd,
            })
        nodes.append(node)

    sock_end(s)
    return flask.jsonify({
        "cmd": cmd,
        "nodes": nodes,
    })


@app.route("/node/<int:node_id>")
def get_node(node_id):
    cmd, node = sock_get_node(node_id)

    if cmd != Msg.GET_NODE.value or node is None:
        return flask.jsonify({
            "cmd": cmd,
        })
    return flask.jsonify({
        "cmd": cmd,
        **node,
    })


@app.route("/features/<int:node_id>")
def get_features(node_id):
    cmd, features = sock_get_features(node_id)

    if cmd != Msg.GET_FEATURES.value or features is None:
        return flask.jsonify({
            "cmd": cmd,
        })
    return flask.jsonify({
        "cmd": cmd,
        **features,
    })


@app.route("/load-midi", methods=["POST"])
def load_midi():
    if "file" not in flask.request.files:
        return flask.redirect("/")

    file_ = flask.request.files["file"]
    if file_.filename == '':
        return flask.redirect("/")

    midi_data = file_.read()

    s = get_sock()
    s.send((
        bytearray([0x69, Msg.LOAD_MIDI.value])
        + struct.pack("<I", len(midi_data))
        + midi_data)
    )
    cmd, r = get_resp(s)
    sock_end(s)

    ntracks = r[0]
    n = 1
    tracks = []
    for track in range(ntracks):
        nchannels = r[n]
        n += 1
        channels = []
        for channel in range(nchannels):
            channel_num = r[n]
            name = r[n + 1:].split(b"\0")[0].decode()
            n += len(name) + 2
            channels.append((channel_num, name))
        tracks.append(channels)

    return flask.redirect("/")


@app.route("/get-tracks", methods=["GET"])
def get_tracks():
    s = get_sock()
    s.send((
        bytearray([0x69, Msg.GET_TRACKS.value, 0x00, 0x00])
    ))
    cmd, r = get_resp(s)
    sock_end(s)

    ntracks = r[0]
    n = 1
    tracks = []
    for track in range(ntracks):
        nchannels = r[n]
        n += 1
        channels = []
        for channel in range(nchannels):
            channel_num = r[n]
            name = r[n + 1:].split(b"\0")[0].decode()
            n += len(name) + 2
            channels.append((channel_num, name))
        tracks.append(channels)

    return flask.jsonify({
        "cmd": cmd,
        "tracks": tracks,
    })


@app.route("/play")
def start_playing():
    s = get_sock()
    s.send(bytearray([0x69, Msg.START_PLAYING.value]))
    cmd, _ = get_resp(s)
    sock_end(s)

    return flask.jsonify({
        "cmd": cmd,
        "ok": cmd == Msg.START_PLAYING.value
    })


@app.route("/stop")
def stop_playing():
    s = get_sock()
    s.send(bytearray([0x69, Msg.STOP_PLAYING.value]))
    cmd, _ = get_resp(s)
    sock_end(s)

    return flask.jsonify({
        "cmd": cmd,
        "ok": cmd == Msg.STOP_PLAYING.value
    })


@app.route("/")
def index():
    return flask.render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
