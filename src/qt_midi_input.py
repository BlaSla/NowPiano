# -*- coding: utf-8 -*-
"""Independent MIDI input for NowPiano."""
import threading

import mido
from PyQt6.QtCore import QObject, pyqtSignal


class MidiInput(QObject):
    """MIDI input bridge. RtMidi callbacks only emit Qt signals."""

    status_changed = pyqtSignal(str)
    note_on = pyqtSignal(int, int, int)   # note, velocity, channel (zero-based)
    note_off = pyqtSignal(int, int)       # note, channel (zero-based)
    diagnostic = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._port = None
        self._port_name = ""
        self._lock = threading.Lock()
        self._held = set()

    @staticmethod
    def available_ports():
        try:
            return list(mido.get_input_names())
        except Exception:
            return []

    @property
    def connected(self):
        return self._port is not None

    @property
    def port_name(self):
        return self._port_name

    def connect_port(self, name):
        self.disconnect_port()
        if not name:
            self.status_changed.emit("MIDI: ?????????? ?? ???????")
            return False
        try:
            port = mido.open_input(name, callback=self._callback)
            self._port = port
            self._port_name = name
            self.status_changed.emit(f"MIDI ?????????: {name}")
            return True
        except Exception as exc:
            self._port = None
            self._port_name = ""
            self.status_changed.emit(f"?????? MIDI: {exc}")
            return False

    def _callback(self, message):
        # Callback ??????????? ? ?????? RtMidi: ??????? ????????? ? QWidget.
        try:
            if message.type == "note_on":
                note = int(message.note)
                velocity = int(message.velocity)
                channel = int(getattr(message, "channel", 0))
                key = (channel, note)

                if velocity > 0:
                    with self._lock:
                        if key in self._held:
                            return
                        self._held.add(key)
                    self.note_on.emit(note, velocity, channel)
                    self.diagnostic.emit(
                        f"????? {channel + 1}: ???? {note}, velocity {velocity}"
                    )
                else:
                    self._release(note, channel)

            elif message.type == "note_off":
                self._release(
                    int(message.note),
                    int(getattr(message, "channel", 0))
                )
            # MIDI clock, start/stop ? ?????? ????????? ????????????.
        except Exception as exc:
            self.diagnostic.emit(f"MIDI callback: {exc}")

    def is_note_held(self, note):
        """????????? ????????? ???? ? ??????? ?? MIDI callback-??????."""
        note = int(note)
        with self._lock:
            return any(n == note for _, n in self._held)

    def _release(self, note, channel):
        key = (channel, note)
        with self._lock:
            if key not in self._held:
                return
            self._held.remove(key)
        self.note_off.emit(note, channel)

    def disconnect_port(self):
        with self._lock:
            held = list(self._held)
            self._held.clear()

        for channel, note in held:
            self.note_off.emit(note, channel)

        port = self._port
        self._port = None
        old_name = self._port_name
        self._port_name = ""

        if port is not None:
            try:
                port.close()
            except Exception:
                pass

        if old_name:
            self.status_changed.emit("MIDI ????????")

    def close(self):
        self.disconnect_port()
