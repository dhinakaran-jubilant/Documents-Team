import os
import sys

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

for k in list(sys.modules.keys()):
    if k.startswith('google.protobuf'):
        del sys.modules[k]


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

_OCR_READER = None

def load_ocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        from paddleocr import PaddleOCR
        # det_limit_type='max' with det_limit_side_len=1500 caps the longest side
        # enable_mkldnn=False resolves the PIR ConvertPirAttribute2RuntimeAttribute crash on CPU
        _OCR_READER = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            det_limit_type='max',
            det_limit_side_len=1500,
            det_db_unclip_ratio=2.0,
            enable_mkldnn=False
        )
    return _OCR_READER

def _safe_scale_for_ocr(image, max_dim=2000):
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
    
    # Find all contours (RETR_LIST to ensure we don't miss the outer one if hierarchy is weird)
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
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

def extract_bank_name(ocr_results, image_height):
    potential_banks = []
    
    for bbox, (text, prob) in ocr_results:
        clean_text = text.strip()
        if prob < 0.1:
            continue
            
        text_no_spaces = re.sub(r'[\s\-:,\.]', '', clean_text)
        
        y_coords = [p[1] for p in bbox]
        y_center = sum(y_coords) / 4.0
        relative_y = y_center / float(image_height)
        
        if relative_y < 0.50:
            if re.search(r'(BANK|LTD|LIMITED|INDIA|UNION|HDFC|ICICI|SBI|AXIS|FEDERAL|CUB)', clean_text, re.IGNORECASE) or \
               re.search(r'(BANK|LTD|LIMITED|INDIA)', text_no_spaces, re.IGNORECASE):
                potential_banks.append((prob, clean_text))
                
    if not potential_banks:
        return "Not Found"
        
    def score_bank(text):
        if re.search(r'(?i)\b(BANK|UNION|HDFC|ICICI|SBI|AXIS|FEDERAL|CUB)\b', text):
            return 2
        if re.search(r'(?i)(LTD|LIMITED|INDIA)', text):
            return 1
        return 0
        
    potential_banks.sort(key=lambda x: (score_bank(x[1]), x[0]), reverse=True)
    best_match = potential_banks[0][1]
    
    match = re.search(r'(?i)(.*?(?:BANK|LTD|LIMITED|INDIA|UNION|HDFC|ICICI|SBI|AXIS|FEDERAL|CUB))', best_match)
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
            
    import difflib
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
    # 1. Try finding IFSC first, as it's deterministic and highly accurate
    for bbox, (text, prob) in ocr_results:
        clean_text = text.replace(" ", "")
        # Use lookahead to find all overlapping 11-char patterns
        matches = re.finditer(r'(?=([A-Z]{4}[0Oo][A-Z0-9]{6}))', clean_text, re.IGNORECASE)
        for match in matches:
            ifsc = match.group(1).upper()
            prefix = ifsc[:4]
            
            # Fuzzy match the prefix to handle 1-character OCR errors (like BARS -> BARB)
            import difflib
            known_prefixes = list(BANK_IFSC_PREFIX.values())
            close_prefixes = difflib.get_close_matches(prefix, known_prefixes, n=1, cutoff=0.74)
            
            if close_prefixes:
                matched_prefix = close_prefixes[0]
                for name, pfx in BANK_IFSC_PREFIX.items():
                    if pfx == matched_prefix:
                        return name
                        
    # 2. If no valid IFSC found, fall back to the fuzzy text matching
    return extract_bank_name(ocr_results, image_height)

