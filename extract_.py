import re
import os
import cv2
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def clean_extracted_name(name):
    """
    Strips leading noise prefix words, relation keywords, and short abbreviations
    from the extracted cardholder name.
    """
    if not name:
        return None
    words = name.split()
    clean_words = []
    for w in words:
        w_clean = w.strip(".,:-_`'\"| ")
        if not w_clean:
            continue
        # Reject relation keywords
        if w_clean.lower() in ["father", "mother", "husband", "wife", "son", "daughter", "relation", "parent", "to"]:
            continue
        # Reject short noise prefixes like "Fy", keep single-letter initials (like "C") or "C."
        if len(w_clean) < 3 and not w_clean.endswith('.') and len(w_clean) != 1:
            continue
        clean_words.append(w)
    
    if clean_words:
        return " ".join(clean_words)
    return None

def extract_address_from_ocr(texts):
    """
    Intelligently parses the English address from either the top-left 'To' block
    (extremely clean letter format) or the bottom-right 'Address:' block.
    Automatically filters out any Hindi-to-English OCR gibberish remnants.
    """
    # Heuristic A: Look for "To" letter address block
    for idx_t, text in enumerate(texts):
        if not text:
            continue
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for idx, line in enumerate(lines):
            if line.lower() == "to" or line.lower().startswith("to "):
                # The next line is likely the name, let's check up to 3 lines
                for offset in range(1, 4):
                    if idx + offset < len(lines):
                        potential_name = lines[idx + offset].strip(".,:-_`'\"| ")
                        # Match all-caps, title-case, and initials!
                        words = re.findall(r'\b[A-Z][A-Za-z]*\.?\b', potential_name)
                        if words and any(len(w.replace('.', '')) >= 3 for w in words):
                            # Name found! Address lines immediately follow
                            address_lines = []
                            for k in range(idx + offset + 1, len(lines)):
                                addr_line = lines[k].strip(".,:-_`'\"| ")
                                # Stop on typical footer or adjacent keywords
                                if any(stop_word in addr_line.lower() for stop_word in ["pin code", "mobile", "aadhaar", "vid", "enrolment", "your"]):
                                    pin_match = re.search(r'\b\d{6}\b', addr_line)
                                    if pin_match:
                                        address_lines.append(f"PIN Code: {pin_match.group(0)}")
                                    break
                                if len(address_lines) > 6 or "address" in addr_line.lower():
                                    break
                                
                                # Filter out full date strings like "25/06/2013"
                                if re.search(r'\b\d{2}/\d{2}/\d{4}\b', addr_line):
                                    continue
                                
                                # Filter Hindi gibberish (keep uppercase, titlecase, digits, punctuation)
                                words_in_line = addr_line.split()
                                clean_words = []
                                for w in words_in_line:
                                    w_stripped = w.strip(".,:-_`'\"|()[]{}")
                                    if not w_stripped:
                                        clean_words.append(w)
                                        continue
                                    if w_stripped.isupper() or w_stripped[0].isupper() or any(c.isdigit() for c in w_stripped):
                                        if w_stripped.startswith('s') and len(w_stripped) > 2 and w_stripped[1].isupper():
                                            w = w[1:]
                                        if w_stripped.startswith('g') and len(w_stripped) > 2 and w_stripped[1].isupper():
                                            w = w[1:]
                                        clean_words.append(w)
                                
                                clean_line = " ".join(clean_words).strip(" .,:-_`'\"|")
                                if clean_line:
                                    address_lines.append(clean_line)
                                    
                                # Break immediately once a 6-digit Indian PIN code line is read to prevent footer leaks
                                if re.search(r'\b\d{6}\b', addr_line):
                                    break
                            
                            if address_lines:
                                clean_lines = []
                                for al in address_lines:
                                    al_clean = al.strip()
                                    # Remove trailing isolated symbols (like ", {" or " |")
                                    al_clean = re.sub(r'[\s,\|\{\}\[\]]+[^A-Za-z0-9\(\)]$', '', al_clean)
                                    # Remove trailing single letters or digits preceded by space/comma (like ", 1" or ", g")
                                    al_clean = re.sub(r'[\s,\|]+[a-zA-Z0-9]$', '', al_clean)
                                    al_clean = al_clean.strip(" .,:-_`'\"|")
                                    if len(al_clean) <= 1:
                                        continue
                                    clean_lines.append(al_clean)
                                
                                address = ", ".join(clean_lines)
                                # Spaces around hyphens
                                address = re.sub(r'\s*-\s*', ' - ', address)
                                # Clean commas and return
                                address = re.sub(r'\s*,\s*', ', ', address)
                                address = re.sub(r',(\s*,)+', ',', address)
                                address = address.replace("VTC: ", "").replace("PIN Code: ", "").replace("PO: ", "").replace("District: ", "").replace("State: ", "").strip()
                                return address

    # Heuristic B: Look for bottom-right "Address:" block
    for idx_t, text in enumerate(texts):
        if not text:
            continue
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for idx, line in enumerate(lines):
            # Strict address label match
            lower_line = line.lower().strip(".,:-_`'\"| ")
            if lower_line == "address" or lower_line.startswith("address:") or lower_line.startswith("address :") or lower_line.startswith("addresss:") or lower_line.startswith("addresss :"):
                address_lines = []
                # Read the next 4 lines
                for k in range(idx, min(idx + 5, len(lines))):
                    addr_line = lines[k].strip(".,:-_`'\"| ")
                    
                    # Split into words and keep uppercase, titlecase, digits, parentheses
                    words = addr_line.split()
                    clean_words = []
                    for w in words:
                        w_stripped = w.strip(".,:-_`'\"|")
                        if not w_stripped:
                            continue
                        
                        # Clean leading lowercase prefixes first
                        w_temp = w_stripped
                        if w_temp.startswith('g') and len(w_temp) > 2 and w_temp[1].isupper():
                            w = w[1:]
                            w_temp = w_temp[1:]
                        if w_temp.startswith('s') and len(w_temp) > 2 and w_temp[1].isupper():
                            w = w[1:]
                            w_temp = w_temp[1:]
                        if w_temp.startswith('S') and len(w_temp) > 5 and w_temp[1].islower() and 'kerala' in w_temp.lower():
                            w = "Kerala" + w[len("Sikerala"):] if "Sikerala" in w else "Kerala"
                            w_temp = "Kerala"
                        
                        # Keep if uppercase, title-case, contains digits, or is inside parentheses/brackets
                        if w_temp.isupper() or w_temp[0].isupper() or any(c.isdigit() for c in w_temp) or (w_temp.startswith('(') and w_temp.endswith(')')) or (w_temp.startswith('[') and w_temp.endswith(']')):
                            w_clean = w.strip("|[]{} g")
                            clean_words.append(w_clean)
                    
                    clean_line = " ".join(clean_words).strip(" .,:-_`'\"|")
                    if k == idx:
                        clean_line = re.sub(r'(?i)address\s*:\s*', '', clean_line).strip()
                        clean_line = re.sub(r'(?i)addresss\s*:\s*', '', clean_line).strip()
                        clean_line = re.sub(r'(?i)address\s*', '', clean_line).strip()
                    
                    if clean_line and len(clean_line) > 1:
                        address_lines.append(clean_line)
                        # Break immediately if PIN code is read
                        if re.search(r'\b\d{6}\b', addr_line):
                            break
                
                if address_lines:
                    address = ", ".join(address_lines)
                    address = re.sub(r'\s*-\s*', ' - ', address)
                    address = re.sub(r'\s*,\s*', ', ', address)
                    address = re.sub(r',(\s*,)+', ',', address)
                    return address
                    
    return None
 
