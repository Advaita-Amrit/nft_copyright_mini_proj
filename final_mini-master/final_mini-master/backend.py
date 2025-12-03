"""
Backend module for Invisible Watermark Tool
Contains all watermark processing logic, utilities, and business logic
"""
# backend.py (top imports)
from blockchain import BlockchainClient, metadata_to_data_uri
import os

from PIL import Image
import numpy as np
import json
from datetime import datetime
import hashlib
import io
import base64


class WatermarkProcessor:
    """Main class for handling watermark operations"""
    
    @staticmethod
    def str_to_bin(s):
        """Convert a string to its binary representation."""
        return ''.join([format(ord(i), '08b') for i in s])

    @staticmethod
    def bin_to_str(b):
        """Convert a binary string back to a regular string."""
        # Split into 8-bit chunks
        chars = [b[i:i+8] for i in range(0, len(b), 8)]
        # Convert each chunk to a character, ignoring any partial chunk at the end
        return ''.join([chr(int(c, 2)) for c in chars if len(c) == 8])

    @staticmethod
    def embed_watermark(img, watermark_json):
        """Embeds the watermark JSON string into the image using LSB."""
        data = WatermarkProcessor.str_to_bin(watermark_json)
        data += '1111111111111110'  # EOF marker
        
        arr = np.array(img)
        flat = arr.flatten()
        
        if len(data) > len(flat):
            raise ValueError('Watermark data is too large for this image.')
            
        for i in range(len(data)):
            # Clear the least significant bit (LSB) and then set it
            flat[i] = (flat[i] & 0xFE) | int(data[i])
            
        arr = flat.reshape(arr.shape)
        return Image.fromarray(arr)

    @staticmethod
    def extract_watermark(img):
        """Extracts a watermark string from an image, if one exists."""
        arr = np.array(img)
        flat = arr.flatten()
        bits = []
        
        # Extract LSB from each pixel value
        # We can optimize this, but for clarity, we'll check a reasonable range.
        # A full image scan can be slow. Let's assume watermarks are in the first part.
        # A typical JSON watermark won't be millions of bits.
        # Let's check enough pixels for a decent-sized watermark (e.g., 4096 bytes * 8 bits)
        pixel_check_limit = min(len(flat), 4096 * 8 * 3) # ~4KB of data
        
        for i in range(pixel_check_limit):
            bits.append(str(flat[i] & 1))
            
        bits_str = ''.join(bits)
        eof = bits_str.find('1111111111111110')
        
        if eof == -1:
            # No EOF marker found
            return None
            
        data = bits_str[:eof]
        return WatermarkProcessor.bin_to_str(data)

    @staticmethod
    def get_image_download_link(img, filename):
        """Generate a download link for the image."""
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        href = f'<a href="data:image/png;base64,{img_str}" download="{filename}">Download {filename}</a>'
        return href


class WatermarkValidator:
    """Class for validating watermark data and user inputs"""
    
    @staticmethod
    def validate_embed_inputs(owner, passkey, confirm_passkey, uploaded_file):
        """Validate inputs for embedding watermark"""
        errors = []
        
        if not uploaded_file:
            errors.append("Please upload an image first.")
        
        if not owner:
            errors.append("Owner field is required.")
        
        if not passkey:
            errors.append("Passkey is required for security.")
        
        if passkey != confirm_passkey:
            errors.append("Passkeys do not match.")
            
        return errors
    
    @staticmethod
    def validate_resell_inputs(new_owner, new_passkey, confirm_new_passkey):
        """Validate inputs for reselling watermark"""
        errors = []
        
        # if not new_owner:
        #     errors.append("New owner field is required.")
        
        if not new_passkey:
            errors.append("New passkey is required.")
        
        if new_passkey != confirm_new_passkey:
            errors.append("New passkeys do not match.")
            
        return errors
    
    @staticmethod
    def validate_passkey_verification(passkey):
        """Validate passkey for verification"""
        if not passkey:
            return "Please enter a passkey."
        return None


class WatermarkDataManager:
    """Class for managing watermark data and session state"""
    
    @staticmethod
    def create_watermark_data(owner, buyer, datetime_str, passkey):
        """Create watermark data payload"""
        passkey_hash = hashlib.sha256(passkey.encode()).hexdigest()
        
        return {
            'owner': owner,
            'buyer': buyer,
            'datetime': datetime_str,
            'passkey_hash': passkey_hash
        }
    
    @staticmethod
    def create_resell_data(new_owner, new_buyer, new_passkey):
        """Create resell watermark data payload"""
        new_passkey_hash = hashlib.sha256(new_passkey.encode()).hexdigest()
        
        return {
            'owner': new_owner,
            'buyer': new_buyer,
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'passkey_hash': new_passkey_hash
        }
    
    @staticmethod
    def verify_passkey(passkey, stored_hash):
        """Verify passkey against stored hash"""
        provided_hash = hashlib.sha256(passkey.encode()).hexdigest()
        return provided_hash == stored_hash
    
    @staticmethod
    def parse_watermark_data(watermark_data):
        """Parse watermark data from JSON string"""
        try:
            return json.loads(watermark_data)
        except json.JSONDecodeError:
            return None


class ImageProcessor:
    """Class for handling image operations"""
    
    @staticmethod
    def load_image(uploaded_file):
        """Load and convert image to RGB"""
        return Image.open(uploaded_file).convert('RGB')
    
    @staticmethod
    def generate_image_hash(image):
        """Generate hash for image to detect changes"""
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        return hashlib.md5(image_bytes.getvalue()).hexdigest()
    
    @staticmethod
    def check_existing_watermark(image):
        """Check if image already has a watermark"""
        return WatermarkProcessor.extract_watermark(image)


