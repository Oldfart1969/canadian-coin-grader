
from __future__ import annotations
from PIL import Image
import numpy as np
import cv2
import math

GRADE_POINTS = [
    (1, "PO-1"), (2, "FR-2"), (3, "AG-3"), (4, "G-4"), (6, "G-6"),
    (8, "VG-8"), (10, "VG-10"), (12, "F-12"), (15, "F-15"),
    (20, "VF-20"), (25, "VF-25"), (30, "VF-30"), (35, "VF-35"),
    (40, "EF-40"), (45, "EF-45"), (50, "AU-50"), (53, "AU-53"),
    (55, "AU-55"), (58, "AU-58"), (60, "MS-60"), (61, "MS-61"),
    (62, "MS-62"), (63, "MS-63"), (64, "MS-64"), (65, "MS-65"),
    (66, "MS-66"), (67, "MS-67"), (68, "MS-68"), (69, "MS-69"), (70, "MS-70")
]

def _to_cv(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def _coin_mask(gray):
    h, w = gray.shape
    yy, xx = np.ogrid[:h, :w]
    cx, cy = w/2, h/2
    r = min(h, w) * 0.43
    mask = ((xx-cx)**2 + (yy-cy)**2 <= r*r).astype(np.uint8) * 255
    return mask

def _normalize(x, lo, hi):
    return float(np.clip((x-lo)/(hi-lo), 0, 1))

def _analyze(img: Image.Image):
    cv = _to_cv(img)
    gray = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    mask = _coin_mask(gray)

    # Detail / focus: variance of Laplacian over central coin area
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    detail_raw = float(lap[mask > 0].var())
    detail = _normalize(math.log1p(detail_raw), 3.8, 7.0)

    # Local contrast as a proxy for surviving relief / definition
    blur = cv2.GaussianBlur(gray, (0,0), 7)
    local = cv2.absdiff(gray, blur)
    contrast_raw = float(local[mask > 0].mean())
    contrast = _normalize(contrast_raw, 3.5, 15.0)

    # Surface uniformity: robust dispersion after removing illumination gradient
    smooth = cv2.GaussianBlur(gray, (0,0), 25)
    residual = cv2.absdiff(gray, smooth)
    residual_vals = residual[mask > 0]
    surf_p90 = float(np.percentile(residual_vals, 90))
    surface = 1.0 - _normalize(surf_p90, 10, 38)

    # "Luster" photo proxy: balance of highlights and tonal range.
    vals = gray[mask > 0]
    p10, p50, p90 = np.percentile(vals, [10, 50, 90])
    tonal_range = p90 - p10
    highlight_fraction = float(np.mean(vals > min(245, p90 + 8)))
    luster = 0.75*_normalize(tonal_range, 45, 145) + 0.25*_normalize(highlight_fraction, 0.005, 0.09)

    # Marks proxy: short strong edges in inner fields. This is intentionally conservative.
    edges = cv2.Canny(gray, 90, 190)
    inner = _coin_mask(gray)
    edge_density = float(np.mean(edges[inner > 0] > 0))
    marks = _normalize(edge_density, 0.055, 0.19)

    # Exposure quality
    clipped = float(np.mean((vals < 8) | (vals > 247)))
    exposure_quality = 1.0 - _normalize(clipped, 0.01, 0.16)

    return {
        "detail": detail,
        "contrast": contrast,
        "surface": surface,
        "luster": luster,
        "marks": marks,
        "exposure_quality": exposure_quality,
    }

def _nearest_grade(n, strike):
    n = float(np.clip(n, 1, 70))
    point, label = min(GRADE_POINTS, key=lambda p: abs(p[0]-n))
    if strike.startswith("Proof-Like"):
        if point >= 60:
            label = label.replace("MS-", "PL-")
    elif strike.startswith("Specimen"):
        if point >= 60:
            label = label.replace("MS-", "SP-")
    elif strike.startswith("Proof"):
        if point >= 60:
            label = label.replace("MS-", "PR-")
    return point, label

def _label_for(n, strike):
    return _nearest_grade(n, strike)[1]

def validate_image(img: Image.Image, side: str):
    issues = []
    w, h = img.size
    if min(w,h) < 700:
        issues.append(f"La photo de l'{side} est plutôt petite; 1200 px ou plus est préférable.")
    a = _analyze(img)
    if a["detail"] < 0.22:
        issues.append(f"La photo de l'{side} semble manquer de netteté.")
    if a["exposure_quality"] < 0.55:
        issues.append(f"L'exposition de l'{side} semble difficile (zones très sombres ou brûlées).")
    return issues

def grade_coin(obv, rev, denomination, year, strike):
    a = _analyze(obv)
    b = _analyze(rev)
    avg = {k:(a[k]+b[k])/2 for k in a}

    # Two-stage approximation:
    # preservation_score estimates circulated wear; mint_quality separates 60–67-ish coins.
    preservation = (
        0.34*avg["detail"] +
        0.23*avg["contrast"] +
        0.19*avg["surface"] +
        0.14*avg["luster"] +
        0.10*(1-avg["marks"])
    )

    # Nonlinear mapping gives useful spread through circulated grades.
    if preservation < 0.18:
        numeric = 3 + preservation/0.18*5
    elif preservation < 0.32:
        numeric = 8 + (preservation-0.18)/0.14*12
    elif preservation < 0.46:
        numeric = 20 + (preservation-0.32)/0.14*20
    elif preservation < 0.60:
        numeric = 40 + (preservation-0.46)/0.14*18
    else:
        mint_quality = (
            0.28*avg["surface"] +
            0.25*(1-avg["marks"]) +
            0.20*avg["detail"] +
            0.17*avg["luster"] +
            0.10*avg["contrast"]
        )
        numeric = 58 + 10.0*np.clip((mint_quality-0.38)/0.50, 0, 1)

    # A two-photo algorithm should almost never claim 69/70.
    numeric = min(float(numeric), 67.0)

    # Confidence is image-quality confidence, not certification confidence.
    side_agreement = 1.0 - min(1.0, abs(
        (a["detail"]+a["surface"]+a["contrast"])/3 -
        (b["detail"]+b["surface"]+b["contrast"])/3
    ) / 0.42)
    photo_quality = (avg["detail"]*0.45 + avg["exposure_quality"]*0.35 + side_agreement*0.20)
    confidence = float(np.clip(0.38 + 0.43*photo_quality, 0.35, 0.82))

    _, grade = _nearest_grade(numeric, strike)
    spread = 3 if numeric < 50 else (2 if numeric < 60 else 1.5)
    low = _label_for(numeric-spread, strike)
    high = _label_for(numeric+spread, strike)

    warnings = []
    if numeric >= 60:
        warnings.append(
            "La distinction entre MS-62, MS-63, MS-64, etc. dépend fortement du lustre, des hairlines, "
            "des marques dans les zones focales et de l'eye appeal; des photos statiques limitent cette évaluation."
        )
    if avg["exposure_quality"] < 0.65:
        warnings.append("L'éclairage réduit la fiabilité de l'estimation.")
    warnings.append(
        "Ce moteur n'est pas encore entraîné sur une banque massive de pièces canadiennes certifiées; "
        "le résultat doit être considéré comme une estimation de prototype."
    )

    return {
        "grade": grade,
        "numeric_grade": numeric,
        "confidence": confidence,
        "range": (low, high),
        "metrics": {
            "detail_score": round(avg["detail"]*100, 1),
            "surface_score": round(avg["surface"]*100, 1),
            "contrast_score": round(avg["contrast"]*100, 1),
            "luster_score": round(avg["luster"]*100, 1),
            "marks_penalty": round(avg["marks"]*100, 1),
        },
        "warnings": warnings,
        "meta": {"denomination": denomination, "year": year, "strike": strike}
    }

def grade_explanation(result):
    n = result["numeric_grade"]
    if n < 12:
        condition = "La pièce paraît fortement usée, avec une perte importante de détails."
    elif n < 40:
        condition = "La pièce paraît circulée, avec une usure visible mais des éléments du dessin encore bien identifiables."
    elif n < 50:
        condition = "L'usure semble légère et principalement concentrée sur les points hauts."
    elif n < 60:
        condition = "La pièce semble proche de l'état neuf, avec seulement de faibles signes d'usure ou de friction."
    else:
        condition = "L'image est compatible avec une pièce non circulée; le sous-grade dépend surtout de la qualité des surfaces, du lustre et des marques."
    return condition + " La fourchette affichée reflète l'incertitude normale d'une analyse faite à partir de photographies."
