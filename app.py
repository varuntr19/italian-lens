import os
import time
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

import db
import extract

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12MB, plenty for a resized JPEG

db.init_db()


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    photo = request.files.get("photo")
    if not photo:
        return jsonify({"error": "No photo uploaded."}), 400

    filename = f"{int(time.time() * 1000)}.jpg"
    path = UPLOAD_DIR / filename
    photo.save(path)

    try:
        result = extract.analyze_image(path)
    except extract.ExtractionError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500

    capture_id = db.save_capture(
        image_filename=filename,
        scene_description=result["scene_description"],
        phrases=result["phrases"],
        vocabulary=result["vocabulary"],
    )

    return jsonify(
        {
            "capture_id": capture_id,
            "image_url": f"/uploads/{filename}",
            **result,
        }
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/api/captures")
def captures():
    items = db.list_captures()
    for c in items:
        c["image_url"] = f"/uploads/{c['image_filename']}"
    return jsonify(items)


@app.route("/api/captures/<int:capture_id>")
def capture_detail(capture_id):
    c = db.get_capture(capture_id)
    if not c:
        abort(404)
    c["image_url"] = f"/uploads/{c['image_filename']}"
    return jsonify(c)


@app.route("/api/vocabulary")
def vocabulary():
    return jsonify(db.list_vocabulary())


@app.route("/api/vocabulary/<int:vocab_id>", methods=["DELETE"])
def delete_vocabulary(vocab_id):
    db.delete_vocabulary(vocab_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5420))
    app.run(host="0.0.0.0", port=port, debug=True)
