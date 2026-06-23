import numpy as np
from sklearn.cluster import DBSCAN

def _pca_extents(pts):
    C = pts.mean(0)
    Q = pts - C
    _, _, Vt = np.linalg.svd(Q, full_matrices=False)
    P = Q @ Vt.T  # rotate into principal axes
    exts = P.max(0) - P.min(0)
    exts = np.sort(exts)[::-1]  # L >= W >= H
    return exts.tolist()

def detect_vehicle_rois(pts_under, eps=0.6, min_samples=15, min_pts=200):
    """Cluster the undercarriage slice and keep clusters with vehicle-like PCA extents."""
    if pts_under.shape[0] == 0:
        return []
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(pts_under)
    rois = []
    for k in np.unique(db.labels_):
        if k == -1:
            continue
        cluster = pts_under[db.labels_ == k]
        if cluster.shape[0] < min_pts:
            continue
        L, W, H = _pca_extents(cluster)
        # Wider tolerances; we'll tighten later if needed
        if 2.0 <= L <= 20.0 and 1.2 <= W <= 3.8 and 0.4 <= H <= 4.0:
            rois.append(cluster)
    return rois

def wheel_candidates_in_roi(vehicle_pts, eps=0.25, min_samples=8):
    """Find compact lateral-edge clusters as wheel candidates (vehicle-frame PCA)."""
    C = vehicle_pts.mean(0)
    Q = vehicle_pts - C
    _, _, Vt = np.linalg.svd(Q, full_matrices=False)
    R = Vt.T
    P = Q @ R

    y = P[:, 1]
    side_thresh = np.percentile(np.abs(y), 70.0)
    side_pts = P[np.abs(y) > side_thresh]
    if side_pts.shape[0] == 0:
        return [], {"R": R, "C": C}

    db = DBSCAN(eps=eps, min_samples=min_samples).fit(side_pts[:, :2])
    wheels = []
    for k in np.unique(db.labels_):
        if k == -1:
            continue
        w = side_pts[db.labels_ == k]
        cov = np.cov(w[:, :2].T)
        evals, _ = np.linalg.eig(cov)
        compact = np.sqrt(float(np.max(evals))) < 0.25
        if compact and len(w) > 15:
            center_xy = w[:, :2].mean(0)
            side_sign = np.sign(center_xy[1])
            wheels.append({"center_xy": center_xy, "side": side_sign, "P": w})
    return wheels, {"R": R, "C": C}

def pair_axles(wheels, dx_tol=0.45):
    left = [w for w in wheels if w["side"] < 0]
    right = [w for w in wheels if w["side"] > 0]
    pairs, used = [], set()
    for wl in left:
        x_l = wl["center_xy"][0]
        best_j, best_dx = -1, 1e9
        for j, wr in enumerate(right):
            if j in used:
                continue
            dx = abs(wr["center_xy"][0] - x_l)
            if dx < best_dx:
                best_dx, best_j = dx, j
        if best_j >= 0 and best_dx < dx_tol:
            pairs.append((wl, right[best_j]))
            used.add(best_j)
    return pairs
