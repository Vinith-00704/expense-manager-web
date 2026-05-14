"""tests/test_sms_parser.py"""
import pytest
from app.services.sms_parsers import parse_sms
from app.services.sms_parsers.upi_parser import UPIParser
from app.services.sms_parsers.hdfc_parser import HDFCSMSParser


UPI_MSGS = [
    "UPI transaction of Rs.250 to Uber successful. Ref: 123456",
    "Rs.540.00 paid via Google Pay to SWIGGY. UPI Ref No: 789",
    "PhonePe UPI: Rs.1200 debited from your account to Amazon",
]

HDFC_MSGS = [
    "Rs.540 spent on HDFC Bank Card XX1234 at SWIGGY on 04-05-26.",
    "HDFC Bank: Rs.1500.00 debited from A/c XX9876 on 03-05-26 to VPA xyz@upi.",
]


@pytest.mark.parametrize("sms", UPI_MSGS)
def test_upi_parser_can_parse(sms):
    parser = UPIParser()
    assert parser.can_parse(sms)


@pytest.mark.parametrize("sms", UPI_MSGS)
def test_upi_parser_extracts_amount(sms):
    result = parse_sms(sms)
    assert result is not None
    assert result["amount"] > 0


@pytest.mark.parametrize("sms", HDFC_MSGS)
def test_hdfc_parser_can_parse(sms):
    parser = HDFCSMSParser()
    assert parser.can_parse(sms)


@pytest.mark.parametrize("sms", HDFC_MSGS)
def test_hdfc_parser_extracts_amount(sms):
    result = parse_sms(sms)
    assert result is not None
    assert result["amount"] > 0


def test_unrecognised_sms_returns_none():
    result = parse_sms("Your OTP is 123456. Do not share.")
    assert result is None


def test_parse_sms_result_has_required_keys():
    sms = "UPI transaction of Rs.300 to Netflix successful."
    result = parse_sms(sms)
    assert result is not None
    for key in ("merchant", "amount", "direction", "date"):
        assert key in result, f"Missing key: {key}"
