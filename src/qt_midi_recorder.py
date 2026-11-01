# -*- coding: utf-8 -*-
"""Independent timestamped MIDI performance recorder."""

import threading
import time


class MidiRecorder:
    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self._state = "stopped"
            self._segment_start = None
            self._elapsed_before_segment = 0.0
            self._active = {}
            self._notes = []

    @property
    def state(self):
        with self._lock:
            return self._state

    def _elapsed(self, now=None):
        if self._state == "recording":
            if now is None:
                now = time.monotonic()
            return self._elapsed_before_segment + max(
                0.0, now - self._segment_start
            )
        return self._elapsed_before_segment

    def start(self):
        with self._lock:
            if self._state == "recording":
                return False
            self._notes = []
            self._active = {}
            self._elapsed_before_segment = 0.0
            self._segment_start = time.monotonic()
            self._state = "recording"
            return True

    def note_on(self, note, velocity, channel=0):
        with self._lock:
            if self._state != "recording":
                return
            key = (int(channel), int(note))
            if key in self._active:
                return
            self._active[key] = (
                self._elapsed(),
                max(1, min(127, int(velocity)))
            )

    def note_off(self, note, channel=0):
        with self._lock:
            if self._state != "recording":
                return
            key = (int(channel), int(note))
            active = self._active.pop(key, None)
            if active is None:
                return
            start, velocity = active
            end = self._elapsed()
            if end > start:
                self._notes.append({
                    "note": key[1],
                    "channel": key[0],
                    "velocity": velocity,
                    "start": start,
                    "duration": end - start,
                })

    def _close_active(self, elapsed):
        for (channel, note), (start, velocity) in list(self._active.items()):
            duration = max(0.0, elapsed - start)
            if duration > 0:
                self._notes.append({
                    "note": note,
                    "channel": channel,
                    "velocity": velocity,
                    "start": start,
                    "duration": duration,
                })
        self._active.clear()

    def pause(self):
        with self._lock:
            if self._state != "recording":
                return False
            elapsed = self._elapsed(time.monotonic())
            self._close_active(elapsed)
            self._elapsed_before_segment = elapsed
            self._segment_start = None
            self._state = "paused"
            return True

    def resume(self):
        with self._lock:
            if self._state != "paused":
                return False
            self._segment_start = time.monotonic()
            self._state = "recording"
            return True

    def stop(self):
        with self._lock:
            if self._state == "recording":
                elapsed = self._elapsed(time.monotonic())
                self._close_active(elapsed)
                self._elapsed_before_segment = elapsed
            self._segment_start = None
            self._state = "stopped"
            return self.snapshot()

    def snapshot(self):
        with self._lock:
            result = [dict(item) for item in self._notes]
            if self._state == "recording":
                elapsed = self._elapsed(time.monotonic())
                for (channel, note), (start, velocity) in self._active.items():
                    duration = max(0.0, elapsed - start)
                    if duration > 0:
                        result.append({
                            "note": note,
                            "channel": channel,
                            "velocity": velocity,
                            "start": start,
                            "duration": duration,
                        })
            return sorted(result, key=lambda x: (x["start"], x["note"]))

    @property
    def duration(self):
        """Elapsed recording time, excluding paused intervals."""
        with self._lock:
            return self._elapsed()

    def export_midi(self, path, bpm=120):
        import mido

        bpm = float(bpm)
        if not 20 <= bpm <= 400:
            raise ValueError("BPM must be between 20 and 400")

        notes = self.snapshot()
        if not notes:
            raise ValueError("Recording contains no notes")

        ticks_per_beat = 480
        tempo = mido.bpm2tempo(bpm)
        events = []

        for item in notes:
            start_tick = round(item["start"] * bpm / 60 * ticks_per_beat)
            end_tick = round(
                (item["start"] + item["duration"]) *
                bpm / 60 * ticks_per_beat
            )
            end_tick = max(start_tick + 1, end_tick)
            channel = max(0, min(15, int(item["channel"])))
            note = max(0, min(127, int(item["note"])))
            velocity = max(1, min(127, int(item["velocity"])))

            events.append((
                start_tick, 1,
                mido.Message(
                    "note_on", channel=channel, note=note,
                    velocity=velocity
                )
            ))
            events.append((
                end_tick, 0,
                mido.Message(
                    "note_off", channel=channel, note=note,
                    velocity=0
                )
            ))

        events.sort(key=lambda x: (x[0], x[1]))

        midi = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

        previous_tick = 0
        for tick, _, message in events:
            message.time = max(0, tick - previous_tick)
            track.append(message)
            previous_tick = tick

        track.append(mido.MetaMessage("end_of_track", time=0))
        midi.save(str(path))
        return len(notes)
