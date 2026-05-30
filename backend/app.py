"""
Project: Fin Report - Documents team
Author: Dhinakaran Sekar
Email: dhinakaran.s@jubilantenterprises.in
Date: 2026-04-30 18:41
Description: Main Backend Flask application for handling file uploads, PDF generation, and user authentication.
"""

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import os
import tempfile
import atexit
import shutil
import json
import re
import pdfplumber
import cv2
import pytesseract
from utils.pdf_generator import process_excel_to_pdfs, create_zip_archive
from utils.promissory_generator import fill_promissory_note_docx, fill_letterpad_docx, fill_ltrl_docx, fill_letter_of_undertaking_docx
import requests
import sys
# Add parent directory to sys.path so we can import extract_
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extract_ import extract_bank_details

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
app = Flask(__name__)
# Database Configuration (SQLite for DocumentsTeam)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///documents.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize database and seed admin user
with app.app_context():
    db.create_all()
    # Check and add missing columns dynamically to support database evolution safely
    try:
        from sqlalchemy import text
        db.session.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(100)"))
        db.session.commit()
        print("Successfully added email column to users table")
    except Exception:
        db.session.rollback()
        
    try:
        from sqlalchemy import text
        db.session.execute(text("ALTER TABLE users ADD COLUMN accessed_menus VARCHAR(255) DEFAULT 'fin-report,documat'"))
        db.session.commit()
        print("Successfully added accessed_menus column to users table")
    except Exception:
        db.session.rollback()
    
    # Remove the old admin user if it exists
    old_admin = User.query.filter_by(employee_code='JC0033').first()
    if old_admin:
        db.session.delete(old_admin)
        db.session.commit()
        print("Removed old admin user: JC0033")

    # Clean up lowercase 'admin' user by converting or deleting
    lowercase_admin = User.query.filter_by(employee_code='admin').first()
    if lowercase_admin:
        db.session.delete(lowercase_admin)
        db.session.commit()
        print("Removed legacy lowercase admin user")

    # Seed the new default admin user in uppercase
    admin_user = User.query.filter_by(employee_code='ADMIN').first()
    if not admin_user:
        admin_user = User(
            employee_code='ADMIN',
            password=generate_password_hash('Admin@123'),
            name='System Admin',
            role='admin',
            is_initial_password=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Seeded default admin user: ADMIN / Admin@123")
    elif admin_user.is_initial_password:
        # Ensure password matches the requested default if still in initial state
        admin_user.password = generate_password_hash('Admin@123')
        db.session.commit()
        print("Updated existing admin user password to: Admin@123")

# Enable CORS for React frontend (default dev port 5173 for vite)
CORS(app, resources={r"/*": {"origins": "*", "expose_headers": ["X-Process-Time", "Content-Disposition"]}})

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
                    address = address.replace("VTC: ", "").replace("PIN Code: ", "").replace("PO: ", "").replace("District: ", "").replace("State: ", "").strip()
                    return address
                    
    return None

def crop_only_card(img):
    """
    Crops only the card from the image by using thresholding + contour detection.
    Falls back to Canny edge-based contours or center-cropping if contours cannot be found.
    """
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

def extract_pan_details_from_img(file_path, img):
    """
    Crops the PAN card first, then runs robust multi-pass OCR to extract
    the PAN number, Cardholder Name, Father's Name, and Date of Birth.
    """
    cropped = crop_only_card(img)
    if cropped is None:
        cropped = img
        
    config_3 = '--oem 3 --psm 3'
    config_6 = '--oem 3 --psm 6'
    
    try:
        text_3 = pytesseract.image_to_string(cropped, config=config_3)
        text_6 = pytesseract.image_to_string(cropped, config=config_6)
        text_color = pytesseract.image_to_string(img)
    except Exception as e:
        text_3, text_6, text_color = "", "", ""
        
    all_passes = [text_3, text_6, text_color]
    full_text = "\n".join(all_passes)
    
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

    return {
        "document_type": "pan",
        "name": name,
        "father_name": father_name,
        "pan_number": pan_number,
        "dob": dob,
        "address": None,
        "raw_text": full_text
    }

def extract_text_from_img(file_path):
    """
    Performs robust OCR on an image. First classifies whether the document is
    an Aadhaar card or a PAN card, then routes to the appropriate extraction engine.
    """
    if not os.path.exists(file_path):
        return {"error": "Image file not found", "name": None, "raw_text": ""}

    img = cv2.imread(file_path)
    if img is None:
        return {"error": "Corrupted or unsupported image file format", "name": None, "raw_text": ""}

    # Grayscale Conversion
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Light-weight OCR pass to classify the image as Aadhar or PAN
    try:
        first_pass_text = pytesseract.image_to_string(img)
    except Exception as e:
        first_pass_text = ""

    lower_text = re.sub(r'\s+', ' ', first_pass_text).lower()
    
    # Classification rules
    is_pan = False
    pan_pattern = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')
    if any(k in lower_text for k in ["permanent", "income tax", "department", "pancard", "permanent account"]) or pan_pattern.search(first_pass_text.upper()):
        is_pan = True

    if is_pan:
        return extract_pan_details_from_img(file_path, img)

    # 2. Detect side-by-side scan / A4 page letter layout
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
            return {"error": f"OCR Engine Error: {str(e)}", "name": None, "raw_text": ""}
            
        front_texts = [left_bottom_text_3, left_bottom_text_6, left_text_3, left_text_6, default_text]
        all_texts = [left_bottom_text_3, left_bottom_text_6, right_bottom_text_3, right_bottom_text_6, left_text_3, left_text_6, right_text_3, right_text_6, default_text, full_text_3, full_text_6]
    else:
        try:
            full_text_6 = pytesseract.image_to_string(gray, config=custom_config_6)
            full_text_3 = pytesseract.image_to_string(gray, config=custom_config_3)
        except Exception as e:
            return {"error": f"OCR Engine Error: {str(e)}", "name": None, "raw_text": ""}
            
        front_texts = [default_text, full_text_3, full_text_6]
        all_texts = [default_text, full_text_3, full_text_6]

    text = "\n".join([t for t in all_texts if t])

    # Parse Card Fields from front texts specifically
    name = None
    extracted_fields = {
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

    # Iterate lines to extract clean fields
    for text_pass in front_texts:
        if not text_pass:
            continue
        lines = [line.strip() for line in text_pass.split("\n") if line.strip()]
        for idx, line in enumerate(lines):
            # a. DOB Match
            if dob_pattern.search(line) and any(k in line.lower() for k in ["dob", "birth", "gpb"]):
                match = dob_pattern.search(line)
                extracted_fields["dob"] = f"DOB: {match.group(0)}"
                
                # Backtrack Name
                for j in range(idx - 1, -1, -1):
                    prev_line = lines[j].strip(".,:-_`'\"| ")
                    if any(rk in prev_line.lower() for rk in ["father", "mother", "husband", "wife", "son", "daughter", "relation", "parent", "to"]):
                        continue
                    words = re.findall(r'\b[A-Z][A-Za-z]*\.?\b', prev_line)
                    if words and any(len(w.replace('.', '')) >= 3 for w in words):
                        candidate_name = clean_extracted_name(" ".join(words))
                        if candidate_name:
                            name = candidate_name
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
                            name = candidate_name
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

    # Fallback to general line-by-line checks if DOB match not found
    if not name:
        skip_keywords = {
            "government", "india", "dob", "male", "female", 
            "download", "issue", "vid", "address", "enrollment",
            "father", "mother", "husband", "wife", "year", "birth"
        }
        for text_pass in front_texts:
            if not text_pass:
                continue
            lines = [line.strip() for line in text_pass.split("\n") if line.strip()]
            for line in lines:
                cleaned_line = line.strip(".,:-_`'\" ")
                if any(word in cleaned_line.lower() for word in skip_keywords):
                    continue
                if re.fullmatch(r"[A-Za-z\.\s]{3,}", cleaned_line):
                    words = cleaned_line.split()
                    if 1 <= len(words) <= 4:
                        candidate_name = clean_extracted_name(cleaned_line)
                        if candidate_name:
                            name = candidate_name
                            break
            if name:
                break

    # Extract the address
    address = extract_address_from_ocr(all_texts)
    
    father_name = None
    # 1. Highly robust raw text search over all passes (handles OCR misreads and contour crop failures)
    father_pattern = re.compile(
        r'\b(?:[SDWC][\s/\\|1I\.]\s*[Oo0]\b|Care\s+of\b|Father(?:\'s)?(?:\s+Name)?\b|Husband(?:\'s)?(?:\s+Name)?\b|Mother(?:\'s)?(?:\s+Name)?\b)[\s:\-]*([A-Z][A-Za-z\s\.\-]{2,40})',
        re.IGNORECASE
    )
    match = father_pattern.search(text)
    if match:
        candidate = match.group(1).split('\n')[0].strip(" .,:-_`'\"|")
        # Exclude common address/footer keywords to ensure high precision
        if not any(k in candidate.lower() for k in ["address", "pin", "code", "near", "opposite", "floor", "house", "ward"]):
            father_name = candidate

    # 2. Fallback search anywhere in the clean address string
    if not father_name and address:
        match = re.search(r'\b(?:S/O|D/O|W/O|C/O|C/o|S/o|D/o|W/o|Care of)[\s:\-]*([^,\n]+)', address, re.IGNORECASE)
        if match:
            father_name = match.group(1).strip(" .,:-_`'\"|")

    return {"document_type": "aadhaar", "name": name, "father_name": father_name, "gender": extracted_fields.get("gender"), "address": address, "raw_text": text}

def parse_extracted_text(text):
    # Extract fields
    legal_name = None
    trade_name = None
    business_address = None
    business_constitution = None
    signature_valid = False

    # Legal Name
    match = re.search(r"Legal Name\s+(.+)", text)
    if match:
        legal_name = match.group(1).strip()

    # Trade Name
    match = re.search(r"Trade Name, if any\s+(.+)", text)
    if match:
        trade_name = match.group(1).strip()

    # Address of Principal Place of Business
    match = re.search(
        r"Address of Principal Place of(.*?)(?=\bDate of Liability\b|\bDate of Issue\b|\bPeriod of Validity\b|\bType of Registration\b|\n\s*\d+\.\s|$)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if match:
        raw_address = match.group(1)
        raw_address = re.sub(r'^\s*Business\s*', ' ', raw_address, flags=re.IGNORECASE)
        raw_address = re.sub(r'\n\s*Business\s*', '\n', raw_address, flags=re.IGNORECASE)
        business_address = " ".join(raw_address.split())

        # Format the address to ensure pincode comes before state with a hyphen (e.g. District - Pincode, State)
        pin_end = re.search(r'(.*?)[,\s\-]+([A-Za-z\s]+)[,\s\-]+(\d{6})\.?$', business_address)
        if pin_end:
            rest = pin_end.group(1).strip().strip(',').strip('-').strip()
            state = pin_end.group(2).strip()
            pin = pin_end.group(3)
            business_address = f"{rest} - {pin}, {state}."
        else:
            pin_mid = re.search(r'(.*?)[,\s\-]+(\d{6})[,\s\-]+([A-Za-z\s]+)\.?$', business_address)
            if pin_mid:
                rest = pin_mid.group(1).strip().strip(',').strip('-').strip()
                pin = pin_mid.group(2)
                state = pin_mid.group(3).strip()
                business_address = f"{rest} - {pin}, {state}."

    # District
    district = None
    dist_match = re.search(r"District\s*[-:]?\s*([^,.\n]+)", text, re.IGNORECASE)
    if dist_match:
        district = dist_match.group(1).strip()
    elif business_address:
        dist_match = re.search(r"District\s*[-:]?\s*([^,.]+)", business_address, re.IGNORECASE)
        if dist_match:
            district = dist_match.group(1).strip()
        else:
            # Fallback: extract place/district that immediately precedes the pincode (e.g., "Kottayam-686573" -> "Kottayam")
            fallback_match = re.search(r'([^,\s][^,]+?)\s*[-]?\s*(\d{6})\b', business_address)
            if fallback_match:
                district = fallback_match.group(1).strip()

    # Registration Number (GSTIN)
    pan_number = None
    reg_match = re.search(r"Registration Number\s*[-:]?\s*([a-zA-Z0-9]{15})", text, re.IGNORECASE)
    if reg_match:
        registration_number = reg_match.group(1).strip().upper()
        pan_number = registration_number[2:12]
    else:
        # Fallback to standard 15-character GSTIN regex pattern
        gstin_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Zz]{1}[A-Z\d]{1}\b", text)
        if gstin_match:
            registration_number = gstin_match.group(0).strip().upper()
            pan_number = registration_number[2:12]

    # Final Output
    result = {
        "legal_name": legal_name,
        "trade_name": trade_name,
        "pan_number": pan_number,
        "business_address": business_address,
        "district": district
    }

    return result

def extract_text_from_pdf(pdf_path):
    # Read PDF text
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return parse_extracted_text(text)

@app.route('/extract-pdf', methods=['POST'])
def handle_extract_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    filename_lower = file.filename.lower()
    
    # 1. Handle PDF
    if filename_lower.endswith('.pdf'):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                file.save(temp_pdf.name)
                temp_pdf_path = temp_pdf.name
                
            result = extract_text_from_pdf(temp_pdf_path)
            result["document_type"] = "gst"
            
            # Clean up the file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                
            return jsonify({"success": True, "data": result})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    # 2. Handle Images (PNG, JPG, JPEG, WEBP, BMP)
    elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
        try:
            print(filename_lower)
            suffix = os.path.splitext(filename_lower)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_img:
                file.save(temp_img.name)
                temp_img_path = temp_img.name
                
            # Perform OCR on the image
            ocr_res = extract_text_from_img(temp_img_path)
            
            # Clean up the file
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
            if "error" in ocr_res:
                return jsonify({"error": ocr_res["error"]}), 400
                
            raw_text = ocr_res.get("raw_text", "")
            
            # If document_type is PAN, directly build the PAN result dictionary
            if ocr_res.get("document_type") == "pan":
                result = {
                    "document_type": "pan",
                    "legal_name": ocr_res.get("name"),
                    "father_name": ocr_res.get("father_name"),
                    "pan_number": ocr_res.get("pan_number"),
                    "dob": ocr_res.get("dob"),
                    "business_address": None
                }
                return jsonify({"success": True, "data": result})

            # Try to parse standard GST patterns from the image OCR text
            result = parse_extracted_text(raw_text)
            
            if result.get("trade_name") or (result.get("legal_name") and result.get("business_address")):
                result["document_type"] = "gst"
            else:
                result["document_type"] = "aadhaar"
            
            # If standard GST legal name wasn't found (e.g. Aadhaar or PAN card),
            # fall back to the heuristically parsed holder name from extract_text_from_img
            if not result.get("legal_name") and ocr_res.get("name"):
                result["legal_name"] = ocr_res["name"]
                
            if not result.get("father_name") and ocr_res.get("father_name"):
                result["father_name"] = ocr_res["father_name"]
                
            if not result.get("gender") and ocr_res.get("gender"):
                result["gender"] = ocr_res["gender"]
                
            # If standard GST address wasn't found (e.g. Aadhaar card),
            # fall back to the heuristically parsed address from extract_text_from_img
            if not result.get("business_address") and ocr_res.get("address"):
                result["business_address"] = ocr_res["address"]
                
            return jsonify({"success": True, "data": result})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "Invalid file format. Please upload a PDF or an Image (.png, .jpg, .jpeg, .webp, .bmp)."}), 400

