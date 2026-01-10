from flask import Flask, render_template, request, jsonify, send_file, Response
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
    
    try:
        temp_dir = tempfile.mkdtemp(dir='/home/pr3cision/Music/video_downloader_webapp')
        
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

@app.route('/download_instagram', methods=['POST'])
def download_instagram():
    data = request.json
    username = data.get('username')
    count = data.get('count', 5)
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    try:
        temp_dir = tempfile.mkdtemp(dir='/home/pr3cision/Music/video_downloader_webapp')
        
        result = subprocess.run([
            'bash', '-c', 
            f'cd "{temp_dir}" && source /home/pr3cision/Music/video_downloader_webapp/instaloader_env/bin/activate && python /home/pr3cision/Music/video_downloader_webapp/video_downloader_improved.py {username} {count}'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            shutil.rmtree(temp_dir)
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

@app.route('/download_instagram_post', methods=['POST'])
def download_instagram_post():
    data = request.json
    post_url = data.get('post_url')
    
    if not post_url:
        return jsonify({'error': 'Post URL required'}), 400
    
    try:
        temp_dir = tempfile.mkdtemp(dir='/home/pr3cision/Music/video_downloader_webapp')
        
        result = subprocess.run([
            'bash', '-c', 
            f'cd "{temp_dir}" && source /home/pr3cision/Music/video_downloader_webapp/instaloader_env/bin/activate && python /home/pr3cision/Music/video_downloader_webapp/video_downloader_improved.py --url "{post_url}"'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            shutil.rmtree(temp_dir)
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

@app.route('/download_youtube_playlist', methods=['POST'])
def download_youtube_playlist():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best')
    format_type = data.get('format', 'mp4')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    task_id = str(int(time.time()))
    progress_data[task_id] = {'status': 'starting', 'current': 0, 'total': 0}
    
    def download_with_progress():
        try:
            temp_dir = tempfile.mkdtemp(dir='/home/pr3cision/Music/video_downloader_webapp')
            
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
    
    threading.Thread(target=download_with_progress).start()
    return jsonify({'task_id': task_id})

@app.route('/download_file/<task_id>')
def download_file(task_id):
    if task_id in progress_data and progress_data[task_id].get('status') == 'ready':
        file_path = progress_data[task_id]['file']
        del progress_data[task_id]
        return send_file(file_path, as_attachment=True, download_name="youtube_playlist.zip")
    return jsonify({'error': 'File not ready'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
