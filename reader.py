# axlescan/reader.py
from pathlib import Path
import time
import numpy as np

class FrameReader:
    def __init__(self, pcap_path, meta_path):
        self.pcap_path = str(pcap_path)
        # IMPORTANT: keep None if meta not supplied
        self.meta_path = str(meta_path) if meta_path else None
        self._frame_index = {}

    def frames(self):
        pcap_abs = str(Path(self.pcap_path).resolve())
        meta_abs = str(Path(self.meta_path).resolve()) if self.meta_path else None
        meta_exists = bool(meta_abs and Path(meta_abs).is_file())

        print(f"[dbg] reader starting: pcap={pcap_abs} meta={meta_abs if meta_exists else 'None'}", flush=True)

        # Modern SDK path via open_source
        try:
            from ouster.sdk import open_source, core
        except Exception as e:
            print(f"[dbg] reader: ouster.sdk unavailable ({type(e).__name__}: {e})", flush=True)
            return

        # Build attempts: if meta file exists, pass it; otherwise DO NOT pass meta
        if meta_exists:
            attempts = [
                (pcap_abs,       [meta_abs], False),
                (pcap_abs,       [meta_abs], True),
                ([pcap_abs],     [meta_abs], False),
                ([pcap_abs],     [meta_abs], True),
            ]
        else:
            attempts = [
                (pcap_abs,       None,       False),
                (pcap_abs,       None,       True),
                ([pcap_abs],     None,       False),
                ([pcap_abs],     None,       True),
            ]

        for url, meta, collate in attempts:
            try:
                if meta is None:
                    print(f"[dbg] open_source(url={url!r}, meta=None, collate={collate})", flush=True)
                    src = open_source(url, sensor_idx=0, collate=collate)
                else:
                    print(f"[dbg] open_source(url={url!r}, meta_len={len(meta)}, collate={collate})", flush=True)
                    src = open_source(url, meta=meta, sensor_idx=0, collate=collate)
            except Exception as e:
                print(f"[dbg] open_source failed: {type(e).__name__}: {e}", flush=True)
                continue

            if not getattr(src, "metadata", None):
                print("[dbg] open_source: no metadata present", flush=True)
                # If we didn’t pass meta and none is embedded, this combo won’t work.
                continue

            info = src.metadata[0]
            xyz_lut = core.XYZLut(info)
            fcount = 0

            for scans in src:
                scan = scans[0] if isinstance(scans, (list, tuple)) else scans
                if scan is None:
                    continue
                fcount += 1

                # XYZ (support both call styles)
                try:
                    xyz = xyz_lut(scan)
                except Exception:
                    try:
                        rng = scan.field(core.ChanField.RANGE)
                        xyz = xyz_lut(rng)
                    except Exception as e2:
                        if fcount <= 3:
                            print(f"[dbg] xyz_lut failed: {type(e2).__name__}: {e2}", flush=True)
                        continue

                # RANGE mask if available
                try:
                    rng = scan.field(core.ChanField.RANGE)
                    mask = (rng > 0)
                except Exception:
                    mask = None

                pts = xyz[mask].reshape(-1, 3) if mask is not None else xyz.reshape(-1, 3)

                if fcount <= 3:
                    nz = int(mask.sum()) if mask is not None else pts.shape[0]
                    print(f"[dbg] reader: frame#{fcount} xyz={tuple(xyz.shape)} pts={pts.shape[0]} nonzero={nz}", flush=True)

                # Timestamp
                t_arr = getattr(scan, "timestamp", None)
                t_ns = int(np.max(t_arr)) if t_arr is not None else int(time.time() * 1e9)

                self._frame_index[t_ns] = pts.copy()
                yield {"t_ns": t_ns, "points": pts}

            if fcount > 0:
                print(f"[dbg] open_source succeeded with frames={fcount}", flush=True)
                return

        print("[dbg] open_source exhausted attempts with 0 frames", flush=True)

    def frame_points_by_timestamp(self, t_ns):
        return self._frame_index.get(t_ns)
