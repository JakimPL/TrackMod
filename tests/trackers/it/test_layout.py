from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.trackers.it.layout.envelope import ENVELOPE_OFFSETS, envelope_field
from trackmod.trackers.it.layout.file import FILE_HEADER
from trackmod.trackers.it.layout.instrument import INSTRUMENT_HEADER
from trackmod.trackers.it.layout.pattern import PATTERN_HEADER
from trackmod.trackers.it.layout.sample import SAMPLE_HEADER

# Every size and offset here is written out as the number this format's headers have rather than
# imported from the constant that states it, so a record laid out a byte adrift disagrees with the
# tracker rather than agreeing with itself.

RECORDS = (
    (FILE_HEADER, 192),
    (PATTERN_HEADER, 8),
    (SAMPLE_HEADER, 80),
    (INSTRUMENT_HEADER, 554),
)

ENVELOPE_BLOCKS = {
    EnvelopeKind.VOLUME: 0x130,
    EnvelopeKind.PANNING: 0x182,
    EnvelopeKind.PITCH: 0x1D4,
}

DOS_FILENAME_BYTES = 12


def test_each_record_is_the_size_this_format_lays_it_out_at() -> None:
    assert all(record.size == size for record, size in RECORDS)


def test_the_three_envelope_blocks_open_where_the_instrument_header_places_them() -> None:
    assert ENVELOPE_OFFSETS == ENVELOPE_BLOCKS


def test_a_record_names_the_file_a_voice_came_from_in_the_bytes_its_system_allowed() -> None:
    for record in (SAMPLE_HEADER, INSTRUMENT_HEADER):
        (filename,) = (field for field in record.fields if field.name == "filename")
        assert filename.size == DOS_FILENAME_BYTES


def test_no_two_fields_of_a_record_overlap() -> None:
    for record, _ in RECORDS:
        occupied: set[int] = set()
        for field in record.fields:
            span = set(range(field.offset, field.offset + field.size))
            assert not span & occupied
            occupied |= span


def test_each_envelope_block_is_named_and_placed_apart() -> None:
    offsets = {kind: ENVELOPE_OFFSETS[kind] for kind in EnvelopeKind}
    assert len(set(offsets.values())) == len(EnvelopeKind)
    names = {envelope_field(kind, "flags") for kind in EnvelopeKind}
    assert names <= {field.name for field in INSTRUMENT_HEADER.fields}
