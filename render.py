# axlescan/render.py
# axlescan/render.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import math
import os

import numpy as np


# ============================================================
# Utilities
# ============================================================

def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _to_np_f32(a) -> np.ndarray:
    if a is None:
        return np.empty((0, 3), dtype=np.float32)
    x = np.asarray(a, dtype=np.float32)
    if x.ndim == 1:
        x = x.reshape(-1, 3)
    if x.shape[-1] != 3:
        raise ValueError("points must be (..., 3)")
    return x


def _bbox_minmax_from_best(best: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Best detection carries bbox as {"min": [x,y,z], "max": [x,y,z]}.
    If absent, returns NaNs to indicate no crop.
    """
    bb = best.get("bbox") or {}
    bmin = np.asarray(bb.get("min"), dtype=np.float32) if bb.get("min") is not None else np.full(3, np.nan, np.float32)
    bmax = np.asarray(bb.get("max"), dtype=np.float32) if bb.get("max") is not None else np.full(3, np.nan, np.float32)
    if bmin.shape != (3,) or bmax.shape != (3,):
        bmin = np.full(3, np.nan, np.float32)
        bmax = np.full(3, np.nan, np.float32)
    return bmin, bmax


def _crop_points_to_bbox(pts: np.ndarray, bmin: np.ndarray, bmax: np.ndarray, margin: float = 0.2) -> np.ndarray:
    """Crop to bbox ± margin (meters). If bbox invalid, return pts unchanged."""
    if np.any(np.isnan(bmin)) or np.any(np.isnan(bmax)):
        return pts
    lo = bmin - margin
    hi = bmax + margin
    m = (pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & \
        (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1]) & \
        (pts[:, 2] >= lo[2]) & (pts[:, 2] <= hi[2])
    sub = pts[m]
    return sub if sub.size else pts  # fall back to full frame if crop is empty


def _rotate_xy(points: np.ndarray, deg: float) -> np.ndarray:
    """Rotate XY plane by deg around Z axis."""
    if points.size == 0:
        return points
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    M = np.array([[c, -s], [s, c]], dtype=np.float32)
    xy = points[:, :2] @ M.T
    out = points.copy()
    out[:, 0] = xy[:, 0]
    out[:, 1] = xy[:, 1]
    return out


def save_bbox_footprint_png(
    bbox: Dict[str, Any],
    out_path: str | Path,
    label: Optional[str] = None,
    size: Tuple[int, int] = (300, 180),
) -> str:

    L = float(bbox.get("L", 0.0) or 0.0)
    W = float(bbox.get("W", 0.0) or 0.0)

    W_px, H_px = size
    pad = 12
    _ensure_dir(Path(out_path))

    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (W_px, H_px), "white")
        drw = ImageDraw.Draw(img)

        # frame
        drw.rectangle([0, 0, W_px - 1, H_px - 1], outline=(220, 220, 220))

        # scale rectangle to fit
        avail_w = W_px - 2 * pad
        avail_h = H_px - 2 * pad
        if L > 0 and W > 0:
            sx = avail_w / L
            sy = avail_h / W
            s = min(sx, sy)
            rect_w = max(2, int(L * s))
            rect_h = max(2, int(W * s))
        else:
            rect_w = rect_h = 0

        x0 = (W_px - rect_w) // 2
        y0 = (H_px - rect_h) // 2
        x1 = x0 + rect_w
        y1 = y0 + rect_h

        # bbox rectangle
        if rect_w > 0 and rect_h > 0:
            drw.rectangle([x0, y0, x1, y1], outline=(30, 30, 30), width=3)

        # text (dims + optional label)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        dims = f"{L:.2f} m × {W:.2f} m"
        tx = W_px // 2
        ty = H_px - pad - 12
        tw, th = drw.textsize(dims, font=font)
        drw.text((tx - tw // 2, ty), dims, fill=(90, 90, 90), font=font)

        if label:
            tw2, th2 = drw.textsize(label, font=font)
            drw.text((tx - tw2 // 2, pad // 2), label, fill=(60, 60, 60), font=font)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out_path), format="PNG")
        return str(Path(out_path).resolve())

    except Exception:
        # Minimal fallback
        arr = np.full((H_px, W_px, 3), 255, dtype=np.uint8)
        try:
            from PIL import Image
            Image.fromarray(arr).save(str(out_path), format="PNG")
            return str(Path(out_path).resolve())
        except Exception:
            return str(Path(out_path))



def _project_points(
    pts: np.ndarray,
    mode: str = "oblique",
    rot_deg: float = 30.0,
) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """
    Return 2D projected points Nx2 in [x,y] meters and bounds (xmin,xmax,ymin,ymax).
    - 'top': XY
    - 'side': XZ
    - 'oblique': XY rotated by rot_deg
    """
    if pts.size == 0:
        return np.empty((0, 2), np.float32), (-5.0, 5.0, -3.0, 3.0)  # sane defaults

    if mode == "side":
        P = pts[:, [0, 2]]  # XZ
    else:
        P = pts[:, [0, 1]]  # XY
        if mode == "oblique":
            # rotate in XY for a nicer angle
            theta = math.radians(rot_deg)
            c, s = math.cos(theta), math.sin(theta)
            R = np.array([[c, -s], [s, c]], dtype=np.float32)
            P = P @ R.T

    xmin, ymin = P.min(axis=0)
    xmax, ymax = P.max(axis=0)
    # expand a bit so grid/axes are not glued to the border
    mx = max(1e-3, (xmax - xmin) * 0.05)
    my = max(1e-3, (ymax - ymin) * 0.05)
    return P, (float(xmin - mx), float(xmax + mx), float(ymin - my), float(ymax + my))


def _draw_points_to_png(
    P_world: np.ndarray,
    bounds: Tuple[float, float, float, float],
    out_path: str | Path,
    size: Tuple[int, int] = (720, 540),
    title: Optional[str] = None,
    axis_labels: Tuple[str, str] = ("X (m)", "Y (m)"),
    grid_step: float = 1.0,
    show_axes: bool = True,
    bbox_rect_world: Optional[Tuple[float, float, float, float]] = None,  # xmin,xmax,ymin,ymax in world
    note: Optional[str] = None,
) -> str:
    """
    Draw projected points to a PNG with axes and a metric grid.
    Uses Pillow; falls back to Matplotlib if Pillow is unavailable.
    """
    W_px, H_px = size
    pad = 36  # larger pad to fit labels
    _ensure_dir(Path(out_path))

    xmin, xmax, ymin, ymax = bounds
    if xmax <= xmin:
        xmax = xmin + 1.0
    if ymax <= ymin:
        ymax = ymin + 1.0

    # World -> pixel mapping
    sx = (W_px - 2 * pad) / (xmax - xmin)
    sy = (H_px - 2 * pad) / (ymax - ymin)
    s = min(sx, sy)
    cx = (xmin + xmax) * 0.5
    cy = (ymin + ymax) * 0.5

    def world_to_px(pt: Tuple[float, float]) -> Tuple[int, int]:
        x = (pt[0] - cx) * s + W_px / 2
        y = (pt[1] - cy) * s + H_px / 2
        y = H_px - y  # flip for image coords
        return int(round(x)), int(round(y))

    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (W_px, H_px), "white")
        drw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        # Grid Box
        if show_axes and grid_step > 0:
            gx0 = math.floor(xmin / grid_step) * grid_step
            gx1 = math.ceil(xmax / grid_step) * grid_step
            gy0 = math.floor(ymin / grid_step) * grid_step
            gy1 = math.ceil(ymax / grid_step) * grid_step

            # vertical grid lines (x = const)
            x_val = gx0
            while x_val <= gx1 + 1e-6:
                x0, y0 = world_to_px((x_val, ymin))
                x1_, y1_ = world_to_px((x_val, ymax))
                color = (230, 230, 230) if abs(x_val) > 1e-9 else (160, 160, 160)  # darker for x=0
                drw.line([(x0, y0), (x1_, y1_)], fill=color, width=1)
                # label some grid lines
                if abs(x_val) > 1e-9:
                    txt = f"{x_val:.0f}"
                    tw, th = drw.textsize(txt, font=font)
                    drw.text((x0 - tw // 2, H_px - pad + 4), txt, fill=(120, 120, 120), font=font)
                x_val += grid_step

            # horizontal grid lines (y = const)
            y_val = gy0
            while y_val <= gy1 + 1e-6:
                x0, y0 = world_to_px((xmin, y_val))
                x1_, y1_ = world_to_px((xmax, y_val))
                color = (230, 230, 230) if abs(y_val) > 1e-9 else (160, 160, 160)  # darker for y=0
                drw.line([(x0, y0), (x1_, y1_)], fill=color, width=1)
                # label some grid lines (left side)
                if abs(y_val) > 1e-9:
                    txt = f"{y_val:.0f}"
                    tw, th = drw.textsize(txt, font=font)
                    drw.text((pad - tw - 4, y0 - th // 2), txt, fill=(120, 120, 120), font=font)
                y_val += grid_step

        #  POINTS 
        if P_world.size:
            # Map to pixels
            X = (P_world[:, 0] - cx) * s + W_px / 2
            Y = (P_world[:, 1] - cy) * s + H_px / 2
            Y = H_px - Y
            sz = 1
            g = 40  # dark gray points
            for x, y in zip(X.astype(int), Y.astype(int)):
                if 0 <= x < W_px and 0 <= y < H_px:
                    drw.rectangle([x - sz, y - sz, x + sz, y + sz], outline=(g, g, g), fill=(g, g, g))
        else:
            txt = "No points (showing axes)"
            tw, th = drw.textsize(txt, font=font)
            drw.text(((W_px - tw) // 2, (H_px - th) // 2), txt, fill=(100, 100, 100), font=font)

        if bbox_rect_world is not None:
            x0w, x1w, y0w, y1w = bbox_rect_world
            p0 = world_to_px((x0w, y0w))
            p1 = world_to_px((x1w, y1w))
            x0, y0 = min(p0[0], p1[0]), min(p0[1], p1[1])
            x1, y1 = max(p0[0], p1[0]), max(p0[1], p1[1])
            drw.rectangle([x0, y0, x1, y1], outline=(30, 30, 30), width=2)

        # --- title / labels ---
        if title:
            tw, th = drw.textsize(title, font=font)
            drw.text(((W_px - tw) // 2, 6), title, fill=(60, 60, 60), font=font)

        if show_axes:
            # axis labels
            lx = axis_labels[0]
            ly = axis_labels[1]
            tw, th = drw.textsize(lx, font=font)
            drw.text(((W_px - tw) // 2, H_px - th - 6), lx, fill=(60, 60, 60), font=font)
            tw, th = drw.textsize(ly, font=font)
            drw.text((6, (H_px - th) // 2), ly, fill=(60, 60, 60), font=font)

        if note:
            tw, th = drw.textsize(note, font=font)
            drw.text((pad, H_px - pad - th - 4), note, fill=(120, 80, 80), font=font)

        img.save(str(out_path), format="PNG")
        return str(Path(out_path).resolve())

    except Exception:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=(W_px / 100.0, H_px / 100.0), dpi=100)
            ax = fig.add_subplot(111)
            ax.set_facecolor("white")
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)
            ax.grid(True, which="both")
            ax.set_xlabel(axis_labels[0])
            ax.set_ylabel(axis_labels[1])
            if P_world.size:
                ax.scatter(P_world[:, 0], P_world[:, 1], s=1)
            if bbox_rect_world is not None:
                x0w, x1w, y0w, y1w = bbox_rect_world
                ax.add_patch(plt.Rectangle((x0w, y0w), x1w - x0w, y1w - y0w, fill=False, linewidth=1.5))
            if title:
                ax.set_title(title)
            if note:
                ax.text(0.01, 0.01, note, transform=ax.transAxes, fontsize=7, color="tab:red")
            fig.tight_layout(pad=0.5)
            fig.savefig(str(out_path), dpi=100, bbox_inches="tight", pad_inches=0.0)
            plt.close(fig)
            return str(Path(out_path).resolve())
        except Exception:
            arr = np.full((H_px, W_px, 3), 255, dtype=np.uint8)
            try:
                from PIL import Image
                Image.fromarray(arr).save(str(out_path), format="PNG")
                return str(Path(out_path).resolve())
            except Exception:
                return str(Path(out_path))


def render_track_image(
    pts: np.ndarray,
    best: Dict[str, Any],
    out_path: str | Path,
    cam: str = "oblique", #oblique is top left and side
    zoom: float = 1.8,
    size: Tuple[int, int] = (720, 540),
    grid_step: float = 1.0,
    show_axes: bool = True,
) -> str:
    """
    CPU 2D renderer for a single vehicle's points with axes & grid.
    - Crops to the bbox ± margin (but falls back to full frame if empty)
    - Projects to 2D (top/side/oblique)
    - Draws points + metric grid + axis labels; overlays bbox
    """
    pts = _to_np_f32(pts)
    bmin, bmax = _bbox_minmax_from_best(best)
    sub = _crop_points_to_bbox(pts, bmin, bmax, margin=0.25 * zoom)
    used_fallback = (sub.size == 0 and pts.size > 0)
    if sub.size == 0 and pts.size > 0:
        sub = pts 

    mode = cam if cam in ("top", "side", "oblique") else "oblique"
    P, bounds = _project_points(sub, mode=mode, rot_deg=30.0)

    # Define bbox rect in projected world coordinates for overlay
    if mode == "side":
        bbox_world = (float(bmin[0]), float(bmax[0]), float(bmin[2]), float(bmax[2]))
        axis_labels = ("X (m)", "Z (m)")
    else:
        # rotate bbox corners in XY if oblique (approximate)
        if np.all(np.isfinite(bmin)) and np.all(np.isfinite(bmax)):
            x0, x1 = float(bmin[0]), float(bmax[0])
            y0, y1 = float(bmin[1]), float(bmax[1])
        else:
            x0 = y0 = -1.0
            x1 = y1 = 1.0
        bbox_world = (x0, x1, y0, y1)
        axis_labels = ("X (m)", "Y (m)")

    title = f"Track {best.get('track_id','')}  •  {mode.upper()}"
    note = "No points in bbox (showing full frame)" if used_fallback else None

    return _draw_points_to_png(
        P_world=P,
        bounds=bounds,
        out_path=out_path,
        size=size,
        title=title,
        axis_labels=axis_labels,
        grid_step=grid_step,
        show_axes=show_axes,
        bbox_rect_world=bbox_world,
        note=note,
    )

#3d render that uses CPU for WSL
def _try_import_open3d():
    try:
        import open3d as o3d  # type: ignore
        return o3d
    except Exception:
        return None


def _render_open3d_pointcloud(
    pts: np.ndarray,
    out_path: str | Path,
    zoom: float = 1.8,
    cam_elev_deg: float = 25.0,
    cam_azim_deg: float = 35.0,
    size: Tuple[int, int] = (720, 540),
) -> str:
    o3d = _try_import_open3d()
    if o3d is None:
        raise RuntimeError("Open3D not available")

    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts.astype(np.float64)))
    if len(pcd.points) == 0:
        arr = np.full((size[1], size[0], 3), 255, dtype=np.uint8)
        try:
            from PIL import Image
            Image.fromarray(arr).save(str(out_path), format="PNG")
            return str(Path(out_path).resolve())
        except Exception:
            raise

    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultUnlit"
    mat.point_size = 1.5

    w, h = size
    renderer = o3d.visualization.rendering.OffscreenRenderer(w, h)
    scene = renderer.scene
    scene.set_background(np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32))
    scene.scene.set_sun_light([0.577, -0.577, -0.577], [1.0, 1.0, 1.0], 75000)
    scene.scene.enable_sun_light(True)

    scene.add_geometry("pcd", pcd, mat)

    aabb = scene.bounding_box
    center = aabb.get_center()
    extent = aabb.get_max_bound() - aabb.get_min_bound()
    radius = float(np.linalg.norm(extent)) * (0.8 / max(zoom, 0.1))

    elev = math.radians(cam_elev_deg)
    azim = math.radians(cam_azim_deg)
    eye = [
        center[0] + radius * math.cos(elev) * math.cos(azim),
        center[1] + radius * math.cos(elev) * math.sin(azim),
        center[2] + radius * math.sin(elev),
    ]
    up = [0.0, 0.0, 1.0]

    renderer.scene.camera.look_at(center, eye, up)
    img = renderer.render_to_image()
    o3d.io.write_image(str(out_path), img, quality=100)
    return str(Path(out_path).resolve())


def render_track_image_3d(
    pts: np.ndarray,
    best: Dict[str, Any],
    out_path: str | Path,
    zoom: float = 1.8,
    cam_elev_deg: float = 25.0,
    cam_azim_deg: float = 35.0,
    size: Tuple[int, int] = (720, 540),
    turntable_gif: Optional[str] = None,
) -> str:
    """
    Preferred renderer: 3D with Open3D off-screen (EGL or OSMesa).
    Falls back to CPU 2D with axes if Open3D is unavailable or fails.
    """
    pts = _to_np_f32(pts)
    bmin, bmax = _bbox_minmax_from_best(best)
    sub = _crop_points_to_bbox(pts, bmin, bmax, margin=0.25 * zoom)

    try:
        result_path = _render_open3d_pointcloud(sub, out_path, zoom=zoom,
                                                cam_elev_deg=cam_elev_deg, cam_azim_deg=cam_azim_deg, size=size)
    except Exception:
        # CPU 2D rendering (with axes) GPU windows
        result_path = render_track_image(sub, best, out_path, cam="oblique", zoom=zoom, size=size)
    return result_path

