from vb6_parser._errors import ParseError, VbRuntimeError, InternalError

def test_parse_error_is_exception():
    e = ParseError("bad syntax", stderr="details here")
    assert isinstance(e, Exception)
    assert "bad syntax" in str(e)
    assert e.stderr == "details here"

def test_runtime_error_carries_hint():
    e = VbRuntimeError("JRE not found. Install Java 17+.")
    assert "Java" in str(e)

def test_internal_error():
    e = InternalError("json decode failed")
    assert isinstance(e, Exception)
