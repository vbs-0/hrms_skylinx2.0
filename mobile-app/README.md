# Skylinx HRMS — Flutter mobile app

A **WebView shell**: it loads your existing HRMS web app inside a native Flutter
container and exposes native device features (biometric, location, camera) to
the web pages through a JS↔Dart bridge. You keep every web feature; native code
is only the thin shell + device APIs.

---

## ⚙️ Where to set the server (the one thing you asked for)

Edit **`lib/config/app_config.dart`** → `_defaultServerUrl`:

```dart
static const String _defaultServerUrl = 'https://skylinxhrms.qzz.io';
```

Or override at build time without touching source:

```bash
flutter run        --dart-define=SERVER_URL=https://your-domain.com
flutter build apk  --dart-define=SERVER_URL=https://your-domain.com
```

That's the only place the app decides which server to talk to.

---

## One-time setup

Requires the Flutter SDK (https://docs.flutter.dev/get-started/install).

```bash
cd mobile-app

# 1) scaffold the native android/ + ios/ folders (uses this pubspec & lib/)
flutter create --org com.skylinx --project-name skylinx_hrms .

# 2) install dependencies
flutter pub get

# 3) run on a connected device / emulator
flutter run
```

`flutter create .` keeps the existing `lib/` and `pubspec.yaml` and only fills
in the platform boilerplate. Then apply the platform permissions below.

---

## Android permissions

Add inside `android/app/src/main/AndroidManifest.xml`, **above** `<application>`:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.USE_BIOMETRIC"/>
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
```

**Biometric requires** the activity to be a FragmentActivity. In
`android/app/src/main/.../MainActivity.kt` change:

```kotlin
import io.flutter.embedding.android.FlutterFragmentActivity
class MainActivity : FlutterFragmentActivity()   // was FlutterActivity
```

In `android/app/build.gradle` set a modern minSdk (geolocator/local_auth need it):

```gradle
defaultConfig { minSdkVersion 23 }
```

If (and only if) you point at a **plain http://** server, also set
`AppConfig.allowCleartext = true` and add to the `<application>` tag:
`android:usesCleartextTraffic="true"`.

---

## iOS permissions

Add to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>Used for attendance photo / face capture.</string>
<key>NSLocationWhenInUseUsageDescription</key>
<string>Used to verify your location for attendance.</string>
<key>NSFaceIDUsageDescription</key>
<string>Used to unlock the app and confirm actions.</string>
```

If pointing at a plain http:// server, add an App Transport Security exception.

---

## How the web app calls native features (JS bridge)

From any HRMS web page running inside the shell:

```js
// biometric confirm (e.g. before punch-in)
const r = await window.flutter_inappwebview.callHandler('native',
            { action: 'biometric', reason: 'Confirm punch-in' });
if (r.ok) { /* proceed */ }

// get current GPS location for attendance
const loc = await window.flutter_inappwebview.callHandler('native',
            { action: 'location' });
// loc -> { ok: true, lat: 17.38, lng: 78.48 }  (post this to your API)
```

Add more actions in `lib/screens/webview_screen.dart` → `_registerBridge`.

---

## What's included

| File | Purpose |
|---|---|
| `lib/config/app_config.dart` | **server URL** + app flags (one place) |
| `lib/main.dart` | app entry + theme |
| `lib/screens/splash_screen.dart` | splash + optional biometric app-lock |
| `lib/screens/webview_screen.dart` | the shell: WebView, JS bridge, permissions, back-nav, offline |
| `lib/screens/offline_screen.dart` | no-connection page with retry |
| `lib/services/biometric_service.dart` | local_auth wrapper |

## Build a release APK

```bash
flutter build apk --release --dart-define=SERVER_URL=https://your-domain.com
# output: build/app/outputs/flutter-apk/app-release.apk
```

## Not included yet (add when needed)
- **Push notifications** (Firebase Messaging — needs a Firebase project + `google-services.json`).
- **Background geofencing** when the app is closed (`flutter_background_geolocation`, a paid plugin) — current location works on-demand via the bridge.
- App icons / splash image (use `flutter_launcher_icons`).
