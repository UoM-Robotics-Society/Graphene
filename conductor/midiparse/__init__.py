#!/usr/bin/env python3

from __future__ import annotations

import enum
import pprint


class MidiFormat(enum.Enum):
    MultiChannel    = 0
    Simultaneous    = 1
    Independent     = 2


# hr mn se fr ff
# hr = hour
# mn = minute
# se = second
# fr = frame
# ff = frame fraction
class MidiSMPTETag:
    def __init__(self, hr: int, mn: int, se: int, fr: int, ff: int):
        self.hr = hr
        self.mn = mn
        self.se = se
        self.fr = fr
        self.ff = frr

    def __repr__(self):
        return f'[{self.hr}:{self.mn}:{self.se}:{self.fr}.{self.ff}]'

    def __eq__(self, other):
        return self.hr == other.hr and self.mn == other.mn and self.se == other.se \
                and self.fr == other.fr and self.ff == other.ff


# ticks-per-quarter-note | (frames-per-second, ticks-per-frame)
MidiDivision = int | tuple[int, int]


class MidiHeader:
    def __init__(self, fmt: MidiFormat, tracks: int, division: MidiDivision):
        self.fmt = fmt
        self.tracks = tracks
        self.division = division

    def __repr__(self):
        return f'MHdr(fmt: {self.fmt}, tracks: {self.tracks}, division: {self.division})'

    def __eq__(self, other):
        return self.fmt == other.fmt and self.tracks == other.tracks and self.division == other.division


class MidiEventType(enum.Enum):
    NoteOff             = 0x8 # 0kkkkkkk 0vvvvvvv : key=[0-127], vel=[0-127]
    NoteOn              = 0x9 # 0kkkkkkk 0vvvvvvv : key=[0-127], vel=[0-127]
    KeyPressure         = 0xa # 0kkkkkkk 0ppppppp : key=[0-127], pressure=[0-127]
    ControllerChange    = 0xb # 0ccccccc 0vvvvvvv : controller=[0-127], controller-value=[0-127]
    ProgramChange       = 0xc # 0ppppppp : program=[0-127]
    ChannelPressure     = 0xd # 0ppppppp : pressure=[0-127]
    PitchBlend          = 0xe # 0ccccccc 0fffffff : coarse=[0-127], fine=[0-127] (coarse+fine = 14-bit res.)


MidiEventTag = int | tuple[int, int]


class MidiEvent:
    """
    The data encoded by each event type and associated tag can be found here:
    http://personal.kent.edu/~sbirch/Music_Production/MP-II/MIDI/midi_channel_voice_messages.htm
    """

    def __init__(self, ev_type: MidiEventType, channel: int, tag: MidiEventTag):
        self.ev_type = ev_type
        self.channel = channel
        self.tag     = tag

    def __repr__(self):
        return f'Midi({self.ev_type},{self.channel:0x},{self.tag})'

    def __eq__(self, other):
        return self.ev_type == other.ev_type and self.channel == other.channel and self.tag == other.tag


class SysExEvent:
    def __init__(self, ev_len: int, ev_bytes: bytes):
        self.ev_len = ev_len
        self.ev_bytes = ev_bytes

    def __repr__(self):
        return f'SysEx({self.ev_len},{self.ev_bytes})'

    def __eq__(self, other):
        return self.ev_len == other.ev_len and self.ev_bytes == other.ev_bytes


class MetaEventType(enum.Enum):
    SequenceNumber  = 0x00 # 02 ss ss
    TextEvent       = 0x01 # len text...
    Copyright       = 0x02 # len text...
    TrackName       = 0x03 # len text...
    InstrumentName  = 0x04 # len text...
    Lyric           = 0x05 # len text...
    Marker          = 0x06 # len text...
    CuePoint        = 0x07 # len text...
    ChannelPrefix   = 0x20 # 01 cc
    EndOfTrack      = 0x2f # 00
    Tempo           = 0x51 # 03 tt tt tt
    SMPTEOffset     = 0x54 # 05 hr mn se fr ff
    TimeSignature   = 0x58 # 04 nn dd cc bb
    KeySignature    = 0x59 # 02 sf mi
    CustomEvent     = 0x7f # len data...


