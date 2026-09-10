from flask import Flask, request, jsonify
import whisper
import tempfile
import os
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

model = whisper.load_model("small")  # можно "small", "medium", "large"

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        file.save(tmp.name)
        try:
            result = model.transcribe(tmp.name)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            os.remove(tmp.name)

    return jsonify(result)
