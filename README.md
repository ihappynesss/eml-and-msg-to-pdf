# Email to PDF Converter API

A Flask-based REST API service that converts email files (.eml, .msg) to Gmail-style PDF documents with all attachments extracted, converted, and merged into a single PDF file.

## Features

- ✅ Parses .eml and .msg email files
- ✅ Gmail-style PDF formatting
- ✅ Extracts all attachments
- ✅ Converts attachments to PDF (images, text files, PDFs, nested emails)
- ✅ Merges everything into a single PDF (email first, attachments alphabetically)
- ✅ Returns PDF as base64 or downloadable file
- ✅ Supports Google Drive file IDs

## API Endpoints

### `GET /`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "Email to PDF Converter",
  "version": "1.0.0"
}
```

### `POST /convert`
Convert email file to PDF and return as base64.

**Request Body:**
```json
{
  "fileUrl": "https://example.com/email.eml"
}
```

Or use Google Drive file ID:
```json
{
  "googleDriveFileId": "165Onx_d_9dejfB-2PVzLiP23JO2aPey7"
}
```

**Response:**
```json
{
  "success": true,
  "pdfBase64": "JVBERi0xLjcKCjEgMCBvYmo...",
  "fileName": "email_printout_abc123.pdf",
  "emailSubject": "Meeting Notes",
  "emailFrom": "sender@example.com",
  "attachmentCount": 5,
  "totalPages": 12,
  "fileSize": 245678
}
```

### `POST /convert/download`
Convert email file to PDF and return as downloadable file.

**Request Body:**
```json
{
  "fileUrl": "https://example.com/email.eml"
}
```

**Response:**
PDF file download

## Deployment to Railway

### Prerequisites
- Railway account (https://railway.app)
- Git installed locally

### Step 1: Prepare the Project

1. Clone or download this repository
2. Navigate to the project directory:
   ```bash
   cd railway-email-to-pdf
   ```

### Step 2: Deploy to Railway

#### Option A: Deploy from GitHub

1. Push this code to a GitHub repository
2. Go to [Railway](https://railway.app)
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Select your repository
6. Railway will automatically detect the Dockerfile and deploy

#### Option B: Deploy using Railway CLI

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login to Railway:
   ```bash
   railway login
   ```

3. Initialize and deploy:
   ```bash
   railway init
   railway up
   ```

### Step 3: Get Your API URL

After deployment, Railway will provide you with a public URL like:
```
https://your-app-name.up.railway.app
```

### Step 4: Test the API

Test the health check endpoint:
```bash
curl https://your-app-name.up.railway.app/
```

Test the conversion endpoint:
```bash
curl -X POST https://your-app-name.up.railway.app/convert \
  -H "Content-Type: application/json" \
  -d '{"fileUrl": "https://example.com/email.eml"}'
```

## Using with n8n

Once deployed on Railway, you can use this API in n8n workflows:

1. Add an **HTTP Request** node
2. Set **Method** to `POST`
3. Set **URL** to `https://your-app-name.up.railway.app/convert`
4. Set **Body Content Type** to `JSON`
5. Add the request body:
   ```json
   {
     "fileUrl": "{{ $json.emailFileUrl }}"
   }
   ```
6. The response will contain the PDF as base64 in `pdfBase64` field

## Local Development

### Run Locally with Docker

```bash
docker build -t email-to-pdf .
docker run -p 8080:8080 email-to-pdf
```

### Run Locally with Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app/main.py
```

The API will be available at `http://localhost:8080`

## Environment Variables

- `PORT`: Port to run the server on (default: 8080)

## Project Structure

```
railway-email-to-pdf/
├── app/
│   ├── main.py              # Flask application
│   └── email_processor.py   # Email parsing and PDF conversion logic
├── Dockerfile               # Docker configuration
├── requirements.txt         # Python dependencies
├── .dockerignore           # Docker ignore file
└── README.md               # This file
```

## Troubleshooting

### Google Drive Files Not Downloading

If you're using Google Drive file IDs, ensure:
1. The file is shared with "Anyone with the link can view"
2. The file ID is correct
3. Use the constructed URL format: `https://drive.google.com/uc?export=download&id=FILE_ID`

### PDF Generation Errors

If PDF generation fails:
1. Check the email file format is valid (.eml or .msg)
2. Ensure the file is publicly accessible
3. Check Railway logs for detailed error messages

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.
