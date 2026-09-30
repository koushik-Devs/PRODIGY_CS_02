from pathlib import Path
from uuid import uuid4

import numpy as np
from flask import Flask, render_template, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = Path(__file__).resolve().parent / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


def encrypt_decrypt_image(image_path, key, output_name):
    """Apply reversible single-byte XOR to image pixels (educational only)."""
    with Image.open(image_path) as image:
        data = np.asarray(image.convert("RGB"), dtype=np.uint8)
    transformed = np.bitwise_xor(data, key)
    output_path = UPLOAD_FOLDER / output_name
    Image.fromarray(transformed).save(output_path, format="PNG")
    return output_name


@app.route("/", methods=["GET", "POST"])
def index():
    result_path = None
    if request.method == "POST":
        image = request.files.get("image")
        key_value = request.form.get("key", "")
        mode = request.form.get("mode", "")

        if image is None or not image.filename or not key_value:
            return render_template("index.html", error="Image and key are required.")
        if mode not in {"encrypt", "decrypt"}:
            return render_template("index.html", error="Choose encrypt or decrypt.")
        safe_name = secure_filename(image.filename)
        suffix = Path(safe_name).suffix.lower()
        if not safe_name or suffix not in ALLOWED_EXTENSIONS:
            return render_template("index.html", error="Upload a supported image file.")
        try:
            key = int(key_value)
        except ValueError:
            return render_template("index.html", error="Key must be an integer from 0 to 255.")
        if not 0 <= key <= 255:
            return render_template("index.html", error="Key must be an integer from 0 to 255.")

        token = uuid4().hex
        input_path = UPLOAD_FOLDER / f"input_{token}{suffix}"
        output_name = f"result_{token}.png"
        try:
            image.save(input_path)
            result_name = encrypt_decrypt_image(input_path, key, output_name)
            result_path = f"static/uploads/{result_name}"
        except (UnidentifiedImageError, OSError, ValueError):
            return render_template("index.html", error="The uploaded file is not a valid supported image.")
        finally:
            input_path.unlink(missing_ok=True)

    return render_template("index.html", result_path=result_path)


@app.route("/download/<filename>")
def download(filename):
    safe_name = secure_filename(filename)
    if safe_name != filename or not safe_name.startswith("result_"):
        return "File not found", 404
    return send_from_directory(UPLOAD_FOLDER, safe_name, as_attachment=True)


@app.errorhandler(413)
def file_too_large(_error):
    return render_template("index.html", error="Image must be 10 MB or smaller."), 413


if __name__ == "__main__":
    app.run(debug=False)
