import argparse
from .pipeline import run_scan
from .nethealth import netcheck, write_health_report  # if you added netcheck

def main():
    parser = argparse.ArgumentParser(prog="axlescan", description="PCAP scan → axle counts + screenshots")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- scan ---
    p = sub.add_parser("scan", help="Run one-pass scan on a PCAP")
    p.add_argument("--pcap", required=True)
    p.add_argument("--meta", required=False, default=None)
    p.add_argument("--out", required=True)

    # detection / tracking
    p.add_argument("--slice", nargs=2, type=float, default=[0.05, 0.40], metavar=("MIN","MAX"))
    p.add_argument("--eps-vehicle", type=float, default=0.25)
    p.add_argument("--eps-wheel",   type=float, default=0.15)
    p.add_argument("--pair-dx",     type=float, default=0.35)
    p.add_argument("--min-track-s", type=float, default=1.0)

    # reporting / images
    p.add_argument("--export-images", action="store_true")
    p.add_argument("--image-cam", choices=["oblique","top","side"], default="oblique")
    p.add_argument("--no-html", action="store_true")

    # performance
    p.add_argument("--frames", type=int, default=None, help="Process at most N frames")
    p.add_argument("--downsample", type=float, default=0.10, help="Voxel size [m] prefilter (0 disables)")

    # image controls (define each ONCE)
    p.add_argument("--image-mode", choices=["2d","3d"], default="2d",
                   help="2d (matplotlib) or 3d (Open3D) thumbnails")
    p.add_argument("--image-zoom", type=float, default=1.8,
                   help="Zoom for screenshots (1.0 fits bbox; higher = tighter)")
    p.add_argument("--image-stack", type=int, default=0,
                   help="Stack +/-N frames around best for images (0=off)")
    p.add_argument("--turntable", action="store_true",
                   help="Also write a small rotating GIF (3D only)")

    # --- netcheck (optional) ---
    h = sub.add_parser("netcheck", help="Network health preflight for a PCAP")
    h.add_argument("--pcap", required=True)
    h.add_argument("--out",  required=True)

    args = parser.parse_args()

    if args.cmd == "scan":
        run_scan(args)
    elif args.cmd == "netcheck":
        res = netcheck(args.pcap)
        write_health_report(args.out, args.pcap, res)
        print(f"[netcheck] ok={res['ok']} encap={res['capinfos'].get('Encapsulation')} "
              f"lidar/imu={res['packets']['lidar_7502']}/{res['packets']['imu_7503']} "
              f"badcsum={res['udp_checksum_bad']['lidar']}/{res['udp_checksum_bad']['imu']}")
        print(f"[netcheck] wrote: {args.out}/network_health.(json|md)")
