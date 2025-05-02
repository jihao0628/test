from flask import Flask, request, send_file, render_template_string
from yt_dlp import YoutubeDL
import os

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouTube 影片下載器 by jihao</title>
    <link rel="icon" type="image/png" href="https://www.youtube.com/favicon.ico">
    <style>
        body { font-family: Arial, "Microsoft JhengHei", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { text-align: center; }
        .input-group { margin: 20px 0; }
        select, input[type="text"] { width: 80%; padding: 10px; margin: 10px 0; }
        button { padding: 10px 20px; background: #ff0000; color: white; border: none; cursor: pointer; }
        button:hover { background: #cc0000; }
        .progress { width: 80%; margin: 20px auto; background: #f0f0f0; border-radius: 5px; }
        .progress-bar { width: 0%; height: 20px; background: #4CAF50; border-radius: 5px; transition: width 0.3s; }
        .author { position: fixed; bottom: 10px; right: 10px; color: #666; }
        #loading { font-size: 20px; font-weight: bold; color: #0066cc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube 影片下載器</h1>
        <form method="post" onsubmit="showLoading()">
            <div class="input-group">
                <input type="text" name="url" placeholder="請輸入 YouTube 影片網址" value="{{ url or '' }}" required>
            </div>
            <div class="input-group">
                <select name="format">
                    <option value="mp4_best">MP4 最高畫質</option>
                    <option value="mp4_720">MP4 720p</option>
                    <option value="mp4_480">MP4 480p</option>
                    <option value="mp4_360">MP4 360p</option>
                </select>
            </div>
            <button type="submit" name="action" value="download">下載影片</button>
            <button type="submit" name="action" value="preview">預覽資訊</button>
        </form>
        {% if error %}
        <p style="color: red;">{{ error }}</p>
        {% endif %}
        {% if preview_info %}
        <div style="text-align: left; margin: 20px auto; max-width: 80%; background: #f5f5f5; padding: 10px; border-radius: 5px;">
            {{ preview_info | safe }}
        </div>
        {% endif %}
        <div id="loading" style="display: none; margin: 20px 0;">
            請稍後，正在處理中...
        </div>
    </div>
    <div class="author"> 
        版本:1.0.2<br>
        版本發行日期:2025/4/9<br>
        作者：jihao
    </div>
    <script>
        function showLoading() {
            let loadingText = document.getElementById('loading');
            let dots = 0;
            loadingText.style.display = 'block';

            setInterval(function() {
                dots = (dots + 1) % 4;  // Cycle through 0 to 3
                loadingText.innerText = '請稍後' + '.'.repeat(dots);  // Add dots based on the count
            }, 500);  // Update every 500ms
        }
    </script>
</body>
</html>
'''

def format_duration(duration):
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    return f"{hours} 小時 {minutes} 分 {seconds} 秒" if hours else f"{minutes} 分 {seconds} 秒"

def get_yt_opts(format_type, output_path, hook=None):
    base_opts = {
        'outtmpl': output_path,
        'retries': 5,
        'socket_timeout': 15,
        'concurrent_fragment_downloads': 10,
        'buffer_size': 1048576 * 10,
    }
    if hook:
        base_opts['progress_hooks'] = [hook]
    format_map = {
        'mp4_best': 'best[ext=mp4]',
        'mp4_720': 'best[height<=720][ext=mp4]',
        'mp4_480': 'best[height<=480][ext=mp4]',
        'mp4_360': 'best[height<=360][ext=mp4]'
    }
    base_opts['format'] = format_map.get(format_type, 'best[ext=mp4]')
    return base_opts

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        url = request.form['url']
        format_type = request.form.get('format', 'mp4_best')

        if not url.startswith(('http://', 'https://')) or ('youtube.com' not in url and 'youtu.be' not in url):
            return render_template_string(HTML, error="請輸入有效的 YouTube 網址", url=url)

        if request.form.get('action') == 'preview':
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', '')
                    duration = info.get('duration', 0)
                    thumbnail = info.get('thumbnail', '')
                    formatted_duration = format_duration(duration)
                    preview_info = f"""
                    <div>
                        <p><strong>標題:</strong> {title}</p>
                        <p><strong>時長:</strong> {formatted_duration}</p>
                        <p><strong>縮圖:</strong></p>
                        <img src="{thumbnail}" style="max-width: 320px; margin-top: 10px;">
                    </div>"""
                    return render_template_string(HTML, preview_info=preview_info, url=url)
            except Exception as e:
                return render_template_string(HTML, error=f"預覽失敗：{str(e)}", url=url)

        # Handle download
        try:
            with YoutubeDL() as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video')
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()

            filename_template = f"temp_{title}.%(ext)s"
            ydl_opts = get_yt_opts(format_type, filename_template)

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            for ext in ['mp4', 'mkv']:
                filename = f"temp_{title}.{ext}"
                if os.path.exists(filename):
                    return_data = send_file(
                        filename,
                        as_attachment=True,
                        download_name=f"{title}.{ext}",
                        mimetype=f'video/{ext}'
                    )
                    os.remove(filename)
                    return return_data

            return render_template_string(HTML, error="下載失敗，請重試", url=url)

        except Exception as e:
            return render_template_string(HTML, error=f"下載錯誤：{str(e)}", url=url)

    return render_template_string(HTML, url='')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
