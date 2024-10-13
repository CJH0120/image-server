import os
import logging
from flask import Flask, send_file, abort, request
from PIL import Image
from io import BytesIO
from flask_caching import Cache
from dotenv import load_dotenv
from flask_cors import CORS
from werkzeug.utils import secure_filename
import time
import re

# .env 파일 로드
load_dotenv()

app = Flask(__name__)

# 기본 환경 변수 설정
default_image_path = os.getenv('DEFAULT_IMAGE_PATH', '/default/path')
cache_timeout = int(os.getenv('CACHE_TIMEOUT', 60))

# 캐시 설정
cache = Cache(app, config={'CACHE_TYPE': os.getenv('CACHE_TYPE', 'SimpleCache')})

# CORS 설정 (필요한 경우, 특정 도메인으로 제한할 수 있음)
CORS(app)  # 기본값으로 모든 도메인 허용

# 로깅 설정
logging.basicConfig(level=logging.INFO)

@app.route('/<path:folder_path>/<filename>', methods=['GET'])
@cache.cached(timeout=cache_timeout, query_string=True)
def resize_image(folder_path, filename):
    client_ip = request.remote_addr
    logging.info( "Received request from Method:[GET]", client_ip)
    width = request.args.get('w', type=int)
    height = request.args.get('h', type=int)
    if not is_valid_path(folder_path) or not is_valid_path(filename):
        abort(400, f"Your IP is {client_ip}. I will launch a DDoS attack soon Thanks.")

    image_path = os.path.join(default_image_path, folder_path, filename)

    try:
        with Image.open(image_path) as img:
            # 너비와 높이가 지정되지 않은 경우 원본 이미지 크기 사용
            width, height = (img.size if width is None or height is None else (width, height))
            
            # 입력 유효성 검사
            if width < 1 or height < 1:
                abort(400, "Width and height must be greater than 0.")

            # 이미지 리사이징
            new_image = img.resize((width, height), Image.LANCZOS)

            # BytesIO 객체 생성 후 요청한 형식으로 저장
            output = BytesIO()
            output_format = request.args.get('format', default='WEBP').upper()
            output_format = output_format if output_format in ['JPEG', 'PNG', 'WEBP'] else 'WEBP'

            new_image.save(output, format=output_format, quality=100)
            output.seek(0)

            # MIME 타입 설정
            mime_type = 'image/' + output_format.lower()
            return send_file(output, mimetype=mime_type)

    except FileNotFoundError:
        logging.error(f"ERROR - File not found.  Path : {image_path} client IP: {client_ip}")
        abort(404, f"Not found: {image_path}")
    except Exception as e:
        logging.error(f"Server Error: {e} Path : {image_path} client IP: {client_ip} ")
        abort(500, f"Internal server error. ${e}") 

@app.route('/upload', methods=['POST'])
def upload_image():
    logging.info( "Received request from Method:[POST]", request.remote_addr)
    if request.remote_addr != '127.0.0.1':
        abort(401, "Unauthorized access. Only local requests are allowed.")
    if 'image' not in request.files or 'folder' not in request.form:
        abort(400, "No image or folder specified.")

    image = request.files['image']
    folder = request.form['folder']

    # 폴더 경로 생성
    folder_path = os.path.join(default_image_path, folder)
    os.makedirs(folder_path, exist_ok=True) 

    try:
        file_extension = os.path.splitext(image.filename)[1].lower() 
        if file_extension not in ['.png', '.jpg', '.jpeg', '.webp']:
            abort(400, "Unsupported file type. Please upload png, jpg, jpeg, webp, or avif files.")

        # 이미지 열기
        img = Image.open(image)

     
        timestamp = int(time.time() * 1000000)

        webp_filename = f"{timestamp}.webp"  
        image_path = os.path.join(folder_path, webp_filename)

        # WebP 형식으로 저장
        img.save(image_path, format='WEBP', quality=100)
        return_path = f'/{folder}/{webp_filename}'
        logging.info(f"Uploaded and converted image: {return_path}")
        return {"message": "Image uploaded and converted successfully.", "path": return_path}, 201

    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        abort(500, "Internal server error.")

def is_valid_path(path):
    return not re.search(r'(\.\.|/\.|\\\.|\.\./|\\\.)', path)

# 포트 설정
port = int(os.getenv('PORT', 5000))
if __name__ == '__main__':
    app.run(debug=os.getenv('DEBUG_MODE', 'true').lower() == 'true', port=port)