# nn dd cc bb
# numerator = nn
# denominator = 2^-dd
# midi clocks per metronome tick = cc
# midi 32nd notes per quarter note = bb
MidiTimeSignature = tuple[int, int, int, int]


# sf mi
# sf: -7 = 7 flats, -1 = 1 flat, 0 = key of C, +1 = 1 sharp, +7 = 7 sharps
# mi: 0 = major key, 1 = minor key
MidiKeySignature = tuple[int, int]


MetaEventTag = int | str |  MidiSMPTETag | MidiTimeSignature | MidiKeySignature | bytes | None


class MetaEvent:
    def __init__(self, ev_type: MetaEventType, tag: MetaEventTag):
        self.ev_type = ev_type
        self.tag     = tag

    def __repr__(self):
        return f'Meta({self.ev_type},{self.tag})'

    def __eq__(self, other):
        return self.ev_type == other.ev_type and self.tag == other.tag


class MidiTrackEventType(enum.Enum):
    Midi    = 0
    SysEx   = 1
    Meta    = 2


class MidiTrackEvent:
    def __init__(self, track_ev_type: MidiTrackEventType, track_ev: MidiEvent | SysExEvent | MetaEvent, track: MidiTrack):
        self.track_ev_type = track_ev_type
        self.track_ev = track_ev
        self.track = track

    def __repr__(self):
        return str(self.track_ev)

    def __eq__(self, other):
        return self.track_ev_type == other.track_ev_type and self.track_ev == other.track_ev and self.track == other.track


