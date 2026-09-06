from enum import StrEnum, unique


@unique
class Capability(StrEnum):
    """A quantity a tracker format bounds, named once so every format states the same vocabulary.

    A name means one quantity in one unit wherever it is stated, so a caller comparing two formats
    compares two numbers of the same kind. The pair that measures a waveform is where the unit matters
    most: ``SAMPLE_FRAMES`` counts frames per channel as the model holds them, and ``SAMPLE_BYTES``
    counts the block those frames occupy once stored, which a sample's depth and channel count settle.
    """

    CHANNELS = "channels"
    PATTERNS = "patterns"
    ORDERS = "orders"
    PATTERN_ROWS = "pattern_rows"
    PATTERN_BYTES = "pattern_bytes"
    INSTRUMENTS = "instruments"
    SAMPLES = "samples"
    SAMPLES_PER_INSTRUMENT = "samples_per_instrument"
    SAMPLE_FRAMES = "sample_frames"
    SAMPLE_BYTES = "sample_bytes"
    SAMPLE_RATE = "sample_rate"
    SAMPLE_VOLUME = "sample_volume"
    SAMPLE_GAIN = "sample_gain"
    INSTRUMENT_VOLUME = "instrument_volume"
    ENVELOPE_POINTS = "envelope_points"
    ENVELOPE_VALUE = "envelope_value"
    ENVELOPE_TICK = "envelope_tick"
    FADEOUT = "fadeout"
    NOTE = "note"
    TEMPO = "tempo"
    SPEED = "speed"
    VOLUME_COMMAND = "volume_command"
    VOLUME_PANNING = "volume_panning"
    SONG_VOLUME = "song_volume"
    MIX_VOLUME = "mix_volume"
    MESSAGE_BYTES = "message_bytes"
