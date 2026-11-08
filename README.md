# CarlinkO — Vehicle Location mod

This repo contains a patched build of **CarlinkO 1.14.10** (versionCode 180)
that unlocks the built-in **"Vehicle Location"** screen — the map page that
shows your car's position, its address, a **Navigate car** button and
**Geofence** support — the same thing the GAC app does.

## How the locate feature actually works

A quick but important point, because it changes what this mod can and can't do.

The GAC app does **not** use your phone's GPS to find the car. GAC shows the
car on a map because the car has a built-in telematics box (T-Box) that sends
its own GPS position to the manufacturer's cloud. The app just signs in to your
account and asks the server "where is my car?".

**CarlinkO already has this exact capability built in.** Decompiling the app
shows a complete Google-Maps page (`carlinko/ui/google_map/...`) that calls the
CarlinkO backend endpoint `/maps/deviceLocate` to fetch the position reported by
the CarlinkO terminal in your car, then draws the marker, reverse-geocodes the
address, and offers navigation and geofences. The relevant UI strings are
already in the APK (`vehicleLocation`, `googleNavigateToCar`, `googleTabGeofence`,
`mapLoadingError = "Failed to get vehicle location"`, etc.).

The screen is simply **hidden behind a server flag**. When the backend returns
the vehicle-control config, it includes a boolean `mapNavigation`. The home
screen shows the live map card only when `mapNavigation == true`; otherwise it
draws a placeholder image (`google_map_emtpy.png`) and the map tab is disabled.
For this account/vehicle the server is sending `mapNavigation = false`, so the
feature never appears.

## What the patch does

Rather than bolt on a second, inferior "remember where I parked" feature, this
mod **turns on the real thing** by forcing `mapNavigation` to `true`.

The app is built with Flutter, so the logic lives in compiled Dart inside
`lib/arm64-v8a/libapp.so` (not in Java/smali). The patch changes a single
instruction inside `VehicleControlConfigBean.fromJson`, where the parsed JSON
value for `mapNavigation` is stored into the object:

```
file: lib/arm64-v8a/libapp.so   (CarlinkO 1.14.10, versionCode 180)
offset 0xBB4EF0
  before:  F8 50 03 A1   ldur x1, [fp, #-0x100]   ; x1 = json["mapNavigation"]
  after:   C1 82 00 91   add  x1, NULL, #0x20     ; x1 = Dart `true`
```

After this, every `VehicleControlConfigBean` parsed from the server reports
`mapNavigation = true`, so the home screen renders the live **Vehicle Location**
map card and the map tab, which then pull the car's real position from
`/maps/deviceLocate`.

See [`patch/patch_carlinko.py`](patch/patch_carlinko.py) for the exact,
reproducible patch.

### Important limitation

This unlocks the UI and wires it to the backend the app already talks to. The
map will show the car **only if the CarlinkO terminal in your vehicle actually
reports a GPS position to the CarlinkO server** (i.e. the hardware has a GPS/GNSS
module and an active data SIM, and your plan includes location). If the terminal
never uploads a position, `/maps/deviceLocate` has nothing to return and the page
will show *"Failed to get vehicle location."* That is a hardware/account matter,
not something an APK patch can create. If the GAC app can locate the car but
CarlinkO can't even after this patch, the two apps are talking to different
telematics boxes/clouds, and only the GAC-side one has the GPS feed.

## Install

The patch is in a **split APK** (`arm64_v8a`), so you must install the base APK
and all splits **together, signed with the same key**. All APKs in
[`dist/`](dist/) are already re-signed with one key.

- **Phone:** use *SAI (Split APKs Installer)* or *APKMirror Installer* →
  "install multiple / split APKs" → select all 6 files in `dist/`.
- **ADB:**
  ```
  adb install-multiple dist/base.apk dist/split_config.arm64_v8a.apk \
      dist/split_config.en.apk dist/split_config.in.apk \
      dist/split_config.ms.apk dist/split_config.xxhdpi.apk
  ```

Because the signing key differs from the Play Store one, **uninstall the
original CarlinkO first** (back up / note your login). This build is `arm64-v8a`
only — fine for essentially all modern phones.

## Rebuild it yourself

```
python3 patch/patch_carlinko.py <original split_config.arm64_v8a.apk> out.apk
# then re-sign base + every split with ONE key, e.g. uber-apk-signer:
java -jar uber-apk-signer.jar -a <folder-with-all-apks> --allowResign
```

A GitHub Actions workflow ([`.github/workflows/build.yml`](.github/workflows/build.yml))
does the patch-and-sign automatically when you upload the six original APKs.

## Legitimacy / safety notes

- This only flips a feature flag the vendor already ships in the app; it adds no
  new network endpoints and sends your data nowhere new.
- It's an unofficial, self-signed build. Use at your own risk; it may break on
  app updates or if the vendor adds signature checks.
- Re-signed with a self-generated debug-style key (`CN=CarlinkO Mod`). Anyone
  rebuilding should generate their own key.
