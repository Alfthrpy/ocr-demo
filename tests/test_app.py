from streamlit.testing.v1 import AppTest

def test_app_ui_elements():
    # Load app
    at = AppTest.from_file("src/app.py").run()
    
    # Check title
    assert at.title[0].value == "Demo OCR Invoice (PP-StructureV3)"
    
    # Check if file uploader exists
    assert len(at.file_uploader) == 1