def extract_english_text_from_aadhaar(file_path):
    """
    Performs precise OCR on an Aadhaar card image and extracts ONLY the English text fields.
    Supports both standard cards, portrait letters, and vertical side-by-side scans.
    """
    if not os.path.exists(file_path):
        # Try local path as a fallback
        local_path = os.path.basename(file_path)
        if os.path.exists(local_path):
            file_path = local_path
        else:
            print(f"Error: Image file not found at '{file_path}'")
            return
 
    # 1. Load image
    img = cv2.imread(file_path)
    if img is None:
        print("Error: Corrupted or unsupported image file format.")
        return
 
    # 2. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
 
    # 3. Detect if this is a vertical side-by-side scan / A4 page letter
    is_side_by_side = False
    if h >= 1000 and w >= 800:
        is_side_by_side = True
 
    custom_config_6 = r'--oem 3 --psm 6'
    custom_config_3 = r'--oem 3 --psm 3'
 
    # Perform a default color pass (extremely clean on portrait scans)
    try:
        default_text = pytesseract.image_to_string(img)
    except Exception:
        default_text = ""
 
    if is_side_by_side:
        # Split vertically down the middle
        left_half = img[:, :w//2]
        right_half = img[:, w//2:]
        
        # Use crop_only_card to crop and isolate the actual cards
        cropped_left = crop_only_card(left_half)
        cropped_right = crop_only_card(right_half)
        
        left_card = cropped_left if cropped_left is not None else left_half
        right_card = cropped_right if cropped_right is not None else right_half
        
        left_gray = cv2.cvtColor(left_card, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right_card, cv2.COLOR_BGR2GRAY)
        
        # Split horizontally down the middle of both cropped splits
        lh, lw = left_gray.shape
        rh, rw = right_gray.shape
        left_bottom = left_gray[lh//2:, :]
        right_bottom = right_gray[rh//2:, :]
        
        try:
            left_bottom_text_3 = pytesseract.image_to_string(left_bottom, config=custom_config_3)
            left_bottom_text_6 = pytesseract.image_to_string(left_bottom, config=custom_config_6)
            right_bottom_text_3 = pytesseract.image_to_string(right_bottom, config=custom_config_3)
            right_bottom_text_6 = pytesseract.image_to_string(right_bottom, config=custom_config_6)
            
            left_text_6 = pytesseract.image_to_string(left_gray, config=custom_config_6)
            left_text_3 = pytesseract.image_to_string(left_gray, config=custom_config_3)
            right_text_6 = pytesseract.image_to_string(right_gray, config=custom_config_6)
            right_text_3 = pytesseract.image_to_string(right_gray, config=custom_config_3)
            
            full_text_6 = pytesseract.image_to_string(gray, config=custom_config_6)
            full_text_3 = pytesseract.image_to_string(gray, config=custom_config_3)
        except Exception as e:
            print("OCR Engine Error:", e)
            return
            
        front_texts = [left_bottom_text_3, left_bottom_text_6, left_text_3, left_text_6, default_text]
        all_texts = [left_bottom_text_3, left_bottom_text_6, right_bottom_text_3, right_bottom_text_6, left_text_3, left_text_6, right_text_3, right_text_6, default_text, full_text_3, full_text_6]
    else:
        try:
            full_text_6 = pytesseract.image_to_string(gray, config=custom_config_6)
            full_text_3 = pytesseract.image_to_string(gray, config=custom_config_3)
        except Exception as e:
            print("OCR Engine Error:", e)
            return
            
        front_texts = [default_text, full_text_3, full_text_6]
        all_texts = [default_text, full_text_3, full_text_6]

    extracted_fields = {
        "name": None,
        "dob": None,
        "gender": None,
        "aadhaar": None,
        "vid": None,
        "address": None
    }

    # Regex patterns
    dob_pattern = re.compile(r'\b\d{2}/\d{2}/\d{4}\b')
    # Support YOB (4-digit year like 1967)
    yob_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
    aadhaar_pattern = re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b')
    vid_pattern = re.compile(r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b')

    # Iterate lines to extract clean fields from front texts
    for text in front_texts:
        if not text:
            continue
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for idx, line in enumerate(lines):
            # a. DOB Match
            if dob_pattern.search(line) and any(k in line.lower() for k in ["dob", "birth", "gpb"]):
                match = dob_pattern.search(line)
                extracted_fields["dob"] = f"DOB: {match.group(0)}"
                
                # Backtrack Name
                for j in range(idx - 1, -1, -1):
                    prev_line = lines[j].strip(".,:-_`'\"| ")
                    # Reject lines with relation keywords
                    if any(rk in prev_line.lower() for rk in ["father", "mother", "husband", "wife", "son", "daughter", "relation", "parent", "to"]):
                        continue
                    words = re.findall(r'\b[A-Z][A-Za-z]*\.?\b', prev_line)
                    if words and any(len(w.replace('.', '')) >= 3 for w in words):
                        candidate_name = clean_extracted_name(" ".join(words))
                        if candidate_name:
                            extracted_fields["name"] = candidate_name
                            break
                            
            # a2. YOB Match
            elif yob_pattern.search(line) and any(k in line.lower() for k in ["birth", "dob", "yob"]):
                match = yob_pattern.search(line)
                if not extracted_fields["dob"]:
                    extracted_fields["dob"] = f"Year of Birth: {match.group(0)}"
                
                # Backtrack Name
                for j in range(idx - 1, -1, -1):
                    prev_line = lines[j].strip(".,:-_`'\"| ")
                    if any(rk in prev_line.lower() for rk in ["father", "mother", "husband", "wife", "son", "daughter", "relation", "parent", "to"]):
                        continue
                    words = re.findall(r'\b[A-Z][A-Za-z]*\.?\b', prev_line)
                    if words and any(len(w.replace('.', '')) >= 3 for w in words):
                        candidate_name = clean_extracted_name(" ".join(words))
                        if candidate_name:
                            extracted_fields["name"] = candidate_name
                            break
            
            # b. Gender Match
            if "male" in line.lower() or "female" in line.lower():
                gender = "FEMALE" if "female" in line.lower() else "MALE"
                extracted_fields["gender"] = gender

            # c. Aadhaar Number Match
            if aadhaar_pattern.search(line) and "vid" not in line.lower():
                match = aadhaar_pattern.search(line)
                extracted_fields["aadhaar"] = match.group(0)

            # d. VID Match
            if vid_pattern.search(line) or "vid" in line.lower():
                match = vid_pattern.search(line)
                if match:
                    extracted_fields["vid"] = f"VID : {match.group(0)}"
                elif re.search(r'\d{4}', line):
                    digits = "".join(re.findall(r'\d', line))
                    if len(digits) >= 16:
                        groups = [digits[i:i+4] for i in range(0, 16, 4)]
                        extracted_fields["vid"] = f"VID : {' '.join(groups)}"

    # If Aadhaar number wasn't found in front texts, try all texts
    if not extracted_fields["aadhaar"]:
        for text in all_texts:
            if not text:
                continue
            match = aadhaar_pattern.search(text)
            if match:
                extracted_fields["aadhaar"] = match.group(0)
                break

    # e. Address Match
    extracted_fields["address"] = extract_address_from_ocr(all_texts)

    # Print clean English text only
    print("--- EXTRACTED ENGLISH TEXT ---")
    if extracted_fields["name"]:
        print("Name:", extracted_fields["name"])
    if extracted_fields["dob"]:
        print(extracted_fields["dob"])
    if extracted_fields["gender"]:
        print("Gender:", extracted_fields["gender"])
    if extracted_fields["aadhaar"]:
        print("Aadhaar:", extracted_fields["aadhaar"])
    if extracted_fields["vid"]:
        print(extracted_fields["vid"])
    if extracted_fields["address"]:
        print("Address:", extracted_fields["address"])
    print("------------------------------")

def crop_only_card(img_or_path):
    """
    Crops only the card from the image by using thresholding + contour detection.
    Falls back to Canny edge-based contours or center-cropping if contours cannot be found.
    """
    if isinstance(img_or_path, str):
        img = cv2.imread(img_or_path)
    else:
        img = img_or_path
        
    if img is None:
        return None
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    # 1. Try thresholding + external contour detection
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_area = h * w
    best_box = None
    max_area = 0
    
    for cnt in contours:
        x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
        area = w_c * h_c
        aspect_ratio = float(w_c) / h_c
        if 0.15 * img_area < area < 0.98 * img_area:
            if 1.2 < aspect_ratio < 1.9:
                if area > max_area:
                    max_area = area
                    best_box = (x_c, y_c, w_c, h_c)
                    
    if best_box:
        x_c, y_c, w_c, h_c = best_box
        pad_x = int(w_c * 0.02)
        pad_y = int(h_c * 0.02)
        x1 = max(0, x_c - pad_x)
        y1 = max(0, y_c - pad_y)
        x2 = min(w, x_c + w_c + pad_x)
        y2 = min(h, y_c + h_c + pad_y)
        return img[y1:y2, x1:x2]
        
    # 2. Try Canny edge-based contours
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
        area = w_c * h_c
        aspect_ratio = float(w_c) / h_c
        if 0.15 * img_area < area < 0.98 * img_area:
            if 1.2 < aspect_ratio < 1.9:
                if area > max_area:
                    max_area = area
                    best_box = (x_c, y_c, w_c, h_c)
                    
    if best_box:
        x_c, y_c, w_c, h_c = best_box
        return img[y_c:y_c+h_c, x_c:x_c+w_c]
        
    # 3. Fallback to center 85% crop
    cy1, cy2 = int(h * 0.075), int(h * 0.925)
    cx1, cx2 = int(w * 0.075), int(w * 0.925)
    return img[cy1:cy2, cx1:cx2]

def clean_pan_field(val):
    if not val:
        return None
    val = val.strip(" .,:-_`'\"|()[]{}")
    val = re.sub(r'^[a-z]\s+', '', val)
    return val

def extract_pan_details(image_path):
    """
    Crops the PAN card first, then runs robust multi-pass OCR to extract
    the PAN number, Cardholder Name, Father's Name, and Date of Birth.
    """
    if not os.path.exists(image_path):
        # Try local path as fallback
        local_path = os.path.basename(image_path)
        if os.path.exists(local_path):
            image_path = local_path
        else:
            print(f"Error: PAN card image file not found at '{image_path}'")
            return None

    cropped = crop_only_card(image_path)
    if cropped is None:
        print("Error: Could not crop card.")
        return None
        
    config_3 = '--oem 3 --psm 3'
    config_6 = '--oem 3 --psm 6'
    
    try:
        text_3 = pytesseract.image_to_string(cropped, config=config_3)
        text_6 = pytesseract.image_to_string(cropped, config=config_6)
        text_color = pytesseract.image_to_string(cv2.imread(image_path))
    except Exception as e:
        print("OCR Engine Error:", e)
        return None
        
    all_passes = [text_3, text_6, text_color]
    
    pan_number = None
    name = None
    father_name = None
    dob = None
    
    pan_pattern = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')
    dob_pattern = re.compile(r'\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b')
    
    # 1. Parse PAN number
    for pas in all_passes:
        clean_pas = re.sub(r'\s+', ' ', pas)
        words = clean_pas.split()
        for w in words:
            w_clean = re.sub(r'\s+', '', w).upper()
            w_clean = w_clean.strip(".,:-_`'\"|()")
            if pan_pattern.match(w_clean):
                pan_number = w_clean
                break
        if pan_number:
            break
            
    # 2. Parse DOB
    for pas in all_passes:
        match = dob_pattern.search(pas)
        if match:
            dob = match.group(0)
            break
            
    # 3. Parse Cardholder Name
    for pas in all_passes:
        lines = [l.strip() for l in pas.split("\n") if l.strip()]
        for idx, line in enumerate(lines):
            # Check for cardholder name label strictly excluding father/mother/husband/ather/parent keywords
            if ("name" in line.lower() or "ta /name" in line.lower()) and not any(k in line.lower() for k in ["father", "mother", "husband", "parent", "ather"]):
                for offset in range(1, 3):
                    if idx + offset < len(lines):
                        potential_name = clean_pan_field(lines[idx + offset])
                        if potential_name and re.fullmatch(r"[A-Z\s]{3,}", potential_name) and "income" not in potential_name.lower():
                            name = potential_name
                            break
                if name:
                    break
                    
    # 4. Parse Father's Name
    for pas in all_passes:
        lines = [l.strip() for l in pas.split("\n") if l.strip()]
        for idx, line in enumerate(lines):
            if "father" in line.lower() or "ather's name" in line.lower() or "relation" in line.lower() or "parent" in line.lower():
                for offset in range(1, 3):
                    if idx + offset < len(lines):
                        potential_fname = clean_pan_field(lines[idx + offset])
                        if potential_fname and re.fullmatch(r"[A-Z\s]{3,}", potential_fname) and "income" not in potential_fname.lower():
                            father_name = potential_fname
                            break
                if father_name:
                    break

    print("--- EXTRACTED PAN DETAILS ---")
    print("PAN Number    :", pan_number)
    print("Name          :", name)
    print("Father's Name :", father_name)
    print("Date of Birth :", dob)
    print("-----------------------------")
    return {"pan_number": pan_number, "name": name, "father_name": father_name, "dob": dob}

VALID_PREFIXES = ["CIUB", "HDFC", "ICIC", "UTIB", "SBIN", "PUNB", "CNRB", "BARB", "YESB", "KKBK", "UBIN", "IDIB", "FDRL", "INDB", "IBKL", "SIBL"]

def extract_bank_details(file_path):
    """
    Extracts bank account details (IFSC, Account Number)
    from cheques and passbook images using OCR and advanced regex/heuristics.
    Multiple preprocessing passes (sharpening, CLAHE, resize) + PSM4/PSM3/PSM6
    ensure reliable extraction from low-contrast cheque images.
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist!")
        return None

    img = cv2.imread(file_path)
    if img is None:
        print(f"Error: Could not read image {file_path}")
        return None

    import numpy as np
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Preprocessing passes ──────────────────────────────────────────────────
    # 1. Sharpen the colour image (best for cheques with light pastel background)
    sharpen_kernel  = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened_color = cv2.filter2D(img, -1, sharpen_kernel)
    sharpened_gray  = cv2.cvtColor(sharpened_color, cv2.COLOR_BGR2GRAY)

    # 2. Standard resize passes on gray (2x and 1.5x for different font sizes)
    resized_gray    = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    resized_sharp   = cv2.resize(sharpened_gray, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
    resized_sharp_15 = cv2.resize(sharpened_gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LANCZOS4)

    # 3. CLAHE enhanced
    clahe           = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_gray      = clahe.apply(gray)
    resized_clahe   = cv2.resize(clahe_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # Run multiple OCR passes — PSM4 works well for cheques (single-column text blocks)
    passes_config = [
        (resized_sharp_15, '--oem 3 --psm 4'), # Primary 1: sharpened 1.5x, PSM4 (great for account numbers)
        (resized_sharp,  '--oem 3 --psm 4'),   # Primary 2: sharpened 2x, PSM4 (great for IFSC)
        (resized_sharp_15, '--oem 3 --psm 6'), # Sharpened 1.5x, PSM6
        (resized_sharp,  '--oem 3 --psm 6'),   # Sharpened 2x, PSM6
        (resized_gray,   '--oem 3 --psm 3'),   # Standard 2x, PSM3
        (resized_gray,   '--oem 3 --psm 6'),   # Standard 2x, PSM6
        (resized_clahe,  '--oem 3 --psm 4'),   # CLAHE 2x, PSM4
        (gray,           '--oem 3 --psm 3'),   # Original, PSM3
        (gray,           '--oem 3 --psm 6'),   # Original, PSM6
    ]

    all_passes = []
    for src, cfg in passes_config:
        try:
            all_passes.append(pytesseract.image_to_string(src, config=cfg))
        except Exception:
            all_passes.append("")

    ifsc = None
    account_number = None
    bank_name = None

    # A. Heuristics for IFSC Code
    # Standard IFSC: [A-Z]{4}0[A-Z0-9]{6} — position-5 is always digit '0'
    # OCR commonly misreads '0' as 'O', so we accept both in position 5.
    ifsc_pattern       = re.compile(r'\b([A-Za-z]{4})[0Oo]([A-Za-z0-9]{6})\b')
    ifsc_label_pattern = re.compile(r'IFSC[:\s]*([A-Za-z]{4}[0Oo][A-Za-z0-9]{6})', re.IGNORECASE)

    for pas in all_passes:
        # Try label-anchored match first (most reliable on cheques)
        label_match = ifsc_label_pattern.search(pas)
        if label_match:
            raw    = label_match.group(1).upper()
            prefix = raw[:4].replace('1', 'I').replace('0', 'O')
            suffix = raw[5:].replace('O', '0').replace('I', '1').replace('L', '1')
            candidate = f"{prefix}0{suffix}"
            if len(candidate) == 11:
                ifsc = candidate
                break

        # Fallback: broad pattern scan
        matches = ifsc_pattern.findall(pas)
        for m in matches:
            part1 = m[0].upper().replace('1', 'I').replace('0', 'O')
            part2 = m[1].upper().replace('O', '0').replace('G', '6').replace('I', '1').replace('L', '1').replace('l', '1')
            if 'g' in m[1].lower():
                part2 = part2.replace('G', '9')
            if part1 == "C1UB":
                part1 = "CIUB"
            if part1 in VALID_PREFIXES:
                candidate_ifsc = f"{part1}0{part2}"
                if len(candidate_ifsc) == 11:
                    ifsc = candidate_ifsc
                    break
        if ifsc:
            break

    # B. Heuristics for Account Number
    candidates = []
    
    # Try direct label match first (like A/C No. XXXXXXX)
    acc_label_pattern = re.compile(r'(?:a/c|account|acc no|acno|खा\.स\.|खाता|a/c\s*no\.?|a/c\s*no)[\s:.\-]*(\d{9,18})', re.IGNORECASE)

    for pas in all_passes:
        # First check for label match
        label_match = acc_label_pattern.search(pas)
        if label_match:
            # If we find a strong label match, add it with a very high score
            candidates.append((100, label_match.group(1)))

        lines = pas.split('\n')
        for line in lines:
            if not line.strip():
                continue

            # Skip MICR bottom line (cheque special symbols)
            if any(indicator in line for indicator in ['"', '⑈', 'O00', 'BOO', '@@', '\u201c', '\u201d']):
                continue

            # Merge spaces between digits (spaced account numbers on cheques)
            line_cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', line)
            line_cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', line_cleaned)

            # Extract all digit sequences 9–18 digits
            digits = re.findall(r'\b(\d{9,18})\b', line_cleaned)
            for d in digits:
                score = 5
                line_lower = line.lower()
                # High-confidence: explicit account keywords
                if any(kw in line_lower for kw in ['a/c', 'account', 'acc no', 'acno', 'खा.स.', 'खाता']):
                    score = 15
                elif any(kw in line_lower for kw in ['no.', 'no ', 'number', 'num']):
                    score = 10
                # Penalise cheque number lines
                if any(kw in line_lower for kw in ['chq', 'cheque', 'ch.no', 'chq.no']):
                    score = max(1, score - 8)
                candidates.append((score, d))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        account_number = candidates[0][1]

    # C. Heuristics for Bank Name
    for pas in all_passes:
        pas_upper = pas.upper()
        if "FEDERAL BANK" in pas_upper or "FDRL" in pas_upper:
            bank_name = "FEDERAL BANK"
            break
        elif "CITY UNION BANK" in pas_upper or "CUB" in pas_upper:
            bank_name = "CITY UNION BANK"
            break
        elif "HDFC" in pas_upper:
            bank_name = "HDFC BANK"
            break
        elif "ICICI" in pas_upper:
            bank_name = "ICICI BANK"
            break

    # D. ICICI Bank Specific Branch Fallback
    if bank_name == "ICICI BANK" and not ifsc and account_number and len(account_number) == 12:
        branch_code = account_number[:4]
        ifsc = f"ICIC000{branch_code}"

    print(f"\n--- EXTRACTED BANK DETAILS ({os.path.basename(file_path)}) ---")
    print("IFSC Code      :", ifsc)
    print("Account Number :", account_number)
    print("Bank Name      :", bank_name)
    print("-------------------------------------------------------------")

    return {
        "ifsc": ifsc,
        "account_number": account_number,
        "bank_name": bank_name
    }

if __name__ == '__main__':
    # Run the PAN card extraction test
    pan_image = r"D:\Projects\DocumentsTeam\WhatsApp Image 2026-05-18 at 10.35.15 AM (1).jpeg"
    extract_pan_details(pan_image)

    # Run the Bank Cheque extraction tests
    print("\n=== RUNNING BANK CHEQUE EXTRACTION TESTS ===")
    cheques = [
        r"D:\Projects\DocumentsTeam\cub cheque.jpeg",
        r"D:\Projects\DocumentsTeam\hdfc cheque.jpeg",
        r"D:\Projects\DocumentsTeam\icici cheque.jpeg"
    ]
    for chq in cheques:
        extract_bank_details(chq)
