"""Generative checks for the protocol and security-sensitive boundaries."""

from __future__ import annotations

import json

from hypothesis import given, settings, strategies as st

from deck3ds import protocol
from deck3ds.configuration.arguments import normalize_web_url
from deck3ds.pairing import (
    PAIRING_ATTEMPTS_PER_SOURCE,
    PairingManager,
    PairingResult,
)


json_scalars = st.none() | st.booleans() | st.integers(-(2**31), 2**31 - 1) | st.text(max_size=80)
json_values = st.recursive(
    json_scalars,
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=5),
    max_leaves=20,
)


@settings(max_examples=100, deadline=None)
@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=20), json_values, min_size=1, max_size=8
    ),
    chunk_sizes=st.lists(st.integers(min_value=1, max_value=31), min_size=1, max_size=30),
)
def test_frames_round_trip_under_arbitrary_tcp_fragmentation(payload, chunk_sizes):
    frame = protocol.encode(payload)
    reader = protocol.FrameReader()
    received = []
    offset = 0
    for size in chunk_sizes:
        reader.feed(frame[offset : offset + size])
        offset += size
        received.extend(reader)
        if offset >= len(frame):
            break
    if offset < len(frame):
        reader.feed(frame[offset:])
        received.extend(reader)
    assert received == [payload]


@settings(max_examples=100)
@given(length=st.integers(min_value=protocol.MAX_MESSAGE + 1, max_value=2**32 - 1))
def test_oversized_announced_frames_always_fail_closed(length):
    reader = protocol.FrameReader()
    reader.feed(length.to_bytes(4, "big"))
    try:
        list(reader)
    except protocol.ProtocolError:
        return
    raise AssertionError("oversized frame accepted")


@settings(max_examples=100)
@given(
    label=st.text(
        alphabet=st.characters(
            whitelist_categories=("Ll", "Lu", "Nd"),
            whitelist_characters=".-",
        ),
        min_size=1,
        max_size=80,
    )
)
def test_bare_web_hosts_are_normalized_to_https(label):
    # A dot ensures urlsplit sees a normal host while still exercising Unicode
    # labels and length variation. The normalized value must remain JSON-safe.
    target = normalize_web_url(f"{label}.example")
    assert target.startswith("https://")
    json.dumps(target)


@settings(max_examples=40)
@given(invalid=st.text(min_size=0, max_size=12).filter(lambda value: not (len(value) == 6 and value.isascii() and value.isdigit())))
def test_pairing_quota_never_accepts_malformed_codes(invalid):
    pairing = PairingManager(clock=lambda: 100.0)
    results = [
        pairing.consume_result(invalid, "same-console")
        for _ in range(PAIRING_ATTEMPTS_PER_SOURCE + 2)
    ]
    assert PairingResult.ACCEPTED not in results
    assert results[-1] is PairingResult.RATE_LIMITED