class MidiTrack:
    ENCODING = 'latin-1'
    LOG = False

    def __init__(self, header: MidiHeader, source: bytes):
        self.header = header
        self.source = source
        self.cur = 0
        self.running_status = None

    def __repr__(self):
        return f'MTrk(len: {len(self.source):0x}, cur: {self.cur})'

    def __iter__(self):
        self.total_ticks = 0
        self.cur = 0
        self.running_status = None
        return self

    def __next__(self):
        dt, ev, read = self._parse_event(self.cur)
        self.cur += read

        if ev.track_ev_type == MidiTrackEventType.Meta and ev.track_ev.ev_type == MetaEventType.EndOfTrack:
            raise StopIteration

        return dt, ev

    def _log(self, msg):
        if self.LOG:
            print(msg)

    def _read_bytes(self, cur: int, count: int) -> tuple[int, int]:
        return int.from_bytes(self.source[cur:cur+count], 'big'), count

    def _read_slice(self, cur: int, count: int) -> tuple[bytes, int]:
        return self.source[cur:cur+count], count

    def _read_variable_length(self, cur: int) -> tuple[int, int]:
        value, i = self.source[cur] & 0x7f, 1

        current = self.source[cur]
        while current & 0x80:
            current = self.source[cur + i]
            value = (value << 7) + (current & 0x7f)
            i += 1

        assert i <= 4, f'Bad MIDI variable length value, expected <=4 bytes, got {i} bytes'

        return value, i

    def _parse_event(self, cur: int) -> tuple[int, MidiTrackEvent, int]:
        offset = 0

        self._log(f'===== cur: {cur:0x}/{len(self.source):0x} =====')

        delta_time, read = self._read_variable_length(cur)
        offset += read

        self._log(f'Read {read} bytes for deltatime: {delta_time:0x}')

        self.total_ticks += delta_time
        self._log(f'Total deltatime: {self.total_ticks:0x}')

        ev_type, read = self._read_bytes(cur + offset, 1)
        offset += read

        self._log(f'Read {read} bytes for event type: {ev_type:0x}')

        match ev_type:
            case 0xf0 | 0xf7: # sysex, 0xf7 terminated, 0xf7 unterminated
                track_ev_type = MidiTrackEventType.SysEx
                track_ev, read = self._parse_sysex_event(cur + offset, ev_type == 0xf0)
                self._log(f'Read {read} bytes of sysex event')

            case 0xff: # meta-event
                track_ev_type = MidiTrackEventType.Meta
                track_ev, read = self._parse_meta_event(cur + offset)
                self._log(f'Read {read} bytes of meta event')

            case _: # midi event
                track_ev_type = MidiTrackEventType.Midi
                track_ev, read = self._parse_midi_event(cur + offset, ev_type)
                self._log(f'Read {read} bytes of midi event')

        offset += read

        self._log(f'Read {offset} total bytes in event')

        return self.total_ticks, MidiTrackEvent(track_ev_type, track_ev, self), offset

    def _parse_sysex_event(self, cur: int, terminated: bool) -> tuple[SysExEvent, int]:
        self.running_status = None

        offset = 0

        ev_len, read = self._read_variable_length(cur)
        offset += read

        self._log(f'Read {read} bytes for sysex event len: {ev_len:0x}')

        data, read = self._read_slice(cur + offset, ev_len)
        offset += read

        self._log(f'Read {read} bytes for sysex event data: {data}')

        return SysExEvent(read, data), offset

    def _parse_meta_event(self, cur: int) -> tuple[MetaEvent, int]:
        self.running_status = None

        offset = 0

        ev_type, read = self._read_bytes(cur, 1)
        offset += read

        self._log(f'Read {read} bytes for meta event type: {ev_type:0x}')

        ev_len, read = self._read_variable_length(cur + offset)
        offset += read

        self._log(f'Read {read} bytes for meta event len: {ev_len:0x}')

        data, read = self._read_slice(cur + offset, ev_len)
        offset += read

        if ev_len:
            self._log(f'Read {read} bytes for meta event data: {data}')

        match ev_type:
            case MetaEventType.SequenceNumber.value:
                sequence = int.from_bytes(data, 'big')
                result = MetaEvent(MetaEventType.SequenceNumber, sequence)

            case MetaEventType.TextEvent.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.TextEvent, text)

            case MetaEventType.Copyright.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.Copyright, text)

            case MetaEventType.TrackName.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.TrackName, text)

            case MetaEventType.InstrumentName.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.InstrumentName, text)

            case MetaEventType.Lyric.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.Lyric, text)

            case MetaEventType.Marker.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.Marker, text)

            case MetaEventType.CuePoint.value:
                text = data.decode(encoding=self.ENCODING)
                result = MetaEvent(MetaEventType.CuePoint, text)

            case MetaEventType.ChannelPrefix.value:
                prefix = int.from_bytes(data, 'big')
                result = MetaEvent(MetaEventType.ChannelPrefix, prefix)

            case MetaEventType.EndOfTrack.value:
                result = MetaEvent(MetaEventType.EndOfTrack, None)
                self._log('===== End Of Track =====')

            case MetaEventType.Tempo.value:
                tempo = int.from_bytes(data, 'big')
                result = MetaEvent(MetaEventType.Tempo, tempo)

            case MetaEventType.SMPTEOffset.value:
                hr = data[0]
                mn = data[1]
                se = data[2]
                fr = data[3]
                ff = data[4]
                smpte_offset = MidiSMPTETag(hr, mn, se, fr, ff)
                result = MetaEvent(MetaEventType.SMPTEOffset, smpte_offset)

            case MetaEventType.TimeSignature.value:
                nn = data[0]
                dd = data[1]
                cc = data[2]
                bb = data[3]
                time_signature = nn, dd, cc, bb
                result = MetaEvent(MetaEventType.TimeSignature, time_signature)

            case MetaEventType.KeySignature.value:
                sf = data[0]
                mi = data[1]
                key_signature = sf, mi
                result = MetaEvent(MetaEventType.KeySignature, key_signature)

            case MetaEventType.CustomEvent.value:
                result = MetaEvent(MetaEventType.CustomEvent, data)

            case _:
                self._log(f'WARN: Unknown MIDI meta event type: {ev_type:0x}, {ev_len} bytes read')
                result = MetaEvent(MetaEventType.CustomEvent, data)

        return result, offset

    def _parse_midi_event(self, cur: int, status: int, stop_recursion: bool = False) -> tuple[MidiEvent, int]:
        offset = 0

        ev_type = status >> 4
        channel = status & 0x0f

        self._log(f'MIDI Voice: ev_type: {ev_type:0x}, channel: {channel}')

        match ev_type:
            case MidiEventType.NoteOff.value:
                key, read = self._read_bytes(cur + offset, 1)
                offset += read

                vel, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.NoteOff, channel, (key, vel))

            case MidiEventType.NoteOn.value:
                key, read = self._read_bytes(cur + offset, 1)
                offset += read

                vel, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.NoteOn, channel, (key, vel))

            case MidiEventType.KeyPressure.value:
                key, read = self._read_bytes(cur + offset, 1)
                offset += read

                pressure, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.KeyPressure, channel, (key, pressure))

            case MidiEventType.ControllerChange.value:
                controller, read = self._read_bytes(cur + offset, 1)
                offset += read

                value, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.ControllerChange, channel, (controller, value))

            case MidiEventType.ProgramChange.value:
                program, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.ProgramChange, channel, program)

            case MidiEventType.ChannelPressure.value:
                pressure, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.ChannelPressure, channel, pressure)

            case MidiEventType.PitchBlend.value:
                coarse, read = self._read_bytes(cur + offset, 1)
                offset += read

                fine, read = self._read_bytes(cur + offset, 1)
                offset += read

                result = MidiEvent(MidiEventType.PitchBlend, channel, (coarse, fine))

            case _: # running status
                assert self.running_status is not None, 'Cannot read running status before status is set'
                assert not stop_recursion, 'Running status read cannot be nested'

                # when we read a running status, the ev_type is our first data
                # byte, and so we need to roll back the cursor to allow us to
                # fetch the byte again
                result, read = self._parse_midi_event(cur - 1, self.running_status, True)

                # we need to compensate for reading the first data byte twice
                offset += read - 1

                return result, offset

        self.running_status = status

        return result, offset


