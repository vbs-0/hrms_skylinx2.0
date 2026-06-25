# Mobile App Strategy

## Recommendation: WebView shell now → native Flutter later (NOT pure PWA)

The app's three core features — **background geofencing, face attendance,
biometric login** — are exactly what PWAs can't do reliably on iOS. That
decides it.

### Why not pure PWA
- **iOS background geolocation/geofencing: not available.** A PWA gets no
  background location when closed. Attendance geofencing would silently stop
  on iPhones. This alone kills PWA.
- **iOS background sync: unsupported.** No auto-sync when the PWA is closed
  (Android has it; iOS doesn't). Offline punches wouldn't reliably flush.
- **iOS web push: only very recent + requires home-screen install**, more
  limited than native. (Exact iOS version / EU-DMA detail is uncertain —
  treat as "works, but constrained.")
- **Camera/face:** getUserMedia works, but no native face/liveness APIs —
  weaker anti-spoofing than native.
- **App Store Guideline 4.2:** a thin PWA-in-a-wrapper risks rejection. Apple
  wants native capability, not a website in a box.

### The three options

| | PWA only | WebView shell (Flutter + InAppWebView) | Full native Flutter |
|---|---|---|---|
| iOS bg geofencing | ❌ | ✅ (native plugin) | ✅ |
| iOS bg sync/push | ❌ / weak | ✅ | ✅ |
| Face / liveness | weak | ✅ native | ✅ native |
| Biometric login | limited | ✅ | ✅ |
| Reuses existing Django UI | ✅ all | ✅ most | ❌ rebuild screens |
| App Store risk (4.2) | high | low | none |
| Effort | ~1–2 wk | **~3–5 wk** | ~3–6 months |
| Offline | limited | medium | full |

### Why WebView shell wins
`flutter_inappwebview` loads the existing Django pages inside a native Flutter
container. The JS↔Dart bridge
(`window.flutter_inappwebview.callHandler(...)`) lets those web pages call
native device features:
- Native **background geofencing** via `flutter_background_geolocation`
  (mature, iOS + Android) → posts punches to the API.
- Native **biometric** (`local_auth`) gates app open / login.
- Native **camera/face** capture for attendance, passed back to the web flow.
- Native **push** (FCM / APNs).

Keeps ~90% of the existing UI. Native code only for the 3–4 device features.
Ships in weeks, passes 4.2 because it has real native capability.

### Auth (verified)
Django uses session cookies + CSRF. For the shell:
- WebView can ride the **session cookie** for normal page browsing (simplest).
- For **native plugins** posting to the API (geofence punches, etc.), add
  **DRF + `djangorestframework-simplejwt`**: `POST /api/token/` with
  credentials → `{access, refresh}`; plugins send
  `Authorization: Bearer <access>`. Avoids CSRF awkwardness on native calls.
  DRF is already installed.

### Phased plan
1. **Phase 0 (3–5 days):** Add `/api/token/` (simplejwt) + a few DRF
   endpoints: punch-in/out, geofence event, current-shift. Needed regardless
   of mobile path.
2. **Phase 1 (1.5–2 wk):** Flutter shell wrapping the site with
   `flutter_inappwebview`, session login, navigation, push (FCM).
3. **Phase 2 (1.5–2 wk):** Wire native plugins via the JS bridge — background
   geofencing → API, biometric gate, camera/face capture.
4. **Phase 3 (later, optional):** Replace highest-traffic web screens
   (dashboard, attendance) with native Flutter screens for speed, leaving the
   long tail in WebView. Incremental — no big-bang rewrite.

### Team / skills
One Flutter dev comfortable with platform channels + the three plugins. No
Django rewrite. iOS needs a Mac + Apple Developer account ($99/yr) for the
geolocation entitlements and TestFlight.

**Bottom line:** skip PWA, build a Flutter WebView shell with native
geofencing/biometric/camera, add JWT endpoints. Migrate hot screens to native
later if performance demands it.
