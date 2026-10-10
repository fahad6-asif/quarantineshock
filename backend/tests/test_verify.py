from app.rag import sources
from app.verify import verify_quote

SRC = sources.body("2026-04-02_la-mesa-expanded-da-2026-16")
EXACT = "The amended quarantine encompasses 84 square miles and contains no commercial agriculture."


def test_exact_quote_passes():
    assert verify_quote(EXACT, SRC)["verified"]


def test_altered_number_fails():
    assert not verify_quote(EXACT.replace("84", "94"), SRC)["verified"]


def test_altered_word_fails():
    assert not verify_quote(EXACT.replace("no commercial", "some commercial"), SRC)["verified"]


def test_invented_sentence_fails():
    assert not verify_quote("The quarantine was lifted on April 30 for all citrus.", SRC)["verified"]


def test_whitespace_and_smart_quotes_pass():
    variant = "The amended   quarantine\nencompasses 84 square miles and contains no commercial agriculture."
    assert verify_quote(variant, SRC)["verified"]
    hass_src = sources.body("cdfa_3417")
    assert verify_quote("Fresh, mature green variety ‘Hass’ avocadoes are not regulated", hass_src)["verified"]
    assert verify_quote("Fresh, mature green variety 'Hass' avocadoes are not regulated", hass_src)["verified"]


def test_ellipsis_quote_checks_each_piece():
    q = "On March 17, APHIS and CDFA expanded the La Mesa Mexfly quarantine ... contains no commercial agriculture"
    assert verify_quote(q, SRC)["verified"]
    bad = "On March 17, APHIS and CDFA expanded the La Mesa Mexfly quarantine ... contains 40 acres of citrus"
    assert not verify_quote(bad, SRC)["verified"]


def test_empty_quote_fails():
    assert not verify_quote("", SRC)["verified"]