def extract_bank_details_from_ocr(text_or_passes):
    """
    Extracts bank account details (IFSC, Account Number) from multi-pass OCR text.
    """
    if isinstance(text_or_passes, list):
        all_passes = text_or_passes
    else:
        all_passes = [text_or_passes]
        
    ifsc = None
    account_number = None
    bank_name = None
    
    # A. Heuristics for IFSC Code
    # Format: [A-Z]{4}0[A-Z0-9]{6}
    ifsc_pattern = re.compile(r'([A-Za-z]{4})[0-9Oo]([A-Za-z0-9]{6})')
    
    VALID_PREFIXES = ["CIUB", "HDFC", "ICIC", "UTIB", "SBIN", "PUNB", "CNRB", "BARB", "YESB", "KKBK", "UBIN", "IDIB", "FDRL", "INDB", "IBKL", "SIBL"]
    
    for pas in all_passes:
        matches = ifsc_pattern.findall(pas)
        for m in matches:
            part1 = m[0].upper()
            part2 = m[1].upper()
            
            # Common OCR error replacements
            part1 = part1.replace('1', 'I').replace('0', 'O')
            part2 = part2.replace('O', '0').replace('G', '6').replace('I', '1').replace('L', '1').replace('l', '1')
            
            # Custom corrections
            if 'g' in m[1].lower():
                part2 = part2.replace('G', '9')
            
            if part1 == "C1UB":
                part1 = "CIUB"
                
            candidate_prefix = part1
            if candidate_prefix in VALID_PREFIXES:
                candidate_ifsc = f"{part1}0{part2}"
                if len(candidate_ifsc) == 11:
                    ifsc = candidate_ifsc
                    break
        if ifsc:
            break
            
    # B. Heuristics for Account Number
    # Score candidate numbers:
    candidates = []
    
    for pas in all_passes:
        lines = pas.split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            # Skip potential bottom line/MICR containing common cheque indicators
            if any(indicator in line for indicator in ['"', '⑈', 'O00', 'BOO']):
                continue
                
            # Merge spaces between digits in this line to capture spaced numbers
            line_cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', line)
            line_cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', line_cleaned) # double pass
            
            # Extract all digit sequences between 9 and 18 digits
            digits = re.findall(r'\b(\d{9,18})\b', line_cleaned)
            for d in digits:
                score = 5
                # Boost score if line has account keywords
                if any(kw in line.lower() for kw in ['a/c', 'account', 'acc', 'no', 'num', 'number']):
                    score = 10
                candidates.append((score, d))
                
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        account_number = candidates[0][1]
            
    # C. Heuristics for Bank Name
    for pas in all_passes:
        pas_upper = pas.upper()
        if "CITY UNION BANK" in pas_upper or "CUB" in pas_upper or "UNION BANK" in pas_upper:
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

    return {
        "ifsc": ifsc,
        "account_number": account_number
    }

