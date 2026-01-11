from flask import Flask, request, jsonify, render_template, Response
from e2b_code_interpreter import Sandbox
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
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    try:
        with Sandbox() as sandbox:
            # Install yt-dlp
            sandbox.run_code("import subprocess; subprocess.run(['pip', 'install', 'yt-dlp'], check=True)")
            
            # Download video
            if format_type == 'mp3':
                code = f"""
import subprocess
result = subprocess.run([
    'yt-dlp', '-x', '--audio-format', 'mp3', 
    '-o', '%(title)s.%(ext)s', '{url}'
], capture_output=True, text=True)
print("Exit code:", result.returncode)
if result.returncode == 0:
    print("SUCCESS: Video downloaded")
else:
    print("ERROR:", result.stderr)
"""
            else:
                code = f"""
import subprocess
result = subprocess.run([
    'yt-dlp', '-f', '{quality}', 
    '-o', '%(title)s.%(ext)s', '{url}'
], capture_output=True, text=True)
print("Exit code:", result.returncode)
if result.returncode == 0:
    print("SUCCESS: Video downloaded")
else:
    print("ERROR:", result.stderr)
"""
            
            result = sandbox.run_code(code)
            
            if "SUCCESS: Video downloaded" in result.text:
                return jsonify({'success': True, 'message': 'Video downloaded successfully'})
            else:
                return jsonify({'error': 'Download failed', 'details': result.text}), 400
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
                sandbox.run_code("import subprocess; subprocess.run(['pip', 'install', 'yt-dlp'], check=True)")
                
                # Get playlist info
                info_code = f"""
import subprocess
result = subprocess.run([
    'yt-dlp', '--flat-playlist', '--dump-json', '{url}'
], capture_output=True, text=True)
print("PLAYLIST_INFO:", len(result.stdout.strip().split('\\n')) if result.stdout.strip() else 0)
"""
                info_result = sandbox.run_code(info_code)
                
                # Extract total videos from output
                total_videos = 3  # Default fallback
                for line in info_result.text.split('\n'):
                    if 'PLAYLIST_INFO:' in line:
                        try:
                            total_videos = int(line.split(':')[1].strip())
                        except:
                            pass
                
                progress_data[task_id] = {'status': 'downloading', 'current': 0, 'total': total_videos}
                
                # Download playlist
                if format_type == 'mp3':
                    download_code = f"""
import subprocess
result = subprocess.run([
    'yt-dlp', '--yes-playlist', '-x', '--audio-format', 'mp3', 
    '-o', '%(title)s.%(ext)s', '{url}'
], capture_output=True, text=True)
print("Download exit code:", result.returncode)
if result.returncode == 0:
    print("DOWNLOAD_SUCCESS")
else:
    print("DOWNLOAD_ERROR:", result.stderr)
"""
                else:
                    download_code = f"""
import subprocess
result = subprocess.run([
    'yt-dlp', '--yes-playlist', '-f', 'best', 
    '-o', '%(title)s.%(ext)s', '{url}'
], capture_output=True, text=True)
print("Download exit code:", result.returncode)
if result.returncode == 0:
    print("DOWNLOAD_SUCCESS")
else:
    print("DOWNLOAD_ERROR:", result.stderr)
"""
                
                result = sandbox.run_code(download_code)
                
                if "DOWNLOAD_SUCCESS" in result.text:
                    progress_data[task_id] = {'status': 'ready', 'current': total_videos, 'total': total_videos, 'message': 'Playlist downloaded successfully'}
                else:
                    progress_data[task_id] = {'status': 'error', 'message': f'Download failed: {result.text}'}
                    
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
