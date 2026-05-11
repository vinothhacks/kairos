"""Integration tests that opt out of the stub LLM autouse fixture.

Mark every test in this directory with @pytest.mark.integration so that
tests/conftest.py's autouse fixture does NOT pin KAIROS_LLM_BACKEND=stub.
"""
