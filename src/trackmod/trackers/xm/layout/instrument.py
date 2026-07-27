from typing import Final

from trackmod.binary.records.field import ArrayField, Field
from trackmod.binary.records.record import Record
from trackmod.trackers.xm.layout.envelope import (
    ENVELOPE_KINDS,
    envelope_fields,
    envelope_points,
)
from trackmod.trackers.xm.spec.identity import MAGIC_INSTRUMENT_BYTES
from trackmod.trackers.xm.spec.sizes import (
    EMPTY_INSTRUMENT_HEADER_BYTES,
    INSTRUMENT_FILE_COUNT_OFFSET,
    INSTRUMENT_FILE_HEADER_BYTES,
    INSTRUMENT_FILE_ORIGIN,
    INSTRUMENT_HEADER_BYTES,
    KEYMAP_NOTES,
    NAME_BYTES,
    TRACKER_NAME_BYTES,
)

MODULE_ORIGIN: Final = 0

IDENTITY_FIELDS: Final = (
    Field(name="header_size", offset=0, code="<I"),
    Field(name="name", offset=4, code=f"{NAME_BYTES}s"),
    Field(name="type", offset=26, code="B"),
    Field(name="sample_count", offset=27, code="<H"),
)

EMPTY_INSTRUMENT_HEADER: Final = Record(size=EMPTY_INSTRUMENT_HEADER_BYTES, fields=IDENTITY_FIELDS)


def body_fields(origin: int) -> tuple[Field, ...]:
    """The keyboard routing, envelopes, vibrato and fadeout an instrument header carries.

    Both of this format's instrument headers lay the same body out behind an identity block of their own
    length, so one description serves them both once it is told how far in the body begins.
    """
    return (
        Field(name="keymap", offset=origin + 33, code=f"{KEYMAP_NOTES}s"),
        *(field for kind in ENVELOPE_KINDS for field in envelope_fields(kind, origin=origin)),
        Field(name="vibrato_type", offset=origin + 235, code="B"),
        Field(name="vibrato_sweep", offset=origin + 236, code="B"),
        Field(name="vibrato_depth", offset=origin + 237, code="B"),
        Field(name="vibrato_rate", offset=origin + 238, code="B"),
        Field(name="fadeout", offset=origin + 239, code="<H"),
    )


def body_points(origin: int) -> tuple[ArrayField, ...]:
    """The point tables of both envelopes an instrument header carries."""
    return tuple(envelope_points(kind, origin=origin) for kind in ENVELOPE_KINDS)


INSTRUMENT_HEADER: Final = Record(
    size=INSTRUMENT_HEADER_BYTES,
    fields=(
        *IDENTITY_FIELDS,
        Field(name="sample_header_size", offset=29, code="<I"),
        *body_fields(MODULE_ORIGIN),
        Field(name="reserved", offset=241, code="<H"),
    ),
    arrays=body_points(MODULE_ORIGIN),
)

INSTRUMENT_FILE_HEADER: Final = Record(
    size=INSTRUMENT_FILE_HEADER_BYTES,
    fields=(
        Field(name="magic", offset=0, code=f"{MAGIC_INSTRUMENT_BYTES}s"),
        Field(name="name", offset=21, code=f"{NAME_BYTES}s"),
        Field(name="stripped", offset=43, code="B"),
        Field(name="tracker", offset=44, code=f"{TRACKER_NAME_BYTES}s"),
        Field(name="version", offset=64, code="<H"),
        *body_fields(INSTRUMENT_FILE_ORIGIN),
        Field(name="sample_count", offset=INSTRUMENT_FILE_COUNT_OFFSET, code="<H"),
    ),
    arrays=body_points(INSTRUMENT_FILE_ORIGIN),
)