def crop_bank_specific(image, bank_name):
    h, w = image.shape[:2]
    rois = {}
    
    # Universal First Part logic for all banks: Left to Right 100%, Top 40%
    rois["First Part"] = image[0:int(0.40*h), 0:w]
    # Universal Second Part logic for all banks: Top 30% to Bottom 80%, Left to Right 50%
    rois["Second Part"] = image[int(0.30*h):int(0.80*h), 0:int(0.50*w)]
        
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
    details = {
        "bank_name": bank_name,
        "account_number": "Not Found",
        "ifsc_code": "IFSC: NOT FOUND"
    }
    
    ifsc_pattern = re.compile(r'([A-Za-z]{4}[0Oo][A-Za-z0-9]{6})')
    acct_pattern = re.compile(r'\d{9,18}')
    
    # Combine both OCR results so we can find the details regardless of which part they landed in
    all_ocr = first_ocr + second_ocr
    
    # 1. Extract IFSC Code
    for bbox, (text, prob) in all_ocr:
        if prob < 0.1: continue
        clean_text = text.strip()
        text_no_spaces = re.sub(r'[\s\-:,\./]', '', clean_text)
        
        # Strip common labels that merge with the code and cause false positive matches
        text_no_spaces_for_ifsc = re.sub(r'(?i)(RTGS|NEFT|IFSC|IFSCODE|IFS|CODE)', '', text_no_spaces)
        
        found_code = None
        
        # Method A: Strict Regex with lookahead for overlapping matches
        matches = re.finditer(r'(?=([A-Za-z]{4}[0Oo][A-Za-z0-9]{6}))', text_no_spaces_for_ifsc)
        for match in matches:
            candidate = match.group(1).upper()
            
            if candidate[:4] in ["CHQN"]:
                continue
                
            expected_prefix = BANK_IFSC_PREFIX.get(bank_name)
            if expected_prefix:
                match_count = sum(1 for a, b in zip(candidate[:4], expected_prefix) if a == b)
                if match_count >= 2:
                    suffix = candidate[-6:].ljust(6, '0')[:6]
                    found_code = expected_prefix + '0' + suffix
                    break # Found a valid candidate!
            else:
                import difflib
                known_prefixes = list(BANK_IFSC_PREFIX.values())
                if difflib.get_close_matches(candidate[:4], known_prefixes, n=1, cutoff=0.74):
                    if len(candidate) >= 11 and candidate[4] == 'O':
                        candidate = candidate[:4] + '0' + candidate[5:]
                    found_code = candidate[:11]
                    break
                    
        if not found_code:
            # Method B: Keyword search + trailing characters
            keyword_match = re.search(r'(?i)(?:IFSCODE|IFSC|IFS)(.{6,15})', text_no_spaces)
            if keyword_match:
                raw_code = keyword_match.group(1).upper()
                raw_code = re.sub(r'[^A-Z0-9]', '', raw_code)
                if len(raw_code) >= 6:
                    found_code = raw_code
                    
        if found_code:
            code = found_code
            
            if "IFS" in clean_text.upper():
                details["ifsc_code"] = code
                break
            elif details["ifsc_code"] == "IFSC: NOT FOUND":
                details["ifsc_code"] = code
                
    # 2. Extract Account Number
    # First, try to locate the physical center of the Account Number label if it's in its own box
    ac_label_center = None
    import math
    for bbox, (text, prob) in all_ocr:
        if prob < 0.1: continue
        # Look for explicit labels
        if re.search(r'(?i)\b(A/C|A\\C|AC|ACCOUNT|ACC|SB)\b', text.replace('.', '').replace('/', '')):
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            ac_label_center = (sum(xs)/4.0, sum(ys)/4.0)
            break
            
    potential_accounts = []
    for bbox, (text, prob) in all_ocr:
        if prob < 0.1: continue
        clean_text = text.strip()
        
        # Rule 4: Do NOT include IFSC code, MICR code, phone number, cheque number, CIF, etc.
        if re.search(r'(?i)(MICR|PH|TEL|MOB|CHQ|CHEQUE|CIF|REF|IFSC|CODE)', clean_text):
            continue
            
        text_no_spaces = re.sub(r'[\s\-:,\./]', '', clean_text)
        
        acct_match = acct_pattern.search(text_no_spaces)
        if acct_match:
            acct_val = acct_match.group()
            
            # Validate account length using the bank's known fixed lengths
            valid_lengths = BANK_ACCT_LENGTHS.get(bank_name)
            if valid_lengths:
                if isinstance(valid_lengths, range):
                    allowed_lengths = set(valid_lengths)
                else:
                    allowed_lengths = set(valid_lengths)
                
                # Allow +/- 1 digit margin for OCR clipping errors
                margin_lengths = allowed_lengths.copy()
                for l in allowed_lengths:
                    margin_lengths.add(l - 1)
                    margin_lengths.add(l + 1)
                    
                if len(acct_val) not in margin_lengths:
                    continue
            
            # Rule 9: Prefer an account number appearing near labels
            has_ac_keyword = bool(re.search(r'(?i)(A/C|AC|ACCOUNT|ACC|SB)', clean_text))
            
            # Rule 6: If the OCR text contains a number with spaces/separators, combine the digits 
            # ONLY if the surrounding context clearly identifies it as an account number.
            if acct_val not in clean_text:
                if not has_ac_keyword:
                    continue
                    
            # Calculate physical distance to the label box (if found)
            dist = float('inf')
            if ac_label_center:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                box_center = (sum(xs)/4.0, sum(ys)/4.0)
                dist = math.hypot(box_center[0] - ac_label_center[0], box_center[1] - ac_label_center[1])
                
            potential_accounts.append({
                "acct": acct_val,
                "has_keyword": has_ac_keyword,
                "distance": dist,
                "prob": prob
            })
            
    if potential_accounts:
        # Rule 10: Select the value explicitly associated with the label (physically closest or in same box)
        potential_accounts.sort(key=lambda x: (not x["has_keyword"], x["distance"], -x["prob"]))
        details["account_number"] = potential_accounts[0]["acct"]
    else:
        # Rule 12: If no reliable account number is found
        details["account_number"] = "ACCOUNT: NOT FOUND"
        
    return details

