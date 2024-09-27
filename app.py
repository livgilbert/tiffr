import os
import time
from flask import Flask, request, render_template, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image, ImageCms

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 16 MB limit

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def remove_old_files(directory):
    now = time.time()  # Current time in seconds since the epoch
    week_in_seconds = 7 * 24 * 60 * 60  # Number of seconds in a week

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # Check if it's a file
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)  # Get the file's last modification time
            if file_age > week_in_seconds:  # If older than a week
                os.remove(file_path)  # Remove the file
                print(f"Removed old file: {file_path}")

def resize_image(image, width_in=None, height_in=None):

    if width_in:
        if width_in > 30:
            width_in = 30
        target_width = width_in * 300
    else:
        target_width = None

    if height_in:
        if height_in > 30:
            height_in = 30
        target_height = height_in * 300
    else:
        target_height = None

    if target_width and target_height:
        return image.resize((target_width, target_height), Image.LANCZOS)
    
    elif target_width:
        aspect_ratio = image.height / image.width
        new_height = int(target_width * aspect_ratio)
        return image.resize((target_width, new_height), Image.LANCZOS)
    
    elif target_height:
        aspect_ratio = image.width / image.height
        new_width = int(target_height * aspect_ratio)
        return image.resize((new_width, target_height), Image.LANCZOS)
    else:
        return image

def convert_to_cmyk(image):
        return ImageCms.profileToProfile(image, "sRGB Color Space Profile.icm", 'USWebCoatedSWOP.icc', renderingIntent=0, outputMode='CMYK')

def convert_to_grayscale(image):
    return image.convert("L")

def process_image(image_path, target_width=None, target_height=None):
    filename = ''.join(os.path.basename(image_path).split(".")[:-1]) # filename w/o ext
    now = datetime.now()
    formatted_time = now.strftime('%Y%m%d%H%M%S')

    with Image.open(image_path) as img:
        resized_image = resize_image(img, target_width, target_height)

        # Save CMYK
        cmyk_image = convert_to_cmyk(resized_image)
        cmyk_filename = formatted_time + filename + 'cmyk.tiff'
        cmyk_output_path = os.path.join(app.config['OUTPUT_FOLDER'], cmyk_filename)
        cmyk_image.save(cmyk_output_path, format="TIFF", compression="tiff_lzw", dpi=(300,300))

        # Save Grayscale
        grayscale_image = convert_to_grayscale(resized_image)
        grayscale_filename = formatted_time + filename + 'grayscale.tiff'
        grayscale_output_path = os.path.join(app.config['OUTPUT_FOLDER'], grayscale_filename)
        grayscale_image.save(grayscale_output_path, format="TIFF", compression="tiff_lzw", dpi=(300,300))

        return cmyk_filename, grayscale_filename

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    remove_old_files(app.config['UPLOAD_FOLDER'])
    remove_old_files(app.config['OUTPUT_FOLDER'])

    if request.method == 'POST':
        file = request.files['file']
        target_width = request.form.get('width', type=int)
        target_height = request.form.get('height', type=int)

        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            cmyk_path, grayscale_path = process_image(file_path, target_width, target_height)

            return render_template('index.html', cmyk_image=cmyk_path, grayscale_image=grayscale_path)

    return render_template('index.html', cmyk_image=None, grayscale_image=None)

@app.route('/outputs/<filename>')
def send_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)

