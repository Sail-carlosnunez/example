# axlescan/geometry.py
import numpy as np

def voxel_downsample(points, voxel_m=0.10):
    if voxel_m <= 0: 
        return points
    # bucketize coords
    q = np.floor(points / voxel_m).astype(np.int32)
    # unique voxel keys
    keys, idx = np.unique(q.view([('', q.dtype)]*3), return_index=True)
    return points[idx]

def fit_ground_plane(points, max_iter=400, thresh=0.02, sample_n=60000, early_stop_inlier_frac=0.65):
    N = points.shape[0]
    if N < 100:
        n = np.array([0.0, 0.0, 1.0]); d = -np.median(points[:,2]); return n, d
    # subsample for speed
    if N > sample_n:
        rng = np.random.default_rng(12345)
        P = points[rng.choice(N, size=sample_n, replace=False)]
    else:
        P = points
    best_inliers = 0
    best_n = np.array([0.0,0.0,1.0]); best_d = 0.0
    rng = np.random.default_rng(12345)
    target = int(early_stop_inlier_frac * len(P))
    for _ in range(max_iter):
        i = rng.choice(len(P), size=3, replace=False)
        p1,p2,p3 = P[i]
        n = np.cross(p2-p1, p3-p1)
        norm = np.linalg.norm(n)
        if norm < 1e-6: continue
        n /= norm
        d = -np.dot(n, p1)
        dist = np.abs(P @ n + d)
        inliers = int((dist < thresh).sum())
        if inliers > best_inliers:
            best_inliers, best_n, best_d = inliers, n, d
            if best_inliers >= target: break
    if best_n[2] < 0:
        best_n, best_d = -best_n, -best_d
    return best_n, best_d
