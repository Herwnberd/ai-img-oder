import os
import sys
import io
import json
import re
import base64
import requests
import hashlib
import hmac
import datetime
from urllib.parse import urlencode
from flask import Flask, render_template, request, jsonify, send_from_directory
from waitress import serve

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

API_URL = os.environ.get('API_URL', "https://147ai.com")
API_KEY = os.environ.get('API_KEY', "")
MODEL = os.environ.get('MODEL', "gpt-image-2-client")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TOS_REGION = os.environ.get('TOS_REGION', "cn-guangzhou")
TOS_ENDPOINT = os.environ.get('TOS_ENDPOINT', "tos-cn-guangzhou.volces.com")
TOS_BUCKET = os.environ.get('TOS_BUCKET', "")
TOS_ACCESS_KEY = os.environ.get('TOS_ACCESS_KEY', "")
TOS_SECRET_KEY = os.environ.get('TOS_SECRET_KEY', "")

def hmac_sha256(key, msg):
    return hmac.new(key, msg, hashlib.sha256).digest()

def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = hmac_sha256(('AWS4' + key).encode('utf-8'), date_stamp.encode('utf-8'))
    k_region = hmac_sha256(k_date, region_name.encode('utf-8'))
    k_service = hmac_sha256(k_region, service_name.encode('utf-8'))
    k_signing = hmac_sha256(k_service, b'aws4_request')
    return k_signing

def generate_presigned_url(bucket, key, access_key, secret_key, region, expires_in=3600):
    t = datetime.datetime.now(datetime.timezone.utc)
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')
    
    canonical_uri = f"/{bucket}/{key}"
    
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    
    params = {
        'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
        'X-Amz-Credential': f"{access_key}/{credential_scope}",
        'X-Amz-Date': amz_date,
        'X-Amz-Expires': str(expires_in),
        'X-Amz-SignedHeaders': 'host',
    }
    
    canonical_querystring = '&'.join([f"{k}={v.replace('/', '%2F')}" for k, v in sorted(params.items())])
    
    host = f"{bucket}.{TOS_ENDPOINT}"
    canonical_request = f"PUT\n{canonical_uri}\n{canonical_querystring}\nhost:{host}\n\nhost\nUNSIGNED-PAYLOAD"
    
    string_to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    
    signing_key = get_signature_key(secret_key, date_stamp, region, 's3')
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    params['X-Amz-Signature'] = signature
    
    final_querystring = '&'.join([f"{k}={v.replace('/', '%2F')}" for k, v in sorted(params.items())])
    
    return f"https://{host}/{key}?{final_querystring}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/upload', methods=['POST'])
def api_upload():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "没有选择文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "文件名不能为空"}), 400
        
        filename = f"uploaded_{os.urandom(16).hex()}.jpg"
        
        file.seek(0)
        file_data = file.read()
        
        tos_url = f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/{filename}"
        
        presigned_url = generate_presigned_url(
            TOS_BUCKET, 
            filename, 
            TOS_ACCESS_KEY, 
            TOS_SECRET_KEY,
            TOS_REGION
        )
        
        headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': str(len(file_data))
        }
        
        resp = requests.put(presigned_url, headers=headers, data=file_data)
        
        if resp.status_code == 200:
            return jsonify({"success": True, "url": tos_url})
        else:
            return jsonify({"success": False, "error": f"上传到TOS失败: {resp.status_code} - {resp.text}"}), 500
        
    except Exception as e:
        return jsonify({"success": False, "error": f"上传失败: {str(e)}"}), 500

@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        images = data.get('images', [])
        requested_timeout = data.get('timeout', 300)
        actual_timeout = max(requested_timeout, 600)
        
        if not prompt:
            return jsonify({"success": False, "error": "提示词不能为空"}), 400
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        content_parts = [{"type": "text", "text": prompt}]
        for img_url in images:
            content_parts.append({"type": "image_url", "image_url": {"url": img_url}})
        
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": content_parts}],
            "max_tokens": 4096
        }
        
        resp = requests.post(
            f"{API_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=actual_timeout
        )
        
        if resp.status_code != 200:
            try:
                error_info = resp.json()
                return jsonify({"success": False, "error": f"API错误: {error_info.get('error', {}).get('message', str(resp.status_code))}"}), 500
            except:
                return jsonify({"success": False, "error": f"API错误: {resp.status_code}"}), 500
        
        result = resp.json()
        
        if not isinstance(result, dict) or "choices" not in result:
            return jsonify({"success": False, "error": "API返回格式异常"}), 500
        
        try:
            content = result["choices"][0]["message"]["content"]
        except:
            return jsonify({"success": False, "error": "解析响应失败"}), 500
        
        b64_pattern = r'data:(image/\w+);base64,([A-Za-z0-9+/=\s]{100,})'
        matches = re.findall(b64_pattern, content)
        
        if matches:
            b64data = matches[0][1].replace("\n", "").replace(" ", "").strip()
            try:
                img_data = base64.b64decode(b64data)
                filename = f"generated_{os.urandom(16).hex()}.png"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                return jsonify({"success": True, "url": f"/uploads/{filename}"})
            except Exception as e:
                return jsonify({"success": False, "error": f"保存图片失败: {str(e)}"}), 500
        
        url_pattern = r'https?://[^\s\)\]"<>]+\.(?:png|jpg|jpeg|webp)'
        urls = re.findall(url_pattern, content)
        if urls:
            return jsonify({"success": True, "url": urls[0]})
        
        return jsonify({"success": False, "error": "未在响应中找到图片"}), 500
        
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": f"请求超时（{actual_timeout}秒）"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("使用 Waitress 服务器启动...")
    serve(app, host='0.0.0.0', port=5000, threads=4)