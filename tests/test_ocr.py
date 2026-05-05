from unittest.mock import patch, MagicMock
from src.ocr_engine import OCREngine

@patch('src.ocr_engine.PPStructureV3')
def test_process_image_returns_structured_data(MockPPStructure):
    # Setup mock
    mock_pipeline_instance = MockPPStructure.return_value
    mock_res = MagicMock()
    mock_res.markdown = {"markdown_images": {}}
    mock_pipeline_instance.predict.return_value = [mock_res]
    mock_pipeline_instance.concatenate_markdown_pages.return_value = "## INVOICE\n\n| Item | Price |\n|---|---|\n"
    
    engine = OCREngine()
    result = engine.process_image("dummy_path.jpg")
    
    # Assertions
    assert "markdown_text" in result
    assert "INVOICE" in result["markdown_text"]
    assert len(result["images"]) == 1
    
    # Verify the mock was called
    mock_pipeline_instance.predict.assert_called_once_with(input="dummy_path.jpg")
