from flask import Flask, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
from youtube_transcript_api.formatters import Formatter  # You can keep this for future use if needed
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle subtitle downloading
@app.route('/get_subtitles', methods=['POST'])
def get_subtitles():
    video_url = request.form.get('videoUrl')
    subtitle_format = request.form.get('format')

    # Validate YouTube URL and extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        error_message = "Invalid YouTube URL. Please enter a valid URL."
        return render_template('result.html', subtitles=None, error=error_message)

    # Fetch available languages for the video
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_languages = [trans.language_code for trans in transcript_list]
    except VideoUnavailable:
        error_message = "The video is unavailable or has been removed."
        return render_template('result.html', subtitles=None, error=error_message)
    except NoTranscriptFound:
        error_message = "No subtitles available for this video."
        return render_template('result.html', subtitles=None, error=error_message)

    # Fetch subtitles for each available language and format
    subtitles_data = {}
    for language_code in available_languages:
        try:
            subtitles = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
            formatted_srt = format_to_srt(subtitles)
            formatted_txt = format_to_text(subtitles)

            subtitles_data[language_code] = {
                'srt': formatted_srt,
                'txt': formatted_txt
            }
        except TranscriptsDisabled:
            continue
        except Exception as e:
            print(f"Error fetching subtitles for language {language_code}: {e}")
            continue

    if not subtitles_data:
        error_message = "No downloadable subtitles found for this video."
        return render_template('result.html', subtitles=None, error=error_message)

    # Pass all subtitles and formats to the template
    return render_template('result.html', subtitles=subtitles_data, format=subtitle_format)

# Helper function to extract video ID from YouTube URL
def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'www.youtube.com':
        query = parse_qs(parsed_url.query)
        return query.get('v', [None])[0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path.strip('/')
    return None

# Helper function to format subtitles to SRT
def format_to_srt(subtitles):
    formatted_srt = ""
    for i, entry in enumerate(subtitles):
        start_time = entry['start']
        end_time = entry['start'] + entry['duration']
        formatted_srt += f"{i + 1}\n"
        formatted_srt += f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n"
        formatted_srt += f"{entry['text']}\n\n"
    return formatted_srt

# Helper function to format timestamps for SRT (HH:MM:SS,ms)
def format_timestamp(seconds):
    millis = int((seconds % 1) * 1000)
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02}:{mins:02}:{secs:02},{millis:03}"

# Helper function to format subtitles to plain text
def format_to_text(subtitles):
    return "\n".join(sub['text'] for sub in subtitles)

# Running the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
