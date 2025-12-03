# Invisible Watermark Tool

A secure watermarking application that uses LSB (Least Significant Bit) steganography to embed invisible watermarks into images.

## Project Structure

The application has been separated into frontend and backend components for better maintainability:

```
mini_project/
├── app.py              # Main application entry point
├── frontend.py         # Streamlit UI components and page layouts
├── backend.py          # Watermark processing logic and business logic
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── streamlit_app.py   # Original monolithic file (kept for reference)
```

## Architecture

### Backend (`backend.py`)

Contains all the business logic and watermark processing:

- `WatermarkProcessor`: Core LSB steganography operations
- `WatermarkValidator`: Input validation logic
- `WatermarkDataManager`: Data management and passkey handling
- `ImageProcessor`: Image loading and processing utilities
- `WatermarkService`: Main service orchestrator

### Frontend (`frontend.py`)

Contains all UI components and page layouts:

- `UIComponents`: Reusable UI components and styling
- `EmbedWatermarkPage`: Embed watermark page logic
- `ExtractWatermarkPage`: Extract watermark page logic
- `AboutPage`: About page content

### Main App (`app.py`)

Connects frontend and backend components and handles routing.

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
streamlit run app.py
```

## Features

- **🔒 Secure Watermarking**: Uses LSB steganography for invisible watermarks
- **🔑 Passkey Protection**: Secure passkey system for reselling protection
- **📝 Ownership Tracking**: Track owner and buyer information
- **⏰ Timestamping**: Automatic date/time stamping
- **🔍 Verification**: Extract and verify existing watermarks
- **🔄 Resell Functionality**: Update ownership details with original passkey
- **📱 Modern Web Interface**: Clean, responsive Streamlit interface

## Security Features

- **Passkey Hashing**: Passkeys are hashed using SHA-256, never stored in plain text
- **Resell Protection**: Only users with the original passkey can resell watermarked images
- **Data Integrity**: Watermarks include EOF markers for reliable extraction
- **Session Management**: Secure session handling prevents unauthorized access

## Migration from Original

The original `streamlit_app.py` file has been preserved for reference. All functionalities remain exactly the same - only the code structure has been improved for better maintainability and separation of concerns.
