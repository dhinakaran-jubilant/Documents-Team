
    
"""Extract Name, Father's Name, and PAN Number using an Anchor-Based ROI Crop Pipeline."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from pytesseract import Output, TesseractNotFoundError
from PIL import Image

try:
    import fitz  # PyMuPDF, only needed for PDF input
except ImportError:  # pragma: no cover
    fitz = None


# --------------------------------------------------------------------------
# Regexes / constants
# --------------------------------------------------------------------------

PAN_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{5}\s*\d{4}\s*[A-Z])(?![A-Z0-9])")
PAN_LOOSE_RE = re.compile(r"(?<![A-Z0-9])([A-Z¢©]{5}\s*[0-9OISB]{4}\s*[A-Z¢©01])(?![A-Z])")
DATE_RE = re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{4}\b")

# Per-word OCR confidence thresholds (0-100) tried in order, loosest last.
# PAN cards carry a large faint background watermark (the Ashoka emblem /
# a ghost portrait). When Tesseract reads a name line, it sometimes also
# "reads" a few extra characters out of that watermark texture immediately
# to the right of the real word (e.g. "VISHAL N" -> "VISHAL N EES",
# "NAGENDRAN" -> "NAGENDRAN S A"). Those stray watermark misreads score much
# lower confidence than genuinely printed text, even though the resulting
# string can look like a perfectly plausible short word/initial. Filtering
# on confidence removes them before they ever become part of the name,
# instead of trying to spot them after the fact from their string shape.
NAME_CONFIDENCE_LEVELS = (60, 40, 20)

@dataclass
class PanDetails:
    name: str = ""
    fathers_name: str = ""
    pan_number: str = ""
    raw_text: str = ""
    cropped_image: "np.ndarray | None" = None
    dob: str = ""
    debug_info: dict = None

@dataclass
class TextWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    bottom: int
    right: int
    conf: float


def _ensure_tesseract(tesseract_cmd: str | None) -> None:
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif not shutil.which("tesseract"):
        raise RuntimeError("Tesseract was not found.")

def _extract_best_name(raw_text: str, prefer_last: bool = True) -> str:
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    valid_lines = []
    for line in lines:
        cleaned = re.sub(r"[^A-Za-z ]", " ", line).upper()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        noise = {"NAME", "FATHER", "FATHERS", "DATE", "BIRTH", "SIGNATURE", "SIGNA", "SIGN",
                 "GOVT", "DEPARTMENT", "INCOME", "TAX", "PERMANENT", "ACCOUNT",
                 "NUMBER", "CARD", "INDIA", "NAMO", "NAAM"}
        words = []
        for w in cleaned.split():
            if w in noise: continue
            if len(w) == 1 and w not in {"V", "N", "S", "K", "M", "R", "J", "A", "P", "T", "B", "C", "D", "G", "L"}: continue
            if len(w) == 2 and w not in {"JR", "SR", "MD", "CH", "DR", "KU", "CH", "SM"}: continue
            words.append(w)
        cleaned = " ".join(words)
        if len(cleaned) >= 3:
            valid_lines.append(cleaned)

    if not valid_lines:
        return ""

    if prefer_last:
        return valid_lines[-1]
    else:
        return valid_lines[0]

def _pick_best_name(candidates: list[str]) -> str:
    """Pick the most complete name from multiple OCR attempts.

    Scores each candidate by the total length of multi-letter words,
    which filters out noisy single-letter fragments that some Tesseract
    modes produce from watermark/Hindi text.  Longer meaningful content
    means the OCR captured more of the printed name.
    """
    candidates = [c for c in candidates if c]
    if not candidates:
        return ""

    def _score(name: str) -> int:
        return sum(len(w) for w in name.split() if len(w) > 1)

    return max(candidates, key=_score)

def _is_plausible_name(line: str) -> bool:
    words = line.split()
    if not words or len(words) > 6: return False
    NOISE = {"INCOME", "TAX", "DEPARTMENT", "GOVT", "GOVERNMENT", "INDIA", "PERMANENT", "ACCOUNT", "NUMBER", "CARD", "FATHER", "FATHERS", "MOTHER", "NAME", "NAMO", "NAAM", "DATE", "BIRTH", "SIGNATURE", "COMMISSIONER", "OFFICE", "ISSUED", "PAN"}
    if any(word in NOISE for word in words): return False
    letters = sum(map(len, words))
    if letters < 4 or letters > 40: return False
    return True

def _extract_from_lines(text: str) -> tuple[str, str, str, bool]:
    lines_raw = [line.strip() for line in text.splitlines() if line.strip()]
    
    name, fathers_name, dob = "", "", ""
    
    # 1. Extract DOB
    for line in lines_raw:
        match = DATE_RE.search(line)
        if match:
            dob = match.group(0)
            break
            
    def clean_val_strict(s: str) -> str:
        # If the line as a whole contains header keywords, return empty string to discard it entirely
        s_no_space = re.sub(r"[^A-Z]", "", s.upper())
        if any(kw in s_no_space for kw in ["INCOME", "TAX", "GOVT", "DEPARTMENT", "PERMANENT", "ACCOUNT"]):
            return ""
            
        # Tesseract often inserts _, |, ~ between the real text on the left and the hologram on the right.
        # Truncate the string at these markers to drop the hologram noise.
        for sep in ['_', '|', '~', '=', ';']:
            idx = s.find(sep)
            if idx > 2 and any(c.isalpha() for c in s[:idx]):
                s = s[:idx]
                
        # Remove standalone lowercase letters which are usually speck/noise misreads
        words = [w for w in s.split() if not (len(w) == 1 and w.islower())]
        s = " ".join(words)
        s = re.sub(r"[^A-Za-z\s]", " ", s)
        s = re.sub(r"\s+", " ", s).strip().upper()
        noise = {"NAME", "FATHER", "FATHERS", "DATE", "BIRTH", "SIGNATURE", "GOVT", "DEPARTMENT", "INCOME", "TAX", "PERMANENT", "ACCOUNT", "PAN", "CARD", "SIGNA", "SIGN", "NAMO", "NAAM", "KAME", "NANE", "MAME", "CAN", "PTE", "FEE"}
        return " ".join([w for w in s.split() if w not in noise])

    father_idx = -1
    for i, line in enumerate(lines_raw):
        upper = line.upper()
        if "FATHER" in upper or "FATHFR" in upper or "FATHERS" in upper:
            father_idx = i
            break
            
    if father_idx != -1:
        # Father's Name: 1-2 lines after FATHER label
        f_lines = []
        for i in range(father_idx + 1, min(father_idx + 4, len(lines_raw))):
            line_upper = lines_raw[i].upper()
            if re.search(r"\d", line_upper):
                break
            if "DATE" in line_upper or "BIRTH" in line_upper:
                break
            # Special characters like '|' are often read as artifacts at the edge of the image,
            # so we shouldn't break on them. They will be cleanly stripped by clean_val_strict.
            if sum(1 for c in lines_raw[i] if c.islower()) > len(lines_raw[i]) * 0.3:
                break
            cleaned = clean_val_strict(lines_raw[i])
            if len(cleaned) >= 2:
                # If we already have the first line of the name, any subsequent line must have a word >= 3 chars.
                # This prevents appending uppercase OCR noise from the Hindi DOB label (e.g. "FT HT").
                if len(f_lines) >= 1 and not any(len(w) >= 3 for w in cleaned.split()):
                    break
                f_lines.append(cleaned)
        fathers_name = " ".join(f_lines)
        
        # Registration Name: 1-2 lines before FATHER label
        n_lines = []
        for i in range(father_idx - 1, max(-1, father_idx - 4), -1):
            line_upper = lines_raw[i].upper()
            if re.search(r"\d", line_upper):
                break
            if "INCOME" in line_upper or "TAX" in line_upper or "GOVT" in line_upper or "DEPARTMENT" in line_upper:
                break
            if "NAM" in line_upper or any(w.endswith("AME") and len(w) == 4 for w in line_upper.split()):
                break
            # Special characters like '|' are often read as artifacts at the edge of the image,
            # so we shouldn't break on them. They will be cleanly stripped by clean_val_strict.
            if sum(1 for c in lines_raw[i] if c.islower()) > len(lines_raw[i]) * 0.3:
                break
            cleaned = clean_val_strict(lines_raw[i])
            if len(cleaned) >= 2:
                n_lines.append(cleaned)
        n_lines.reverse()
        name = " ".join(n_lines)
    else:
        # Fallback if "FATHER" label is missing entirely (e.g., older or specific region PAN cards)
        header_idx = -1
        for i, line in enumerate(lines_raw):
            s_no_space = re.sub(r"[^A-Z]", "", line.upper())
            if any(kw in s_no_space for kw in ["INCOME", "TAX", "GOVT", "DEPARTMENT"]):
                header_idx = i
                
        start_idx = header_idx + 1 if header_idx != -1 else 0
        
        plausible = []
        for i in range(start_idx, len(lines_raw)):
            # Skip lines with digits (DOB or PAN Number)
            if re.search(r"\d", lines_raw[i]): 
                continue
            # Skip lines that are mostly lowercase (> 30%) (these are usually noise from the Hindi labels)
            if sum(1 for c in lines_raw[i] if c.islower()) > len(lines_raw[i]) * 0.3:
                continue
                
            cleaned_line = clean_val_strict(lines_raw[i])
            # A valid name should have at least 3 letters and not be a massive paragraph
            if len(cleaned_line) >= 3 and len(cleaned_line) < 40:
                plausible.append(cleaned_line)
                
        if len(plausible) >= 1: name = plausible[0]
        if len(plausible) >= 2: fathers_name = plausible[1]
        
    return name, fathers_name, dob, (father_idx != -1)

def _fix_pan_loose_chars(candidate: str) -> str:
    chars = list(candidate)
    
    # Fix letters in the first 5 and last 1 characters
    for i in list(range(5)) + [9]:
        if chars[i] in ("¢", "©"):
            chars[i] = "C"
            
    # The last character MUST be a letter, but OCR sometimes reads 'O' as '0' or 'I' as '1'
    if chars[9] == "0": chars[9] = "O"
    if chars[9] == "1": chars[9] = "I"

    # Fix digits in the middle 4 characters
    for i in range(5, 9):
        if chars[i] == "O": chars[i] = "0"
        elif chars[i] == "I": chars[i] = "1"
        elif chars[i] == "S": chars[i] = "5"
        elif chars[i] == "B": chars[i] = "8"
        
    return "".join(chars)

def _find_pan(text: str) -> str:
    upper = text.upper()
    match = PAN_RE.search(upper)
    if match: return re.sub(r"\s+", "", match.group(1))
    match = PAN_LOOSE_RE.search(upper)
    if match: return _fix_pan_loose_chars(re.sub(r"\s+", "", match.group(1)))
    return ""

def _deskew(image: "cv2.Mat") -> "cv2.Mat":
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    angles = []
    for c in contours:
        rect = cv2.minAreaRect(c)
        angle = rect[-1]
        if angle < -45: angle = -(90 + angle)
        else: angle = -angle
        w, h = rect[1]
        if w > 0 and h > 0 and max(w, h) / min(w, h) > 2:
            angles.append(angle)
    if not angles: return image
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5: return image
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

def _get_words(image: "cv2.Mat") -> list[TextWord]:
    data = pytesseract.image_to_data(image, config="--oem 3 --psm 11", output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        # Remove confidence filter to catch poorly recognized anchor words
        if not text: continue
        conf = float(data['conf'][i])
        left = data['left'][i]
        top = data['top'][i]
        w = data['width'][i]
        h = data['height'][i]
        words.append(TextWord(text, left, top, w, h, top + h, left + w, conf))
    return words


def _ocr_text_by_confidence(image: "cv2.Mat", config: str, min_conf: int) -> str:
    """Run Tesseract and rebuild line text keeping only high-confidence words.

    image_to_string() collapses everything to a plain string, so a real
    printed word and an equally plausible-looking watermark misread both
    just come out as text - there is no way to tell them apart afterwards.
    image_to_data() additionally returns Tesseract's own per-word
    confidence, which is what actually distinguishes them: stray reads off
    the background watermark reliably score much lower than genuinely
    printed characters, regardless of how "real" the resulting word looks.
    Words are grouped back into lines using Tesseract's own
    block/paragraph/line numbering so line structure is preserved.
    """
    try:
        data = pytesseract.image_to_data(image, config=config, output_type=Output.DICT)
    except TesseractNotFoundError:
        raise
    except Exception:
        return ""

    n = len(data.get("text", []))
    lines: dict[tuple, list[str]] = {}
    order: list[tuple] = []
    for i in range(n):
        word = data["text"][i].strip()
        if not word:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < min_conf:
            continue
            
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left = data["left"][i]
        word_h = data["height"][i]
        
        if key not in lines:
            lines[key] = []
            order.append(key)
            lines[key].append((word, left, word_h, left + data["width"][i]))
        else:
            # Check horizontal gap from the previous word
            prev_word, prev_left, prev_h, prev_right = lines[key][-1]
            gap = left - prev_right
            
            # If the gap is massive (e.g. more than 1.5x the line height), it's physically disconnected
            # This perfectly isolates the main name from background watermarks or right-side holograms
            if gap > word_h * 1.5:
                continue # Ignore this word and all subsequent words on this physical line
                
            lines[key].append((word, left, word_h, left + data["width"][i]))

    return "\n".join(" ".join(w[0] for w in lines[key]) for key in order)


def _ocr_text_multi_confidence(image: "cv2.Mat", config: str) -> str:
    """Try progressively looser confidence thresholds, then fall back to
    unfiltered image_to_string so a blurry/low-quality photo never ends up
    with no text at all just because every word scored under the highest
    threshold.
    """
    for min_conf in NAME_CONFIDENCE_LEVELS:
        text = _ocr_text_by_confidence(image, config, min_conf)
        if text.strip():
            return text
    return pytesseract.image_to_string(image, config=config)


def _extract_pan_number(gray: "cv2.Mat", thresh_full: "cv2.Mat") -> str:
    """Find the PAN number, trying progressively more aggressive fallbacks.

    Old/faded photocopied cards (uneven scan lighting, low print contrast)
    can come out too washed-out for the adaptive-threshold word pass to
    catch the PAN line at all, even though the number is plainly visible
    to a person. Rather than give up after one preprocessing/OCR attempt,
    this tries several different views of the image in order, stopping as
    soon as one produces a valid-looking match.
    """
    words = _get_words(thresh_full)

    for w in words:
        upper = w.text.upper()
        if PAN_RE.search(upper) or PAN_LOOSE_RE.search(upper):
            pan = _find_pan(upper)
            if pan:
                return pan

    # A valid PAN can be split across adjacent word tokens by Tesseract
    # (e.g. "AEAPC" / "4119G"), so also search the words joined together.
    pan = _find_pan(" ".join(w.text for w in words))
    if pan:
        return pan

    # Fall back to whole-image OCR on a few different renderings: plain
    # grayscale, the threshold image, and a contrast-boosted version for
    # faded/uneven scans where neither of the above has enough contrast
    # for Tesseract to separate the printed characters from the paper.
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    for img, cfg in (
        (gray, "--oem 3 --psm 3"),
        (thresh_full, "--oem 3 --psm 3"),
        (gray, "--oem 3 --psm 6"),
        (thresh_full, "--oem 3 --psm 6"),
        (gray, "--oem 3 --psm 4"),
        (thresh_full, "--oem 3 --psm 4"),
        (enhanced, "--oem 3 --psm 6"),
        (enhanced, "--oem 3 --psm 11"),
    ):
        text = pytesseract.image_to_string(img, config=cfg)
        pan = _find_pan(text)
        if pan:
            return pan

    return ""


def _crop_and_ocr(image: "cv2.Mat", top: int, bottom: int, left: int, right: int) -> str:
    h, w = image.shape[:2]
    top = max(0, int(top))
    bottom = min(h, int(bottom))
    left = max(0, int(left))
    right = min(w, int(right))
    if bottom <= top or right <= left: return ""

    roi = image[top:bottom, left:right]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    text = pytesseract.image_to_string(gray, config="--oem 3 --psm 6").strip()
    return text

def _get_card_regions(image: "cv2.Mat") -> list[tuple["cv2.Mat", tuple[int, int, int, int]]]:
    """Detect up to 2 individual PAN card regions, properly separating side-by-side cards."""
    img_h, img_w = image.shape[:2]
    image_area   = img_h * img_w
    found_boxes  = []  # (area, x1, y1, x2, y2)

    # ── PRIMARY: HSV color mask with a SMALL kernel ────────────────────────
    # Use a 9×9 kernel (not 25×25) — small enough to fill the photo/QR/text
    # holes inside a single card without bridging the gap between two cards.
    hsv    = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask_a = cv2.inRange(hsv, np.array([80, 25, 50]),  np.array([135, 255, 255]))
    mask_b = cv2.inRange(hsv, np.array([65, 10, 30]),  np.array([150, 255, 255]))
    mask   = cv2.bitwise_or(mask_a, mask_b)
    fill_k = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, fill_k, iterations=2)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)

    for lbl in range(1, n_labels):
        area = stats[lbl, cv2.CC_STAT_AREA]
        if area < image_area * 0.03:
            continue
        bx  = stats[lbl, cv2.CC_STAT_LEFT]
        by  = stats[lbl, cv2.CC_STAT_TOP]
        bw  = stats[lbl, cv2.CC_STAT_WIDTH]
        bh  = stats[lbl, cv2.CC_STAT_HEIGHT]
        asp = max(bw, bh) / float(min(bw, bh)) if min(bw, bh) > 0 else 0

        if 1.35 <= asp <= 1.85:
            # Single card — accept directly
            found_boxes.append((area, bx, by, bx + bw, by + bh))

        elif asp > 2.4 and area > image_area * 0.10:
            # Blob is too wide — likely two side-by-side cards merged.
            # Find the split column using horizontal projection (pixel-count valley).
            lbl_mask  = np.uint8(labels == lbl)
            col_sums  = np.sum(lbl_mask, axis=0).astype(np.float32)
            # Search for valley only in the middle third of the blob width
            v_start   = bx + bw // 3
            v_end     = bx + 2 * bw // 3
            mid_slice = col_sums[v_start:v_end]
            if len(mid_slice) > 0:
                split_x = int(np.argmin(mid_slice)) + v_start
                # Verify both halves have a plausible card-like aspect ratio
                lw, rw = split_x - bx, (bx + bw) - split_x
                if lw > 20:
                    la = int(np.sum(lbl_mask[by:by+bh, bx:split_x]))
                    found_boxes.append((la, bx, by, split_x, by + bh))
                if rw > 20:
                    ra = int(np.sum(lbl_mask[by:by+bh, split_x:bx+bw]))
                    found_boxes.append((ra, split_x, by, bx + bw, by + bh))

        elif asp < 1.1 and area > image_area * 0.10:
            # Blob too tall — two cards stacked vertically. Split at row valley.
            lbl_mask  = np.uint8(labels == lbl)
            row_sums  = np.sum(lbl_mask, axis=1).astype(np.float32)
            v_start   = by + bh // 3
            v_end     = by + 2 * bh // 3
            mid_slice = row_sums[v_start:v_end]
            if len(mid_slice) > 0:
                split_y = int(np.argmin(mid_slice)) + v_start
                if split_y - by > 20:
                    found_boxes.append((int(np.sum(lbl_mask[by:split_y, bx:bx+bw])),
                                        bx, by, bx + bw, split_y))
                if (by + bh) - split_y > 20:
                    found_boxes.append((int(np.sum(lbl_mask[split_y:by+bh, bx:bx+bw])),
                                        bx, split_y, bx + bw, by + bh))

    # ── FALLBACK: Canny edge detection ────────────────────────────────────
    if not found_boxes:
        gray    = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged   = cv2.Canny(blurred, 20, 100)
        kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
        closed  = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel, iterations=3)
        cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) < image_area * 0.04:
                continue
            hull = cv2.convexHull(c)
            rect = cv2.minAreaRect(hull)
            (_, _), (rw, rh), _ = rect
            if rw < 1 or rh < 1: continue
            asp = max(rw, rh) / float(min(rw, rh))
            if 1.15 <= asp <= 2.2:
                ex, ey, ew, eh = cv2.boundingRect(hull)
                x1, y1 = max(0, ex), max(0, ey)
                x2, y2 = min(img_w, ex+ew), min(img_h, ey+eh)
                found_boxes.append(((x2-x1)*(y2-y1), x1, y1, x2, y2))

    if not found_boxes:
        return [(image, (0, 0, img_w, img_h))]

    # De-duplicate overlapping boxes (IoU > 0.4 → keep larger)
    found_boxes.sort(key=lambda b: b[0], reverse=True)
    kept = []
    for b in found_boxes:
        ba, bx1, by1, bx2, by2 = b
        overlap = False
        for ka, kx1, ky1, kx2, ky2 in kept:
            ix1, iy1 = max(bx1, kx1), max(by1, ky1)
            ix2, iy2 = min(bx2, kx2), min(by2, ky2)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2-ix1)*(iy2-iy1)
                union = ba + ka - inter
                if union > 0 and inter / union > 0.4:
                    overlap = True
                    break
        if not overlap:
            kept.append(b)

    # ── VALIDATE: Merge false-positive splits of a single card ────────────
    # If we have multiple candidates, check if they are actually halves of one card
    if len(kept) >= 2:
        final_kept = []
        skip_idx = set()
        for i in range(len(kept)):
            if i in skip_idx: continue
            _, x1_i, y1_i, x2_i, y2_i = kept[i]
            w_i, h_i = x2_i - x1_i, y2_i - y1_i
            asp_i = max(w_i, h_i) / float(min(w_i, h_i)) if min(w_i, h_i) > 0 else 0
            
            merged_with_j = -1
            for j in range(i + 1, len(kept)):
                if j in skip_idx: continue
                _, x1_j, y1_j, x2_j, y2_j = kept[j]
                w_j, h_j = x2_j - x1_j, y2_j - y1_j
                asp_j = max(w_j, h_j) / float(min(w_j, h_j)) if min(w_j, h_j) > 0 else 0
                
                # 1. Are they roughly vertically aligned (similar y-range / height)?
                y_overlap = min(y2_i, y2_j) - max(y1_i, y1_j)
                min_h = min(h_i, h_j)
                vertically_aligned = (y_overlap > 0) and (y_overlap / min_h > 0.5)
                
                # 2. Is the horizontal gap between them small relative to total image width?
                gap_x = max(0, max(x1_i, x1_j) - min(x2_i, x2_j))
                small_gap = gap_x < (img_w * 0.15)
                
                if vertically_aligned and small_gap:
                    mx1 = min(x1_i, x1_j)
                    my1 = min(y1_i, y1_j)
                    mx2 = max(x2_i, x2_j)
                    my2 = max(y2_i, y2_j)
                    mw, mh = mx2 - mx1, my2 - my1
                    masp = max(mw, mh) / float(min(mw, mh)) if min(mw, mh) > 0 else 0
                    
                    # 3. Does their combined bounding box roughly match a standard ID card aspect ratio (~1.585:1)?
                    merged_good = 1.35 <= masp <= 1.85
                    
                    if merged_good:
                        merged_with_j = j
                        break
                        
            if merged_with_j != -1:
                # Merge i and j
                _, x1_j, y1_j, x2_j, y2_j = kept[merged_with_j]
                mx1 = min(x1_i, x1_j)
                my1 = min(y1_i, y1_j)
                mx2 = max(x2_i, x2_j)
                my2 = max(y2_i, y2_j)
                ma = (mx2 - mx1) * (my2 - my1)
                final_kept.append((ma, mx1, my1, mx2, my2))
                skip_idx.add(merged_with_j)
            else:
                final_kept.append(kept[i])
                
        kept = sorted(final_kept, key=lambda b: b[0], reverse=True)

    crops = []
    for _, x1, y1, x2, y2 in kept[:2]:
        crop = image[y1:y2, x1:x2].copy()
        crops.append((crop, (x1, y1, x2, y2)))
    return crops


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def _extract_normalized_card(original_image: "cv2.Mat", box: tuple[int, int, int, int], debug_info: dict) -> "cv2.Mat":
    """
    Unified, deterministic PAN-card boundary detection.
    Pipeline:
      HSV color mask on a 5%-padded ROI → morphological fill → largest
      connected-component convex hull → minAreaRect → fixed 8% margin
      (clamped to coarse box boundary) → warpPerspective.

    The ROI is strictly limited to the coarse front-card box + 5% padding
    so that a neighbouring back card is NEVER included.
    """
    img_h, img_w = original_image.shape[:2]
    bx1, by1, bx2, by2 = box
    bw = bx2 - bx1
    bh = by2 - by1

    # 5% padded ROI — just enough to recover a slightly clipped card edge
    # without bleeding into a neighbouring card (which is ~100% of a card-
    # width away even when the two cards are touching).
    pad_x = max(5, int(bw * 0.05))
    pad_y = max(5, int(bh * 0.05))
    rx1 = max(0, bx1 - pad_x)
    ry1 = max(0, by1 - pad_y)
    rx2 = min(img_w, bx2 + pad_x)
    ry2 = min(img_h, by2 + pad_y)

    roi      = original_image[ry1:ry2, rx1:rx2]
    roi_h, roi_w = roi.shape[:2]
    roi_area = roi_h * roi_w

    # ── STEP 1 & 2: HSV color mask + morphological fill on the ROI ────────
    hsv    = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask_a = cv2.inRange(hsv, np.array([80,  25, 50]), np.array([135, 255, 255]))
    mask_b = cv2.inRange(hsv, np.array([65,  10, 30]), np.array([150, 255, 255]))
    mask   = cv2.bitwise_or(mask_a, mask_b)

    # Fill internal card holes (photo, QR, text) with a moderately sized kernel
    fill_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, fill_k, iterations=3)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  fill_k, iterations=1)

    # ── STEP 3: Largest connected component in the ROI ────────────────────
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)

    best_label = -1
    best_area  = 0
    for lbl in range(1, n_labels):
        area = stats[lbl, cv2.CC_STAT_AREA]
        if area < roi_area * 0.05:
            continue
        if area > best_area:
            best_area  = area
            best_label = lbl

    if best_label == -1:
        debug_info["crop_method"] = "Fallback: no color mask region (ROI)"
        return original_image[by1:by2, bx1:bx2]

    # ── STEP 3b: CLIP component to the original coarse box ────────────────
    # This is the hard guard that prevents ANY back-card pixel from entering
    # the hull, even if the color mask bled slightly beyond the coarse box.
    component_mask = np.uint8(labels == best_label) * 255
    clip = np.zeros_like(component_mask)
    # coarse box in ROI-local coordinates
    cl_x1 = max(0, bx1 - rx1)
    cl_y1 = max(0, by1 - ry1)
    cl_x2 = min(roi_w, bx2 - rx1)
    cl_y2 = min(roi_h, by2 - ry1)
    clip[cl_y1:cl_y2, cl_x1:cl_x2] = 255
    component_mask = cv2.bitwise_and(component_mask, clip)

    component_pts = cv2.findNonZero(component_mask)
    if component_pts is None:
        debug_info["crop_method"] = "Fallback: clipped mask empty"
        return original_image[by1:by2, bx1:bx2]

    hull = cv2.convexHull(component_pts)

    # ── STEP 4: Minimum-area rotated rectangle of the hull ────────────────
    rect = cv2.minAreaRect(hull)
    (rect_cx, rect_cy), (rect_w, rect_h), angle = rect

    if rect_w < 1 or rect_h < 1:
        debug_info["crop_method"] = "Fallback: degenerate minAreaRect"
        return original_image[by1:by2, bx1:bx2]

    # ── STEP 5: Fixed 8% margin expansion ─────────────────────────────────
    rect_exp = ((rect_cx, rect_cy), (rect_w * 1.08, rect_h * 1.08), angle)
    box_pts  = cv2.boxPoints(rect_exp)
    box_pts  = _order_points(box_pts)

    # Map ROI-local → original image coordinates
    box_pts[:, 0] += rx1
    box_pts[:, 1] += ry1

    # Clip to image bounds
    box_pts[:, 0] = np.clip(box_pts[:, 0], 0, img_w - 1)
    box_pts[:, 1] = np.clip(box_pts[:, 1], 0, img_h - 1)

    # ── STEP 6: Perspective transform ─────────────────────────────────────
    (tl, tr, br, bl) = box_pts
    out_w = max(int(np.linalg.norm(br - bl)), int(np.linalg.norm(tr - tl)))
    out_h = max(int(np.linalg.norm(tr - br)), int(np.linalg.norm(tl - bl)))

    if out_w < 20 or out_h < 20:
        debug_info["crop_method"] = "Fallback: warp dimensions too small"
        return original_image[by1:by2, bx1:bx2]

    dst    = np.array([[0, 0], [out_w-1, 0], [out_w-1, out_h-1], [0, out_h-1]], dtype="float32")
    M      = cv2.getPerspectiveTransform(box_pts, dst)
    warped = cv2.warpPerspective(original_image, M, (out_w, out_h))

    debug_info["crop_method"] = "Unified ROI+clip: mask→hull→minAreaRect→8%→warp"
    return warped



def _correct_orientation_if_needed(image: "cv2.Mat", debug_info: dict) -> "cv2.Mat":
    h, w = image.shape[:2]
    # 1. Aspect Ratio Check
    if w >= h:
        return image  # Already landscape
        
    # Portrait orientation detected. Needs rotation.
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    rotation_angle = None
    try:
        # 2. Determine rotation direction using Tesseract's OSD
        osd = pytesseract.image_to_osd(pil_img, output_type=pytesseract.Output.DICT)
        if osd.get("orientation_conf", 0) > 1.0:
            rotation_angle = osd.get("rotate", 0)
    except Exception:
        pass
        
    # If OSD failed or gave an angle that won't result in landscape (like 0 or 180)
    if rotation_angle is None or rotation_angle in (0, 180):
        # Fall back to heuristic: try both 90 CW and 90 CCW
        img_90_cw = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        img_90_ccw = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        def _score_image(img):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, config="--oem 3 --psm 11").upper()
            return sum(1 for kw in ("INCOME", "TAX", "PERMANENT", "ACCOUNT", "GOVT", "FATHER", "SIGNATURE", "NAME", "INDIA") if kw in text)
            
        score_cw = _score_image(img_90_cw)
        score_ccw = _score_image(img_90_ccw)
        
        if score_cw >= score_ccw:
            image = img_90_cw
        else:
            image = img_90_ccw
    else:
        # 3. Apply the rotation using Pillow
        rotated_pil = pil_img.rotate(-rotation_angle, expand=True)
        image = cv2.cvtColor(np.array(rotated_pil), cv2.COLOR_RGB2BGR)
        
    # 4. Re-validate aspect ratio
    h_new, w_new = image.shape[:2]
    if h_new > w_new:
        msg = "Orientation correction failed to produce a landscape image."
        if debug_info.get("error"):
            debug_info["error"] += f" | {msg}"
        else:
            debug_info["error"] = msg
            
    return image

def _confirm_front_side(region: "cv2.Mat") -> dict:
    h, w = region.shape[:2]
    if max(h, w) < 800:
        scale = 800 / max(h, w)
        region = cv2.resize(region, None, fx=scale, fy=scale)
        
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    is_front_confirmed = False
    confirmation_basis = "NOT_CONFIRMED"
    pan_confidence = 0.0
    text_result = ""
    
    # 1. Strict PAN Check (Primary Confirmation)
    for psm in (6, 11, 3):
        data = pytesseract.image_to_data(gray, config=f"--oem 3 --psm {psm}", output_type=pytesseract.Output.DICT)
        text = " ".join([w for w in data["text"] if w.strip()])
        if not text_result: text_result = text # Save first pass for fallback
        
        # Check raw text
        upper = text.upper()
        match = PAN_RE.search(upper)
        if match:
            is_front_confirmed = True
            confirmation_basis = "PAN_MATCH"
            # Attempt to find the confidence of the match
            pan_str = match.group(1).replace(" ", "")
            for i, w in enumerate(data["text"]):
                if pan_str in w.upper().replace(" ", ""):
                    try:
                        pan_confidence = float(data["conf"][i])
                    except:
                        pass
                    break
            break
            
        # Try OCR correction on near-misses
        loose_match = PAN_LOOSE_RE.search(upper)
        if loose_match:
            candidate = loose_match.group(1).replace(" ", "")
            if len(candidate) == 10:
                corrected = _fix_pan_loose_chars(candidate)
                match = PAN_RE.search(corrected)
                if match:
                    is_front_confirmed = True
                    confirmation_basis = "PAN_MATCH_CORRECTED"
                    break
            
    # 2. Label Check (Secondary Confirmation)
    if not is_front_confirmed:
        # Just use the psm 6 text
        upper = text_result.upper()
        if re.search(r"\bNAME\b", upper) and re.search(r"\bFATHER[S]?\b", upper):
            is_front_confirmed = True
            confirmation_basis = "LABELS_FOUND"
            
    # 3. Fallback scoring (No back-side deductions!)
    front_score = 0
    front_kws = ["INCOME", "TAX", "GOVT", "PERMANENT", "ACCOUNT", "NAME", "FATHER", "DOB", "DATE", "BIRTH", "SIGNATURE"]
    for kw in front_kws:
        if kw in text_result.upper(): front_score += 2
        
    return {
        "text": text_result,
        "front_score": front_score,
        "is_front_confirmed": is_front_confirmed,
        "confirmation_basis": confirmation_basis,
        "pan_confidence": pan_confidence
    }

def _extract_from_crop(image: "cv2.Mat", debug_info: dict) -> tuple[PanDetails, int]:

    h, w = image.shape[:2]
    # Limit upscale to prevent Tesseract distortion on thick text
    if max(h, w) < 1200:
        scale = 1200 / max(h, w)
        image = cv2.resize(image, None, fx=scale, fy=scale)

    ROTATIONS = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    best = None
    for angle, rotate_code in ROTATIONS.items():
        rotated = image if rotate_code is None else cv2.rotate(image, rotate_code)

        scale_factor = 800 / max(rotated.shape[:2])
        if scale_factor < 1:
            small = cv2.resize(rotated, None, fx=scale_factor, fy=scale_factor)
        else:
            small = rotated

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray, lang="eng", config="--oem 3 --psm 11")

        upper = text.upper()
        score = sum(1 for kw in ("INCOME", "TAX", "PERMANENT", "ACCOUNT", "GOVT", "FATHER", "SIGNATURE") if kw in upper)
        if PAN_RE.search(upper): score += 10
        elif PAN_LOOSE_RE.search(upper): score += 5

        if best is None or score > best[0]:
            best = (score, rotated)

    score, correctly_oriented = best

    deskewed = _deskew(correctly_oriented)
    gray_full = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
    thresh_uncropped = cv2.adaptiveThreshold(gray_full, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15)
    img_h, img_w = gray_full.shape

    # Crop image to the left 70% to safely remove photo/hologram/signature noise before OCR for name extraction
    gray = gray_full[:, :int(img_w * 0.70)]
    deskewed_cropped = deskewed[:, :int(img_w * 0.70)]
    
    thresh_full = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15)

    # Generate candidates from both confidence-filtered and raw unfiltered OCR at all levels
    candidates = []
    pass_idx = 0
    for img in (gray, thresh_full):
        for psm in ("4", "6"):
            cfg = f"--oem 3 --psm {psm}"
            
            for min_conf in (60, 40, 20, 0):
                text = _ocr_text_by_confidence(img, cfg, min_conf)
                    
                if text.strip():
                    name_cand, father_cand, dob_cand, found_label = _extract_from_lines(text)
                    candidates.append((name_cand, father_cand, dob_cand, found_label, min_conf, pass_idx))
                pass_idx += 1
            
    # Score candidate pairs to prioritize cleanest text that captures both fields
    best_score = -1
    best_cand = ("", "")
    
    for name_cand, father_cand, dob_cand, found_label, min_conf, p_idx in candidates:
        if not name_cand and not father_cand: continue
        
        score = 0
        if found_label: 
            score += 1000
            
        # We MUST prefer unfiltered passes (min_conf = 0) so we don't accidentally drop valid words of a name
        # just because Tesseract had low confidence in them. Dropping words truncates names!
        score -= min_conf
            
        if name_cand and father_cand: 
            score += 500
        
        # Tie breaker: Prefer earlier passes (gray > thresh, psm 6 > psm 4) instead of rewarding noisy length
        score -= p_idx / 1000.0
        
        if score > best_score:
            best_score = score
            best_cand = (name_cand, father_cand)
            
    name, fathers_name = best_cand
    
    dobs = [c[2] for c in candidates if c[2]]
    dob = dobs[0] if dobs else ""

    # Pass 2: Extract PAN Number on the UNCROPPED image so the PAN on the right isn't chopped in half
    pan = _extract_pan_number(gray_full, thresh_uncropped)
    
    # Fallback: If the uncropped image fails (e.g. QR code scrambles the OCR), try the cropped image.
    if not pan:
        pan = _extract_pan_number(gray, thresh_full)

    raw_full_text_gray = pytesseract.image_to_string(gray, config="--oem 3 --psm 4").strip()
    if not raw_full_text_gray:
        raw_full_text_gray = "(Tesseract found no text in the raw Grayscale image due to low contrast/fading. Extraction relied entirely on Threshold pass.)"
        
    raw_full_text_thresh = pytesseract.image_to_string(thresh_full, config="--oem 3 --psm 4").strip()
    combined_raw_text = f"=== Raw Grayscale Pass ===\n{raw_full_text_gray}\n\n=== Adaptive Threshold Pass ===\n{raw_full_text_thresh}"
    return PanDetails(name=name, fathers_name=fathers_name, pan_number=pan, raw_text=combined_raw_text, cropped_image=deskewed_cropped, dob=dob, debug_info=debug_info), best_score

def _load_pdf_pages(path: Path) -> list["cv2.Mat"]:
    if fitz is None:
        raise RuntimeError("Reading PDF files requires the 'pymupdf' package.")
    pages = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 4: arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3: arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            else: arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            pages.append(arr)
    if not pages: raise ValueError(f"Could not read any pages from PDF: {path}")
    return pages

def extract_pan_details_from_image(path: Path, tesseract_cmd: str | None = None) -> PanDetails:
    _ensure_tesseract(tesseract_cmd)
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        candidate_images = _load_pdf_pages(path)
    else:
        image = cv2.imread(str(path))
        if image is None: raise ValueError(f"Cannot read image: {path}")
        candidate_images = [image]
        
    debug_info = {
        "original_image": candidate_images[0].copy(), # Fallback for UI if needed
        "regions": [],
        "error": None
    }
    
    try:
        # Phase 1: Detect and Confirm Front Side across all pages
        all_regions_data = [] # List of dicts: {"page_idx": int, "region_idx": int, "crop": Mat, "box": tuple, "score_data": dict}
        
        for page_idx, image in enumerate(candidate_images):
            regions = _get_card_regions(image)
            for region_idx, (crop, box) in enumerate(regions):
                score_data = _confirm_front_side(crop)
                all_regions_data.append({
                    "page_idx": page_idx,
                    "region_idx": region_idx,
                    "crop": crop,
                    "box": box,
                    "score_data": score_data
                })
                
        if not all_regions_data:
            raise ValueError("No card-shaped regions detected on any page.")
            
        confirmed_regions = [d for d in all_regions_data if d["score_data"]["is_front_confirmed"]]
        
        best_data = None
        if len(confirmed_regions) == 1:
            best_data = confirmed_regions[0]
        elif len(confirmed_regions) > 1:
            best_data = max(confirmed_regions, key=lambda d: (d["score_data"]["pan_confidence"], d["score_data"]["front_score"]))
        else:
            best_data = max(all_regions_data, key=lambda d: d["score_data"]["front_score"])
            debug_info["error"] = "Front side not confidently detected. Extraction may be inaccurate."
            
        for d in all_regions_data:
            debug_info["regions"].append({
                "page_idx": d["page_idx"],
                "region_idx": d["region_idx"],
                "box": d["box"],
                "score_data": d["score_data"],
                "selected": (d is best_data)
            })
            
        debug_info["original_image"] = candidate_images[best_data["page_idx"]].copy()
            
        # Phase 2: Extract details from the chosen front crop
        original_img = candidate_images[best_data["page_idx"]]
        tight_crop = _extract_normalized_card(original_img, best_data["box"], debug_info)
        
        # 5. Apply orientation correction and update debug_info with the result
        tight_crop = _correct_orientation_if_needed(tight_crop, debug_info)
        debug_info["tight_crop"] = tight_crop.copy()
        
        details, _ = _extract_from_crop(tight_crop, debug_info)
        return details
        
    except TesseractNotFoundError as error:
        raise RuntimeError("Tesseract was not found.") from error
