#!/usr/bin/env python3
"""
Complete Email to PDF Converter with Gmail-style formatting
Handles .eml and .msg files with recursive attachment processing
"""

import email
from email import policy
from email.parser import BytesParser
import json
import os
import tempfile
from datetime import datetime
import base64
from PyPDF2 import PdfMerger
import extract_msg
from weasyprint import HTML, CSS
from pathlib import Path

# Gmail-style CSS for email rendering
GMAIL_STYLE = """
<style>
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 20px;
        background-color: #f5f5f5;
    }
    .email-container {
        max-width: 800px;
        margin: 0 auto;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        border-radius: 2px;
    }
    .email-header {
        padding: 20px 24px;
        border-bottom: 1px solid #e0e0e0;
    }
    .email-subject {
        font-size: 20px;
        font-weight: 400;
        color: #202124;
        margin: 0 0 16px 0;
    }
    .email-meta {
        font-size: 12px;
        color: #5f6368;
    }
    .email-meta-row {
        margin: 4px 0;
        display: flex;
    }
    .email-meta-label {
        font-weight: 500;
        min-width: 60px;
        color: #202124;
    }
    .email-meta-value {
        color: #5f6368;
        word-break: break-word;
    }
    .email-body {
        padding: 24px;
        font-size: 14px;
        line-height: 1.6;
        color: #202124;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .email-attachments {
        padding: 16px 24px;
        border-top: 1px solid #e0e0e0;
        background-color: #f8f9fa;
    }
    .attachments-title {
        font-size: 13px;
        font-weight: 500;
        color: #5f6368;
        margin-bottom: 12px;
    }
    .attachment-item {
        display: inline-block;
        padding: 8px 12px;
        margin: 4px 8px 4px 0;
        background-color: white;
        border: 1px solid #dadce0;
        border-radius: 4px;
        font-size: 13px;
        color: #202124;
    }
    .attachment-icon {
        display: inline-block;
        width: 16px;
        height: 16px;
        margin-right: 8px;
        vertical-align: middle;
    }
    .gmail-logo {
        color: #ea4335;
        font-size: 11px;
        text-align: right;
        padding: 8px 24px;
        color: #5f6368;
    }
</style>
"""