class WatermarkService:
    """Main service class that orchestrates all watermark operations"""
    
    def __init__(self):
        self.processor = WatermarkProcessor()
        self.validator = WatermarkValidator()
        self.data_manager = WatermarkDataManager()
        self.image_processor = ImageProcessor()

         # Blockchain client - configure via env vars or defaults
        rpc = os.environ.get("RPC_URL", "http://127.0.0.1:7545")
        private_key = os.environ.get("PRIVATE_KEY")  # MUST be set or passed
        chain_id = None
        try:
            chain_id = int(os.environ.get("CHAIN_ID", "1337"))
        except:
            chain_id = None

        try:
            self.blockchain = BlockchainClient(rpc, private_key, chain_id)
            # Deploy contract if not yet deployed (or load previously deployed contract address)
            # Optionally you can set EXISTING_CONTRACT_ADDRESS env var to skip deploy.
            existing = os.environ.get("CONTRACT_ADDRESS")
            if existing:
                # If you have the ABI from compiled JSON you can load; but for simplicity, if a contract address
                # is provided we attempt to load the compiled ABI from the client's compile step.
                # If not compiled yet, compile and deploy locally.
                try:
                    # If we've not compiled yet, compile to get ABI
                    self.blockchain.compile_and_deploy(force_redeploy=False)
                    self.blockchain.load_contract(existing, self.blockchain.contract.abi)
                    self.blockchain.contract_address = existing
                except Exception:
                    # fallback to fresh deploy
                    self.blockchain.compile_and_deploy()
            else:
                # Deploy a fresh contract on this node
                self.blockchain.compile_and_deploy()
        except Exception as e:
            # If blockchain initialization fails, set to None and continue - watermarking still works offline
            print(f"[WARNING] Blockchain initialization failed: {e}")
            self.blockchain = None
    
    def embed_watermark(self, uploaded_file, owner, buyer, passkey, confirm_passkey, datetime_str):
        """Embed watermark into image"""
        # Validate inputs
        errors = self.validator.validate_embed_inputs(owner, passkey, confirm_passkey, uploaded_file)
        if errors:
            return None, errors
        
        try:
            # Load image
            image = self.image_processor.load_image(uploaded_file)
            
            # Create watermark data
            data = self.data_manager.create_watermark_data(owner, buyer, datetime_str, passkey)
            
            # Embed watermark
            watermarked_image = self.processor.embed_watermark(image, json.dumps(data))
            
                        # Embed watermark
            watermarked_image = self.processor.embed_watermark(image, json.dumps(data))

            # Compute watermark hash (we already stored passkey_hash in data)
            # Use SHA256 of the watermark JSON string as canonical watermark hash
            watermark_json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            watermark_hash = hashlib.sha256(watermark_json_str.encode()).hexdigest()

            # Prepare token metadata
            metadata = {
                "name": f"WatermarkedArt - {data.get('owner','unknown')}",
                "description": "Invisible watermark record for digital artwork",
                "owner": data.get('owner'),
                "buyer": data.get('buyer'),
                "datetime": data.get('datetime'),
                "watermark_hash": watermark_hash
            }

            token_uri = metadata_to_data_uri(metadata)

            blockchain_result = None
            if self.blockchain:
                try:
                    # Mint to buyer address? We don't have addresses for users in the current app.
                    # For simplicity, mint the NFT to the deployer address (self.blockchain.address).
                    # In production you'd add user wallet connect and pass a recipient address.
                    recipient = self.blockchain.address
                    mint_resp = self.blockchain.mint_nft(recipient, token_uri, watermark_hash)
                    blockchain_result = mint_resp
                except Exception as e:
                    # Non-fatal: watermark embedding succeeded; blockchain mint failed
                    blockchain_result = {"error": str(e)}

            return watermarked_image, blockchain_result

            
        except Exception as e:
            return None, [f"Failed to embed watermark: {e}"]
    
    def extract_watermark(self, uploaded_file):
        """Extract watermark from image"""
        if not uploaded_file:
            return None, ["Please upload an image first."]
        
        try:
            # Load image
            image = self.image_processor.load_image(uploaded_file)
            
            # Extract watermark
            watermark_data = self.processor.extract_watermark(image)
            
            if watermark_data:
                # Parse watermark data
                data = self.data_manager.parse_watermark_data(watermark_data)
                if data:
                    return data, None
                else:
                    return "corrupted", None
            else:
                return None, None
                
        except Exception as e:
            return None, [f"Error extracting watermark: {e}"]
    
    def resell_watermark(self, uploaded_file, new_owner, new_buyer, new_passkey, confirm_new_passkey):
        """Resell/update watermark"""
        # Validate inputs
        errors = self.validator.validate_resell_inputs(new_owner, new_passkey, confirm_new_passkey)
        if errors:
            return None, errors
        
        try:
            # Load image
            image = self.image_processor.load_image(uploaded_file)
            
            # Create new watermark data
            new_data = self.data_manager.create_resell_data(new_owner, new_buyer, new_passkey)
            
            # Embed new watermark
            updated_image = self.processor.embed_watermark(image, json.dumps(new_data))
            
            return updated_image, None
            
        except Exception as e:
            return None, [f"Failed to update watermark: {e}"]
    
    def verify_resell_passkey(self, passkey, existing_watermark):
        """Verify passkey for reselling"""
        error = self.validator.validate_passkey_verification(passkey)
        if error:
            return False, error
        
        if not existing_watermark.get('passkey_hash'):
            return True, None
        
        is_valid = self.data_manager.verify_passkey(passkey, existing_watermark.get('passkey_hash'))
        if is_valid:
            return True, None
        else:
            return False, "Invalid passkey. Cannot resell this image."
    
    def get_download_link(self, image, filename):
        """Get download link for image"""
        return self.processor.get_image_download_link(image, filename)
