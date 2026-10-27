"""Bluetooth plan builder for SigmaOS-bluetooth / bluetooth-tool
(inspired by cinnamon-bluetooth, blueberry, blueferry).

Principles: plan-before-act -- scanning, pairing and connecting are computed
as pure, deterministic plans over a parsed device list; the bluetoothctl/D-Bus
execution layer stays a thin shell the self-test never runs. Defensive MAC
validation, fail-fast on unknown devices.
"""
import argparse, re, sys

ENGINE = {
    "name": "sigma-bluetooth",
    "summary": "Plan bluetooth scan, pairing and connection flows",
    "language": "python",
    "verbs": ["scan-plan", "devices", "pair-plan", "connect-plan"],
    "principles": ["Plan Before Act", "Separation of Concerns",
                   "Defensive Programming", "Fail-Fast", "KISS", "DRY"],
}

cli_doc = """\
$ sigma-bluetooth scan-plan scan.txt --adapter hci0
adapter hci0: 3 device(s)
  select hci0
  scan on
$ sigma-bluetooth devices scan.txt
4C:87:5D:1A:2B:3C  Sony WH-1000XM4  rssi=-62
$ sigma-bluetooth pair-plan scan.txt 4C:87:5D:1A:2B:3C --pin 1234
$ sigma-bluetooth connect-plan scan.txt 4C:87:5D:1A:2B:3C --paired 4C:87:5D:1A:2B:3C
"""

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_RSSI_RE = re.compile(r"^rssi=-?\d+$", re.I)
_ADAPTER_RE = re.compile(r"^hci\d+$")
_PIN_RE = re.compile(r"^\d{4,6}$")


class BluetoothError(ValueError):
    pass


def _read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def parse_scan(text):
    """Parse `Device MAC name [rssi=-NN]` lines into ordered device dicts."""
    devices = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3 or parts[0].lower() != "device":
            raise BluetoothError(
                f"line {lineno}: expected 'Device MAC name', got {line!r}")
        _, mac, rest = parts
        if not _MAC_RE.match(mac):
            raise BluetoothError(f"line {lineno}: bad MAC address {mac!r}")
        rssi, keep = None, []
        for tok in rest.split():
            if _RSSI_RE.match(tok):
                rssi = int(tok.split("=", 1)[1])
            else:
                keep.append(tok)
        name = " ".join(keep)
        if not name:
            raise BluetoothError(f"line {lineno}: device {mac} has empty name")
        devices.append({"mac": mac.upper(), "name": name, "rssi": rssi})
    if not devices:
        raise BluetoothError("scan contained no devices")
    return devices


def _find(devices, address):
    addr = address.strip().upper()
    if not _MAC_RE.match(addr):
        raise BluetoothError(f"bad MAC address: {address!r}")
    for d in devices:
        if d["mac"] == addr:
            return d
    raise BluetoothError(f"device not in scan: {addr}")


def scan_plan(text, adapter="hci0"):
    """Pure plan for an adapter scan (never touches the adapter itself)."""
    if not _ADAPTER_RE.match(adapter):
        raise BluetoothError(f"bad adapter name: {adapter!r}")
    devices = parse_scan(text)
    return {
        "adapter": adapter,
        "found": len(devices),
        "steps": [f"select {adapter}", "scan on", "scan off", "devices"],
    }


def pair_plan(text, address, pin=None, trust=True):
    """Pure pairing plan for a device found in the scan."""
    device = _find(parse_scan(text), address)
    if pin is not None and not _PIN_RE.match(pin):
        raise BluetoothError(f"PIN must be 4-6 digits, got {pin!r}")
    steps = ["agent NoInputNoOutput", "default-agent",
             f"pair {device['mac']}"]
    if pin is not None:
        steps.append(f"pin {pin}")
    if trust:
        steps.append(f"trust {device['mac']}")
    steps.append("menu")
    return {"device": device, "pin": pin, "trust": trust, "steps": steps}


