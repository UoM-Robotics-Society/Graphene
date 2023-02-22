from enum import Enum


class Msg(Enum):
    _ERROR = 0
    ENUMERATE = 1
    GET_NODES = 2
    GET_NODE = 3
    LOAD_MIDI = 4
    START_PLAYING = 5
    STOP_PLAYING = 6
    GET_FEATURES = 7
    GET_TRACKS = 8
