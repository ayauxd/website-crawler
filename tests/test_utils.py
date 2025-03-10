"""
Tests for the utils module.
"""
import sys
import os
import unittest

# Add the parent directory to the path so we can import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import (
    normalize_url,
    is_valid_url,
    get_domain,
    is_same_domain,
    is_internal_link,
    get_file_extension,
    is_image_url,
    is_document_url,
    url_to_filename
)

class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_normalize_url(self):
        """Test URL normalization."""
        self.assertEqual(normalize_url("https://example.com/page?q=test#fragment"), "https://example.com/page?q=test")
        self.assertEqual(normalize_url("https://example.com/page/"), "https://example.com/page/")
        self.assertEqual(normalize_url("#fragment"), "")
    
    def test_is_valid_url(self):
        """Test URL validation."""
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/page?q=test"))
        self.assertFalse(is_valid_url("example.com"))
        self.assertFalse(is_valid_url(""))
        self.assertFalse(is_valid_url("ftp://example.com"))
    
    def test_get_domain(self):
        """Test domain extraction."""
        self.assertEqual(get_domain("https://example.com/page"), "example.com")
        self.assertEqual(get_domain("https://sub.example.com/page"), "sub.example.com")
        self.assertEqual(get_domain("https://example.com:8080/page"), "example.com:8080")
    
    def test_is_same_domain(self):
        """Test domain comparison."""
        self.assertTrue(is_same_domain("https://example.com/page1", "https://example.com/page2"))
        self.assertTrue(is_same_domain("http://example.com", "https://example.com"))
        self.assertFalse(is_same_domain("https://example.com", "https://sub.example.com"))
        self.assertFalse(is_same_domain("https://example1.com", "https://example2.com"))
    
    def test_is_internal_link(self):
        """Test internal link detection."""
        self.assertTrue(is_internal_link("https://example.com", "https://example.com/page"))
        self.assertTrue(is_internal_link("https://example.com", "/page"))
        self.assertFalse(is_internal_link("https://example.com", "https://other.com/page"))
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        self.assertEqual(get_file_extension("https://example.com/image.jpg"), ".jpg")
        self.assertEqual(get_file_extension("https://example.com/document.PDF"), ".pdf")
        self.assertEqual(get_file_extension("https://example.com/page"), "")
    
    def test_is_image_url(self):
        """Test image URL detection."""
        self.assertTrue(is_image_url("https://example.com/image.jpg"))
        self.assertTrue(is_image_url("https://example.com/image.png"))
        self.assertFalse(is_image_url("https://example.com/document.pdf"))
        self.assertFalse(is_image_url("https://example.com/page"))
    
    def test_is_document_url(self):
        """Test document URL detection."""
        self.assertTrue(is_document_url("https://example.com/document.pdf"))
        self.assertTrue(is_document_url("https://example.com/document.docx"))
        self.assertFalse(is_document_url("https://example.com/image.jpg"))
        self.assertFalse(is_document_url("https://example.com/page"))
    
    def test_url_to_filename(self):
        """Test URL to filename conversion."""
        self.assertEqual(url_to_filename("https://example.com"), "index")
        self.assertEqual(url_to_filename("https://example.com/page"), "page")
        self.assertEqual(url_to_filename("https://example.com/path/to/page"), "path_to_page")
        self.assertEqual(url_to_filename("https://example.com/page", ".html"), "page.html")
        
        # Test with query parameters
        filename = url_to_filename("https://example.com/page?id=123&q=test")
        self.assertTrue(filename.startswith("page_"))
        self.assertTrue(len(filename) > 5)  # Should have a hash appended

if __name__ == "__main__":
    unittest.main()
