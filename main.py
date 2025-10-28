from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import re
import json

app = Flask(__name__)

def get_video_id(url):
    """从 YouTube URL 提取视频 ID"""
    m = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None

def fetch_subtitle_from_url(url):
    """从 URL 获取字幕内容"""
    try:
        import urllib.request
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if 'events' in data:
            segments = []
            for event in data['events']:
                if 'segs' in event:
                    text = ''.join([seg.get('utf8', '') for seg in event['segs']]).strip()
                    if text:
                        segments.append({
                            'text': text,
                            'start': event.get('tStartMs', 0) / 1000,
                            'duration': event.get('dDurationMs', 0) / 1000
                        })
            return segments
        return None
    except Exception as e:
        print(f"   ⚠️ 获取字幕 URL 失败: {str(e)}")
        return None

def extract_subtitles_with_playwright(video_id, cookies_base64=None):
    """使用 Playwright 真实浏览器提取字幕"""
    try:
        from playwright.sync_api import sync_playwright
        import base64
        
        print(f"   🎭 启动 Playwright 浏览器...")
        
        with sync_playwright() as p:
            # 启动 Chromium
            browser = p.chromium.launch(headless=True)
            
            # 创建上下文
            context_options = {
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport': {'width': 1920, 'height': 1080},
                'locale': 'en-US',
            }
            
            # 如果有 cookies，添加到上下文
            if cookies_base64:
                try:
                    cookies_text = base64.b64decode(cookies_base64).decode('utf-8')
                    # 解析 Netscape cookies 格式并转换为 Playwright 格式
                    cookies = []
                    for line in cookies_text.split('\n'):
                        if line and not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookies.append({
                                    'name': parts[5],
                                    'value': parts[6],
                                    'domain': parts[0],
                                    'path': parts[2],
                                    'expires': int(parts[4]) if parts[4] != '0' else -1,
                                    'httpOnly': parts[1] == 'TRUE',
                                    'secure': parts[3] == 'TRUE',
                                })
                    context_options['cookies'] = cookies
                    print(f"   🍪 已加载 {len(cookies)} 个 cookies")
                except Exception as e:
                    print(f"   ⚠️  Cookies 解析失败: {e}")
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            # 访问 YouTube 视频
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"   🌐 访问: {url}")
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待页面加载
            page.wait_for_timeout(3000)
            
            # 尝试提取字幕数据
            subtitles = page.evaluate('''() => {
                try {
                    // 从 ytInitialPlayerResponse 提取字幕
                    const playerResponse = window.ytInitialPlayerResponse;
                    if (!playerResponse || !playerResponse.captions) {
                        return null;
                    }
                    
                    const captionTracks = playerResponse.captions.playerCaptionsTracklistRenderer.captionTracks;
                    if (!captionTracks || captionTracks.length === 0) {
                        return null;
                    }
                    
                    // 优先选择英语字幕
                    let track = captionTracks.find(t => t.languageCode === 'en') || captionTracks[0];
                    return track.baseUrl;
                } catch (e) {
                    return null;
                }
            }''')
            
            browser.close()
            
            if subtitles:
                print(f"   ✅ 获取到字幕 URL")
                # 下载字幕内容
                return fetch_subtitle_from_url(subtitles)
            else:
                print(f"   ❌ 未找到字幕数据")
                return None
                
    except Exception as e:
        print(f"   ❌ Playwright 失败: {str(e)}")
        return None

@app.route("/", methods=["GET"])
def home():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "service": "DeepRead Subtitle API",
        "version": "1.0.0"
    })

