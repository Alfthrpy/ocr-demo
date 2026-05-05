import cv2
import numpy as np
from PIL import Image

def draw_boxes(image: np.ndarray, structured_results: list) -> Image.Image:
    """
    Draws bounding boxes and text on the image based on PPStructure output.
    Bbox format: [x1, y1, x2, y2]
    """
    img_bgr = image.copy()
    
    # Define colors for different region types
    colors = {
        'text': (0, 255, 0),     # Green
        'table': (0, 0, 255),    # Red
        'figure': (255, 0, 0),   # Blue
        'title': (0, 255, 255),  # Yellow
        'list': (255, 0, 255),   # Magenta
        'unknown': (128, 128, 128) # Gray
    }
    
    for item in structured_results:
        bbox = item.get('bbox', [])
        region_type = item.get('type', 'unknown')
        
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            color = colors.get(region_type, colors['unknown'])
            
            # Draw rectangle
            cv2.rectangle(img_bgr, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # Add text label (type of region)
            cv2.putText(img_bgr, region_type, (int(x1), int(y1) - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img_rgb)


import re

def clean_ocr_markdown(raw: str | dict) -> str:
    # Kalau masih dict, ambil valuenya dulu
    if isinstance(raw, dict):
        text = raw.get("markdown_texts") or raw.get("markdown_text", "")
    else:
        text = raw

    # Hapus wrapper <html><body> dan </body></html> di dalam div
    # Contoh: <div ...><html><body><table>...</table></body></html></div>
    # → <div ...><table>...</table></div>
    text = re.sub(r'<html><body>', '', text)
    text = re.sub(r'</body></html>', '', text)

    # Hapus div pembungkus center yang kosong atau hanya spasi
    text = re.sub(r'<div[^>]*>\s*</div>', '', text)

    # Rapikan multiple blank lines jadi max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()