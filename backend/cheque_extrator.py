import os
import sys

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

for k in list(sys.modules.keys()):
    if k.startswith('google.protobuf'):
        del sys.modules[k]


import warnings
warnings.filterwarnings("ignore", message=r".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import cv2
import numpy as np
if not hasattr(np, 'sctypes'):
    np.sctypes = {
        'int': [np.int8, np.int16, np.int32, np.int64],
        'uint': [np.uint8, np.uint16, np.uint32, np.uint64],
        'float': [np.float16, np.float32, np.float64],
        'complex': [np.complex64, np.complex128],
        'others': [bool, object, bytes, str, np.void]
    }
from PIL import Image
import pdf2image
import io
import re
import json
import difflib
import math
import requests
from bs4 import BeautifulSoup

_OCR_READER = None

def load_ocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        from paddleocr import PaddleOCR
        try:
            _OCR_READER = PaddleOCR(
                use_textline_orientation=False,
                lang='en',
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                enable_mkldnn=False
            )
        except Exception:
            _OCR_READER = PaddleOCR(
                use_angle_cls=False,
                lang='en',
                enable_mkldnn=False
            )
    return _OCR_READER

def _safe_scale_for_ocr(image, max_dim=1280):
    """Ensure images passed to OCR do not blow up memory or trigger max_side_limit limits."""
    if image is None or image.size == 0:
        return image
    h, w = image.shape[:2]
    max_side = max(h, w)
    if max_side > max_dim:
        scale = max_dim / float(max_side)
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image

def _unpack_ocr_item(item):
    """Safely unpack any PaddleOCR result item into (bbox, text, prob)."""
    if not item:
        return None, "", 0.0
    try:
        if isinstance(item, dict):
            bbox = item.get('points') or item.get('bbox') or []
            text = str(item.get('transcription') or item.get('text') or '')
            prob = float(item.get('confidence') or item.get('score') or 1.0)
            return bbox, text, prob
        if isinstance(item, (list, tuple)) and len(item) == 2:
            bbox = item[0]
            if isinstance(item[1], (tuple, list)):
                return bbox, str(item[1][0]), float(item[1][1]) if len(item[1]) > 1 else 1.0
            return bbox, str(item[1]), 1.0
        if len(item) >= 3:
            return item[0], str(item[1]), float(item[2])
    except Exception:
        pass
    return None, "", 0.0

def normalize_paddle_ocr_results(raw_results):
    """Normalizes any PaddleOCR output structure (v2, v3, PaddleX OCRResult) into a list of items."""
    if not raw_results:
        return []
    
    normalized = []
    items_to_process = raw_results if isinstance(raw_results, (list, tuple)) else [raw_results]
    
    for res in items_to_process:
        if res is None:
            continue
            
        # PaddleOCR 3.x / PaddleX OCRResult
        if hasattr(res, 'get') or isinstance(res, dict):
            if 'rec_texts' in res and 'rec_scores' in res:
                texts = res.get('rec_texts', [])
                scores = res.get('rec_scores', [])
                polys = res.get('rec_polys', [])
                boxes = res.get('rec_boxes', [])
                
                for i, text in enumerate(texts):
                    score = float(scores[i]) if i < len(scores) else 1.0
                    poly = None
                    if i < len(polys) and polys[i] is not None:
                        poly = polys[i].tolist() if hasattr(polys[i], 'tolist') else polys[i]
                    elif i < len(boxes) and boxes[i] is not None:
                        b = boxes[i].tolist() if hasattr(boxes[i], 'tolist') else boxes[i]
                        if len(b) >= 4:
                            poly = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]
                    normalized.append([poly, (str(text), score)])
                continue
            elif 'text' in res or 'transcription' in res:
                bbox = res.get('points') or res.get('bbox') or []
                text = str(res.get('transcription') or res.get('text') or '')
                score = float(res.get('confidence') or res.get('score') or 1.0)
                normalized.append([bbox, (text, score)])
                continue

        # PaddleOCR 2.x format: list of [points, (text, score)]
        if isinstance(res, (list, tuple)):
            if len(res) == 2 and isinstance(res[1], (tuple, list)):
                normalized.append(res)
            elif len(res) == 1 and isinstance(res[0], list):
                for item in res[0]:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        normalized.append(item)
            else:
                for item in res:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        normalized.append(item)

    return normalized

def order_points(pts):
    # Sort the points based on their x-coordinates
    xSorted = pts[np.argsort(pts[:, 0]), :]
    # Grab the left-most and right-most points
    leftMost = xSorted[:2, :]
    rightMost = xSorted[2:, :]
    
    # Sort the left-most points according to their y-coordinates
    leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
    (tl, bl) = leftMost
    
    # Calculate Euclidean distance from tl to the rightMost points
    # The point with the largest distance is the bottom-right
    D = np.linalg.norm(rightMost - tl, axis=1)
    if D[0] > D[1]:
        br = rightMost[0]
        tr = rightMost[1]
    else:
        br = rightMost[1]
        tr = rightMost[0]
        
    return np.array([tl, tr, br, bl], dtype="float32")

def four_point_transform(image, pts):
    # obtain a consistent order of the points and unpack them
    # individually
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    # compute the width of the new image, which will be the
    # maximum distance between bottom-right and bottom-left
    # x-coordiates or the top-right and top-left x-coordinates
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    # compute the height of the new image, which will be the
    # maximum distance between the top-right and bottom-right
    # y-coordinates or the top-left and bottom-left y-coordinates
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    # compute the perspective transform matrix and then apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    # return the warped image
    return warped