def parse_eml_file(file_path):
    """Parse .eml file and extract all data including attachments"""
    print(f"📧 Parsing .eml file: {file_path}")
    
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    email_data = {
        'from': str(msg.get('From', '')),
        'to': str(msg.get('To', '')),
        'cc': str(msg.get('CC', '')),
        'subject': str(msg.get('Subject', '')),
        'date': str(msg.get('Date', '')),
        'body_text': '',
        'body_html': '',
        'attachments': []
    }
    
    # Extract body and attachments
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" in disposition or part.get_filename():
                filename = part.get_filename()
                if filename:
                    # Save attachment to temp file
                    temp_dir = tempfile.mkdtemp()
                    attachment_path = os.path.join(temp_dir, filename)
                    
                    try:
                        with open(attachment_path, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        
                        email_data['attachments'].append({
                            'filename': filename,
                            'path': attachment_path,
                            'content_type': content_type,
                            'size': os.path.getsize(attachment_path)
                        })
                        print(f"  📎 Found attachment: {filename}")
                    except Exception as e:
                        print(f"  ⚠️  Could not extract attachment {filename}: {e}")
                        
            elif content_type == "text/plain" and not email_data['body_text']:
                try:
                    email_data['body_text'] = part.get_content()
                except:
                    pass
            elif content_type == "text/html" and not email_data['body_html']:
                try:
                    email_data['body_html'] = part.get_content()
                except:
                    pass
    else:
        try:
            email_data['body_text'] = msg.get_content()
        except:
            pass
    
    return email_data

def parse_msg_file(file_path):
    """Parse .msg file and extract all data including attachments"""
    print(f"📧 Parsing .msg file: {file_path}")
    
    msg = extract_msg.Message(file_path)
    
    email_data = {
        'from': msg.sender or '',
        'to': msg.to or '',
        'cc': msg.cc or '',
        'subject': msg.subject or '',
        'date': str(msg.date) if msg.date else '',
        'body_text': msg.body or '',
        'body_html': msg.htmlBody or '',
        'attachments': []
    }
    
    # Extract attachments
    temp_dir = tempfile.mkdtemp()
    for attachment in msg.attachments:
        filename = attachment.longFilename or attachment.shortFilename or 'unknown'
        attachment_path = os.path.join(temp_dir, filename)
        
        try:
            with open(attachment_path, 'wb') as f:
                f.write(attachment.data)
            
            email_data['attachments'].append({
                'filename': filename,
                'path': attachment_path,
                'content_type': 'application/octet-stream',
                'size': os.path.getsize(attachment_path)
            })
            print(f"  📎 Found attachment: {filename}")
        except Exception as e:
            print(f"  ⚠️  Could not extract attachment {filename}: {e}")
    
    msg.close()
    return email_data

def create_gmail_html(email_data):
    """Create Gmail-style HTML for the email"""
    
    # Format date nicely
    date_str = email_data['date']
    
    # Use body_text or strip HTML from body_html
    body_content = email_data['body_text']
    if not body_content and email_data['body_html']:
        import re
        body_content = re.sub('<[^<]+?>', '', email_data['body_html'])
    
    # Escape HTML special characters in body
    body_content = (body_content or 'No content')
    body_content = body_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Build attachments section
    attachments_html = ''
    if email_data['attachments']:
        attachments_html = '<div class="email-attachments">'
        attachments_html += '<div class="attachments-title">Attachments</div>'
        for att in email_data['attachments']:
            size_kb = att['size'] / 1024
            attachments_html += f'<div class="attachment-item">📎 {att["filename"]} ({size_kb:.1f} KB)</div>'
        attachments_html += '</div>'
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    {GMAIL_STYLE}
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <div class="email-subject">{email_data['subject']}</div>
            <div class="email-meta">
                <div class="email-meta-row">
                    <span class="email-meta-label">From:</span>
                    <span class="email-meta-value">{email_data['from']}</span>
                </div>
                <div class="email-meta-row">
                    <span class="email-meta-label">To:</span>
                    <span class="email-meta-value">{email_data['to']}</span>
                </div>
                {f'<div class="email-meta-row"><span class="email-meta-label">Cc:</span><span class="email-meta-value">{email_data["cc"]}</span></div>' if email_data['cc'] else ''}
                <div class="email-meta-row">
                    <span class="email-meta-label">Date:</span>
                    <span class="email-meta-value">{date_str}</span>
                </div>
            </div>
        </div>
        <div class="email-body">{body_content}</div>
        {attachments_html}
        <div class="gmail-logo">Generated from email file</div>
    </div>
</body>
</html>
"""
    return html

def convert_html_to_pdf(html_content, output_path):
    """Convert HTML to PDF using WeasyPrint"""
    print(f"  🔄 Converting HTML to PDF: {output_path}")
    HTML(string=html_content).write_pdf(output_path)
    print(f"  ✓ PDF created: {os.path.getsize(output_path)} bytes")

def convert_attachment_to_pdf(attachment_path, output_pdf_path):
    """Convert various file types to PDF"""
    filename = os.path.basename(attachment_path)
    ext = os.path.splitext(filename)[1].lower()
    
    print(f"  🔄 Converting attachment to PDF: {filename}")
    
    try:
        if ext in ['.eml', '.msg']:
            # Recursively process email attachments
            if ext == '.eml':
                nested_email = parse_eml_file(attachment_path)
            else:
                nested_email = parse_msg_file(attachment_path)
            
            html = create_gmail_html(nested_email)
            convert_html_to_pdf(html, output_pdf_path)
            return True
            
        elif ext == '.pdf':
            # Already a PDF, just copy it
            import shutil
            shutil.copy(attachment_path, output_pdf_path)
            return True
            
        elif ext in ['.txt', '.log', '.csv']:
            # Text files - create simple PDF
            with open(attachment_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: monospace; padding: 20px; font-size: 10px; white-space: pre-wrap; }}
        h1 {{ font-size: 14px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>{filename}</h1>
    <pre>{content[:10000]}</pre>
</body>
</html>
"""
            HTML(string=html).write_pdf(output_pdf_path)
            return True
            
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            # Image files
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ margin: 0; padding: 20px; text-align: center; }}
        h1 {{ font-size: 14px; margin-bottom: 20px; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>{filename}</h1>
    <img src="file://{attachment_path}" />
</body>
</html>
"""
            HTML(string=html).write_pdf(output_pdf_path)
            return True
            
        else:
            # Unsupported file type - create placeholder PDF
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial; padding: 40px; text-align: center; }}
        h1 {{ color: #666; }}
        p {{ color: #999; }}
    </style>
</head>
<body>
    <h1>📄 {filename}</h1>
    <p>File type: {ext}</p>
    <p>This file type cannot be converted to PDF automatically.</p>
</body>
</html>
"""
            HTML(string=html).write_pdf(output_pdf_path)
            return True
            
    except Exception as e:
        print(f"  ⚠️  Error converting {filename}: {e}")
        # Create error placeholder PDF
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial; padding: 40px; text-align: center; }}
        h1 {{ color: #d32f2f; }}
        p {{ color: #666; }}
    </style>
</head>
<body>
    <h1>⚠️ {filename}</h1>
    <p>Error converting file: {str(e)[:200]}</p>
</body>
</html>
"""
        HTML(string=html).write_pdf(output_pdf_path)
        return False

def merge_pdfs(pdf_list, output_path):
    """Merge multiple PDFs into one"""
    print(f"\n📦 Merging {len(pdf_list)} PDFs...")
    
    merger = PdfMerger()
    
    for pdf_path in pdf_list:
        if os.path.exists(pdf_path):
            print(f"  ➕ Adding: {os.path.basename(pdf_path)}")
            merger.append(pdf_path)
    
    merger.write(output_path)
    merger.close()
    
    print(f"✓ Merged PDF created: {output_path}")
    print(f"  Size: {os.path.getsize(output_path)} bytes")

def process_email_to_pdf(email_file_path, output_pdf_path):
    """
    Main function to process email and all attachments to PDF
    """
    
    print("="*80)
    print("📧 EMAIL TO PDF CONVERTER (Gmail Style)")
    print("="*80)
    print()
    
    # Step 1: Parse email - detect file type from extension or content
    ext = os.path.splitext(email_file_path)[1].lower()
    
    # If no extension, try to detect from content
    if not ext:
        with open(email_file_path, 'rb') as f:
            header = f.read(10)
        if header.startswith(b'\xD0\xCF\x11\xE0'):
            ext = '.msg'
        else:
            ext = '.eml'  # Default to .eml
    
    if ext == '.eml':
        email_data = parse_eml_file(email_file_path)
    elif ext == '.msg':
        email_data = parse_msg_file(email_file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    print(f"\n✓ Email parsed successfully")
    print(f"  Subject: {email_data['subject']}")
    print(f"  From: {email_data['from']}")
    print(f"  Attachments: {len(email_data['attachments'])}")
    
    # Step 2: Create Gmail-style HTML and convert to PDF
    print(f"\n📄 Creating Gmail-style PDF for email...")
    html = create_gmail_html(email_data)
    
    temp_dir = tempfile.mkdtemp()
    email_pdf_path = os.path.join(temp_dir, '00_email.pdf')
    convert_html_to_pdf(html, email_pdf_path)
    
    # Step 3: Convert all attachments to PDF
    pdf_list = [email_pdf_path]
    
    if email_data['attachments']:
        print(f"\n📎 Processing {len(email_data['attachments'])} attachments...")
        
        # Sort attachments alphabetically
        sorted_attachments = sorted(email_data['attachments'], key=lambda x: x['filename'].lower())
        
        for idx, att in enumerate(sorted_attachments, start=1):
            att_pdf_path = os.path.join(temp_dir, f'{idx:02d}_{att["filename"]}.pdf')
            
            if convert_attachment_to_pdf(att['path'], att_pdf_path):
                pdf_list.append(att_pdf_path)
    
    # Step 4: Merge all PDFs
    merge_pdfs(pdf_list, output_pdf_path)
    
    print(f"\n{'='*80}")
    print(f"✅ SUCCESS! Combined PDF created: {output_pdf_path}")
    print(f"{'='*80}")
    
    return {
        'success': True,
        'output_path': output_pdf_path,
        'email_subject': email_data['subject'],
        'email_from': email_data['from'],
        'attachment_count': len(email_data['attachments']),
        'total_pages': len(pdf_list)
    }

# Main function is now imported by Flask app
# Can still be run as standalone script if needed
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python email_processor.py <email_file> <output_pdf>")
        sys.exit(1)
    
    email_file = sys.argv[1]
    output_pdf = sys.argv[2]
    
    try:
        result = process_email_to_pdf(email_file, output_pdf)
        print(f"\n✓ Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
