"""
Main application file for Invisible Watermark Tool
Connects frontend and backend components
"""

from frontend import UIComponents, EmbedWatermarkPage, ExtractWatermarkPage, AboutPage
from backend import WatermarkService


def main():
    """Main application function"""
    # Setup UI components
    UIComponents.setup_page_config()
    UIComponents.load_custom_css()
    UIComponents.display_header()
    
    # Initialize watermark service
    watermark_service = WatermarkService()
    
    # Display navigation and handle page routing
    page = UIComponents.display_navigation()
    
    if page == "Embed Watermark":
        embed_page = EmbedWatermarkPage(watermark_service)
        embed_page.render()
    elif page == "Extract Watermark":
        extract_page = ExtractWatermarkPage(watermark_service)
        extract_page.render()
    else:
        AboutPage.render()


if __name__ == "__main__":
    main()
