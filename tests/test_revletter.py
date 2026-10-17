import pytest

from drawing import revletter as r


def test_alphabet_skips():
    for bad in "ILOQ":
        assert bad not in r.ALPHABET
    assert len(r.ALPHABET) == 22


def test_sequence_and_rollover():
    assert [r.letter_for_index(i) for i in range(10)] == list("ABCDEFGHJK")
    assert r.letter_for_index(21) == "Z"
    assert r.letter_for_index(22) == "AA"
    assert r.letter_for_index(23) == "AB"
    assert r.letter_for_index(22 + 22) == "BA"


def test_round_trip():
    for i in range(0, 600):
        assert r.index_for_letter(r.letter_for_index(i)) == i


def test_release_count():
    assert r.letter_for_release_count(1) == "A"
    assert r.letter_for_release_count(7) == "G"
    assert r.letter_for_release_count(8) == "H"
    assert r.letter_for_release_count(9) == "J"  # I skipped
    with pytest.raises(ValueError):
        r.letter_for_release_count(0)


def test_model_and_clerical():
    assert r.next_clerical_rev("C") == "C.01"
    assert r.next_clerical_rev("C.01") == "C.02"
    assert r.next_model_rev("C.02") == "D"
    assert r.next_model_rev("H") == "J"
    assert r.next_model_rev("K") == "M"  # L skipped
    assert r.next_model_rev("N") == "P"  # O skipped
    assert r.next_model_rev("P") == "R"  # Q skipped
    assert r.next_model_rev("Z") == "AA"


@pytest.mark.parametrize("bad", ["I", "L", "O", "Q", "c", "C.1", "", "C.001", "A1"])
def test_rejects(bad):
    with pytest.raises(ValueError):
        r.parse(bad)
