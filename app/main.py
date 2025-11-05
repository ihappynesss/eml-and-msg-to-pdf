"""
Email to PDF Converter API
Flask application for Railway deployment
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import requests
from email_processor import process_email_to_pdf
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
PORT = int(os.environ.get('PORT', 8080))

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Email to PDF Converter',
        'version': '1.0.0'
    })

@app.route('/convert', methods=['POST'])
def convert_email_to_pdf():
    """
    Convert email file to Gmail-style PDF
    
    Request body:
    {
        "fileUrl": "https://example.com/email.eml",
        "googleDriveFileId": "optional_file_id"  // Alternative to fileUrl
    }
    
    Returns:
    {
        "success": true,
        "pdfBase64": "...",
        "fileName": "email_printout_123456.pdf",
        "emailSubject": "...",
        "emailFrom": "...",
        "attachmentCount": 5,
        "totalPages": 12,
        "fileSize": 245678
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Get file URL or Google Drive file ID
        file_url = data.get('fileUrl')
        gdrive_file_id = data.get('googleDriveFileId')
        
        if not file_url and not gdrive_file_id:
            return jsonify({
                'success': False,
                'error': 'Either fileUrl or googleDriveFileId must be provided'
            }), 400
        
        # If Google Drive file ID is provided, construct the download URL
        if gdrive_file_id:
            file_url = f"https://drive.google.com/uc?export=download&id={gdrive_file_id}"
        
        logger.info(f"Processing email from URL: {file_url}")
        
        # Download the file
        temp_email_path = os.path.join(tempfile.gettempdir(), f'email_{os.urandom(8).hex()}')
        
        response = requests.get(file_url, stream=True, timeout=30)
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Failed to download file: HTTP {response.status_code}'
            }), 400
        
        with open(temp_email_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded file: {os.path.getsize(temp_email_path)} bytes")
        
        # Check if we got HTML instead of the actual file
        with open(temp_email_path, 'rb') as f:
            header = f.read(100)
        
        if header.startswith(b'<!DOCTYPE html>') or header.startswith(b'<html'):
            os.unlink(temp_email_path)
            return jsonify({
                'success': False,
                'error': 'Received HTML page instead of email file. Please ensure the file is publicly accessible and the URL is a direct download link.'
            }), 400
        
        # Process the email
        output_pdf_path = os.path.join(tempfile.gettempdir(), f'output_{os.urandom(8).hex()}.pdf')
        
        result = process_email_to_pdf(temp_email_path, output_pdf_path)
        
        if not result['success']:
            # Clean up
            try:
                os.unlink(temp_email_path)
            except:
                pass
            return jsonify(result), 500
        
        # Read the PDF and encode as base64
        import base64
        with open(output_pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Clean up temp files
        try:
            os.unlink(temp_email_path)
            os.unlink(output_pdf_path)
        except:
            pass
        
        logger.info(f"Conversion successful: {len(pdf_data)} bytes")
        
        return jsonify({
            'success': True,
            'pdfBase64': pdf_base64,
            'fileName': f'email_printout_{os.urandom(4).hex()}.pdf',
            'emailSubject': result.get('email_subject', ''),
            'emailFrom': result.get('email_from', ''),
            'attachmentCount': result.get('attachment_count', 0),
            'totalPages': result.get('total_pages', 0),
            'fileSize': len(pdf_data)
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/convert/download', methods=['POST'])
def convert_and_download():
    """
    Convert email file to PDF and return as downloadable file
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        file_url = data.get('fileUrl')
        gdrive_file_id = data.get('googleDriveFileId')
        
        if not file_url and not gdrive_file_id:
            return jsonify({
                'success': False,
                'error': 'Either fileUrl or googleDriveFileId must be provided'
            }), 400
        
        if gdrive_file_id:
            file_url = f"https://drive.google.com/uc?export=download&id={gdrive_file_id}"
        
        # Download the file
        temp_email_path = os.path.join(tempfile.gettempdir(), f'email_{os.urandom(8).hex()}')
        
        response = requests.get(file_url, stream=True, timeout=30)
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Failed to download file: HTTP {response.status_code}'
            }), 400
        
        with open(temp_email_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Process the email
        output_pdf_path = os.path.join(tempfile.gettempdir(), f'output_{os.urandom(8).hex()}.pdf')
        
        result = process_email_to_pdf(temp_email_path, output_pdf_path)
        
        if not result['success']:
            try:
                os.unlink(temp_email_path)
            except:
                pass
            return jsonify(result), 500
        
        # Return the PDF file
        return send_file(
            output_pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='email_printout.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
