import re
from typing import List, Dict, Optional

class InvoiceParser:
    def __init__(self):
        # Define basic regex patterns for MVP
        self.patterns = {
            'invoice_number': r'(?i)invoice\s*(?:no|number|#)?\s*[:\-]\s*([a-zA-Z0-9\-]+)',
            'date': r'(?i)date\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
            'total_amount': r'(?i)total\s*(?:amount)?\s*[:\-]?\s*(?:usd|rp|\$)?\s*([\d,\.]+)'
        }

    def parse(self, texts: List[str]) -> Dict[str, Optional[str]]:
        result = {
            'invoice_number': None,
            'date': None,
            'total_amount': None
        }
        
        # We will iterate through texts and try to match our patterns
        for text in texts:
            for field, pattern in self.patterns.items():
                if result[field] is None:  # Only get the first match for simplicity
                    match = re.search(pattern, text)
                    if match:
                        result[field] = match.group(1).strip()
                        
        # Clean up total amount
        if result['total_amount']:
            # Replace commas and keep decimal point if necessary, or just extract the number
            cleaned = re.sub(r'[^\d\.]', '', result['total_amount'])
            result['total_amount'] = cleaned
            
        return result