def _midi_read_header(source: bytes) -> tuple[MidiHeader, int]:
    magic = source[:4] # 4-bytes ascii 'MThd'
    assert magic == b'MThd', f'Bad MIDI header chunk magic. Expected \'MThd\', got \'{magic}\''

    length = int.from_bytes(source[4:8], 'big') # 32-bit int
    assert length <= 6, f'Bad MIDI header chunk length. Expected >=6, got {length}'

    fmt = int.from_bytes(source[8:10], 'big')
    tracks = int.from_bytes(source[10:12], 'big')
    raw_division = int.from_bytes(source[12:14], 'big')

    if raw_division & 0x8000:
        division = int.from_bytes(source[12:13]), int.from_bytes(source[13:14])
    else:
        division = raw_division

    return MidiHeader(fmt, tracks, division), 8 + length # hdr, read_bytes


def _midi_read_track(hdr: MidiHeader, source: bytes) -> tuple[MidiTrack, int]:
    magic = source[:4]
    assert magic == b'MTrk', f'Bad MIDI track chunk magic. Expected \'MTrk\', got {magic}'

    length = int.from_bytes(source[4:8], 'big')

    return MidiTrack(hdr, source[8:8+length]), 8 + length


def midi_parse(source: bytes) -> tuple[MidiHeader, list[MidiTrack]]:
    hdr, read = _midi_read_header(source)
    offset = read

    trks = []
    for i in range(hdr.tracks):
        trk, read = _midi_read_track(hdr, source[offset:])
        offset += read
        trks.append(trk)

    assert offset == len(source), 'Bad MIDI file. Remaining unprocessed data'

    return hdr, trks


class MidiMixer:
    def __init__(self, hdr: MidiHeader, trks: list[MidiTrack]):
        self.hdr = hdr
        self.trks = trks

    @classmethod
    def rebase(cls, hdr: MidiHeader, track: list[tuple[int, MidiTrackEvent]]):
        tempo = 500000 # uspqn, default = 120 bpm

        def ms(hdr: MidiHeader, tempo: int, dt: int) -> int:
            match hdr.division:
                case int(tpqn):
                    # tempo = uspqn
                    return int((float(dt) / (float(tpqn) / float(tempo))) / 1000.0)

                case tuple(fps, tpf):
                    return int((float(dt) / (float(fps) * float(tpf))) * 1000.0)

        for dt, ev in track:
            match ev.track_ev_type:
                case MidiTrackEventType.Meta:
                    if ev.track_ev.ev_type == MetaEventType.Tempo:
                        tempo = ev.track_ev.tag

            yield ms(hdr, tempo, dt), ev

    @classmethod
    def for_track(cls, hdr: MidiHeader, trks: list[MidiTrack], *args, **kwargs):
        match hdr.fmt:
            case 0:
                return MultiChannelMidiMixer(hdr, trks, *args, **kwargs)

            case 1:
                return IndependentMidiMixer(hdr, trks, *args, **kwargs)

            case 2:
                return SimultaneousMidiMixer(hdr, trks, *args, **kwargs)

            case _:
                assert 0, f'Unknown MIDI track format: {hdr.fmt}'


