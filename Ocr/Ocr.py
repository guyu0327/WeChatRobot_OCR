import base64

import requests

from Ocr.utils.AuthV3Util import addAuthParams

# 您的应用ID
APP_KEY = ''
# 您的应用密钥
APP_SECRET = ''


def createRequest(path):
    '''
    note: 将下列变量替换为需要请求的参数
    取值参考文档: https://ai.youdao.com/DOCSIRMA/html/%E6%96%87%E5%AD%97%E8%AF%86%E5%88%ABOCR/API%E6%96%87%E6%A1%A3/%E9%80%9A%E7%94%A8%E6%96%87%E5%AD%97%E8%AF%86%E5%88%AB%E6%9C%8D%E5%8A%A1/%E9%80%9A%E7%94%A8%E6%96%87%E5%AD%97%E8%AF%86%E5%88%AB%E6%9C%8D%E5%8A%A1-API%E6%96%87%E6%A1%A3.html
    '''
    lang_type = 'auto'
    detect_type = '10012'
    angle = '0'
    column = 'onecolumn'
    rotate = 'donot_rotate'
    doc_type = 'json'
    image_type = '1'

    # 数据的base64编码
    img = readFileAsBase64(path)
    data = {'img': img, 'langType': lang_type, 'detectType': detect_type, 'angle': angle,
            'column': column, 'rotate': rotate, 'docType': doc_type, 'imageType': image_type}

    addAuthParams(APP_KEY, APP_SECRET, data)

    header = {'Content-Type': 'application/x-www-form-urlencoded'}
    res = doCall('https://openapi.youdao.com/ocrapi', header, data, 'post')
    return str(res.content, 'utf-8')


def doCall(url, header, params, method):
    if 'get' == method:
        return requests.get(url, params)
    elif 'post' == method:
        return requests.post(url, params, header)


def readFileAsBase64(path):
    f = open(path, 'rb')
    data = f.read()
    return str(base64.b64encode(data), 'utf-8')
