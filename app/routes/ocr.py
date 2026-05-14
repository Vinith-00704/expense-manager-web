"""
app/routes/ocr.py  —  /api/ocr/*
OCR placeholder routes — ready for future receipt/invoice scanning.
"""
from flask import Blueprint
from flask_jwt_extended import jwt_required
from ..utils.response import error

ocr_bp = Blueprint("ocr", __name__)


@ocr_bp.post("/upload")
@jwt_required()
def upload():
    """
    POST /api/ocr/upload
    TODO: Implement receipt OCR using pytesseract or Google Vision API.
    """
    return error("OCR receipt scanning is not yet implemented. Coming soon.", 501)


@ocr_bp.post("/invoice")
@jwt_required()
def invoice():
    """TODO: Invoice OCR extraction."""
    return error("Invoice OCR is not yet implemented.", 501)


@ocr_bp.post("/qr")
@jwt_required()
def qr_scan():
    """TODO: QR code merchant/amount extraction."""
    return error("QR scanning is not yet implemented.", 501)