def connect_plan(text, address, paired):
    """Pure connect plan; refuses devices that were never paired (fail-fast)."""
    device = _find(parse_scan(text), address)
    known = {p.strip().upper() for p in paired}
    if device["mac"] not in known:
        raise BluetoothError(
            f"{device['mac']} is not paired; run pair-plan first")
    return {
        "device": device,
        "steps": [f"connect {device['mac']}", f"info {device['mac']}"],
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"],
                                description=ENGINE["summary"])
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("scan-plan", help="plan an adapter scan")
    sp.add_argument("scan", help="simulated scan file ('-' for stdin)")
    sp.add_argument("--adapter", default="hci0")
    dv = sub.add_parser("devices", help="list parsed scan results")
    dv.add_argument("scan")
    pp = sub.add_parser("pair-plan", help="plan pairing with a device")
    pp.add_argument("scan")
    pp.add_argument("address")
    pp.add_argument("--pin", default=None)
    pp.add_argument("--no-trust", action="store_true")
    cp = sub.add_parser("connect-plan", help="plan connecting to a paired device")
    cp.add_argument("scan")
    cp.add_argument("address")
    cp.add_argument("--paired", nargs="+", default=[],
                    help="known paired addresses")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = _read(args.scan)
        if args.cmd == "scan-plan":
            plan = scan_plan(text, adapter=args.adapter)
            print(f"adapter {plan['adapter']}: {plan['found']} device(s)")
            for step in plan["steps"]:
                print(f"  {step}")
        elif args.cmd == "devices":
            for d in parse_scan(text):
                rssi = "?" if d["rssi"] is None else str(d["rssi"])
                print(f"{d['mac']}  {d['name']}  rssi={rssi}")
        elif args.cmd == "pair-plan":
            plan = pair_plan(text, args.address, pin=args.pin,
                             trust=not args.no_trust)
            dev = plan["device"]
            print(f"pairing {dev['mac']} ({dev['name']})")
            for step in plan["steps"]:
                print(f"  {step}")
        elif args.cmd == "connect-plan":
            plan = connect_plan(text, args.address, paired=args.paired)
            dev = plan["device"]
            print(f"connecting {dev['mac']} ({dev['name']})")
            for step in plan["steps"]:
                print(f"  {step}")
        return 0
    except BluetoothError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    sample = """\
# simulated hcitool/bluetoothctl scan
Device 4C:87:5D:1A:2B:3C Sony WH-1000XM4 rssi=-62
Device AA:BB:CC:DD:EE:FF Logitech MX Master 3
Device 11:22:33:44:55:66 Sugar Skull Keyboard
"""
    devs = parse_scan(sample)
    assert len(devs) == 3
    assert devs[0]["mac"] == "4C:87:5D:1A:2B:3C"
    assert devs[0]["rssi"] == -62 and devs[1]["rssi"] is None
    assert devs[2]["name"] == "Sugar Skull Keyboard"

    plan = scan_plan(sample, adapter="hci1")
    assert plan["found"] == 3 and plan["steps"][0] == "select hci1"

    pair = pair_plan(sample, "4c:87:5d:1a:2b:3c", pin="1234")
    assert pair["steps"][2] == "pair 4C:87:5D:1A:2B:3C"
    assert "pin 1234" in pair["steps"]
    assert pair["steps"][-2] == "trust 4C:87:5D:1A:2B:3C"
    assert pair_plan(sample, "AA:BB:CC:DD:EE:FF", trust=False)["steps"] \
        .count("trust AA:BB:CC:DD:EE:FF") == 0

    conn = connect_plan(sample, "AA:BB:CC:DD:EE:FF",
                        paired=["aa:bb:cc:dd:ee:ff"])
    assert conn["steps"][0] == "connect AA:BB:CC:DD:EE:FF"

    for bad in (
        lambda: parse_scan("Device not-a-mac Foo Bar"),
        lambda: parse_scan("# only a comment\n"),
        lambda: parse_scan("Device 00:11:22:33:44:55"),
        lambda: pair_plan(sample, "AA:BB:CC:DD:EE:FF", pin="12a4"),
        lambda: pair_plan(sample, "00:00:00:00:00:00"),
        lambda: pair_plan(sample, "nonsense"),
        lambda: connect_plan(sample, "AA:BB:CC:DD:EE:FF", paired=[]),
        lambda: scan_plan(sample, adapter="usb0"),
    ):
        try:
            bad()
        except BluetoothError:
            pass
        else:
            raise AssertionError("expected BluetoothError")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