@app.route('/extract-bank', methods=['POST'])
def handle_extract_bank():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    filename_lower = file.filename.lower()
    
    try:
        if filename_lower.endswith('.pdf'):
            text = ""
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                file.save(temp_pdf.name)
                temp_pdf_path = temp_pdf.name
                
            with pdfplumber.open(temp_pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                
            details = extract_bank_details_from_ocr(text)
            return jsonify({"success": True, "data": details})
                
        elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            suffix = os.path.splitext(filename_lower)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_img:
                file.save(temp_img.name)
                temp_img_path = temp_img.name
                
            # Direct usage of extract_bank_details from extract_.py
            details = extract_bank_details(temp_img_path)
            
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
            if details is None:
                return jsonify({"error": "Could not extract details from cheque"}), 400
                
            return jsonify({"success": True, "data": details})
        else:
            return jsonify({"error": "Unsupported file format. Please upload a PDF or an Image."}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ifsc/<ifsc_code>', methods=['GET'])
def proxy_ifsc(ifsc_code):
    ifsc_code = ifsc_code.strip().upper()
    if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc_code):
        return jsonify({"error": "Invalid IFSC code format"}), 400
        
    try:
        url = f"https://ifsc.razorpay.com/{ifsc_code}"
        # Server-side requests bypass CORS blocks
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 404:
            return jsonify({"error": "IFSC code not found"}), 404
        else:
            return jsonify({"error": "Failed to retrieve bank details"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-promissory-note', methods=['POST'])
def handle_generate_promissory_note():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        form_data = data.get('formData', {})
        joinees_list = data.get('joinees', [])
        loans = data.get('loans', [])
        
        if not loans:
            loans = [{
                'lenderName': form_data.get('lenderName'),
                'loanAmount': form_data.get('loanAmount'),
                'repayment': form_data.get('repayment')
            }]
        
        # Validate critical fields
        required_fields = ['proprietorName', 'loanDate', 'place']
        missing = [f for f in required_fields if not form_data.get(f)]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
            
        for idx, loan in enumerate(loans):
            loan_missing = [f for f in ['lenderName', 'loanAmount', 'repayment'] if not loan.get(f)]
            if loan_missing:
                return jsonify({"error": f"Loan #{idx + 1} is missing fields: {', '.join(loan_missing)}"}), 400
            
        # Determine if we have any guarantors
        # A joinee is a guarantor if they have a non-empty name (excluding prefix titles like Mr./Mrs.)
        has_guarantor = False
        cleaned_joinees = []
        for j in joinees_list:
            name = j.get('name', '').strip()
            # Remove title prefixes (Mr., Mrs., Mr, Mrs) and support zero spaces after them
            name_without_title = re.sub(r'^(Mr\.|Mrs\.|Smt\.|Smt|Sri\.|Sri|Mr|Mrs|Ms\.|Ms)\s*', '', name, flags=re.IGNORECASE).strip()
            if name_without_title or j.get('father', '').strip() or j.get('pan', '').strip() or j.get('address', '').strip():
                has_guarantor = True
                cleaned_joinees.append(j)
                
        # Use cleaned_joinees for all template fill operations
        joinees_list = cleaned_joinees

        # Resolve template folder and paths dynamically
        if has_guarantor:
            template_folder = os.path.join(app.root_path, 'template', 'Proprietor_with_guarantor')
            
            promissory_template_name = 'Promissory Note.docx'
            promissory_template_path = os.path.join(template_folder, promissory_template_name)
            
            # Check for different possible names of the Letterpad template
            letterpad_template_name = 'Letterpad.docx'
            if os.path.exists(os.path.join(template_folder, 'LETTERPAD -FC- THALAKULAM.docx')):
                letterpad_template_name = 'LETTERPAD -FC- THALAKULAM.docx'
            elif os.path.exists(os.path.join(template_folder, 'Letter pad.docx')):
                letterpad_template_name = 'Letter pad.docx'
            letterpad_template_path = os.path.join(template_folder, letterpad_template_name)
            
            ltrl_template_name = 'LTRL.docx'
            ltrl_template_path = os.path.join(template_folder, ltrl_template_name)
            
            undertaking_template_name = 'Letter of Undertaking.docx'
            undertaking_template_path = os.path.join(template_folder, undertaking_template_name)
        else:
            template_folder = os.path.join(app.root_path, 'template', 'Proprietor')
            
            promissory_template_name = 'Promissory Note.docx'
            promissory_template_path = os.path.join(template_folder, promissory_template_name)
            
            # Check for different possible names of the Letterpad template
            letterpad_template_name = 'Letterpad.docx'
            if os.path.exists(os.path.join(template_folder, 'LETTERPAD -FC- THALAKULAM.docx')):
                letterpad_template_name = 'LETTERPAD -FC- THALAKULAM.docx'
            elif os.path.exists(os.path.join(template_folder, 'Letter pad.docx')):
                letterpad_template_name = 'Letter pad.docx'
            letterpad_template_path = os.path.join(template_folder, letterpad_template_name)
            
            undertaking_template_name = 'Letter of Undertaking.docx'
            undertaking_template_path = os.path.join(template_folder, undertaking_template_name)
            
            # No LTRL template for Proprietor without guarantor
            ltrl_template_path = None

        if not os.path.exists(promissory_template_path):
            return jsonify({"error": f"Promissory Note template not found at: {promissory_template_path}"}), 404
            
        if not os.path.exists(letterpad_template_path):
            # Try alternate fallback
            fallback_name = 'Letter pad.docx' if letterpad_template_name == 'Letterpad.docx' else 'Letterpad.docx'
            fallback_path = os.path.join(template_folder, fallback_name)
            if os.path.exists(fallback_path):
                letterpad_template_path = fallback_path
            else:
                return jsonify({"error": f"Letterpad template not found at: {letterpad_template_path}"}), 404
                
        if has_guarantor and not os.path.exists(ltrl_template_path):
            return jsonify({"error": f"LTRL template not found at: {ltrl_template_path}"}), 404
            
        if not os.path.exists(undertaking_template_path):
            return jsonify({"error": f"Letter of Undertaking template not found at: {undertaking_template_path}"}), 404
                
        # Zip them together
        import zipfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip_path = temp_zip.name
            
        proprietor_name_clean = secure_filename(form_data.get('proprietorName', 'Borrower'))
        
        try:
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for loan in loans:
                    loan_form_data = dict(form_data)
                    loan_form_data['lenderName'] = loan['lenderName']
                    loan_form_data['loanAmount'] = loan['loanAmount']
                    loan_form_data['repayment'] = loan['repayment']
                    
                    # Generate dynamic temp docx files for this loan
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_promissory:
                        temp_promissory_path = temp_promissory.name
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_letterpad:
                        temp_letterpad_path = temp_letterpad.name
                    if has_guarantor:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_ltrl:
                            temp_ltrl_path = temp_ltrl.name
                    else:
                        temp_ltrl_path = None
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_undertaking:
                        temp_undertaking_path = temp_undertaking.name
                    
                    try:
                        # Fill templates
                        fill_promissory_note_docx(loan_form_data, joinees_list, promissory_template_path, temp_promissory_path)
                        fill_letterpad_docx(loan_form_data, joinees_list, letterpad_template_path, temp_letterpad_path)
                        if has_guarantor:
                            fill_ltrl_docx(loan_form_data, joinees_list, ltrl_template_path, temp_ltrl_path)
                        fill_letter_of_undertaking_docx(loan_form_data, joinees_list, undertaking_template_path, temp_undertaking_path)
                        
                        lender_name_clean = secure_filename(loan['lenderName'])
                        if len(loans) == 1:
                            promissory_filename = f"Promissory_Note_{proprietor_name_clean}.docx"
                            letterpad_filename = f"Letterpad_{proprietor_name_clean}.docx"
                            if has_guarantor:
                                ltrl_filename = f"LTRL_{proprietor_name_clean}.docx"
                            undertaking_filename = f"Letter_of_Undertaking_{proprietor_name_clean}.docx"
                        else:
                            promissory_filename = f"Promissory_Note_{proprietor_name_clean}_{lender_name_clean}.docx"
                            letterpad_filename = f"Letterpad_{proprietor_name_clean}_{lender_name_clean}.docx"
                            if has_guarantor:
                                ltrl_filename = f"LTRL_{proprietor_name_clean}_{lender_name_clean}.docx"
                            undertaking_filename = f"Letter_of_Undertaking_{proprietor_name_clean}_{lender_name_clean}.docx"
                            
                        zip_file.write(temp_promissory_path, arcname=promissory_filename)
                        zip_file.write(temp_letterpad_path, arcname=letterpad_filename)
                        if has_guarantor:
                            zip_file.write(temp_ltrl_path, arcname=ltrl_filename)
                        zip_file.write(temp_undertaking_path, arcname=undertaking_filename)
                    finally:
                        temp_paths = [temp_promissory_path, temp_letterpad_path, temp_undertaking_path]
                        if has_guarantor:
                            temp_paths.append(temp_ltrl_path)
                        for p in temp_paths:
                            if p and os.path.exists(p):
                                try:
                                    os.remove(p)
                                except Exception:
                                    pass
            
            # Read the zip file bytes
            import io
            with open(temp_zip_path, 'rb') as f:
                zip_bytes = io.BytesIO(f.read())
        finally:
            if os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except Exception:
                    pass
            
        zip_filename = f"Documents_{proprietor_name_clean}.zip"
        
        return send_file(
            zip_bytes,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Endpoint for uploading Excel files and generating PDF reports.
    Returns a ZIP file containing the generated PDFs.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"error": "Only Excel files (.xlsx, .xls) are supported"}), 400

    temp_dir = tempfile.mkdtemp()
    
    import time
    start_time = time.time()
    try:
        # Process the excel file and get list of paths
        pdf_paths = process_excel_to_pdfs(file, temp_dir)
        
        if not pdf_paths:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"error": "No valid data found to generate reports"}), 400
            
        zip_path = os.path.join(temp_dir, "financial_reports.zip")
        create_zip_archive(pdf_paths, zip_path)
        
        duration = time.time() - start_time
        
        # Send the zip file back
        response = send_file(
            zip_path,
            as_attachment=True,
            download_name="financial_reports.zip",
            mimetype="application/zip"
        )
        response.headers['X-Process-Time'] = f"{duration:.2f}"
        return response
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

