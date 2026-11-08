#!/usr/bin/env python3
"""
CarlinkO 1.14.10 (versionCode 180) - "Vehicle Location" unlock patch.

CarlinkO already contains a full Google Maps "Vehicle Location" page
(car marker, address, "Navigate car", geofences) that reads the position
reported by the CarlinkO terminal through the backend (/maps/deviceLocate).

The page is only shown when the server-side vehicle control config sends
`mapNavigation: true`. This patch forces that flag to `true` inside
VehicleControlConfigBean.fromJson in the compiled Dart code (libapp.so).

Usage:
    python3 patch_carlinko.py <original split_config.arm64_v8a.apk> <output apk>

Then sign base.apk + all split_config.*.apk with the SAME key and install
them together (adb install-multiple, or SAI / APKMirror Installer).
"""
import shutil
import struct
import sys
import zipfile

LIB = "lib/arm64-v8a/libapp.so"

# (file offset, original instruction, patched instruction, description)
PATCHES = [
    (
        0xBB4EF0,
        0xF85003A1,  # ldur x1, [fp, #-0x100]   ; parsed json["mapNavigation"]
        0x910082C1,  # add  x1, x22(NULL), #0x20 ; Dart `true`
        "VehicleControlConfigBean.fromJson: mapNavigation := true",
    ),
]


def patch_lib(data: bytearray) -> bytearray:
    for off, orig, new, desc in PATCHES:
        cur = struct.unpack_from("<I", data, off)[0]
        if cur == new:
            print(f"[=] already patched: {desc}")
            continue
        if cur != orig:
            sys.exit(
                f"[!] unexpected bytes at {off:#x}: {cur:#010x} (expected {orig:#010x}).\n"
                "    This patch only fits CarlinkO 1.14.10 (versionCode 180)."
            )
        struct.pack_into("<I", data, off, new)
        print(f"[+] {desc} @ {off:#x}")
    return data


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    tmp = dst + ".tmp"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            if item.filename.startswith("META-INF/"):
                continue  # drop old signature
            buf = zin.read(item.filename)
            if item.filename == LIB:
                buf = bytes(patch_lib(bytearray(buf)))
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, buf)
    shutil.move(tmp, dst)
    print(f"[✓] written {dst} (unsigned)")


if __name__ == "__main__":
    main()
