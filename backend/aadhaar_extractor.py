import cv2
import numpy as np
import pytesseract
import re
import pymupdf as fitz  # PyMuPDF
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
def preprocess_format_c(image):
    """
    Detects if the image is a scanned photocopy (Format C) where content is only in the top 35%.
    Returns (cropped_image, is_format_c).
    """
    if image is None: return image, False
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, content_mask = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    my = int(h * 0.03)
    mx = int(w * 0.03)
    if my >= h or mx >= w: return image, False
    core_mask = content_mask[my:h-my, mx:w-mx]
    total_content = np.sum(core_mask == 255)
    if total_content == 0: return image, False
    core_h = core_mask.shape[0]
    top_45_h = int(core_h * 0.45)
    top_content = np.sum(core_mask[:top_45_h, :] == 255)
    if (top_content / total_content) > 0.85:
        top_45_mask_full = content_mask[:int(h * 0.45), mx:w-mx]
        row_ratios = np.sum(top_45_mask_full == 255, axis=1) / (w - 2*mx)
        content_rows = np.where(row_ratios > 0.01)[0]
        if len(content_rows) > 0:
            min_y = content_rows[0]
            max_y = content_rows[-1]
            pad = 20
            crop_y1 = max(0, min_y - pad)
            crop_y2 = min(h, max_y + pad)
            return image[crop_y1:crop_y2, :], True
    return image, False
def detect_and_split_aadhaar(image):
    """
    Takes an input image (numpy array from cv2)
    Returns a dictionary with 'front' and 'back' crops, plus 'diagnostic' data.
    """
    if image is None:
        return None
    processed_image, is_potential_format_c = preprocess_format_c(image)
    processed_image = crop_white_margins(processed_image)
    cropped_image = tight_crop_background(processed_image)
    if cropped_image is None or cropped_image.size == 0:
        return {"cropped_document": None, "front": None, "back": None, "diagnostic": {}}
    diagnostic = {}
    front, back, split_diag = split_front_back(cropped_image, is_potential_format_c)
    if "rotated_document" in split_diag:
        cropped_image = split_diag["rotated_document"]
    diagnostic.update(split_diag)
    is_format_b = False
    is_format_e = False
    for log_line in diagnostic.get("decision_log", []):
        if log_line.startswith("CLASSIFICATION:") and "FORMAT B" in log_line:
            is_format_b = True
        elif log_line.startswith("CLASSIFICATION:") and "FORMAT E" in log_line:
            is_format_e = True

    if front is not None and not is_format_e:
        front = tight_crop_background(front)
    if back is not None and not is_format_e:
        back = tight_crop_background(back)
    return {
        "cropped_document": cropped_image, 
        "front": front, 
        "back": back,
        "diagnostic": diagnostic
    }
def crop_white_margins(image, padding=15):
    """
    Removes pure white/empty margins around a document.
    Useful for digital PDFs (Format B) where tight_crop_background
    might leave large white borders because it doesn't see a 'card edge'.
    """
    if image is None or image.size == 0:
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    img_h, img_w = image.shape[:2]
    min_x, min_y = img_w, img_h
    max_x, max_y = 0, 0
    found_valid = False
    for cnt in contours:
        if cv2.contourArea(cnt) > 20:
            x, y, w, h = cv2.boundingRect(cnt)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
            found_valid = True
    if not found_valid:
        return image
    x1 = max(0, min_x - padding)
    y1 = max(0, min_y - padding)
    x2 = min(img_w, max_x + padding)
    y2 = min(img_h, max_y + padding)
    return image[y1:y2, x1:x2]
