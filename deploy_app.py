from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import os
import tempfile
import zipfile
import shutil
import json
import threading
import time
import re
import uuid

app = Flask(__name__)
progress_data = {}

# Get the directory where the app is running
APP_DIR = os.path.dirname(os.path.abspath(__file__))

def create_user_temp_dir():
    """Create a unique temporary directory for each user session"""
    return tempfile.mkdtemp(dir=APP_DIR, prefix=f'user_{uuid.uuid4().hex[:8]}_')

def cleanup_temp_dir(temp_dir):
    """Safely cleanup temporary directory"""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except:
        pass

@app.route('/')
def home():
    return render_template('combined_ui.html')

@app.route('/progress/<task_id>')
def progress(task_id):
    if task_id in progress_data:
        return jsonify(progress_data[task_id])
    return jsonify({'status': 'not_found'}), 404

@app.route('/download_youtube', methods=['POST'])
def download_youtube():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    format_type = data.get('format', 'mp4')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    temp_dir = None
    try:
        temp_dir = create_user_temp_dir()
        
        if format_type == 'mp3':
            cmd = f'yt-dlp --no-warnings -x --audio-format mp3 -o "{temp_dir}/%(title)s.%(ext)s" "{url}"'
        else:
            cmd = f'yt-dlp --no-warnings -f "{quality}" -o "{temp_dir}/%(title)s.%(ext)s" "{url}"'
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            files = os.listdir(temp_dir)
            if files:
                file_path = os.path.join(temp_dir, files[0])
                return send_file(file_path, as_attachment=True)
        
        return jsonify({'error': result.stderr}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)

@app.route('/download_instagram', methods=['POST'])
def download_instagram():
    data = request.json
    username = data.get('username')
    count = data.get('count', 5)
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    temp_dir = None
    try:
        temp_dir = create_user_temp_dir()
        
        # Check if instaloader is available
        result = subprocess.run(['python', '-c', 'import instaloader'], capture_output=True)
        if result.returncode != 0:
            return jsonify({'error': 'Instagram downloader not available on this server'}), 400
        
        # Use the video downloader script if it exists
        script_path = os.path.join(APP_DIR, 'video_downloader_improved.py')
        if os.path.exists(script_path):
            result = subprocess.run([
                'python', script_path, username, str(count)
            ], cwd=temp_dir, capture_output=True, text=True)
        else:
            return jsonify({'error': 'Instagram downloader not configured'}), 400
        
        if result.returncode != 0:
            return jsonify({'error': result.stdout + result.stderr}), 400
        
        zip_path = f"{temp_dir}/{username}_videos.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(('.mp4', '.mov', '.avi')):
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, file)
        
        if os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True, download_name=f"{username}_videos.zip")
        else:
            return jsonify({'error': 'No videos found'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)

@app.route('/download_instagram_post', methods=['POST'])
def download_instagram_post():
    data = request.json
    post_url = data.get('post_url')
    
    if not post_url:
        return jsonify({'error': 'Post URL required'}), 400
    
    temp_dir = None
    try:
        temp_dir = create_user_temp_dir()
        
        script_path = os.path.join(APP_DIR, 'video_downloader_improved.py')
        if os.path.exists(script_path):
            result = subprocess.run([
                'python', script_path, '--url', post_url
            ], cwd=temp_dir, capture_output=True, text=True)
        else:
            return jsonify({'error': 'Instagram downloader not configured'}), 400
        
        if result.returncode != 0:
            return jsonify({'error': result.stdout + result.stderr}), 400
        
        # Find the downloaded video file
        video_file = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.mp4', '.mov', '.avi')):
                    video_file = os.path.join(root, file)
                    break
            if video_file:
                break
        
        if video_file and os.path.exists(video_file):
            return send_file(video_file, as_attachment=True, download_name=os.path.basename(video_file))
        else:
            return jsonify({'error': 'No video found or post is not a video'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_dir:
            cleanup_temp_dir(temp_dir)

@app.route('/download_youtube_playlist', methods=['POST'])
def download_youtube_playlist():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    format_type = data.get('format', 'mp4')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    task_id = str(int(time.time())) + '_' + uuid.uuid4().hex[:8]
    progress_data[task_id] = {'status': 'starting', 'current': 0, 'total': 0}
    
    def download_with_progress():
        temp_dir = None
        try:
            temp_dir = create_user_temp_dir()
            
            # First get playlist info to count videos
            info_cmd = f'yt-dlp --flat-playlist --dump-json "{url}"'
            info_result = subprocess.run(info_cmd, shell=True, capture_output=True, text=True)
            
            total_videos = len([line for line in info_result.stdout.strip().split('\n') if line.strip()])
            progress_data[task_id] = {'status': 'downloading', 'current': 0, 'total': total_videos}
            
            # Base command with progress tracking
            base_cmd = f'yt-dlp --yes-playlist --ignore-errors --no-warnings --newline'
            
            if format_type == 'mp3':
                cmd = f'{base_cmd} -x --audio-format mp3 --audio-quality 0 -o "{temp_dir}/%(title)s.%(ext)s" "{url}"'
            else:
                if quality == 'best':
                    cmd = f'{base_cmd} -f "best[ext={format_type}]/best" -o "{temp_dir}/%(title)s.%(ext)s" "{url}"'
                else:
                    height = quality[:-1]
                    cmd = f'{base_cmd} -f "best[height<={height}][ext={format_type}]/best[height<={height}]/best" -o "{temp_dir}/%(title)s.%(ext)s" "{url}"'
            
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            current_count = 0
            for line in process.stdout:
                if '[download]' in line and 'Destination:' in line:
                    current_count += 1
                    progress_data[task_id] = {'status': 'downloading', 'current': current_count, 'total': total_videos}
            
            process.wait()
            
            # Check downloaded files
            downloaded_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(('.mp4', '.webm', '.mkv', '.mp3', '.m4a')):
                        downloaded_files.append(os.path.join(root, file))
            
            if downloaded_files:
                progress_data[task_id] = {'status': 'zipping', 'current': len(downloaded_files), 'total': total_videos}
                
                zip_path = f"{temp_dir}/playlist.zip"
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file_path in downloaded_files:
                        zipf.write(file_path, os.path.basename(file_path))
                
                progress_data[task_id] = {'status': 'ready', 'file': zip_path, 'current': len(downloaded_files), 'total': total_videos}
            else:
                progress_data[task_id] = {'status': 'error', 'message': 'No videos downloaded'}
                
        except Exception as e:
            progress_data[task_id] = {'status': 'error', 'message': str(e)}
        finally:
            # Cleanup will happen when file is downloaded
            pass
    
    threading.Thread(target=download_with_progress).start()
    return jsonify({'task_id': task_id})

@app.route('/download_file/<task_id>')
def download_file(task_id):
    if task_id in progress_data and progress_data[task_id].get('status') == 'ready':
        file_path = progress_data[task_id]['file']
        temp_dir = os.path.dirname(file_path)
        
        def cleanup_after_send():
            time.sleep(5)  # Give time for download to complete
            cleanup_temp_dir(temp_dir)
            if task_id in progress_data:
                del progress_data[task_id]
        
        threading.Thread(target=cleanup_after_send).start()
        return send_file(file_path, as_attachment=True, download_name="youtube_playlist.zip")
    return jsonify({'error': 'File not ready'}), 400

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