@app.route("/extract", methods=["POST"])
def extract():
    """提取 YouTube 字幕 - 使用后端配置的 Cookie"""
    import os
    
    url = request.json.get("url", "")
    vid = get_video_id(url)
    
    if not vid:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    # 从环境变量获取 YouTube Cookies
    youtube_cookies_raw = os.environ.get("YOUTUBE_COOKIES", "")
    youtube_cookies_base64 = os.environ.get("YOUTUBE_COOKIES_BASE64", "")
    
    # 优先使用 Base64 编码的 cookies（避免换行符问题）
    youtube_cookies = ""
    if youtube_cookies_base64:
        try:
            import base64
            youtube_cookies = base64.b64decode(youtube_cookies_base64).decode('utf-8')
            print(f"🔓 使用 Base64 解码的 Cookies")
        except Exception as e:
            print(f"⚠️  Base64 解码失败: {e}")
    
    # 如果没有 Base64，使用原始值
    if not youtube_cookies and youtube_cookies_raw:
        youtube_cookies = youtube_cookies_raw
    
    try:
        print(f"\n{'='*60}")
        print(f"🎯 开始提取字幕")
        print(f"📹 视频 ID: {vid}")
        print(f"🍪 Cookies 状态: {'已配置' if youtube_cookies else '未配置'}")
        if youtube_cookies:
            print(f"🍪 Cookies 长度: {len(youtube_cookies)} 字符")
            print(f"🍪 Cookies 前 100 字符: {youtube_cookies[:100]}")
        print(f"{'='*60}")
        
        # 获取完整字幕（自动翻页）
        segments = []
        page = 0
        e0 = None  # 初始化错误变量
        
        # 策略 0: 使用 Playwright 真实浏览器（最强大！）
        try:
            print(f"\n🎭 方法 0: 使用 Playwright 真实浏览器...")
            segments = extract_subtitles_with_playwright(vid, youtube_cookies_base64)
            
            if segments:
                print(f"✅ Playwright 成功: {len(segments)} 段")
            else:
                raise Exception("Playwright 未找到字幕")
                
        except Exception as e:
            e0 = e
            print(f"❌ Playwright 失败: {str(e0)}")
            segments = []
        
        # 如果 Playwright 失败，尝试其他方法
        e1 = None  # 初始化错误变量
        if not segments:
            # 策略 1: 使用 yt-dlp (最强大，能绕过限制)
            try:
                print(f"\n🚀 方法 1: 使用 yt-dlp 提取字幕...")
                
                ydl_opts = {
                    'skip_download': True,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'en-US', 'en-GB'],
                    'subtitlesformat': 'json3',
                    'quiet': True,
                    'no_warnings': True,
                    # 伪装成真实浏览器
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'referer': 'https://www.youtube.com/',
                    'headers': {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    },
                }
                
                # 如果配置了 cookies，写入临时文件
                import tempfile
                import os as os_module
                cookie_file_path = None
                if youtube_cookies:
                    print(f"   🍪 使用配置的 YouTube Cookies")
                    
                    # 创建临时文件
                    fd, cookie_file_path = tempfile.mkstemp(suffix='.txt', text=True)
                    
                    # 写入 cookies
                    with os_module.fdopen(fd, 'w') as f:
                        f.write(youtube_cookies)
                        f.flush()
                    
                    print(f"   📝 Cookies 文件已写入: {cookie_file_path}")
                    
                    # 验证文件
                    with open(cookie_file_path, 'r') as f:
                        content = f.read()
                        lines = content.split('\n')
                        cookie_lines = [l for l in lines if l and not l.startswith('#')]
                        print(f"   ✓ Cookie 文件行数: {len(lines)}，有效 cookie 行数: {len(cookie_lines)}")
                    
                    ydl_opts['cookiefile'] = cookie_file_path
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                    
                    # 获取字幕
                    if 'subtitles' in info and info['subtitles']:
                        print(f"📋 找到手动字幕: {list(info['subtitles'].keys())}")
                        # 优先使用手动字幕
                        for lang in ['en', 'en-US', 'en-GB']:
                            if lang in info['subtitles']:
                                subtitle_url = info['subtitles'][lang][0]['url']
                                print(f"✅ 使用手动字幕: {lang}")
                                segments = fetch_subtitle_from_url(subtitle_url)
                                if segments:
                                    break
                    
                    elif 'automatic_captions' in info and info['automatic_captions']:
                        print(f"📋 找到自动字幕: {list(info['automatic_captions'].keys())}")
                        # 使用自动字幕
                        for lang in ['en', 'en-US', 'en-GB']:
                            if lang in info['automatic_captions']:
                                # 找到 json3 格式的字幕
                                for subtitle in info['automatic_captions'][lang]:
                                    if subtitle.get('ext') == 'json3':
                                        subtitle_url = subtitle['url']
                                        print(f"✅ 使用自动字幕: {lang}")
                                        segments = fetch_subtitle_from_url(subtitle_url)
                                        if segments:
                                            break
                                if segments:
                                    break
                    
                    if segments:
                        print(f"✅ yt-dlp 成功: {len(segments)} 段")
                    else:
                        raise Exception("yt-dlp 未找到字幕")
                
                # 清理临时 cookie 文件
                if cookie_file_path:
                    try:
                        os_module.unlink(cookie_file_path)
                        print(f"   🗑️  已清理临时 cookie 文件")
                    except:
                        pass
                        
            except Exception as e:
                e1 = e
                print(f"❌ yt-dlp 失败: {str(e1)}")
                
                # 策略 2: 备用 youtube-transcript-api
                try:
                    print(f"\n🔄 方法 2: 使用 youtube-transcript-api...")
                    transcript_list = YouTubeTranscriptApi.list_transcripts(vid)
                    
                    # 优先选择英语字幕
                    selected_transcript = None
                    for transcript in transcript_list:
                        if transcript.language_code in ['en', 'en-US', 'en-GB']:
                            selected_transcript = transcript
                            break
                    
                    if not selected_transcript:
                        selected_transcript = list(transcript_list)[0]
                    
                    segments = selected_transcript.fetch()
                    print(f"✅ youtube-transcript-api 成功: {len(segments)} 段")
                    
                except Exception as e2:
                    error_msg = f"所有方法都失败了。Playwright: {str(e0)}; yt-dlp: {str(e1)}; transcript-api: {str(e2)}"
                    print(f"\n❌ {error_msg}")
                    return jsonify({"error": error_msg}), 404
        
        # 格式化输出
        full_text = " ".join([s["text"] for s in segments])
        
        # 格式化为标准格式
        formatted_segments = []
        for idx, seg in enumerate(segments):
            formatted_segments.append({
                "segment_id": f"seg_{str(idx).zfill(4)}",
                "start": seg["start"],
                "duration": seg["duration"],
                "end": seg["start"] + seg["duration"],
                "timestamp": format_timestamp(seg["start"]),
                "text": seg["text"]
            })
        
        # 统计信息
        total_duration = segments[-1]["start"] + segments[-1]["duration"] if segments else 0
        word_count = len(full_text.split())
        
        print(f"\n{'='*60}")
        print(f"✅ 提取成功！")
        print(f"📝 总段数: {len(formatted_segments)}")
        print(f"💬 总字数: {word_count}")
        print(f"⏱️  时长: {format_timestamp(total_duration)}")
        print(f"{'='*60}\n")
        
        return jsonify({
            "success": True,
            "video_id": vid,
            "transcript": formatted_segments,
            "meta": {
                "segment_count": len(formatted_segments),
                "word_count": word_count,
                "duration_seconds": total_duration,
                "duration_formatted": format_timestamp(total_duration),
                "source": "youtube_transcript_api"
            }
        })
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}\n")
        return jsonify({"error": str(e)}), 500

def format_timestamp(seconds):
    """格式化时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{str(minutes).zfill(2)}:{str(secs).zfill(2)}"
    return f"{minutes}:{str(secs).zfill(2)}"

if __name__ == "__main__":
    # 监听 0.0.0.0 方便容器访问
    # Zeabur 使用 8080 端口
    port = 8080
    print("\n🚀 DeepRead Subtitle API 启动中...")
    print(f"📡 监听端口: {port}")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)