def detect_and_crop_cheque(image):
    # image is a numpy array (RGB)
    original = image.copy()
    h_orig, w_orig = image.shape[:2]
    image_area = h_orig * w_orig
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    # Apply Gaussian blur to smooth out noise
    gray = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # Edge detection
    edged = cv2.Canny(gray, 30, 150)
    
    # Morphological operations to close gaps in the outer boundary
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edged = cv2.dilate(edged, kernel, iterations=3)
    edged = cv2.erode(edged, kernel, iterations=1)
    
    # Find all contours safely across both OpenCV 3 and OpenCV 4
    find_contours_res = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = find_contours_res[0] if len(find_contours_res) == 2 else find_contours_res[1]
    
    best_contour = None
    best_score = -1
    
    for c in contours:
        area = cv2.contourArea(c)
        
        # 1. Reject small internal contours (must be at least 35% of the image)
        # This completely ignores date boxes, logos, ₹ symbols, text, etc.
        if area < 0.35 * image_area:
            continue
            
        # 2. Check Aspect Ratio using Minimum Area Rectangle
        rect = cv2.minAreaRect(c)
        width = rect[1][0]
        height = rect[1][1]
        
        if width == 0 or height == 0:
            continue
            
        aspect_ratio = max(width / height, height / width)
        
        # Cheques are horizontal documents, usually aspect ratio is between 1.8 and 3.0
        # We allow 1.5 to 4.0 to be safe, rejecting squares or extremely long strips.
        if aspect_ratio < 1.5 or aspect_ratio > 4.0:
            continue
            
        # 3. Four-corner approximation
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        
        # Calculate rectangularity (extent) to penalize irregular background blobs.
        # A true cheque will have rectangularity very close to 1.0.
        # An irregular background blob might have a large area but low rectangularity.
        rect_area = width * height
        rectangularity = area / rect_area if rect_area > 0 else 0
        
        # Square the rectangularity to heavily penalize non-rectangular blobs
        score = area * (rectangularity ** 2)
        
        # If it forms a clean 4-point convex polygon, heavily prefer it
        if len(approx) == 4 and cv2.isContourConvex(approx):
            score *= 1.5
            candidate = approx.reshape(4, 2)
        else:
            # Fallback to the 4 corners of the minimum bounding rectangle for this contour
            box = cv2.boxPoints(rect)
            candidate = box
            
        if score > best_score:
            best_score = score
            best_contour = candidate
            
    if best_contour is None:
        # Fallback to entire image bounds if no valid cheque contour is found
        # This prevents cropping a random small region if detection fails completely.
        best_contour = np.array([[0,0], [w_orig,0], [w_orig,h_orig], [0,h_orig]])
            
    cheque_contour = np.int32(best_contour)
            
    # Draw the detected boundary on a copy of the original image
    boundary_img = original.copy()
    cv2.drawContours(boundary_img, [cheque_contour], -1, (0, 255, 0), 4)
    
    # Draw the 4 corner points explicitly as requested
    for pt in cheque_contour:
        x, y = pt.ravel()
        cv2.circle(boundary_img, (int(x), int(y)), 10, (0, 0, 255), -1)

    # Perform perspective transform for tight crop
    pts = cheque_contour.astype("float32")
    
    # 8. Keep only a very small safety margin of 3-5 pixels outside the cheque boundary
    # We enforce a strict 4-pixel margin outward from the geometric center.
    center = np.mean(pts, axis=0)
    padded_pts = np.zeros_like(pts)
    for i in range(4):
        vector = pts[i] - center
        length = np.linalg.norm(vector)
        if length > 0:
            # Expand strictly by 4 pixels to get the exact requested safety margin
            padded_pts[i] = center + vector * ((length + 4.0) / length)
        else:
            padded_pts[i] = pts[i]
    
    # Clip to image boundaries
    padded_pts[:, 0] = np.clip(padded_pts[:, 0], 0, w_orig - 1)
    padded_pts[:, 1] = np.clip(padded_pts[:, 1], 0, h_orig - 1)
    
    cropped = four_point_transform(image, padded_pts)
            
    return boundary_img, cropped

def preprocess_for_ocr(image):
    # PaddleOCR performs best on native resolution. 
    # Upscaling artificially can cause its internal detection resizing to lose fine details.
    return image

COMMON_BANKS = [
    "STATE BANK OF INDIA", "STATE BANK", "HDFC BANK", "ICICI BANK", "AXIS BANK", 
    "KOTAK MAHINDRA BANK", "INDUSIND BANK", "YES BANK", "PUNJAB NATIONAL BANK", 
    "BANK OF BARODA", "BANK OF INDIA", "CANARA BANK", "UNION BANK OF INDIA", 
    "UNION BANK", "IDBI BANK", "INDIAN BANK", "CENTRAL BANK OF INDIA", "UCO BANK", 
    "BANK OF MAHARASHTRA", "FEDERAL BANK", "SOUTH INDIAN BANK", 
    "KARNATAKA BANK", "CITY UNION BANK", "TAMILNAD MERCANTILE BANK", 
    "KARUR VYSYA BANK", "INDIAN OVERSEAS BANK", "PUNJAB AND SIND BANK",
    "BANDHAN BANK", "IDFC FIRST BANK", "RBL BANK", "CSB BANK", 
    "DCB BANK", "DHANLAXMI BANK", "STANDARD CHARTERED BANK", "CITIBANK",
    "HSBC BANK", "DBS BANK", "JAMMU AND KASHMIR BANK", "DEUTSCHE BANK"
]