def extract_cheque_from_file(file_input):
    """
    Public entry point for Flask/API use.
    Accepts a file path (str) or raw bytes.
    Returns a dict: {bank_name, account_number, ifsc_code}
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

    # Step 1 — Detect & crop cheque
    _, cropped_img = detect_and_crop_cheque(img_array)

    # Step 2 — Preprocess for OCR
    processed_img = preprocess_for_ocr(cropped_img)

    # Step 3 — Load PaddleOCR reader (singleton)
    reader = load_ocr_reader()

    # Step 4 — Extract bank details from top 40%
    h, w = processed_img.shape[:2]
    top_40_img = processed_img[0:int(0.40 * h), 0:w]
    top_40_scaled = _safe_scale_for_ocr(top_40_img, max_dim=2000)
    
    full_ocr_results = reader.ocr(top_40_scaled)
    full_ocr_results = full_ocr_results[0] if full_ocr_results and full_ocr_results[0] else []

    height = top_40_scaled.shape[0]
    bank_name = extract_bank_name_with_fallback(full_ocr_results, height)

    # Step 5 — Bank-specific deep crop
    rois = crop_bank_specific(processed_img, bank_name)

    first_roi  = _safe_scale_for_ocr(rois.get("First Part",  np.zeros((10, 10, 3), dtype=np.uint8)), max_dim=2000)
    second_roi = _safe_scale_for_ocr(rois.get("Second Part", np.zeros((10, 10, 3), dtype=np.uint8)), max_dim=2000)

    # Step 6 — OCR on ROIs
    first_ocr  = reader.ocr(first_roi)
    first_ocr  = first_ocr[0]  if first_ocr  and first_ocr[0]  else []

    second_ocr = reader.ocr(second_roi)
    second_ocr = second_ocr[0] if second_ocr and second_ocr[0] else []

    # Step 7 — Extract final details
    return extract_final_details(first_ocr, second_ocr, bank_name)
