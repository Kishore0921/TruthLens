import uuid
import os
import json
import numpy as np
from PIL import Image, ImageStat
from pathlib import Path
from backend.schemas import Finding, EvidenceLocation
from backend.config import PROCESSED_DIR
from backend.forensic.metadata import extract_image_metadata
from backend.models_registry import ModelRegistry

async def analyze_image(evidence_id: str, filepath: str, media_type: str) -> list[Finding]:
    findings: list[Finding] = []
    processed_dir = PROCESSED_DIR / evidence_id
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with Image.open(filepath) as img_file:
            img = img_file.copy()
    except Exception as e:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="image",
            engine="image_validator",
            indicator="file_read_error",
            description=f"Failed to read image file: {str(e)}",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="high",
            limitations=["File is corrupted or in an unreadable format"]
        ))
        return findings

    # 1. Image Properties & Dimensions
    file_size = os.path.getsize(filepath)
    width, height = img.size
    img_format = img.format or "UNKNOWN"
    img_mode = img.mode
    
    findings.append(Finding(
        finding_id=str(uuid.uuid4()),
        evidence_id=evidence_id,
        media_type="image",
        engine="image_properties",
        indicator="file_properties",
        description=f"Confirmed image properties: {width}x{height} pixels, format={img_format}, mode={img_mode}, size={file_size:,} bytes",
        location=EvidenceLocation(),
        model_score=None,
        confidence_band="high",
        limitations=["Confirmed file header and container metadata only"]
    ))

    # 2. Metadata & EXIF Analysis
    metadata = extract_image_metadata(filepath)
    exif = metadata.get("exif", {})
    if exif:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="image",
            engine="metadata_extraction",
            indicator="exif_data_present",
            description=f"EXIF metadata present ({len(exif)} fields recorded). Camera/software tags detected.",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="high",
            limitations=["EXIF metadata can be inserted, stripped, or modified by standard tools"]
        ))
        
        # Check specific metadata tags
        for dt_field in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
            if dt_field in exif:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="image",
                    engine="metadata_extraction",
                    indicator="metadata_timestamp",
                    description=f"Embedded timestamp ({dt_field}): {exif[dt_field]}",
                    location=EvidenceLocation(),
                    model_score=None,
                    confidence_band="high",
                    limitations=["Device timestamps depend on device clock accuracy and can be altered"]
                ))
                break
                
        for device_field in ["Make", "Model", "Software"]:
            if device_field in exif:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="image",
                    engine="metadata_extraction",
                    indicator=f"metadata_{device_field.lower()}",
                    description=f"Reported {device_field}: {exif[device_field]}",
                    location=EvidenceLocation(),
                    model_score=None,
                    confidence_band="high",
                    limitations=[f"{device_field} is a user-editable or firmware-reported field"]
                ))
    else:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="image",
            engine="metadata_extraction",
            indicator="exif_absent",
            description="No EXIF metadata structure located. Standard for screenshots, web social media re-encodings, or stripped files.",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="high",
            limitations=["Absence of EXIF metadata does not indicate artificial generation or tampering"]
        ))

    # 3. Error Level Analysis (ELA)
    try:
        img_rgb = img.convert("RGB")
        ela_temp_path = processed_dir / "ela_temp.jpg"
        ela_viz_path = processed_dir / "ela_visualization.png"
        
        # Re-save at fixed quality (92)
        img_rgb.save(ela_temp_path, "JPEG", quality=92)
        resaved = Image.open(ela_temp_path)
        
        orig_arr = np.array(img_rgb, dtype=np.float32)
        resaved_arr = np.array(resaved, dtype=np.float32)
        
        diff = np.abs(orig_arr - resaved_arr)
        max_diff = float(np.max(diff))
        mean_diff = float(np.mean(diff))
        std_diff = float(np.std(diff))
        
        # Normalize and enhance contrast for visualization
        scale = 255.0 / (max_diff + 1e-6) if max_diff > 0 else 1.0
        ela_visual = np.clip(diff * min(scale, 10.0), 0, 255).astype(np.uint8)
        Image.fromarray(ela_visual).save(ela_viz_path)
        
        # Remove temporary file
        if ela_temp_path.exists():
            ela_temp_path.unlink()
            
        # Regional variance check across a 4x4 grid
        h, w = diff.shape[:2]
        region_means = []
        for r in range(4):
            for c in range(4):
                y1, y2 = int(r * h / 4), int((r + 1) * h / 4)
                x1, x2 = int(c * w / 4), int((c + 1) * w / 4)
                if y2 > y1 and x2 > x1:
                    region_means.append(float(np.mean(diff[y1:y2, x1:x2])))
                    
        min_r = min(region_means) if region_means else 0.0
        max_r = max(region_means) if region_means else 0.0
        variance_ratio = (max_r / (min_r + 1e-5)) if min_r > 0 else 1.0
        
        # Normalised heuristic score: 0.0 to 1.0 (indicator of compression inconsistency)
        heuristic_score = round(float(np.clip(variance_ratio / 6.0, 0.0, 1.0)), 3)
        band = "low" if heuristic_score < 0.4 else ("medium" if heuristic_score < 0.75 else "high")
        
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="image",
            engine="ela_engine",
            indicator="compression_error_distribution",
            description=(
                f"Error Level Analysis completed (JPEG Q92 delta). Mean residual: {mean_diff:.2f}, "
                f"Max residual: {max_diff:.1f}, Standard deviation: {std_diff:.2f}. "
                f"Regional variance ratio: {variance_ratio:.2f}. "
                f"{'Elevated localized compression divergence observed.' if variance_ratio > 3.5 else 'Relatively uniform compression characteristics.'}"
            ),
            location=EvidenceLocation(region={"variance_ratio": round(variance_ratio, 2)}),
            model_score=heuristic_score,
            confidence_band=band,
            limitations=[
                "ELA indicates compression surface discrepancies, NOT confirmed forgery",
                "Different textures, edge density, and high-frequency patterns naturally produce varying error levels",
                "Cannot distinguish between legitimate localized editing and synthetic insertion"
            ]
        ))
    except Exception as e:
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="image",
            engine="ela_engine",
            indicator="ela_processing_exception",
            description=f"Error Level Analysis could not be computed: {str(e)}",
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="low",
            limitations=["Format conversion or color space incompatibility during ELA"]
        ))

    # 4. Color Channel Statistics
    try:
        stats = ImageStat.Stat(img.convert("RGB"))
        r_mean, g_mean, b_mean = stats.mean[:3]
        r_std, g_std, b_std = stats.stddev[:3]
        
        findings.append(Finding(
            finding_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            media_type="image",
            engine="image_statistics",
            indicator="rgb_channel_distribution",
            description=(
                f"Color channel distribution: R(μ={r_mean:.1f}, σ={r_std:.1f}), "
                f"G(μ={g_mean:.1f}, σ={g_std:.1f}), B(μ={b_mean:.1f}, σ={b_std:.1f})"
            ),
            location=EvidenceLocation(),
            model_score=None,
            confidence_band="high",
            limitations=["Descriptive empirical distribution; does not imply manipulation on its own"]
        ))
    except Exception:
        pass
        
    # 5. Pretrained / Reference-Independent Authenticity Models
    registry = ModelRegistry.get_instance()
    for task_name in ["ai_image_frequency_analysis", "sensor_noise_consistency"]:
        adapters = registry.get_models_for_task(task_name)
        for adapter in adapters:
            try:
                pred = await adapter.predict(filepath)
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="image",
                    engine=adapter.model_id,
                    indicator=pred.indicator,
                    description=pred.description,
                    location=EvidenceLocation(region=pred.details),
                    model_score=pred.score,
                    confidence_band=pred.confidence_band,
                    limitations=pred.limitations
                ))
            except Exception as e:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    evidence_id=evidence_id,
                    media_type="image",
                    engine=adapter.model_id,
                    indicator="model_execution_error",
                    description=f"Model {adapter.model_id} failed: {str(e)}",
                    location=EvidenceLocation(),
                    model_score=None,
                    confidence_band="low",
                    limitations=["Model inference failed gracefully"]
                ))
        
    return findings