BANK_ALIASES = {
    "BARODA": "BANK OF BARODA",
    "BOB": "BANK OF BARODA",
    "SBI": "STATE BANK OF INDIA",
    "STATE BANK": "STATE BANK OF INDIA",
    "CANARA": "CANARA BANK",
    "HDFC": "HDFC BANK",
    "ICICI": "ICICI BANK",
    "AXIS": "AXIS BANK",
    "KOTAK": "KOTAK MAHINDRA BANK",
    "PNB": "PUNJAB NATIONAL BANK",
    "UNION BANK": "UNION BANK OF INDIA",
    "INDUSIND": "INDUSIND BANK",
    "IDBI": "IDBI BANK",
    "INDIAN BANK": "INDIAN BANK",
    "CENTRAL BANK": "CENTRAL BANK OF INDIA",
    "UCO": "UCO BANK",
    "MAHARASHTRA": "BANK OF MAHARASHTRA",
    "FEDERAL": "FEDERAL BANK",
    "CUB": "CITY UNION BANK",
    "KVB": "KARUR VYSYA BANK",
    "YES BANK": "YES BANK",
    "BANDHAN": "BANDHAN BANK",
    "IDFC": "IDFC FIRST BANK",
    "RBL": "RBL BANK",
    "CSB": "CSB BANK",
    "DCB": "DCB BANK"
}

