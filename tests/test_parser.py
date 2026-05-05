from src.parser import InvoiceParser

def test_extract_invoice_info():
    # Simulate OCR text output
    ocr_texts = [
        "ACME Corp",
        "Invoice No: INV-2023-001",
        "Date: 25/12/2023",
        "Item 1     $100.00",
        "Item 2     $50.00",
        "Total Amount: $150.00",
        "Thank you for your business"
    ]
    
    parser = InvoiceParser()
    parsed_data = parser.parse(ocr_texts)
    
    assert parsed_data['invoice_number'] == 'INV-2023-001'
    assert parsed_data['date'] == '25/12/2023'
    assert parsed_data['total_amount'] == '150.00'

def test_extract_invoice_info_missing_fields():
    ocr_texts = [
        "ACME Corp",
        "Just some text",
        "No invoice number here"
    ]
    
    parser = InvoiceParser()
    parsed_data = parser.parse(ocr_texts)
    
    assert parsed_data['invoice_number'] is None
    assert parsed_data['date'] is None
    assert parsed_data['total_amount'] is None