def tight_crop_background(image, padding=15, return_bbox=False):
    """
    Removes background (white, black, or dark wooden table) from the image.
    Uses a dual-strategy (brightness & adaptive edge) to find candidate contours,
    then evaluates them to find the true card boundary without merging with background noise.
    """
    if image is None or image.size == 0:
        return (image, (0, 0, 1, 1)) if return_bbox else image
    img_h, img_w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(np.mean(gray))
    candidates = []
    if mean_brightness < 220:
        _, bright_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cnts, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates.extend(cnts)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    high_thresh, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    low_thresh = 0.5 * high_thresh
    edges = cv2.Canny(blurred, int(low_thresh), int(high_thresh))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates.extend(cnts)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    s_channel = hsv[:, :, 1]
    try:
        _, sat_mask = cv2.threshold(s_channel, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        sat_mask = cv2.morphologyEx(sat_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        sat_mask = cv2.morphologyEx(sat_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        cnts, _ = cv2.findContours(sat_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates.extend(cnts)
    except Exception:
        pass
    kernel_grad = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    gradient = cv2.morphologyEx(blurred, cv2.MORPH_GRADIENT, kernel_grad)
    try:
        _, grad_mask = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        grad_mask = cv2.morphologyEx(grad_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        cnts, _ = cv2.findContours(grad_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates.extend(cnts)
    except Exception:
        pass
    if not candidates:
        return (image, (0, 0, img_w, img_h)) if return_bbox else image
    candidates = sorted(candidates, key=cv2.contourArea, reverse=True)
    for cnt in candidates:
        area = cv2.contourArea(cnt)
        if area < (img_w * img_h * 0.10):
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw >= img_w * 0.95 and ch >= img_h * 0.95:
            continue
        mask_expanded = np.zeros((img_h, img_w), dtype=np.uint8)
        min_x_exp = max(0, x - 30)
        max_x_exp = min(img_w, x + cw + 30)
        min_y_exp = max(0, y - 30)
        max_y_exp = min(img_h, y + ch + 30)
        mask_expanded[min_y_exp:max_y_exp, min_x_exp:max_x_exp] = 1
        mask_inner = np.zeros((img_h, img_w), dtype=np.uint8)
        mask_inner[y:y+ch, x:x+cw] = 1
        mask_ring = cv2.bitwise_xor(mask_expanded, mask_inner)
        outside_mean = cv2.mean(gray, mask=mask_ring)[0] if cv2.countNonZero(mask_ring) > 0 else 0
        inside_mean = cv2.mean(gray, mask=mask_inner)[0] if cv2.countNonZero(mask_inner) > 0 else 0
        is_card_on_table = (inside_mean > outside_mean + 10)
        if (is_card_on_table and cw >= img_w * 0.25 and ch >= img_h * 0.25) or \
           (cw >= img_w * 0.85 and ch >= img_h * 0.85):
            min_x = max(0, x - padding)
            min_y = max(0, y - padding)
            max_x = min(img_w, x + cw + padding)
            max_y = min(img_h, y + ch + padding)
            cropped = image[min_y:max_y, min_x:max_x]
            if cropped.size > 0:
                return (cropped, (min_x, min_y, max_x - min_x, max_y - min_y)) if return_bbox else cropped
    return (image, (0, 0, img_w, img_h)) if return_bbox else image
def detect_photo(img_region):
    """
    Detects if a passport-style photo is present in the LEFT half of the image.
    Returns (True, area) if found.
    """
    gray = cv2.cvtColor(img_region, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    left_region = gray[:, :w // 2]
    blurred = cv2.GaussianBlur(left_region, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((20, 20), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw > w * 0.12 and ch > h * 0.20:
            mask = np.zeros_like(left_region)
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            coverage = cv2.countNonZero(cv2.bitwise_and(thresh, mask)) / (cw * ch + 1e-5)
            if coverage > 0.20:
                return True, cw * ch
    return False, 0.0
def detect_qr(img_region):
    """
    Detects a QR code in the image.
    Step 1: Precise OpenCV QRCodeDetector.
    Step 2: Dark-pixel-density fallback in the RIGHT portion only.
            QR codes have 30-65% dark pixels. Fingerprint graphics,
            logos, and text have far less (~5-20%), so they won't
            trigger false positives.
    """
    qr_detector = cv2.QRCodeDetector()
    retval, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(img_region)
    if retval and points is not None and len(points) > 0:
        box = cv2.boundingRect(np.int32(points[0]))
        area = box[2] * box[3]
        cx = box[0] + box[2] // 2
        return True, area, cx
    gray_reg = cv2.cvtColor(img_region, cv2.COLOR_BGR2GRAY)
    h_reg, w_reg = gray_reg.shape
    y1 = int(h_reg * 0.20);  y2 = int(h_reg * 0.80)
    x1 = int(w_reg * 0.50);  x2 = int(w_reg * 0.95)
    if (y2 - y1) < 10 or (x2 - x1) < 10:
        return False, 0.0, 0
    right_band = gray_reg[y1:y2, x1:x2]
    _, binary = cv2.threshold(right_band, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dark_ratio = float(np.sum(binary == 255)) / float(binary.size + 1e-9)
    if 0.25 <= dark_ratio <= 0.75:
        best_cx = x1 + (x2 - x1) // 2
        nominal_area = ((x2 - x1) * (y2 - y1))
        return True, float(nominal_area), best_cx
    return False, 0.0, 0
def deep_crop_back(back_img):
    """
    Deep crops the back side of an Aadhaar card using two conditions:
    Condition 1 — QR code IS present:
        Detect the QR bounding box precisely and crop it out completely
        (keep the left text area only).
    Condition 2 — QR code is NOT present:
        The card has Tamil address (left column) + English address (right column).
        Remove the Tamil left column; keep the English right column only.
    Returns (cropped_img, condition_label).
    """
    if back_img is None or back_img.size == 0:
        return back_img, "none"
    h, w = back_img.shape[:2]
    qr_detector = cv2.QRCodeDetector()
    retval, _, points, _ = qr_detector.detectAndDecodeMulti(back_img)
    if retval and points is not None and len(points) > 0:
        qr_x, qr_y, qr_w, qr_h = cv2.boundingRect(np.int32(points[0]))
        crop_x_end = max(qr_x - 8, int(w * 0.40))
        cropped = back_img[:, :crop_x_end]
        label = f"Condition 1: QR detected (x={qr_x}) → QR removed."
        return cropped, label
    gray = cv2.cvtColor(back_img, cv2.COLOR_BGR2GRAY)
    y1 = int(h * 0.15);  y2 = int(h * 0.85)
    x1 = int(w * 0.55);  x2 = int(w * 0.98)
    right_region = gray[y1:y2, x1:x2]
    _, binary = cv2.threshold(right_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_cnt = max(contours, key=cv2.contourArea)
        cx, cy, cw, ch = cv2.boundingRect(largest_cnt)
        if cw > 30 and ch > 30 and (cw / ch) < 1.3 and (ch / cw) < 1.3:
            roi = closed[cy:cy+ch, cx:cx+cw]
            density = np.sum(roi == 255) / (cw * ch)
            raw_roi = binary[cy:cy+ch, cx:cx+cw]
            raw_density = np.sum(raw_roi == 255) / (cw * ch)
            if density > 0.65 and raw_density > 0.35:
                qr_x_full = x1 + cx
                crop_x_end = max(qr_x_full - 10, int(w * 0.40))
                cropped = back_img[:, :crop_x_end]
                label = f"Condition 1 (contour): QR blob detected (w={cw}, h={ch}, d={density:.2f}, rd={raw_density:.2f}) -> QR removed."
                return cropped, label
    crop_x_start = int(w * 0.50)
    cropped = back_img[:, crop_x_start:]
    label = "Condition 2: No QR found -> Kept right 50% (English address)."
    return cropped, label
def tight_crop_mask(img_reg, mask_reg):
    coords = cv2.findNonZero(mask_reg)
    if coords is None: return img_reg
    x, y, bw, bh = cv2.boundingRect(coords)
    return img_reg[y:y+bh, x:x+bw]
def _crop_to_white_card(image):
    """
    Finds the largest rectangular-ish contour (the Aadhaar card) and tightly crops it,
    ignoring background noise like camera watermarks or table texture.
    """
    if image is None or image.size == 0:
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    img_h, img_w = gray.shape
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 30, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for largest_contour in contours:
        area = cv2.contourArea(largest_contour)
        if area < (img_w * img_h * 0.15):
            continue
        x, y, w, h = cv2.boundingRect(largest_contour)
        if w >= img_w * 0.95 and h >= img_h * 0.95:
            continue
        mask_out = np.ones((img_h, img_w), dtype=np.uint8)
        mask_out[y:y+h, x:x+w] = 0
        outside_mean = cv2.mean(gray, mask=mask_out)[0] if np.any(mask_out) else 0
        mask_in = np.zeros((img_h, img_w), dtype=np.uint8)
        mask_in[y:y+h, x:x+w] = 1
        inside_mean = cv2.mean(gray, mask=mask_in)[0] if np.any(mask_in) else 0
        is_card_on_table = (inside_mean > outside_mean + 10)
        if (is_card_on_table and w >= img_w * 0.30 and h >= img_h * 0.30) or \
           (w >= img_w * 0.85 and h >= img_h * 0.85):
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(img_w, x + w)
            y2 = min(img_h, y + h)
            cropped = image[y1:y2, x1:x2]
            return cropped if cropped.size > 0 else image
    return image
def split_front_back(image, is_potential_format_c=False):
    """
    Attempts to split the image into front and back based on the exact gap and QR/Face logic specified.
    Handles:
    - Format A: 1D split (2 cells)
    - Format B: 2D grid split (4 cells)
    - Format C: 50/50 vertical split without dashed lines
    Returns (front, back, diagnostic). If no split is found, back is None.
    """
    diagnostic = {
        "decision_log": [],
        "contours_drawn": None, 
    }
    if image is None or image.size == 0:
        return image, None, diagnostic
    h, w = image.shape[:2]
    diagnostic["decision_log"].append(f"Processing image for split: w={w}, h={h}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, content_mask = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    col_ratios = np.sum(content_mask == 255, axis=0) / h
    row_ratios = np.sum(content_mask == 255, axis=1) / w
    def find_cut(ratios, axis_name, min_margin=0.35, max_ratio=0.10, min_cov=0.10):
        total_len = len(ratios)
        s_idx = int(total_len * min_margin)
        e_idx = int(total_len * (1.0 - min_margin))
        if s_idx >= e_idx: 
            return -1
        smoothed = np.convolve(ratios, np.ones(5)/5.0, mode='same')
        band = smoothed[s_idx:e_idx]
        if len(band) == 0: return -1
        idx = s_idx + np.argmin(band)
        chosen_ratio = ratios[idx]
        if chosen_ratio >= max_ratio: 
            return -1
        reg1 = ratios[:idx]
        reg2 = ratios[idx:]
        cov1 = np.sum(reg1 > 0.05) / len(reg1) if len(reg1)>0 else 0
        cov2 = np.sum(reg2 > 0.05) / len(reg2) if len(reg2)>0 else 0
        if cov1 < min_cov or cov2 < min_cov: 
            return -1
        return idx
    v_cut = find_cut(col_ratios, "VERTICAL (Columns)", max_ratio=0.25)
    h_cut = find_cut(row_ratios, "HORIZONTAL (Rows)", max_ratio=0.15)
    v_count = 1 if v_cut != -1 else 0
    h_count = 1 if h_cut != -1 else 0
    diagnostic["decision_log"].append(f"Cut lines found: Horizontal count = {h_count}, Vertical count = {v_count}")
    mid_start = int(w * 0.45)
    mid_end = int(w * 0.55)
    has_mid_gap = False
    if mid_end > mid_start:
        min_mid_ratio = np.min(col_ratios[mid_start:mid_end])
        has_mid_gap = min_mid_ratio < 0.10
    aspect_ratio = w / h
    is_wide = aspect_ratio > 1.2
    is_extremely_wide = aspect_ratio > 1.9  # Lowered to catch all side-by-side e-Aadhaar cutouts
    is_very_tall = aspect_ratio < 0.65
    is_a4_page = 0.55 <= aspect_ratio <= 1.0

    def _is_format_e():
        if is_potential_format_c or is_a4_page:
            return False
        if aspect_ratio >= 0.85:  # Must be portrait (taller than wide)
            return False
            
        mid_h = h // 2
        top_content    = np.sum(content_mask[:mid_h, :] == 255)
        bottom_content = np.sum(content_mask[mid_h:, :] == 255)
        total_content  = np.sum(content_mask == 255)
        if total_content == 0:
            return False
            
        top_ratio    = top_content    / total_content
        bottom_ratio = bottom_content / total_content
        
        # Format E is a vertically stacked card. 
        # Both top and bottom halves must have substantial content (at least 30% each)
        if top_ratio >= 0.30 and bottom_ratio >= 0.30:
            # A stacked layout is usually aspect ratio 0.6 to 0.8. 
            # A full e-Aadhaar column is usually very tall (aspect ratio < 0.45).
            if aspect_ratio > 0.45:
                return True
                
        return False

    if is_potential_format_c:
        h_cut = -1
        h_count = 0
        if is_extremely_wide:
            detected_format = "FORMAT C (Photocopy, top region)"
        else:
            detected_format = "FORMAT D (Single Side)"
    elif _is_format_e():
        detected_format = "FORMAT E (Vertically Stacked: Top=Front, Bottom=Back)"
    elif is_very_tall:
        detected_format = "FORMAT B (e-Aadhaar Vertical Column)"
    elif (h_count == 1 and v_count == 1 and not is_wide) or (is_a4_page and v_cut != -1):
        detected_format = "FORMAT B (2x2 Grid, e-Aadhaar A4)"
    elif has_mid_gap and is_extremely_wide:
        detected_format = "FORMAT C (Horizontal side-by-side)"
        h_cut = -1
    else:
        detected_format = "FORMAT D (Single Side)"
    diagnostic["decision_log"].append(f"CLASSIFICATION: {detected_format}")
    diag_img = image.copy()
    aadhaar_front = None
    aadhaar_back = None

    if "FORMAT E" in detected_format:
        aadhaar_front = image  # No deep crop
        aadhaar_back  = None      # Don't use backside image
        diagnostic["decision_log"].append(f"Format E Process: Using entire image as Front (no tight crop). No Back.")
    elif "FORMAT C" in detected_format:
        mid = v_cut if v_cut != -1 else w // 2
        cv2.line(diag_img, (mid, 0), (mid, h), (0, 0, 255), 4) # Draw red line for split
        left_half = image[:, :mid]
        right_half = image[:, mid:]
        aadhaar_front = tight_crop_background(left_half)
        aadhaar_back = tight_crop_background(right_half)
        diagnostic["decision_log"].append(f"Format C Process: Split vertically at x={mid}. Left -> Front, Right -> Back.")
    elif "FORMAT B (e-Aadhaar Vertical Column)" in detected_format:
        aadhaar_front = tight_crop_background(image)
        aadhaar_back = None
        diagnostic["decision_log"].append(f"Format B Vertical Process: Using entire left column as Front. No Back.")
    elif "FORMAT B" in detected_format:
        h_cut = -1
        v_cut = int(w * 0.50)
        cv2.line(diag_img, (v_cut, 0), (v_cut, h), (255, 0, 0), 4)
        cells = []
        cells.append({"pos": "Left-50", "img": image[:, :v_cut], "mask": content_mask[:, :v_cut]})
        cells.append({"pos": "Right-50", "img": image[:, v_cut:], "mask": content_mask[:, v_cut:]})
        diagnostic["decision_log"].append(f"Image segmented into {len(cells)} cell(s) (Vertical split at 50%)")
        def tight_crop_mask(img_reg, mask_reg):
            coords = cv2.findNonZero(mask_reg)
            if coords is None: return img_reg
            x, y, bw, bh = cv2.boundingRect(coords)
            return img_reg[y:y+bh, x:x+bw]
        aadhaar_front = tight_crop_mask(cells[0]["img"], cells[0]["mask"])
        aadhaar_back = tight_crop_mask(cells[1]["img"], cells[1]["mask"])
        diagnostic["decision_log"].append("Format B: Assigned Left splitted image as FRONT and Right splitted image as BACK.")
    elif "FORMAT D" in detected_format:
        diagnostic["decision_log"].append("Format D Process: Single side detected. Evaluating content to classify as Front or Back.")
        cropped = tight_crop_background(image)
        ch, cw = cropped.shape[:2]
        if ch > cw:
            candidates = [
                (cropped, "0deg"),
                (cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE), "CW"),
                (cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE), "CCW"),
            ]
        else:
            candidates = [
                (cropped, "0deg"),
                (cv2.rotate(cropped, cv2.ROTATE_180), "180deg"),
            ]
        best_img = candidates[0][0]
        best_label = candidates[0][1]
        best_score = -1
        best_img = None
        best_label = ""
        for candidate_img, label in candidates:
            text = perform_ocr(candidate_img).lower()
            keywords = ['address', 'add:', 's/o', 'd/o', 'w/o', 'c/o', 'dob', 'male', 'female', 'yob', 'government', 'india', 'pin', 'help@', 'www.']
            score = sum(10 for k in keywords if k in text)
            words = re.findall(r'\b[a-z]{4,}\b', text)
            score += len(words)
            if score > best_score:
                best_score = score
                best_img = candidate_img
                best_label = label + f" (OCR Score: {score})"
        cropped = best_img if best_img is not None else image
        diagnostic["decision_log"].append(f"Format D rotation selected: {best_label}")
        cropped = _crop_to_white_card(cropped)
        diagnostic["rotated_document"] = cropped
        has_photo, photo_area = detect_photo(cropped)
        has_qr, qr_area, _ = detect_qr(cropped)
        diagnostic["decision_log"].append(f"Format D Analysis: Photo={has_photo} (area: {photo_area}), QR={has_qr} (area: {qr_area})")
        diagnostic["decision_log"].append("Running OCR to determine Front vs Back...")
        quick_text = perform_ocr(cropped).lower()
        is_front_ocr = any(k in quick_text for k in ['dob', 'year of birth', 'male', 'female', 'yob', 'father'])
        is_back_ocr = any(k in quick_text for k in ['address', 'add:', 's/o', 'd/o', 'w/o', 'c/o', 'pin'])
        if is_back_ocr and not is_front_ocr:
            diagnostic["decision_log"].append("Classification: BACK (High Confidence - OCR Keywords)")
            aadhaar_back = cropped
        elif is_front_ocr and not is_back_ocr:
            diagnostic["decision_log"].append("Classification: FRONT (High Confidence - OCR Keywords)")
            aadhaar_front = cropped
        else:
            diagnostic["decision_log"].append("OCR Ambiguous. Falling back to visual heuristics (Photo/QR).")
            if has_photo and has_qr:
                diagnostic["decision_log"].append("AMBIGUOUS Format D: Both Photo and QR detected. Prioritizing larger area.")
                if photo_area >= qr_area:
                    diagnostic["decision_log"].append("Classification: FRONT (High Confidence - Area override)")
                    aadhaar_front = cropped
                else:
                    diagnostic["decision_log"].append("Classification: BACK (High Confidence - Area override)")
                    aadhaar_back = cropped
            elif has_photo:
                diagnostic["decision_log"].append("Classification: FRONT (Based on Photo presence)")
                aadhaar_front = cropped
            elif has_qr:
                diagnostic["decision_log"].append("Classification: BACK (Based on QR presence)")
                aadhaar_back = cropped
            else:
                diagnostic["decision_log"].append("UNABLE TO CLASSIFY CONFIDENTLY. Defaulting to FRONT.")
                aadhaar_front = cropped
    else:
        aadhaar_front = tight_crop_background(image)
        diagnostic["decision_log"].append("No split executed. Returning original as single side.")
    diagnostic["contours_drawn"] = diag_img
    if aadhaar_front is not None and aadhaar_back is not None:
        res_str = "aadhaar_front and aadhaar_back correctly extracted."
    elif aadhaar_front is not None:
        res_str = "aadhaar_front extracted. aadhaar_back missing."
    elif aadhaar_back is not None:
        res_str = "aadhaar_back extracted. aadhaar_front missing."
    else:
        res_str = "Could not extract sides cleanly."
        aadhaar_front = image
    return aadhaar_front, aadhaar_back, diagnostic
def deskew_image(image):
    if image is None or image.size == 0:
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5 or abs(angle) > 20:
        return image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated
def get_front_roi(image):
    if image is None or image.size == 0:
        return image
    h, w = image.shape[:2]
    x_start = int(0.22 * w)
    x_end = int(0.85 * w)
    y_start = int(0.15 * h)
    y_end = int(0.85 * h)
    return image[y_start:y_end, x_start:x_end]
def get_back_roi(image):
    if image is None or image.size == 0:
        return image
    h, w = image.shape[:2]
    x_start = int(0.05 * w)
    x_end = int(0.70 * w)
    y_start = int(0.15 * h)
    y_end = int(0.75 * h)
    return image[y_start:y_end, x_start:x_end]
def perform_ocr(roi_image):
    if roi_image is None or roi_image.size == 0:
        return ""
    scale = 2.5
    width = int(roi_image.shape[1] * scale)
    height = int(roi_image.shape[0] * scale)
    upscaled = cv2.resize(roi_image, (width, height), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    bg = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    normalized = 255 - cv2.absdiff(bg, gray)
    blurred = cv2.GaussianBlur(normalized, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    custom_config = r'--oem 3 --psm 6'
    data = pytesseract.image_to_data(thresh, lang='eng', config=custom_config, output_type=pytesseract.Output.DICT)
    lines_dict = {}
    for i in range(len(data['level'])):
        if data['level'][i] == 5:
            conf = int(data['conf'][i])
            word = data['text'][i].strip()
            if word:  # Removed confidence check completely to ensure no text is dropped
                block_num = data['block_num'][i]
                par_num = data['par_num'][i]
                line_num = data['line_num'][i]
                key = (block_num, par_num, line_num)
                if key not in lines_dict:
                    lines_dict[key] = []
                lines_dict[key].append(word)
    extracted_lines = []
    for key in sorted(lines_dict.keys()):
        extracted_lines.append(" ".join(lines_dict[key]))
    text = "\n".join(extracted_lines)
    return text
def clean_ocr_text(text):
    if not text: return []
    return [line.strip() for line in text.split('\n') if line.strip()]
def extract_aadhaar_fields(front_img, back_img, is_format_b=False):
    raw_ocr = {
        "front_text": "",
        "back_text": "",
        "front_roi_img": None,
        "back_roi_img": None
    }
    if front_img is not None and front_img.size > 0:
        raw_ocr["front_text"] = perform_ocr(front_img)
        raw_ocr["front_roi_img"] = cv2.cvtColor(front_img, cv2.COLOR_BGR2RGB)
    if back_img is not None and back_img.size > 0:
        raw_ocr["back_text"] = perform_ocr(back_img)
        raw_ocr["back_roi_img"] = cv2.cvtColor(back_img, cv2.COLOR_BGR2RGB)
    to_block_name = ""
    to_block_father = ""
    to_block_address = ""
    if is_format_b:
        def is_valid_english_line(line_str):
            words = re.sub(r'[^A-Za-z]', ' ', line_str).split()
            if not words: return True  # Numbers/punctuation only is fine
            weird_count = 0
            for w in words:
                if len(w) <= 2: continue
                # Vowel check
                if not re.search(r'[aeiouyAEIOUY]', w):
                    weird_count += 1
                    continue
                # Consonant cluster
                if re.search(r'[bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ]{4,}', w):
                    weird_count += 1
                    continue
                # Weird casing
                if not w.isupper() and not w.islower() and not w.istitle():
                    weird_count += 1
                    continue
            if weird_count / len(words) >= 0.25:
                return False
            return True

        lines = clean_ocr_text(raw_ocr.get("front_text", ""))
        to_idx = -1
        for i, line in enumerate(lines):
            if line.lower().strip() in ['to', 'to |', 'to|'] or line.lower().startswith('to '):
                to_idx = i
                break
        if to_idx != -1:
            raw_english_lines = []
            for line in lines[to_idx+1:]:
                if re.search(r'\d{4}\s\d{4}\s\d{4}', line) or 'your aadhaar' in line.lower() or 'enrollment' in line.lower():
                    break
                clean_line = re.sub(r'[\s\|\}\{\]\[]+$', '', line).strip()
                if clean_line.startswith('[') or clean_line.startswith('('):
                    continue
                if clean_line:
                    raw_english_lines.append(clean_line)
            # STRICT FILTER: Remove regional language hallucinations completely
            english_lines = [line for line in raw_english_lines if is_valid_english_line(line)]
            name_idx = -1
            father_idx = -1
            father_prefixes_strict = ['s/o', 'd/o', 'w/o', 'c/o', 'son of', 'wife of', 'daughter of', 'care of']
            for i, line in enumerate(english_lines):
                lower_line = line.lower()
                for pref in father_prefixes_strict:
                    if lower_line.startswith(pref) or f" {pref}" in lower_line:
                        father_idx = i
                        name_idx = i - 1
                        break
                if father_idx != -1:
                    break
            if name_idx != -1 and name_idx >= 0:
                to_block_name = english_lines[name_idx]
                cand_father = english_lines[father_idx]
                cand_father = re.sub(r'^.*?(s/o|d/o|w/o|c/o|son of|wife of|daughter of|care of)[\:\-\s]*', '', cand_father, flags=re.IGNORECASE)
                to_block_father = re.sub(r'[\:\,\-\.\s]+$', '', cand_father).strip()
                addr_lines = english_lines[father_idx+1:]
            else:
                for i, line in enumerate(english_lines):
                    cand = re.sub(r'^[^a-zA-Z]+', '', line)
                    cand = re.sub(r'[^a-zA-Z]+$', '', cand).strip()
                    if len(cand) > 3 and not re.search(r'[^A-Za-z\.\s\']', cand):
                        words = cand.split()
                        weird = False
                        for w in words:
                            clean_w = re.sub(r'[^A-Za-z]', '', w)
                            if len(clean_w) > 0:
                                if not clean_w.isupper() and not clean_w.islower() and not clean_w.istitle():
                                    weird = True
                                    break
                        if not weird:
                            name_idx = i
                            to_block_name = cand
                            break
                if name_idx != -1:
                    addr_lines = english_lines[name_idx+1:] if name_idx + 1 < len(english_lines) else []
            final_addr = []
            for al in addr_lines:
                clean_al = re.sub(r'[\s\,]+$', '', al).strip()
                clean_al = re.sub(r'\s*\)$', '', clean_al).strip()
                if clean_al:
                    final_addr.append(clean_al)
                if 'pin' in al.lower():
                    break
            to_block_address = ", ".join(final_addr)
    father_prefixes = ['s/o', 'd/o', 'w/o', 'c/o', 'son of', 'daughter of', 'wife of', 'care of', 'father:', 'mother:', 'father', 'mother', 'fatrer', 'fater']
    def extract_father(text):
        lines = clean_ocr_text(text)
        address_start_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'(address|add)\s*:', line, flags=re.IGNORECASE):
                address_start_idx = i
                break
        if address_start_idx != -1:
            lines = lines[address_start_idx:]
        for line in lines:
            line_lower = line.lower()
            for prefix in father_prefixes:
                if prefix in line_lower:
                    idx = line_lower.find(prefix)
                    val = line[idx + len(prefix):].strip()
                    val = re.sub(r'^[\:\,\-\.\s]+', '', val) # strip leading punctuation
                    val = val.split(',')[0].strip()
                    match = re.search(r'\d', val)
                    if match:
                        val = val[:match.start()].strip()
                    val = re.sub(r'[\:\,\-\.\s]+$', '', val).strip() # clean trailing punctuation
                    if val and len(val) > 2: return val
        return ""
    fathers_name = extract_father(raw_ocr["front_text"])
    if not fathers_name:
        fathers_name = extract_father(raw_ocr["back_text"])
    def extract_address(text, extracted_father_name=""):
        lines = clean_ocr_text(text)
        address_start_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'(address|add)\s*:', line, flags=re.IGNORECASE):
                address_start_idx = i
                break
        if address_start_idx != -1:
            lines = lines[address_start_idx:]
        address_lines = []
        capture = False
        for line in lines:
            lower_line = line.lower()
            if re.search(r'(address|add)\s*:', lower_line):
                capture = True
                val = re.sub(r'^(.*?)(address|add)\s*:', '', line, flags=re.IGNORECASE).strip()
                val = re.sub(r'^[^a-zA-Z0-9]+', '', val).strip()
                val = re.sub(r'[\s\|\}\{\]\[]+$', '', val).strip() # Strip trailing e-Aadhaar cut lines
                if val: address_lines.append(val)
                continue
            for prefix in father_prefixes:
                if prefix in lower_line:
                    capture = True
                    break
            if capture:
                if 'uidai' in lower_line or '1947' in lower_line or 'vid' in lower_line or 'help@' in lower_line or 'box no' in lower_line:
                    break
                if re.search(r'\d{4}\s\d{4}\s\d{4}', line):
                    break
                if 'mobile' in lower_line or 'phone' in lower_line or 'signature' in lower_line:
                    break
                if len(line) < 4:
                    continue
                clean_l = re.sub(r'^[^a-zA-Z0-9]+', '', line).strip()
                clean_l = re.sub(r'[\s\|\}\{\]\[]+$', '', clean_l).strip() # Strip trailing e-Aadhaar cut lines
                if clean_l: address_lines.append(clean_l)
                if 'pin code' in lower_line or 'pin:' in lower_line or re.search(r'\b\d{6}\b', line):
                    break
        address_str = " ".join(address_lines)
        if extracted_father_name:
            for prefix in father_prefixes:
                pattern = r'^(?:' + re.escape(prefix) + r')?[\:\,\-\.\s]*' + re.escape(extracted_father_name) + r'[\:\,\-\.\s]*'
                address_str = re.sub(pattern, '', address_str, flags=re.IGNORECASE).strip()
        for prefix in father_prefixes:
            pattern = r'^' + re.escape(prefix) + r'[\:\,\-\.\s]*'
            address_str = re.sub(pattern, '', address_str, flags=re.IGNORECASE).strip()
        return address_str
    if is_format_b:
        address = extract_address(raw_ocr["front_text"], fathers_name)
    else:
        address = extract_address(raw_ocr["back_text"], fathers_name)
    def extract_name(text):
        lines = clean_ocr_text(text)
        if is_format_b:
            father_idx = -1
            for i, line in enumerate(lines):
                for prefix in father_prefixes:
                    if prefix in line.lower():
                        father_idx = i
                        break
                if father_idx != -1: break
            if father_idx > 0:
                for j in range(father_idx - 1, -1, -1):
                    cand = lines[j].strip()
                    if cand.lower() == 'to' or len(cand) < 3: continue
                    cand = re.sub(r'^[^a-zA-Z]+', '', cand)
                    cand = re.sub(r'[^a-zA-Z]+$', '', cand).strip()
                    cand = re.sub(r'(\s+[a-z])+$', '', cand).strip()  # Remove trailing hallucinated lowercase letters
                    if len(cand) > 3 and not re.search(r'[^A-Za-z\.\s\']', cand):
                        return cand
        for i, line in enumerate(lines):
            lower_line = line.lower()
            if 'dob' in lower_line or 'year of birth' in lower_line or 'yob' in lower_line or 'birth' in lower_line or re.search(r'\d{2}/\d{2}/\d{4}', line) or 'male' in lower_line or 'female' in lower_line:
                for j in range(i-1, max(-1, i-6), -1):
                    name_candidate = lines[j]
                    is_father = False
                    for prefix in father_prefixes:
                        if prefix in name_candidate.lower():
                            is_father = True
                            break
                    if is_father:
                        continue
                    name_candidate = re.sub(r'^[^a-zA-Z]+', '', name_candidate)
                    name_candidate = re.sub(r'[^a-zA-Z]+$', '', name_candidate).strip()
                    name_candidate = re.sub(r'(\s+[a-z])+$', '', name_candidate).strip() # Remove trailing hallucinated lowercase letters
                    words = name_candidate.split()
                    lower_words = [w for w in words if w.islower()]
                    if len(lower_words) >= max(1, len(words) // 2):
                        continue
                    if len(name_candidate) > 3 and re.search(r'[A-Za-z]', name_candidate) and not re.search(r'[^A-Za-z\.\s\']', name_candidate):
                        return name_candidate
        for line in lines:
            is_father = False
            for prefix in father_prefixes:
                if prefix in line.lower():
                    is_father = True
                    break
            if is_father:
                continue
            line_clean = re.sub(r'^[^a-zA-Z]+', '', line)
            line_clean = re.sub(r'[^a-zA-Z]+$', '', line_clean).strip()
            line_clean = re.sub(r'(\s+[a-z])+$', '', line_clean).strip() # Remove trailing hallucinated lowercase letters
            if len(line_clean) > 3 and re.search(r'[A-Za-z]', line_clean) and not re.search(r'[^A-Za-z\.\s\']', line_clean):
                words = line_clean.split()
                if len(words) >= 2 and len(line_clean) > 5 and 'government' not in line_clean.lower() and 'india' not in line_clean.lower():
                    return line_clean
        return ""
    name = extract_name(raw_ocr["front_text"])
    if is_format_b:
        lines = clean_ocr_text(raw_ocr["front_text"])
        b_name = ""
        name_idx = -1
        father_idx = -1
        for i, line in enumerate(lines):
            lower_line = line.lower()
            is_father = False
            for prefix in father_prefixes:
                if prefix in lower_line:
                    is_father = True
                    break
            if is_father:
                father_idx = i
                break
        if father_idx > 0:
            for j in range(father_idx - 1, -1, -1):
                cand = lines[j].strip()
                if cand.lower() == 'to': continue
                cand_clean = re.sub(r'^[^a-zA-Z0-9]+', '', cand)
                cand_clean = re.sub(r'[^a-zA-Z0-9]+$', '', cand_clean).strip()
                if len(cand_clean) > 3:
                    b_name = cand_clean
                    name_idx = j
                    break
        else:
            to_idx = -1
            for i, line in enumerate(lines):
                clean_to_check = re.sub(r'[^\w\s]', '', line.lower()).strip()
                if clean_to_check == 'to':
                    to_idx = i
                    break
            if to_idx != -1:
                for j in range(to_idx + 1, min(to_idx + 4, len(lines))):
                    cand = lines[j].strip()
                    cand_clean = re.sub(r'^[^a-zA-Z0-9]+', '', cand)
                    cand_clean = re.sub(r'[^a-zA-Z0-9]+$', '', cand_clean).strip()
                    if len(cand_clean) > 3:
                        b_name = cand_clean
                        name_idx = j
                        break
        if b_name:
            name = b_name
        start_idx = father_idx if father_idx != -1 else name_idx
        if start_idx != -1:
            b_address_lines = []
            for i in range(start_idx + 1, len(lines)):
                line = lines[i]
                lower_line = line.lower()
                if 'mobile' in lower_line or 'phone' in lower_line or 'signature' in lower_line or 'uidai' in lower_line or '1947' in lower_line or 'vid' in lower_line:
                    break
                if re.search(r'\d{4}\s\d{4}\s\d{4}', line):
                    break
                clean_l = re.sub(r'^[^a-zA-Z0-9]+', '', line).strip()
                clean_l = re.sub(r'[\s\|\}\{\]\[]+$', '', clean_l).strip() # Strip trailing e-Aadhaar cut lines
                if clean_l: b_address_lines.append(clean_l)
                if 'pin code' in lower_line or 'pin:' in lower_line or re.search(r'\b\d{6}\b', line):
                    break
            if b_address_lines:
                address = " ".join(b_address_lines)
    if to_block_name:
        name = to_block_name
    if to_block_father:
        fathers_name = to_block_father
    if to_block_address:
        address = to_block_address
    def _truncate_at_pincode(addr):
        """Return address string cut off right after the first 6-digit Indian pincode."""
        m = re.search(r'\b\d{6}\b', addr)
        if m:
            return addr[:m.end()].rstrip(', -')
        return addr
    address = _truncate_at_pincode(address)
    # Ensure address starts with a number or letter, stripping leading symbols like '&'
    if address:
        address = re.sub(r'^[^a-zA-Z0-9]+', '', address)
    return {
        "name": name,
        "fathers_name": fathers_name,
        "address": address,
        "raw_ocr": raw_ocr
    }
def process_aadhaar_image(image):
    """
    End-to-end function to extract Aadhaar details from an image.
    This can be easily imported and used in other projects.
    Returns a dictionary with 'name', 'fathers_name', 'address', and 'raw_ocr'.
    """
    results = detect_and_split_aadhaar(image)
    if not results:
        return None
        
    diag = results.get("diagnostic", {})
    format_msg = "Unknown Format"
    for log_line in diag.get("decision_log", []):
        if log_line.startswith("CLASSIFICATION:"):
            format_msg = log_line.replace("CLASSIFICATION:", "").strip()
            break
            
    front_img = results.get("front")
    back_img  = results.get("back")
    
    deep_cropped_back = back_img
    
    if front_img is not None and "FORMAT B" in format_msg:
        h = front_img.shape[0]
        crop_y = int(h * 0.26)
        # We don't remove the top 26% anymore so that the 'To' block is preserved for OCR!
        # front_img = front_img[crop_y:, :]
        
    if "FORMAT B" not in format_msg and back_img is not None:
        deep_cropped_back, _ = deep_crop_back(back_img)
        
    def trim_bottom_25(img):
        if img is None or img.size == 0:
            return img
        h = img.shape[0]
        return img[:int(h * 0.75), :]
        
    if "FORMAT B" in format_msg:
        front_ocr_img = front_img
        back_ocr_img = deep_cropped_back
    elif "FORMAT E" in format_msg:
        front_ocr_img = front_img
        back_ocr_img = None
    else:
        front_ocr_img = get_front_roi(front_img)
        back_ocr_img = trim_bottom_25(deep_cropped_back)
        
    is_fmt_b = "FORMAT B" in format_msg or "FORMAT E" in format_msg
    ocr_results_dc = extract_aadhaar_fields(front_ocr_img, back_ocr_img, is_format_b=is_fmt_b)
    
    return ocr_results_dc