def extract_bank_name(ocr_results, image_height):
    potential_banks = []
    
    for item in ocr_results:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox or not text or prob < 0.1:
            continue
            
        clean_text = text.strip()
        text_no_spaces = re.sub(r'[\s\-:,\.]', '', clean_text)
        
        y_coords = [p[1] for p in bbox]
        y_center = sum(y_coords) / 4.0
        relative_y = y_center / float(image_height)
        
        if relative_y < 0.50:
            if re.search(r'(BANK|BARODA|LTD|LIMITED|INDIA|UNION|HDFC|ICICI|SBI|AXIS|FEDERAL|CUB|CANARA|KOTAK|PNB)', clean_text, re.IGNORECASE) or \
               re.search(r'(BANK|BARODA|LTD|LIMITED|INDIA|CANARA)', text_no_spaces, re.IGNORECASE):
                potential_banks.append((prob, clean_text))
                
    if not potential_banks:
        return "Not Found"
        
    def score_bank(text):
        if re.search(r'(?i)\b(BANK|BARODA|UNION|HDFC|ICICI|SBI|AXIS|FEDERAL|CUB|CANARA|KOTAK)\b', text):
            return 2
        if re.search(r'(?i)(LTD|LIMITED|INDIA)', text):
            return 1
        return 0
        
    potential_banks.sort(key=lambda x: (score_bank(x[1]), x[0]), reverse=True)
    best_match = potential_banks[0][1]
    
    upper_best = best_match.upper()
    upper_best_nospace = upper_best.replace(" ", "")
    for bank in COMMON_BANKS:
        if bank in upper_best or bank.replace(" ", "") in upper_best_nospace:
            return bank
    for alias, standard_name in BANK_ALIASES.items():
        if alias in upper_best or alias in upper_best_nospace:
            return standard_name
            
    match = re.search(r'(?i)(.*?(?:BANK|LTD|LIMITED|INDIA|UNION|HDFC|ICICI|SBI|AXIS|FEDERAL|CUB|BARODA))', best_match)
    if match:
        cleaned_bank = match.group(1).strip()
        cleaned_bank = re.sub(r'[^A-Za-z\s]+$', '', cleaned_bank).strip()
    else:
        cleaned_bank = best_match.strip()
        
    if not re.search(r'(?i)\bBANK$', cleaned_bank):
        trunc_match = re.search(r'(?i)^(.+\bBANK\b)', cleaned_bank)
        if trunc_match and trunc_match.group(1).strip().upper() != "BANK":
            cleaned_bank = trunc_match.group(1).strip()
        else:
            cleaned_bank += " BANK"
            
    cleaned_bank_upper = cleaned_bank.upper()
    if cleaned_bank_upper == "CUB BANK":
        cleaned_bank_upper = "CITY UNION BANK"
        
    matches = difflib.get_close_matches(cleaned_bank_upper, COMMON_BANKS, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return cleaned_bank_upper

BANK_IFSC_PREFIX = {
    "STATE BANK OF INDIA": "SBIN",
    "STATE BANK": "SBIN",
    "HDFC BANK": "HDFC",
    "ICICI BANK": "ICIC",
    "AXIS BANK": "UTIB",
    "KOTAK MAHINDRA BANK": "KKBK",
    "INDUSIND BANK": "INDB",
    "YES BANK": "YESB",
    "PUNJAB NATIONAL BANK": "PUNB",
    "BANK OF BARODA": "BARB",
    "BANK OF INDIA": "BKID",
    "CANARA BANK": "CNRB",
    "UNION BANK OF INDIA": "UBIN",
    "UNION BANK": "UBIN",
    "IDBI BANK": "IBKL",
    "INDIAN BANK": "IDIB",
    "CENTRAL BANK OF INDIA": "CBIN",
    "UCO BANK": "UCBA",
    "BANK OF MAHARASHTRA": "MAHB",
    "FEDERAL BANK": "FDRL",
    "SOUTH INDIAN BANK": "SIBL",
    "KARNATAKA BANK": "KARB",
    "CITY UNION BANK": "CIUB",
    "TAMILNAD MERCANTILE BANK": "TMBL",
    "KARUR VYSYA BANK": "KVBL",
    "INDIAN OVERSEAS BANK": "IOBA",
    "PUNJAB AND SIND BANK": "PSIB",
    "BANDHAN BANK": "BDBL",
    "IDFC FIRST BANK": "IDFB",
    "RBL BANK": "RATN",
    "CSB BANK": "CSBK",
    "DCB BANK": "DCBL",
    "DHANLAXMI BANK": "DLXB",
    "STANDARD CHARTERED BANK": "SCBL",
    "CITIBANK": "CITI",
    "HSBC BANK": "HSBC",
    "DBS BANK": "DBSS",
    "JAMMU AND KASHMIR BANK": "JAKA",
    "DEUTSCHE BANK": "DEUT"
}

def extract_bank_name_with_fallback(ocr_results, image_height):
    # 1. First, try finding the bank name directly from OCR text
    # If the bank name is clearly printed (e.g. "Bank of Baroda", "State Bank of India"), this is ground truth!
    direct_name = extract_bank_name(ocr_results, image_height)
    if direct_name and direct_name != "Not Found":
        return direct_name

    # 2. Try finding IFSC code with an exact or high-confidence prefix match
    for item in ocr_results:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox or not text:
            continue
        clean_text = text.replace(" ", "")
        is_ifsc_line = bool(re.search(r'(?i)(IFSC|RTGS|NEFT|CODE|BRANCH)', clean_text))
        matches = re.finditer(r'(?=([A-Za-z]{4}[0Oo][A-Za-z0-9]{6}))', clean_text, re.IGNORECASE)
        for match in matches:
            ifsc = match.group(1).upper()
            if len(ifsc) >= 11 and ifsc[4] in ['O', 'o']:
                ifsc = ifsc[:4] + '0' + ifsc[5:]
            prefix = ifsc[:4]
            
            # Direct match
            for name, pfx in BANK_IFSC_PREFIX.items():
                if pfx == prefix:
                    return name
                    
            # Only do fuzzy prefix match if the line clearly relates to IFSC/banking codes
            if is_ifsc_line:
                known_prefixes = list(BANK_IFSC_PREFIX.values())
                close_prefixes = difflib.get_close_matches(prefix, known_prefixes, n=1, cutoff=0.74)
                if close_prefixes:
                    matched_prefix = close_prefixes[0]
                    for name, pfx in BANK_IFSC_PREFIX.items():
                        if pfx == matched_prefix:
                            return name
                        
    return "Not Found"

def crop_bank_specific(image, bank_name):
    h, w = image.shape[:2]
    rois = {}
    
    # Universal First Part logic for all banks: Left to Right 100%, Top 40%
    rois["First Part"] = image[0:int(0.40*h), 0:w]
    # Universal Second Part logic for all banks: Top 30% to Bottom 85%, Left to Right 70%
    rois["Second Part"] = image[int(0.30*h):int(0.85*h), 0:int(0.70*w)]
        
    return rois

BANK_ACCT_LENGTHS = {
    "STATE BANK OF INDIA": [11, 17],
    "STATE BANK": [11, 17],
    "HDFC BANK": [14],
    "ICICI BANK": [12],
    "AXIS BANK": [15],
    "KOTAK MAHINDRA BANK": [8, 14, 10],
    "INDUSIND BANK": [13, 14],
    "YES BANK": [15],
    "PUNJAB NATIONAL BANK": range(9, 17), 
    "BANK OF BARODA": [14],
    "BANK OF INDIA": [15],
    "CANARA BANK": [12, 13],
    "UNION BANK OF INDIA": [15],
    "UNION BANK": [15],
    "IDBI BANK": [12, 13],
    "INDIAN BANK": [9, 10, 11, 17],
    "CENTRAL BANK OF INDIA": [10],
    "UCO BANK": [14],
    "BANK OF MAHARASHTRA": [11],
    "FEDERAL BANK": [14],
    "SOUTH INDIAN BANK": [16],
    "KARNATAKA BANK": [16],
    "CITY UNION BANK": [15],
    "TAMILNAD MERCANTILE BANK": [15],
    "KARUR VYSYA BANK": [16],
    "INDIAN OVERSEAS BANK": [15],
    "PUNJAB AND SIND BANK": [14],
    "BANDHAN BANK": [15],
    "IDFC FIRST BANK": [14, 15],
    "RBL BANK": [15],
    "CSB BANK": [15],
    "DCB BANK": [14],
    "DHANLAXMI BANK": [15],
    "STANDARD CHARTERED BANK": [11],
    "CITIBANK": [10],
    "HSBC BANK": [12],
    "DBS BANK": [10, 12],
    "JAMMU AND KASHMIR BANK": [16],
    "DEUTSCHE BANK": range(10, 17), 
}

def extract_final_details(first_ocr, second_ocr, bank_name):
    clean_bank_name = str(bank_name).strip().upper() if bank_name and bank_name != "Not Found" else bank_name
    details = {
        "bank_name": clean_bank_name,
        "bankname": clean_bank_name,
        "account_number": "Not Found",
        "ifsc_code": "IFSC: NOT FOUND"
    }
    
    ifsc_pattern = re.compile(r'([A-Za-z]{4}[0Oo][A-Za-z0-9]{6})')
    acct_pattern = re.compile(r'\b\d{9,18}\b')
    
    # Combine both OCR results so we can find the details regardless of input format
    all_ocr = (first_ocr or []) + (second_ocr or [])
    if not all_ocr:
        details["account_number"] = "ACCOUNT: NOT FOUND"
        return details
        
    # Estimate image dimensions from bounding boxes for relative positioning
    max_h = 1000
    all_ys = []
    for item in all_ocr:
        bbox, _, _ = _unpack_ocr_item(item)
        if bbox:
            all_ys.extend([p[1] for p in bbox])
    if all_ys:
        max_h = max(all_ys)
        
    # 1. Extract IFSC Code
    for item in all_ocr:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox or not text or prob < 0.1:
            continue
        clean_text = text.strip()
        text_no_spaces = re.sub(r'[\s\-:,\./]', '', clean_text)
        
        found_code = None
        
        # Method A: Strict Regex with lookahead for overlapping matches
        matches = re.finditer(r'(?=([A-Za-z]{4}[0Oo][A-Za-z0-9]{6}))', text_no_spaces)
        for match in matches:
            candidate = match.group(1).upper()
            if len(candidate) >= 11 and candidate[4] in ['O', 'o']:
                candidate = candidate[:4] + '0' + candidate[5:]
                
            if candidate[:4] in ["CHQN", "LIDF", "VALI"]:
                continue
                
            expected_prefix = BANK_IFSC_PREFIX.get(bank_name)
            if expected_prefix:
                match_count = sum(1 for a, b in zip(candidate[:4], expected_prefix) if a == b)
                if match_count >= 2:
                    suffix = candidate[-6:].ljust(6, '0')[:6]
                    found_code = expected_prefix + '0' + suffix
                    break
            else:
                known_prefixes = list(BANK_IFSC_PREFIX.values())
                if candidate[:4] in known_prefixes:
                    found_code = candidate[:11]
                    break
                close = difflib.get_close_matches(candidate[:4], known_prefixes, n=1, cutoff=0.74)
                if close:
                    found_code = close[0] + '0' + candidate[5:11]
                    break
                    
        if not found_code:
            # Method B: Keyword search + trailing characters
            keyword_match = re.search(r'(?i)(?:IFSCODE|IFSC|IFS)\s*(?:CODE)?\s*[:\-]?\s*([A-Za-z]{4}[0Oo][A-Za-z0-9]{6})', text_no_spaces)
            if keyword_match:
                raw_code = keyword_match.group(1).upper()
                if len(raw_code) >= 11 and raw_code[4] in ['O', 'o']:
                    raw_code = raw_code[:4] + '0' + raw_code[5:]
                found_code = raw_code
                    
        if found_code:
            code = found_code
            if "IFS" in clean_text.upper():
                details["ifsc_code"] = code
                break
            elif details["ifsc_code"] == "IFSC: NOT FOUND":
                details["ifsc_code"] = code
                
    # 2. Locate Best Account Number Label Box
    labels = []
    for item in all_ocr:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox or not text or prob < 0.1:
            continue
        clean_text = text.strip()
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        cx = sum(xs) / 4.0
        cy = sum(ys) / 4.0
        rel_y = cy / float(max_h) if max_h > 0 else 0.5
        
        # Check for Account label (English or Hindi: खा. सं. / खाता संख्या)
        if re.search(r'(?i)(A/C|A\\C|A\.C|AC|ACCOUNT|ACC|खा\.?\s*सं|खाता)', clean_text):
            score = 0
            if re.search(r'(?i)(A/C\.?\s*NO|ACC\.?\s*NO|ACCOUNT\.?\s*NO|खा\.?\s*सं|खाता)', clean_text):
                score += 10
            if 0.30 <= rel_y <= 0.80:
                score += 5
            elif rel_y < 0.25:
                # Top header labels like "CASH CREDIT ACCOUNT" are account type, not the account number box
                score -= 5
            labels.append((score, (cx, cy), clean_text))
            
    labels.sort(key=lambda x: x[0], reverse=True)
    best_label = labels[0] if labels else None

    # Check for MICR bottom band account hint
    micr_hint = None
    for item in all_ocr:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox or not text:
            continue
        ys = [p[1] for p in bbox]
        cy = sum(ys) / 4.0
        if cy / float(max_h) > 0.75:
            cleaned_micr = re.sub(r'[^\d]', '', text)
            if len(cleaned_micr) >= 15:
                micr_hint = cleaned_micr

    # 3. Extract Account Number
    potential_accounts = []
    
    for item in all_ocr:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox or not text or prob < 0.1:
            continue
        clean_text = text.strip()
        
        # Rule 4: Do NOT include IFSC code, MICR code, phone number, cheque number, CIF, RS, etc.
        if re.search(r'(?i)(MICR|PH|TEL|MOB|CHQ|CHEQUE|CIF|REF|IFSC|CODE|DATE|RS|RUPEES|PAY)', clean_text):
            continue
            
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        cy = sum(ys) / 4.0
        cx = sum(xs) / 4.0
        rel_y = cy / float(max_h) if max_h > 0 else 0.5
        
        # Ignore items in bottom MICR strip (> 85% height)
        if rel_y > 0.85:
            continue
            
        text_no_spaces = re.sub(r'[\s\-:,\./]', '', clean_text)
        matches = acct_pattern.findall(text_no_spaces)
        
        for acct_val in matches:
            # Validate account length using the bank's known fixed lengths
            valid_lengths = BANK_ACCT_LENGTHS.get(bank_name)
            if valid_lengths:
                allowed_lengths = set(valid_lengths) if not isinstance(valid_lengths, range) else set(valid_lengths)
                margin_lengths = allowed_lengths.copy()
                for l in allowed_lengths:
                    margin_lengths.add(l - 1)
                    margin_lengths.add(l + 1)
                    
                if len(acct_val) not in margin_lengths:
                    continue
                    
            dist = float('inf')
            is_horiz = False
            has_ac_keyword = bool(re.search(r'(?i)(A/C|AC|ACCOUNT|ACC|SB|खा)', clean_text))
            
            if best_label:
                lx, ly = best_label[1]
                dx = abs(cx - lx)
                dy = abs(cy - ly)
                # Horizontally aligned to the right of the account label
                if dy < (0.08 * max_h if max_h > 0 else 40) and cx > lx:
                    is_horiz = True
                    dist = dx
                else:
                    dist = math.hypot(dx, dy * 3.0)
            else:
                dist = cy
                
            micr_match = False
            if micr_hint and len(acct_val) >= 6 and acct_val[-6:] in micr_hint:
                micr_match = True
                
            potential_accounts.append({
                "acct": acct_val,
                "has_keyword": has_ac_keyword,
                "horiz": is_horiz,
                "micr_match": micr_match,
                "distance": dist,
                "prob": prob
            })
            
    if potential_accounts:
        # Sort priority: MICR match > Horizontally aligned with label > Distance > Probability
        potential_accounts.sort(key=lambda x: (
            not x["micr_match"],
            not x["horiz"],
            x["distance"],
            -x["prob"]
        ))
        details["account_number"] = potential_accounts[0]["acct"]
    else:
        details["account_number"] = "ACCOUNT: NOT FOUND"
        
    # Cross-verify or resolve bank_name from IFSC prefix if available
    if details["ifsc_code"] and details["ifsc_code"] != "IFSC: NOT FOUND":
        prefix = details["ifsc_code"][:4]
        for b_name, pfx in BANK_IFSC_PREFIX.items():
            if pfx == prefix:
                details["bank_name"] = b_name.upper()
                break

    if details.get("bank_name") and details["bank_name"] != "Not Found":
        details["bank_name"] = str(details["bank_name"]).strip().upper()
    details["bankname"] = details.get("bank_name", "Not Found")
                
    return details

def extract_ifsc_after_keyword(ocr_items):
    """
    Find text 'IFSC' (or 'IFS CODE') in OCR items and extract the value immediately after it.
    Returns (cleaned_ifsc, matched_line, after_value) or (None, None, None).
    """
    for idx, item in enumerate(ocr_items):
        bbox, text, prob = _unpack_ocr_item(item)
        if not text:
            continue

        # 1. Match 'IFSC' keyword in this line and capture whatever value appears after it
        m = re.search(r'(?i)(?:RTGS\s*/?\s*NEFT\s*)?(?:IFS\s*CODE|IFSC\s*CODE|IFSC|IFS)\s*[:\-.\s]*\s*([A-Za-z0-9\s]{4,30})', text)
        if m:
            after_val = m.group(1).strip()
            cand = re.sub(r'[^A-Za-z0-9]', '', after_val).upper()
            if len(cand) >= 11:
                cand = cand[:11]
                if cand[4] in ['O', 'o']:
                    cand = cand[:4] + '0' + cand[5:]
                if re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', cand):
                    return cand, text, after_val

        # 2. If 'IFSC' keyword is in this line alone, look at the value in the immediately following items
        if re.search(r'(?i)\b(?:RTGS\s*/?\s*NEFT\s*)?(?:IFS\s*CODE|IFSC\s*CODE|IFSC|IFS)\b', text):
            for next_idx in range(idx + 1, min(idx + 4, len(ocr_items))):
                _, next_text, _ = _unpack_ocr_item(ocr_items[next_idx])
                if not next_text:
                    continue
                clean_next = re.sub(r'[^A-Za-z0-9]', '', next_text).upper()
                cand_match = re.search(r'([A-Z]{4}[0Oo][A-Z0-9]{6})', clean_next)
                if cand_match:
                    cand = cand_match.group(1)
                    if cand[4] in ['O', 'o']:
                        cand = cand[:4] + '0' + cand[5:]
                    return cand, f"{text} -> {next_text}", next_text

    return None, None, None

def get_ifsc_details_from_ifsccodebank(ifsc_code):
    """
    Fetches accurate branch name, pincode, bank name, and address details
    from https://www.ifsccodebank.com using the IFSC code.
    Webpage: https://www.ifsccodebank.com/ifsc-code-{ifsc_code}/ifsc
    """
    if not ifsc_code:
        return None
        
    code = str(ifsc_code).strip().upper()
    if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', code):
        return None

    url = f"https://www.ifsccodebank.com/ifsc-code-{code}/ifsc"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        info = {}
        for tr in soup.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if len(cells) == 2:
                k = cells[0].strip().upper().replace(':', '')
                v = cells[1].strip()
                if k and v:
                    info[k] = v

        if not info:
            return None

        bank = info.get("BANK", "").upper()
        branch = info.get("BRANCH", "").upper()
        pincode = info.get("PINCODE", "")
        address = info.get("ADDRESS", "")
        city = info.get("CITY", "").upper()
        district = info.get("DISTRICT", "").upper()
        state = info.get("STATE", "").upper()
        micr = info.get("MICR CODE", "") or info.get("MICR", "")

        if not pincode or len(pincode) != 6:
            pin_match = re.search(r'\b\d{6}\b', address)
            if pin_match:
                pincode = pin_match.group(0)

        # Refine branch if it's a building / tower name (e.g. GF SREE GOKULAM TOWERS -> GANDHIPURAM)
        building_indicators = [
            r'\bTOWERS?\b', r'\bBUILDING\b', r'\bCOMPLEX\b', r'\bESTATE\b',
            r'\bCHAMBERS?\b', r'\bPLAZA\b', r'\bPREMISES\b', r'\bFLOOR\b', r'\bGF\b'
        ]
        is_building_name = any(re.search(pat, branch, re.IGNORECASE) for pat in building_indicators)
        if is_building_name and address:
            localities = re.findall(r'(?:street|road|nagar|lane|block|near|opp|behind|floor|towers?)[\s,.-]*([a-zA-Z]{4,})', address, re.IGNORECASE)
            filtered = [loc.upper() for loc in localities if loc.upper() not in ['STREET', 'ROAD', 'NAGAR', 'LANE', 'BLOCK', 'FLOOR', 'TOWER', 'TOWERS']]
            if filtered:
                branch = filtered[-1]

        return {
            "BANK": bank,
            "BRANCH": branch.upper() if branch else "",
            "PINCODE": pincode,
            "ADDRESS": address,
            "CITY": city,
            "DISTRICT": district,
            "STATE": state,
            "MICR": micr,
            "IFSC": code,
            "bank": bank,
            "branch": branch.upper() if branch else "",
            "pincode": pincode,
            "address": address
        }
    except Exception as e:
        print(f"Error fetching from ifsccodebank: {e}")
        return None

def print_top_40_extraction(top_ocr, ifsc_code, bank_name, matched_ifsc_line=None, branch=None, pincode=None):
    """
    Print extracted data from the top 40% region of the cheque,
    including detected OCR lines, candidate IFSC code, mapped bank name, branch, and pincode.
    """
    encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'

    def _safe_str(val):
        if not isinstance(val, str):
            val = str(val)
        return val.encode(encoding, errors='replace').decode(encoding, errors='replace')

    print("\n" + "=" * 55)
    print("=== [STEP 1: TOP 40% EXTRACTION DATA] ===")
    print(f"Top 40% Detected Lines ({len(top_ocr)} lines):")
    for idx, item in enumerate(top_ocr):
        _, text_val, score_val = _unpack_ocr_item(item)
        if text_val:
            safe_text = _safe_str(text_val)
            print(f"  [{idx:02d}] ({score_val:.2f}) {safe_text}")
    if matched_ifsc_line:
        print(f"-> Matched IFSC Line   : {_safe_str(matched_ifsc_line)}")
    print(f"-> Extracted IFSC Code : {_safe_str(ifsc_code)}")
    print(f"-> Mapped Bank Name    : {_safe_str(bank_name)}")
    if branch:
        print(f"-> Branch Name         : {_safe_str(branch)}")
    if pincode:
        print(f"-> Pincode             : {_safe_str(pincode)}")
    print("=" * 55 + "\n")

def extract_cheque_from_file(file_input):
    """
    Public entry point for Flask/API use.
    Accepts a file path (str) or raw bytes.
    Returns a dict: {bank_name, account_number, ifsc_code, branch, pincode}

    Pipeline:
    1. Crop 40% from top -> extract text -> find IFSC -> map bank name based on IFSC.
    2. Query ifsccodebank.com to fetch branch and pincode using IFSC.
    3. Process remaining 60% of the image -> extract text -> find A/C number.
    """
    # --- Load image into numpy array ---
    if isinstance(file_input, bytes):
        img = Image.open(io.BytesIO(file_input))
    else:
        file_path = str(file_input)
        if file_path.lower().endswith('.pdf'):
            try:
                import pymupdf as fitz  # type: ignore  # PyMuPDF preferred for speed
                doc = fitz.open(file_path)
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            except Exception:
                import pdf2image  # type: ignore  # only needed for PDF fallback
                pages = pdf2image.convert_from_path(file_path, dpi=200)  # type: ignore
                img = pages[0]
        else:
            img = Image.open(file_path)

    img_array = np.array(img.convert('RGB'))

    # Auto-rotate vertical (portrait) images
    if img_array.shape[0] > img_array.shape[1]:
        img_array = np.rot90(img_array, k=1)

    # Detect & crop cheque
    _, cropped_img = detect_and_crop_cheque(img_array)
    processed_img = preprocess_for_ocr(cropped_img)
    h, w = processed_img.shape[:2]

    reader = load_ocr_reader()

    # Optimized Single-Pass OCR: Run detection & recognition once on full preprocessed image
    scaled_img = _safe_scale_for_ocr(processed_img, max_dim=1280)
    raw_ocr = reader.ocr(scaled_img)
    all_ocr = normalize_paddle_ocr_results(raw_ocr)
    scaled_h, scaled_w = scaled_img.shape[:2]

    # Geometrically partition detected items into top 40% region and bottom region
    top_ocr = []
    bottom_ocr = []
    for item in all_ocr:
        bbox, text, prob = _unpack_ocr_item(item)
        if not bbox:
            continue
        ys = [p[1] for p in bbox]
        cy = sum(ys) / len(ys) if ys else 0
        rel_y = cy / float(scaled_h) if scaled_h > 0 else 0
        if rel_y <= 0.42:
            top_ocr.append(item)
        if rel_y >= 0.35:
            bottom_ocr.append(item)

    # -------------------------------------------------------------
    # Step 1: Process top 40% region -> find IFSC -> map bank name
    # -------------------------------------------------------------
    ifsc_code = "IFSC: NOT FOUND"
    bank_name = "Not Found"
    matched_ifsc_line = None

    # Priority 1: Find text 'IFSC' and get the value immediately after it
    cand_ifsc, matched_line, _ = extract_ifsc_after_keyword(top_ocr)
    if cand_ifsc:
        ifsc_code = cand_ifsc
        matched_ifsc_line = matched_line
        prefix = ifsc_code[:4]
        for b_name, pfx in BANK_IFSC_PREFIX.items():
            if pfx == prefix:
                bank_name = b_name
                break

    # Priority 2: Fallback search if 'IFSC' keyword was not detected
    if ifsc_code == "IFSC: NOT FOUND":
        for item in top_ocr:
            bbox, text, prob = _unpack_ocr_item(item)
            if not text:
                continue
            clean_text = text.replace(" ", "")
            matches = re.finditer(r'(?=([A-Za-z]{4}[0Oo][A-Za-z0-9]{6}))', clean_text, re.IGNORECASE)
            for match in matches:
                candidate = match.group(1).upper()
                if len(candidate) >= 11 and candidate[4] in ['O', 'o']:
                    candidate = candidate[:4] + '0' + candidate[5:]
                prefix = candidate[:4]
                if prefix in ["CHQN", "LIDF", "VALI"]:
                    continue
                for b_name, pfx in BANK_IFSC_PREFIX.items():
                    if pfx == prefix:
                        ifsc_code = candidate
                        bank_name = b_name
                        matched_ifsc_line = text
                        break
                if ifsc_code != "IFSC: NOT FOUND":
                    break
            if ifsc_code != "IFSC: NOT FOUND":
                break

    # Fetch branch, pincode, and verified bank name from ifsccodebank.com using extracted IFSC
    branch_name = ""
    pincode_val = ""
    if ifsc_code and ifsc_code != "IFSC: NOT FOUND":
        ifsc_info = get_ifsc_details_from_ifsccodebank(ifsc_code)
        if ifsc_info:
            branch_name = ifsc_info.get("BRANCH", "")
            pincode_val = ifsc_info.get("PINCODE", "")
            if ifsc_info.get("BANK"):
                bank_name = ifsc_info["BANK"].upper()

    # If bank name wasn't resolved by IFSC, extract directly from top 40% text
    if bank_name == "Not Found":
        bank_name = extract_bank_name_with_fallback(top_ocr, int(0.40 * scaled_h))

    if bank_name and bank_name != "Not Found":
        bank_name = str(bank_name).strip().upper()

    # Call print function after extracting data from top 40%
    print_top_40_extraction(top_ocr, ifsc_code, bank_name, matched_ifsc_line, branch=branch_name, pincode=pincode_val)

    # -------------------------------------------------------------
    # Step 2: Process remaining 60% of image -> extract text -> find A/C number
    # -------------------------------------------------------------
    details = extract_final_details(bottom_ocr, [], bank_name)
    details["ifsc_code"] = ifsc_code
    details["ifsc"] = ifsc_code
    details["bank_name"] = bank_name.upper() if bank_name and bank_name != "Not Found" else bank_name
    details["branch"] = branch_name
    details["pincode"] = pincode_val

    # Instant Zero-Overhead Fallback: Search full OCR list directly without repeating neural net inference
    if details["account_number"] == "ACCOUNT: NOT FOUND" or details["ifsc_code"] == "IFSC: NOT FOUND":
        fallback_details = extract_final_details(all_ocr, [], bank_name)
        if details["account_number"] == "ACCOUNT: NOT FOUND":
            details["account_number"] = fallback_details.get("account_number", "ACCOUNT: NOT FOUND")
        if details["ifsc_code"] == "IFSC: NOT FOUND":
            details["ifsc_code"] = fallback_details.get("ifsc_code", "IFSC: NOT FOUND")
            details["ifsc"] = details["ifsc_code"]
        if details["bank_name"] == "Not Found":
            fb_bank = fallback_details.get("bank_name", "Not Found")
            details["bank_name"] = fb_bank.upper() if fb_bank and fb_bank != "Not Found" else fb_bank

    # Ensure both 'ifsc' and 'ifsc_code' keys are set for frontend compatibility
    details["ifsc"] = details.get("ifsc_code", ifsc_code)
    details["ifsc_code"] = details.get("ifsc", ifsc_code)

    # If branch or pincode was missed and valid IFSC is present, lookup again
    final_ifsc = details.get("ifsc") or details.get("ifsc_code") or ""
    if (not details.get("branch") or not details.get("pincode")) and final_ifsc and final_ifsc != "IFSC: NOT FOUND":
        extra_info = get_ifsc_details_from_ifsccodebank(final_ifsc)
        if extra_info:
            if not details.get("branch"):
                details["branch"] = extra_info.get("BRANCH", "")
            if not details.get("pincode"):
                details["pincode"] = extra_info.get("PINCODE", "")
            if extra_info.get("BANK"):
                details["bank_name"] = extra_info["BANK"].upper()

    # Ensure bank name is strictly uppercase in both bank_name and bankname fields
    if details.get("bank_name") and details["bank_name"] != "Not Found":
        details["bank_name"] = str(details["bank_name"]).strip().upper()
    else:
        details["bank_name"] = bank_name.upper() if bank_name and bank_name != "Not Found" else "Not Found"
    details["bankname"] = details["bank_name"]

    return details

