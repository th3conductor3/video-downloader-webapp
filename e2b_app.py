from flask import Flask, request, jsonify, render_template, Response
from e2b import Sandbox
import json
import uuid
import threading
import time

app = Flask(__name__)
progress_data = {}

# Set your E2B API key
import os
os.environ['E2B_API_KEY'] = 'e2b_9a04d473954f7de0f11bbaa76f3043aead685542'

@app.route('/')
def home():
    return render_template('combined_ui.html')

@app.route('/download_youtube', methods=['POST'])
def download_youtube():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    format_type = data.get('format', 'mp4')
    
    with Sandbox() as sandbox:
        # Install yt-dlp
        sandbox.commands.run("pip install yt-dlp")
        
        # Download video
        if format_type == 'mp3':
            cmd = f'yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" "{url}"'
        else:
            cmd = f'yt-dlp -f "{quality}" -o "%(title)s.%(ext)s" "{url}"'
        
        result = sandbox.commands.run(cmd)
        
        if result.exit_code == 0:
            # List files and return the first video/audio file
            files = sandbox.filesystem.list(".")
            for file in files:
                if file.name.endswith(('.mp4', '.mp3', '.webm')):
                    file_content = sandbox.filesystem.read(file.name, format="bytes")
                    return file_content, 200, {
                        'Content-Type': 'application/octet-stream',
                        'Content-Disposition': f'attachment; filename="{file.name}"'
                    }
        
        return jsonify({'error': result.stderr}), 400

@app.route('/download_youtube_playlist', methods=['POST'])
def download_youtube_playlist():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    format_type = data.get('format', 'mp4')
    
    task_id = str(uuid.uuid4())
    progress_data[task_id] = {'status': 'starting', 'current': 0, 'total': 0}
    
    def download_playlist():
        try:
            with Sandbox() as sandbox:
                progress_data[task_id] = {'status': 'installing', 'current': 0, 'total': 0}
                
                # Install yt-dlp
                sandbox.commands.run("pip install yt-dlp")
                
                # Get playlist info
                info_result = sandbox.commands.run(f'yt-dlp --flat-playlist --dump-json "{url}"')
                total_videos = len([line for line in info_result.stdout.split('\n') if line.strip()])
                
                progress_data[task_id] = {'status': 'downloading', 'current': 0, 'total': total_videos}
                
                # Download playlist
                if format_type == 'mp3':
                    cmd = f'yt-dlp --yes-playlist -x --audio-format mp3 -o "%(title)s.%(ext)s" "{url}"'
                else:
                    if quality == 'best':
                        cmd = f'yt-dlp --yes-playlist -f "best" -o "%(title)s.%(ext)s" "{url}"'
                    else:
                        cmd = f'yt-dlp --yes-playlist -f "best[height<={quality[:-1]}]" -o "%(title)s.%(ext)s" "{url}"'
                
                result = sandbox.commands.run(cmd)
                
                if result.exit_code == 0:
                    progress_data[task_id] = {'status': 'zipping', 'current': total_videos, 'total': total_videos}
                    
                    # Create zip
                    sandbox.commands.run("zip -r playlist.zip *.mp4 *.mp3 *.webm *.mkv 2>/dev/null || true")
                    
                    # Read zip file
                    try:
                        zip_content = sandbox.filesystem.read("playlist.zip", format="bytes")
                        progress_data[task_id] = {'status': 'ready', 'file_content': zip_content, 'current': total_videos, 'total': total_videos}
                    except:
                        progress_data[task_id] = {'status': 'error', 'message': 'Failed to create zip file'}
                else:
                    progress_data[task_id] = {'status': 'error', 'message': result.stderr}
                    
        except Exception as e:
            progress_data[task_id] = {'status': 'error', 'message': str(e)}
    
    threading.Thread(target=download_playlist).start()
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def progress(task_id):
    if task_id in progress_data:
        data = progress_data[task_id].copy()
        # Don't send file content in progress updates
        if 'file_content' in data:
            del data['file_content']
        return jsonify(data)
    return jsonify({'status': 'not_found'}), 404

@app.route('/download_file/<task_id>')
def download_file(task_id):
    if task_id in progress_data and progress_data[task_id].get('status') == 'ready':
        file_content = progress_data[task_id]['file_content']
        del progress_data[task_id]  # Cleanup
        
        return Response(
            file_content,
            mimetype='application/zip',
            headers={'Content-Disposition': 'attachment; filename=playlist.zip'}
        )
    return jsonify({'error': 'File not ready'}), 400

if __name__ == '__main__':
    app.run(debug=True)
