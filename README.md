# Video Downloader Webapp

A modern web application for downloading videos from YouTube and Instagram using E2B sandboxes for secure, scalable execution.

## Features

- **YouTube Downloads**: Single videos and playlists with quality/format selection
- **Instagram Downloads**: Profile videos and single posts
- **Real-time Progress**: Live download progress tracking
- **Secure Execution**: Uses E2B sandboxes for isolated, secure downloads
- **Scalable**: Serverless deployment ready

## Deployment

### Railway (Recommended)
1. Fork this repository
2. Connect to Railway
3. Set environment variable: `E2B_API_KEY=your_key_here`
4. Deploy automatically

### Vercel
1. Fork this repository  
2. Connect to Vercel
3. Set environment variable: `E2B_API_KEY=your_key_here`
4. Deploy

### Render
1. Fork this repository
2. Create new Web Service
3. Set environment variable: `E2B_API_KEY=your_key_here`
4. Deploy

## Local Development

```bash
pip install -r requirements.txt
export E2B_API_KEY=your_key_here
python e2b_app.py
```

## Environment Variables

- `E2B_API_KEY`: Your E2B API key (required)

## Tech Stack

- **Backend**: Flask, E2B SDK
- **Frontend**: HTML, CSS, JavaScript
- **Execution**: E2B Sandboxes with yt-dlp and instaloader

## Security

All downloads run in isolated E2B sandboxes, ensuring:
- No server-side file storage
- Secure code execution
- User isolation
- Automatic cleanup