class MultiChannelMidiMixer(MidiMixer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.hdr.fmt == 0, f'MultiChannelMidiMixer only supports format 0 MIDI files'

    def __iter__(self):
        return MidiMixer.rebase(self.hdr, self.trks[0])


class IndependentMidiMixer(MidiMixer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.hdr.fmt == 1, f'IndependentMidiMixer only supports format 1 MIDI files'

    def __iter__(self):
        merged_track = []
        for trk in self.trks:
            merged_track.extend(list(trk))

        return MidiMixer.rebase(self.hdr, sorted(merged_track, key=lambda tup: tup[0]))


class SimultaneousMidiMixer(MidiMixer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.hdr.fmt == 2, f'SimultaneousMidiMixer only supports format 2 MIDI files'

    def __iter__(self):
        merged_tracks = []

        absolute_offset = 0
        for trk in self.trks:
            merged_tracks.extend([(dt + absolute_offset, ev) for dt, ev in trk])
            absolute_offset = merged_tracks[-1][0]

        return MidiMixer.rebase(self.hdr, merged_tracks)


if __name__ == '__main__':
    source = bytes([
        0x4d, 0x54, 0x68, 0x64, # header magic b'MThd'
        0x00, 0x00, 0x00, 0x06, # header length
        0x00, 0x00, # format 0
        0x00, 0x01, # 1 track
        0x00, 0x60, # 96 ticks per quarter note

        0x4d, 0x54, 0x72, 0x6b, # track magic b'MTrk'
        0x00, 0x00, 0x00, 0x3b, # track length
        0x00, 0xff, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08, # time signature
        0x00, 0xff, 0x51, 0x03, 0x07, 0xa1, 0x20, # tempo
        0x00, 0xc0, 0x05, # program-change, chan=0, program=0x05
        0x00, 0xc1, 0x2e, # program-change, chan=1, program=0x2e
        0x00, 0xc2, 0x46, # program-change, chan=2, program=0x46
        0x00, 0x92, 0x30, 0x60, # note-on, chan=2, key=0x30, vel=0x60
        0x00, 0x3c, 0x60, # running-status note-on, chan=2, key=0x3c, vel=0x60
        0x60, 0x91, 0x4c, 0x20, # note-on, chan=1, key=0x4c, vel=0x20
        0x60, 0x90, 0x4c, 0x20, # note-on, chan=0, key=0x4c, vel=0x20
        0x81, 0x40, 0x82, 0x30, 0x40, # note-off, chan=2, key=0x30, vel=0x40
        0x00, 0x3c, 0x40, # running-status note-off, chan=2, key=0x3c, vel=0x40
        0x00, 0x81, 0x43, 0x40, # note-off, chan=1, key=0x4c, vel=0x40
        0x00, 0x80, 0x4c, 0x40, # note-off, chan=0, key=0x4c, vel=0x40
        0x00, 0xff, 0x2f, 0x00 # end-of-track
    ])

    hdr, trks = midi_parse(source)

    assert hdr.fmt == 0
    assert hdr.tracks == 1
    assert hdr.division == 0x60
    print(f'MIDI Header: {hdr}')

    for trk in trks:
        print(f'MIDI Track:')
        pprint.pprint(list(trk))

    mixer = MidiMixer.for_track(hdr, trks)
    print(f'Mixed MIDI Track:')
    pprint.pprint(list(mixer))

    source = bytes([
        0x4d, 0x54, 0x68, 0x64, # header magic b'MThd'
        0x00, 0x00, 0x00, 0x06, # header length
        0x00, 0x01, # format 1
        0x00, 0x04, # 4 tracks
        0x00, 0x60, # 96 ticks per quarter note

        0x4d, 0x54, 0x72, 0x6b, # track magic b'MTrk'
        0x00, 0x00, 0x00, 0x14, # track length
        0x00, 0xff, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08, # time signature
        0x00, 0xff, 0x51, 0x03, 0x07, 0xa1, 0x20, # tempo
        0x83, 0x00, 0xff, 0x2f, 0x00,  # end-of-track

        0x4d, 0x54, 0x72, 0x6b, # track magic b'MTrk'
        0x00, 0x00, 0x00, 0x10, # track length
        0x00, 0xc0, 0x05, # program-change, chan=0, program=0x05
        0x81, 0x40, 0x90, 0x4c, 0x20, # note-on, chan=0, key=0x4c, vel=0x20
        0x81, 0x40, 0x4c, 0x00, # running-status note-on, key=0x4c, vel=0x00
        0x00, 0xff, 0x2f, 0x00, # end-of-track

        0x4d, 0x54, 0x72, 0x6b, # track magic b'MTrk'
        0x00, 0x00, 0x00, 0x0f, # track length
        0x00, 0xc1, 0x2e, # program-change, chan=1, program=0x2e
        0x60, 0x91, 0x43, 0x40, # note-on, chan=1, key=0x43, vel=0x40
        0x82, 0x20, 0x43, 0x00, # running-status note-on, key=0x43, vel=0x00
        0x00, 0xff, 0x2f, 0x00, # end-of-track

        0x4d, 0x54, 0x72, 0x6b, # track magic b'MTrk'
        0x00, 0x00, 0x00, 0x15, # track length
        0x00, 0xc2, 0x46, # program-change, chan=2, program=0x46
        0x00, 0x92, 0x30, 0x60, # note-on, chan=2, key=0x30, vel=0x60
        0x00, 0x3c, 0x60, # running-status note-on, key=0x3c, vel=0x60
        0x83, 0x00, 0x30, 0x00, # running-status note-on, key=0x30, vel=0x00
        0x00, 0x3c, 0x00, # running-status note-on, key=0x3c, vel=0x00
        0x00, 0xff, 0x2f, 0x00, # end-of-track
    ])

    hdr, trks = midi_parse(source)

    assert hdr.fmt == 1
    assert hdr.tracks == 4
    assert hdr.division == 0x60
    print(f'MIDI Header: {hdr}')

    for trk in trks:
        print(f'MIDI Track:')
        pprint.pprint(list(trk))

    mixer = MidiMixer.for_track(hdr, trks)
    print(f'Mixed MIDI Track:')
    pprint.pprint(list(mixer))

    source = bytes([
        0x4d, 0x54, 0x68, 0x64, # header magic b'MThd'
        0x00, 0x00, 0x00, 0x06, # header length
        0x00, 0x02, # format 2
        0x00, 0x01, # 1 track
        0x00, 0x60, # 96 ticks per quarter note

        0x4d, 0x54, 0x72, 0x6b, # track magic b'MTrk'
        0x00, 0x00, 0x00, 0x3b, # track length
        0x00, 0xff, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08, # time signature
        0x00, 0xff, 0x51, 0x03, 0x07, 0xa1, 0x20, # tempo
        0x00, 0xc0, 0x05, # program-change, chan=0, program=0x05
        0x00, 0xc1, 0x2e, # program-change, chan=1, program=0x2e
        0x00, 0xc2, 0x46, # program-change, chan=2, program=0x46
        0x00, 0x92, 0x30, 0x60, # note-on, chan=2, key=0x30, vel=0x60
        0x00, 0x3c, 0x60, # running-status note-on, chan=2, key=0x3c, vel=0x60
        0x60, 0x91, 0x4c, 0x20, # note-on, chan=1, key=0x4c, vel=0x20
        0x60, 0x90, 0x4c, 0x20, # note-on, chan=0, key=0x4c, vel=0x20
        0x81, 0x40, 0x82, 0x30, 0x40, # note-off, chan=2, key=0x30, vel=0x40
        0x00, 0x3c, 0x40, # running-status note-off, chan=2, key=0x3c, vel=0x40
        0x00, 0x81, 0x43, 0x40, # note-off, chan=1, key=0x4c, vel=0x40
        0x00, 0x80, 0x4c, 0x40, # note-off, chan=0, key=0x4c, vel=0x40
        0x00, 0xff, 0x2f, 0x00 # end-of-track
    ])

    hdr, trks = midi_parse(source)

    assert hdr.fmt == 2
    assert hdr.tracks == 1
    assert hdr.division == 0x60
    print(f'MIDI Header: {hdr}')

    for trk in trks:
        print(f'MIDI Track:')
        pprint.pprint(list(trk))

    mixer = MidiMixer.for_track(hdr, trks)
    print(f'Mixed MIDI Track:')
    pprint.pprint(list(mixer))

