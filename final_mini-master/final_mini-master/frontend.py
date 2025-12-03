"""
Frontend module for Invisible Watermark Tool
Contains all Streamlit UI components, page layouts, and user interface logic
"""

import streamlit as st
from PIL import Image
import json
from datetime import datetime
import hashlib
import io
from backend import WatermarkService, ImageProcessor


class UIComponents:
    """Class containing reusable UI components"""
    
    @staticmethod
    def setup_page_config():
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title="Invisible Watermark Tool",
            page_icon="🔒",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    @staticmethod
    def load_custom_css():
        """Load custom CSS styles"""
        st.markdown("""
        <style>
            .main-header {
                font-size: 2.5rem;
                font-weight: bold;
                text-align: center;
                margin-bottom: 2rem;
                color: #1f77b4;
            }
            .section-header {
                font-size: 1.5rem;
                font-weight: bold;
                margin-top: 2rem;
                margin-bottom: 1rem;
                color: #2c3e50;
            }
            .success-message {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 0.375rem;
                padding: 0.75rem;
                margin: 1rem 0;
                color: #155724;
            }
            .error-message {
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 0.375rem;
                padding: 0.75rem;
                margin: 1rem 0;
                color: #721c24;
            }
            .info-box {
                background-color: #d1ecf1;
                border: 1px solid #bee5eb;
                border-radius: 0.375rem;
                padding: 0.75rem;
                margin: 1rem 0;
                color: #0c5460;
            }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def display_header():
        """Display main header"""
        st.markdown('<h1 class="main-header">🔒 Invisible Watermark Tool</h1>', unsafe_allow_html=True)
    
    @staticmethod
    def display_navigation():
        """Display navigation sidebar"""
        st.sidebar.title("Navigation")
        return st.sidebar.selectbox("Choose an option:", ["Embed Watermark", "Extract Watermark", "About"])
    
    @staticmethod
    def display_watermark_details(data, image=None):
        """Display full watermark details"""
        st.success("✅ Watermark found!")
        
        # Display the image if provided
        if image is not None:
            st.subheader("🖼️ Watermarked Image")
            st.image(image, caption="Watermarked Image", use_container_width=True)
        
        st.subheader("📋 Watermark Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Owner", data.get('owner', 'N/A'))
            st.metric("Buyer", data.get('buyer', 'N/A'))
        
        with col2:
            st.metric("Date/Time", data.get('datetime', 'N/A'))
            st.metric("Passkey Protected", "Yes" if data.get('passkey_hash') else "No")
        
        # Show raw data in expander
        with st.expander("🔍 Raw Watermark Data"):
            st.json(data)


class EmbedWatermarkPage:
    """Class for handling the embed watermark page"""
    
    def __init__(self, watermark_service):
        self.watermark_service = watermark_service
        self.image_processor = ImageProcessor()
    
    def render(self):
        """Render the embed watermark page"""
        st.markdown('<h2 class="section-header">📝 Embed Watermark</h2>', unsafe_allow_html=True)
        
        # Create two columns for better layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_form_section()
        
        with col2:
            self._render_preview_section()
        
        # Handle resell functionality
        self._handle_resell_functionality()
        
        # Handle embed watermark button
        self._handle_embed_button()
    
    def _render_form_section(self):
        """Render the form section"""
        st.subheader("📋 Watermark Information")
        
        # Form fields
        self.owner = st.text_input("Owner:", placeholder="Enter owner name")
        self.buyer = st.text_input("Buyer:", placeholder="Enter buyer name")
        
        # Passkey fields
        self.passkey = st.text_input("Passkey:", type="password", placeholder="Enter secure passkey")
        self.confirm_passkey = st.text_input("Confirm Passkey:", type="password", placeholder="Confirm passkey")
        
        # Date/Time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.datetime_str = st.text_input("Date/Time:", value=current_time)
        
        # Image upload
        st.subheader("🖼️ Image Upload")
        self.uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg', 'bmp'],
            help="Upload an image to embed the watermark into"
        )
    
    def _render_preview_section(self):
        """Render the image preview section"""
        st.subheader("📸 Image Preview")
        
        if self.uploaded_file is not None:
            try:
                # Load and display the image
                image = self.image_processor.load_image(self.uploaded_file)
                st.image(image, caption="Original Image", use_container_width=True)
                
                # Check for existing watermark
                existing_watermark = self.watermark_service.processor.extract_watermark(image)
                if existing_watermark:
                    try:
                        wm_data = json.loads(existing_watermark)
                        st.warning("⚠️ This image already sold and is not new Art.")
                        st.info(f"**Previous Owner:** {wm_data.get('owner', 'N/A')}\n\n**Owner:** {wm_data.get('buyer', 'N/A')}\n\n**Transaction Date:** {wm_data.get('datetime', 'N/A')}")
                        
                        if wm_data.get('passkey_hash'):
                            st.error("🔒 This image is passkey protected. You need the original passkey to resell.")
                            # Store existing watermark data for resell functionality
                            st.session_state.existing_watermark = wm_data
                        else:
                            st.info("ℹ️ This watermark is not passkey protected.")
                            st.session_state.existing_watermark = wm_data
                    except:
                        st.warning("⚠️ This image is a new Art.")
                        st.session_state.existing_watermark = None
                else:
                    st.session_state.existing_watermark = None
                
            except Exception as e:
                st.error(f"Error loading image: {e}")
        else:
            st.info("Please upload an image.")
    
    def _handle_resell_functionality(self):
        """Handle resell functionality for existing watermarks"""
        if hasattr(st.session_state, 'existing_watermark') and st.session_state.existing_watermark:
            st.markdown("---")
            st.subheader("🔄 Resell/Update Watermark")
            
            existing_wm = st.session_state.existing_watermark
            
            if existing_wm.get('passkey_hash'):
                # Passkey protected - require verification
                st.info("🔒 This image is passkey protected. Enter the original passkey to update ownership.")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    resell_passkey = st.text_input("Original Passkey:", type="password", 
                                                 placeholder="Enter original passkey to resell", 
                                                 key="resell_passkey")
                with col2:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if st.button("🔓 Verify for Resell", type="secondary"):
                        is_valid, error = self.watermark_service.verify_resell_passkey(resell_passkey, existing_wm)
                        if is_valid:
                            st.success("✅ Passkey verified! You can now update the watermark.")
                            st.session_state.resell_verified = True
                        else:
                            st.error(f"❌ {error}")
                            st.session_state.resell_verified = False
            else:
                # No passkey protection - allow direct update
                st.info("ℹ️ This watermark is not passkey protected. You can update it directly.")
                st.session_state.resell_verified = True
            
            # Show resell form if verified or not passkey protected
            if hasattr(st.session_state, 'resell_verified') and st.session_state.resell_verified:
                self._render_resell_form()
    
    def _render_resell_form(self):
        """Render the resell form"""
        st.markdown("#### 📝 Update Ownership Details")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            new_owner = st.text_input("Current Owner:", placeholder="Enter owner name", key="buyer")
            new_passkey = st.text_input("New Passkey:", type="password", placeholder="Enter new passkey", key="new_passkey")
        with col2:
            new_buyer = st.text_input("New Buyer:", placeholder="Enter new buyer name", key="new_buyer")
            confirm_new_passkey = st.text_input("Confirm New Passkey:", type="password", placeholder="Confirm new passkey", key="confirm_new_passkey")
        
        if st.button("🔄 Update Watermark", type="primary"):
            updated_image, errors = self.watermark_service.resell_watermark(
                self.uploaded_file, new_owner, new_buyer, new_passkey, confirm_new_passkey
            )
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Display success message
                st.success("✅ Watermark updated successfully!")
                
                # Show updated image
                st.subheader("🔄 Updated Watermarked Image")
                st.image(updated_image, caption="Updated Watermarked Image", use_container_width=True)
                
                # Download link
                filename = f"updated_{self.uploaded_file.name}"
                download_link = self.watermark_service.get_download_link(updated_image, filename)
                st.markdown(download_link, unsafe_allow_html=True)
                
                # Clear session state
                st.session_state.existing_watermark = None
                st.session_state.resell_verified = False
    
    def _handle_embed_button(self):
        """Handle the embed watermark button"""
        st.markdown("---")
        
        # Only show embed button if no existing watermark or if reselling
        show_embed_button = True
        if hasattr(st.session_state, 'existing_watermark') and st.session_state.existing_watermark:
            if not (hasattr(st.session_state, 'resell_verified') and st.session_state.resell_verified):
                show_embed_button = False
                st.warning("⚠️ Cannot embed new watermark. This image already has a watermark. Use the 'Resell/Update Watermark' section above to update it.")
        
        if show_embed_button and st.button("🔒 Embed Watermark", type="primary", use_container_width=True):
            watermarked_image, errors = self.watermark_service.embed_watermark(
                self.uploaded_file, self.owner, self.buyer, self.passkey, self.confirm_passkey, self.datetime_str
            )
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Display success message
                st.success("✅ Watermark embedded successfully!")
                
                # Show watermarked image
                st.subheader("🔒 Watermarked Image")
                st.image(watermarked_image, caption="Watermarked Image", use_container_width=True)
                
                # Download link
                filename = f"watermarked_{self.uploaded_file.name}"
                download_link = self.watermark_service.get_download_link(watermarked_image, filename)
                st.markdown(download_link, unsafe_allow_html=True)
                
                # Clear sensitive data
                st.session_state.passkey = ""
                st.session_state.confirm_passkey = ""


class ExtractWatermarkPage:
    """Class for handling the extract watermark page"""
    
    def __init__(self, watermark_service):
        self.watermark_service = watermark_service
        self.image_processor = ImageProcessor()
    
    def render(self):
        """Render the extract watermark page"""
        st.markdown('<h2 class="section-header">🔍 Extract Watermark</h2>', unsafe_allow_html=True)
        
        # Initialize session state for watermark data
        self._initialize_session_state()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            self._render_upload_section()
        
        with col2:
            self._render_preview_section()
        
        # Handle extract button
        self._handle_extract_button()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'watermark_data' not in st.session_state:
            st.session_state.watermark_data = None
        if 'current_image_hash' not in st.session_state:
            st.session_state.current_image_hash = None
        if 'current_image' not in st.session_state:
            st.session_state.current_image = None
    
    def _render_upload_section(self):
        """Render the upload section"""
        st.subheader("🖼️ Upload Image")
        self.uploaded_file = st.file_uploader(
            "Choose an image file to scan",
            type=['png', 'jpg', 'jpeg', 'bmp'],
            help="Upload an image to extract watermark information from"
        )
    
    def _render_preview_section(self):
        """Render the image preview section"""
        st.subheader("📸 Image Preview")
        if self.uploaded_file is not None:
            try:
                image = self.image_processor.load_image(self.uploaded_file)
                st.image(image, caption="Image to Scan", use_container_width=True)
                
                # Generate hash for current image to detect changes
                current_hash = self.image_processor.generate_image_hash(image)
                
                # Reset watermark data if image changed
                if st.session_state.current_image_hash != current_hash:
                    st.session_state.current_image_hash = current_hash
                    st.session_state.watermark_data = None
                    st.session_state.current_image = image
                    
            except Exception as e:
                st.error(f"Error loading image: {e}")
        else:
            st.info("Please upload an image.")
    
    def _handle_extract_button(self):
        """Handle the extract watermark button"""
        st.markdown("---")
        
        if st.button("🔍 Extract Watermark", type="primary", use_container_width=True):
            result, errors = self.watermark_service.extract_watermark(self.uploaded_file)
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            elif result == "corrupted":
                st.warning("⚠️ It's a new Art!")
                # Note: We don't have access to raw watermark data here, but this maintains the original functionality
            elif result:
                # Watermark found and parsed successfully
                st.session_state.watermark_data = result
                st.success("✅ Watermark found!")
                UIComponents.display_watermark_details(result, st.session_state.current_image)
            else:
                st.info("ℹ️ No watermark found in this image.")
                st.session_state.watermark_data = None


class AboutPage:
    """Class for handling the about page"""
    
    @staticmethod
    def render():
        """Render the about page"""
        st.markdown('<h2 class="section-header">ℹ️ About</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        ## 🔒 Invisible Watermark Tool
        
        This application uses **LSB (Least Significant Bit) Steganography** to embed invisible watermarks into images. 
        The watermarks are completely invisible to the naked eye and contain ownership and transaction information.
        
        ### ✨ Features
        
        - **🔒 Secure Watermarking**: Uses LSB steganography for invisible watermarks
        - **🔑 Passkey Protection**: Secure passkey system for reselling protection
        - **📝 Ownership Tracking**: Track owner and buyer information
        - **⏰ Timestamping**: Automatic date/time stamping
        - **🔍 Verification**: Extract and verify existing watermarks
        - **🔄 Resell Functionality**: Update ownership details with original passkey
        - **📱 Modern Web Interface**: Clean, responsive Streamlit interface
        
        ### 🛡️ Security Features
        
        - **Passkey Hashing**: Passkeys are hashed using SHA-256, never stored in plain text
        - **Resell Protection**: Only users with the original passkey can resell watermarked images
        - **Access Control**: Watermarked images require passkey verification to view sensitive details
        - **Data Integrity**: Watermarks include EOF markers for reliable extraction
        - **Session Management**: Secure session handling prevents unauthorized access
        
        ### 📋 How to Use
        
        1. **Embed Watermark**: Upload an image, fill in the details, and embed a watermark
        2. **Extract Watermark**: Upload any image to check for existing watermarks
        3. **Resell Images**: Upload a watermarked image and use the original passkey to update ownership details
        4. **Update Ownership**: Change owner, buyer, and passkey information for reselling
        
        ### ⚠️ Important Notes
        
        - Watermarks work best with PNG and BMP images
        - Large watermarks may not fit in small images
        - Always keep your passkeys secure - they cannot be recovered if lost
        - The watermark is embedded in the least significant bits, so image quality is preserved
        """)
        
        st.markdown("---")
        st.markdown("**Made with ❤️ using Streamlit**")