# --- Authentication Routes ---

@app.route('/api/login/', methods=['POST'])
def login():
    """
    Handles user login by verifying employee code and password.
    Returns user details including role and initial password status.
    """
    try:
        data = request.json
        emp_code = str(data.get('employee_code', '')).strip().upper()
        password = data.get('password', '')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if user:
            if check_password_hash(user.password, password):
                return jsonify({
                    'success': True,
                    'user': {
                        'employee_code': user.employee_code,
                        'name': user.name,
                        'role': user.role,
                        'is_initial_password': user.is_initial_password,
                        'accessed_menus': user.accessed_menus or 'fin-report,documat'
                    }
                })
            else:
                print("Password mismatch")
        else:
            print("User not found in DB")
            
        return jsonify({'success': False, 'message': 'Invalid employee code or password'}), 401
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/initial-setup/', methods=['POST'])
def initial_setup():
    """
    Handles the first-time password change and security question setup for new users.
    """
    try:
        data = request.json
        emp_code = str(data.get('employee_code', '')).strip().upper()
        new_password = data.get('new_password')
        question = data.get('q1')
        answer = data.get('a1')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        user.password = generate_password_hash(new_password)
        user.is_initial_password = False
        user.security_question = question
        user.security_answer = generate_password_hash(answer.lower().strip())
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Setup completed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/forgot-password/request/', methods=['POST'])
def forgot_password_request():
    """
    Retrieves the security question for a user who has forgotten their password.
    """
    try:
        data = request.json
        emp_code = str(data.get('employee_code', '')).strip().upper()
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if (user and user.security_question):
            return jsonify({'success': True, 'question': user.security_question, 'role': user.role})
        return jsonify({'success': False, 'message': 'User not found or security questions not set'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/forgot-password/reset/', methods=['POST'])
def forgot_password_reset():
    """
    Resets the user's password after verifying their security question answer.
    """
    try:
        data = request.json
        emp_code = str(data.get('employee_code', '')).strip().upper()
        answer = data.get('answer', '').lower().strip()
        new_password = data.get('new_password')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if user and user.security_answer and check_password_hash(user.security_answer, answer):
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Password reset successful'})
        return jsonify({'success': False, 'message': 'Incorrect answer or user not found'}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- User Management Routes ---

@app.route('/api/users/', methods=['GET'])
def get_all_users():
    """
    Returns a list of all users in the system.
    """
    try:
        users = User.query.all()
        user_list = []
        for u in users:
            user_list.append({
                'id': u.id,
                'employee_code': u.employee_code,
                'name': u.name,
                'email': u.email,
                'role': u.role,
                'accessed_menus': u.accessed_menus or 'fin-report,documat',
                'is_initial_password': u.is_initial_password,
                'security_question': u.security_question
            })
        return jsonify({'success': True, 'users': user_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/', methods=['POST'])
def create_user():
    """
    Creates a new user with custom fields.
    """
    try:
        data = request.json
        emp_code = str(data.get('employee_code', '')).strip().upper()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        temp_pwd = data.get('password', '').strip()
        accessed = data.get('accessed_menus', '') # can be string or list
        role = data.get('role', 'user').strip()
        
        if not emp_code or not name:
            return jsonify({'success': False, 'message': 'Employee code and name are required'}), 400
            
        existing_user = User.query.filter_by(employee_code=emp_code).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'A user with this employee code already exists'}), 400
            
        # Convert list of menus to comma-separated string if needed
        if isinstance(accessed, list):
            accessed_str = ",".join(accessed)
        else:
            accessed_str = str(accessed).strip() or 'fin-report,documat'
            
        pwd_to_hash = temp_pwd if temp_pwd else '123456'
        pwd_hash = generate_password_hash(pwd_to_hash)
        
        new_user = User(
            employee_code=emp_code,
            name=name,
            email=email,
            role=role,
            password=pwd_hash,
            accessed_menus=accessed_str,
            is_initial_password=True
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User created successfully', 'user': {
            'id': new_user.id,
            'employee_code': new_user.employee_code,
            'name': new_user.name,
            'email': new_user.email,
            'role': new_user.role,
            'accessed_menus': new_user.accessed_menus,
            'is_initial_password': new_user.is_initial_password
        }})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Deletes a user from the system by ID.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=2000, ssl_context=('cert.pem', 'key.pem'))
