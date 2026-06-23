# axlescan/track.py
import numpy as np
from datetime import datetime, timezone

class TrackManager:
    def __init__(self):
        self.tracks = {}
        self.next_id = 1

    def _bbox_iou(self, a, b):
        a_min = np.array(a["min"]); a_max = np.array(a["max"])
        b_min = np.array(b["min"]); b_max = np.array(b["max"])
        inter_min = np.maximum(a_min, b_min)
        inter_max = np.minimum(a_max, b_max)
        inter = np.maximum(0.0, inter_max - inter_min)
        inter_vol = inter[0] * inter[1] * inter[2]
        vol_a = np.prod(a_max - a_min)
        vol_b = np.prod(b_max - b_min)
        union = vol_a + vol_b - inter_vol + 1e-9
        return float(inter_vol / union)

    def update(self, t_ns, detections):
        # Assign detections to existing tracks by bbox IoU
        for det in detections:
            best_id, best_iou = None, 0.0
            for tid, tr in self.tracks.items():
                iou = self._bbox_iou(det["bbox"], tr["bbox"])
                if iou > best_iou:
                    best_iou, best_id = iou, tid
            if best_id is not None and best_iou > 0.05:
                tr = self.tracks[best_id]
                tr["frames"].append({"t_ns": t_ns, **det})
                tr["bbox"] = det["bbox"]
            else:
                tid = self.next_id; self.next_id += 1
                self.tracks[tid] = {
                    "track_id": tid,
                    "frames": [{"t_ns": t_ns, **det}],
                    "bbox": det["bbox"],
                }

    def finalize(self, min_duration_s=1.0):
        out = []
        for tid, tr in self.tracks.items():
            frames = tr["frames"]
            if not frames:
                continue
            t0 = frames[0]["t_ns"]; t1 = frames[-1]["t_ns"]
            duration_s = (t1 - t0) / 1e9
            if duration_s < min_duration_s:
                continue

            counts = [f["axle_count"] for f in frames]
            vals, freqs = np.unique(counts, return_counts=True)
            modal = int(vals[np.argmax(freqs)]) if len(vals) else 0
            conf = float(np.max(freqs) / len(frames)) if len(frames) else 0.0

            mins = np.min([f["bbox"]["min"] for f in frames], axis=0)
            maxs = np.max([f["bbox"]["max"] for f in frames], axis=0)
            dims = maxs - mins
            L, W, H = dims.tolist()

            centers = np.array([f["veh_center"] for f in frames])
            rng = float(np.median(np.linalg.norm(centers, axis=1))) if centers.size else float("nan")

            frames_sorted = sorted(frames, key=lambda f: (-f["confidence"], -len(f["wheels"])))
            best = frames_sorted[0]

            out.append({
                "track_id": tid,
                "t_start_ns": int(t0),
                "t_end_ns": int(t1),
                "t_start_iso": datetime.fromtimestamp(t0/1e9, tz=timezone.utc).isoformat(),
                "t_end_iso": datetime.fromtimestamp(t1/1e9, tz=timezone.utc).isoformat(),
                "duration_s": float(duration_s),
                "axle_count_mode": modal,
                "axle_confidence": conf,
                "bbox": {"L": float(L), "W": float(W), "H": float(H)},
                "range_m_med": rng,
                "best_ts": int(best["t_ns"]),
                "best_ts_iso": datetime.fromtimestamp(best["t_ns"]/1e9, tz=timezone.utc).isoformat(),
            })
        out.sort(key=lambda r: r["t_start_ns"])
        return out

    def pick_best_frame(self, track_row):
        tid = track_row["track_id"]
        frames = self.tracks.get(tid, {}).get("frames", [])
        if not frames:
            return None
        frames_sorted = sorted(frames, key=lambda f: (-f["confidence"], -len(f["wheels"])))
        return frames_sorted[0]
