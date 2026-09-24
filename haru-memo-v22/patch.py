from pathlib import Path
import sys

root = Path(sys.argv[1])
j = root / 'app/src/main/java/app/harume/memo'
gradle = root / 'app/build.gradle'
manifest = root / 'app/src/main/AndroidManifest.xml'
def change(path, before, after):
    s = path.read_text()
    if before not in s:
        raise RuntimeError('Anchor missing in ' + str(path) + ': ' + before[:70])
    path.write_text(s.replace(before, after))

change(gradle, "applicationId 'app.harume.memo.v21'", "applicationId 'app.harume.memo.v22'")
change(gradle, "versionCode 3", "versionCode 4")
change(gradle, "versionName '2.1'", "versionName '2.2'")
change(manifest, 'android:label="하루메모 2.1"', 'android:label="하루메모 2.2"')
change(manifest, '<uses-permission android:name="android.permission.VIBRATE" />',
       '<uses-permission android:name="android.permission.VIBRATE" />\n    <uses-permission android:name="android.permission.WAKE_LOCK" />')

(j / 'VolumeShortcutBridge.java').write_text(r'''package app.harume.memo;

import android.content.Context;
import android.media.AudioManager;
import android.media.MediaMetadata;
import android.media.VolumeProvider;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.hardware.display.DisplayManager;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;
import android.view.Display;

/** Optional second input route; a media session is NOT guaranteed to get locked-screen keys. */
final class VolumeShortcutBridge {
    private final Context app;
    private final Runnable onLongPress;
    private MediaSession session;
    private VolumeProvider provider;
    private long firstDown, lastDown, lastFire;
    private int consecutive;

    VolumeShortcutBridge(Context app, Runnable onLongPress) {
        this.app = app.getApplicationContext();
        this.onLongPress = onLongPress;
    }

    static boolean screenIsOff(Context c) {
        try {
            DisplayManager m = (DisplayManager)c.getSystemService(Context.DISPLAY_SERVICE);
            Display d = m == null ? null : m.getDisplay(Display.DEFAULT_DISPLAY);
            if (d != null) {
                int state = d.getState();
                return state == Display.STATE_OFF || state == Display.STATE_DOZE
                    || state == Display.STATE_DOZE_SUSPEND;
            }
        } catch (RuntimeException ignored) { }
        PowerManager pm = (PowerManager)c.getSystemService(Context.POWER_SERVICE);
        return pm != null && !pm.isInteractive();
    }

    boolean active() { return session != null; }

    void activate() {
        if (session != null) return;
        try {
            provider = new VolumeProvider(VolumeProvider.VOLUME_CONTROL_RELATIVE, 15, 7) {
                @Override public void onAdjustVolume(int direction) {
                    if (direction == AudioManager.ADJUST_LOWER) volumeLower();
                    else { firstDown = lastDown = 0; consecutive = 0; }
                    setCurrentVolume(7);
                }
            };
            session = new MediaSession(app, "HaruMemo Screen Off Volume Shortcut");
            session.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
            session.setPlaybackToRemote(provider);
            session.setMetadata(new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, "하루메모 · 버튼 녹음 대기")
                .build());
            session.setPlaybackState(new PlaybackState.Builder()
                .setState(PlaybackState.STATE_PLAYING, PlaybackState.PLAYBACK_POSITION_UNKNOWN, 1.0f)
                .setActions(0).build());
            session.setActive(true);
            app.getSharedPreferences("haru_settings", Context.MODE_PRIVATE).edit()
                .putBoolean("media_session_ready", true).remove("last_media_error").apply();
        } catch (RuntimeException ex) {
            Log.w("HaruMemo", "MediaSession route unavailable", ex);
            app.getSharedPreferences("haru_settings", Context.MODE_PRIVATE).edit()
                .putBoolean("media_session_ready", false)
                .putString("last_media_error", ex.getClass().getSimpleName()).apply();
            deactivate();
        }
    }

    private void volumeLower() {
        if (!app.getSharedPreferences("haru_settings", Context.MODE_PRIVATE)
                .getBoolean("volume_shortcut", false)) return;
        boolean off = screenIsOff(app);
        app.getSharedPreferences("haru_settings", Context.MODE_PRIVATE).edit()
            .putLong("last_media_seen", System.currentTimeMillis())
            .putBoolean("last_media_off", off).apply();
        if (!off) { consecutive = 0; return; }
        long now = SystemClock.elapsedRealtime();
        if (now - lastDown > 500 || lastDown == 0) {
            firstDown = now; consecutive = 0;
        }
        lastDown = now;
        consecutive++;
        // Remote volume callbacks have no key-up. Require a series of repeats,
        // not a single tap. Some devices never emit repeats; report that honestly.
        if (consecutive >= 3 && now - firstDown >= 380 && now - lastFire > 1700) {
            lastFire = now; firstDown = 0; lastDown = 0; consecutive = 0;
            onLongPress.run();
        }
    }

    void deactivate() {
        if (session != null) {
            try { session.setActive(false); session.release(); }
            catch (RuntimeException ignored) { }
        }
        session = null; provider = null;
        app.getSharedPreferences("haru_settings", Context.MODE_PRIVATE).edit()
            .putBoolean("media_session_ready", false).apply();
    }
}
''')

(j / 'RecordingAccessibilityService.java').write_text(r'''package app.harume.memo;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityEvent;

/** Key filter only; no screen contents are read. */
public final class RecordingAccessibilityService extends AccessibilityService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean down, fired;
    private long startAt;
    private Runnable timer;
    private PowerManager.WakeLock keyWake;

    @Override protected void onServiceConnected() {
        super.onServiceConnected();
        AccessibilityServiceInfo i = getServiceInfo();
        if (i != null) {
            i.flags |= AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS;
            setServiceInfo(i);
        }
        getSharedPreferences("haru_settings", MODE_PRIVATE).edit()
            .putLong("last_accessibility_connected", System.currentTimeMillis()).apply();
    }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }
    @Override public void onInterrupt() { }

    @Override protected boolean onKeyEvent(KeyEvent e) {
        if (e.getKeyCode() != KeyEvent.KEYCODE_VOLUME_DOWN) return false;
        SharedPreferences p = getSharedPreferences("haru_settings", MODE_PRIVATE);
        if (!p.getBoolean("volume_shortcut", false)) return false;
        boolean off = VolumeShortcutBridge.screenIsOff(this);
        if (e.getAction() == KeyEvent.ACTION_DOWN && e.getRepeatCount() == 0) {
            p.edit().putLong("last_a11y_seen", System.currentTimeMillis())
                .putBoolean("last_a11y_off", off).apply();
        }
        if (!off) { clearPress(); return false; }
        if (e.getAction() == KeyEvent.ACTION_DOWN) {
            p.edit().putLong("last_key_seen", System.currentTimeMillis()).apply();
            if (!down) {
                down = true; fired = false; startAt = e.getEventTime();
                holdWake();
                timer = () -> { if (down && !fired) fire(); };
                handler.postDelayed(timer, 850);
            } else if (!fired && e.getEventTime() - startAt >= 850) fire();
        } else if (e.getAction() == KeyEvent.ACTION_UP) {
            if (down && !fired && e.getEventTime() - startAt >= 850) fire();
            clearPress();
        }
        // Do not consume a DOWN but pass its UP (or vice versa).
        // Both are passed through; volume may change while recording shortcut operates.
        return false;
    }
    private void holdWake() {
        try {
            PowerManager pm = (PowerManager)getSystemService(POWER_SERVICE);
            if (pm != null) {
                keyWake = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "HaruMemo:keyPress");
                keyWake.acquire(2200);
            }
        } catch (RuntimeException ex) { Log.w("HaruMemo", "Wake lock unavailable", ex); }
    }
    private void fire() {
        if (!down || fired) return;
        fired = true;
        boolean accepted = VoiceRecorderService.requestShortcut(this, "접근성");
        if (!accepted) VoiceRecorderService.showShortcutFallback(this);
    }
    private void clearPress() {
        if (timer != null) handler.removeCallbacks(timer);
        timer = null; down = fired = false;
        if (keyWake != null) {
            try { if (keyWake.isHeld()) keyWake.release(); } catch (RuntimeException ignored) { }
            keyWake = null;
        }
    }
    @Override public void onDestroy() { clearPress(); super.onDestroy(); }
}
''')

service = j / 'VoiceRecorderService.java'
change(service, 'import android.os.IBinder;', 'import android.os.IBinder;\nimport android.os.Handler;\nimport android.os.Looper;\nimport android.os.SystemClock;')
change(service, 'private static volatile VoiceRecorderService instance;',
       '''private static volatile VoiceRecorderService instance;
    private VolumeShortcutBridge volumeBridge;
    private final Handler shortcutHandler = new Handler(Looper.getMainLooper());
    private long lastShortcutAt;
    /** Use the ALREADY RUNNING foreground microphone service; never start a new one in background. */
    static boolean requestShortcut(Context c, String source) {
        VoiceRecorderService s = instance;
        if (s == null || !s.armed) {
            c.getSharedPreferences("haru_settings", Context.MODE_PRIVATE).edit()
                .putString("last_shortcut_error", "녹음 대기 서비스가 종료됨").apply();
            return false;
        }
        s.shortcutHandler.post(() -> {
            long now = SystemClock.elapsedRealtime();
            if (!s.armed || now - s.lastShortcutAt < 1550) return;
            s.lastShortcutAt = now;
            s.prefs().edit().putLong("last_shortcut_trigger", System.currentTimeMillis())
                .putString("last_shortcut_source", source).apply();
            if (s.recorder == null) s.beginRecording(-1);
            else s.finishRecording();
        });
        return true;
    }''')
change(service, 'db = new MemoStore(this);',
       'db = new MemoStore(this);\n        volumeBridge = new VolumeShortcutBridge(this, () -> requestShortcut(this, "미디어 세션"));')
change(service, 'if (ACTION_DISARM.equals(action)) {\n            armed = false;',
       'if (ACTION_DISARM.equals(action)) {\n            if (volumeBridge != null) volumeBridge.deactivate();\n            armed = false;')
change(service, 'if (armed) { showArmedNotification(); return; }',
       'if (armed) { showArmedNotification(); if (volumeBridge != null) volumeBridge.activate(); return; }')
change(service, 'armed = true;\n            showArmedNotification();',
       'armed = true;\n            showArmedNotification();\n            if (volumeBridge != null) volumeBridge.activate();')
change(service, 'prefs().edit().putBoolean(PREF_ACTIVE, true).putLong(PREF_STARTED, started).commit();',
       'prefs().edit().putBoolean(PREF_ACTIVE, true).putLong(PREF_STARTED, started)\n                .putLong("last_record_started", System.currentTimeMillis()).remove("last_shortcut_error").commit();')
change(service, 'Log.e("HaruMemo", "Recorder start failed", ex);',
       'Log.e("HaruMemo", "Recorder start failed", ex);\n            prefs().edit().putString("last_shortcut_error", "녹음 시작 실패: " + ex.getClass().getSimpleName()).apply();')
change(service, 'db.attachAudio(memoId, recordingFile.getAbsolutePath(), lengthMs);',
       'db.attachAudio(memoId, recordingFile.getAbsolutePath(), lengthMs);\n            prefs().edit().putLong("last_record_saved", System.currentTimeMillis()).apply();')
change(service, 'armed = false;\n        prefs().edit().putBoolean(PREF_ARMED, false).putBoolean(PREF_ACTIVE, false).apply();',
       'armed = false;\n        if (volumeBridge != null) volumeBridge.deactivate();\n        prefs().edit().putBoolean(PREF_ARMED, false).putBoolean(PREF_ACTIVE, false).apply();')
change(service, '@Override public void onDestroy() {\n        armed = false;',
       '@Override public void onDestroy() {\n        if (volumeBridge != null) volumeBridge.deactivate();\n        armed = false;')

activity = j / 'MainActivity.java'
s = activity.read_text()
a = s.index('        if (!accessibilityEnabled()) {', s.index('    private void prepareShortcut()'))
b = s.index('        try {', a)
s = s[:a] + '        // MediaSession fallback can run even if accessibility is unavailable.\n' + s[b:]
s = s.replace('            accessibilityEnabled()) prepareShortcut();',
              '            true) prepareShortcut();')
s = s.replace('접근성 권한 없이 화면이 꺼진 상태의 볼륨 버튼을 받을 수 없어요.',
              '접근성 또는 미디어 세션으로 볼륨 버튼 입력을 시도해요.')
anchor = '''        settingsServiceStatus.setText(text.toString());'''
assert anchor in s
diagnostics = '''        text.append("\\n\\n[입력 진단]");
        long aa = prefs.getLong("last_a11y_seen", 0);
        long mm = prefs.getLong("last_media_seen", 0);
        text.append("\\n접근성 버튼: ").append(aa > 0 ? stamp.format(new Date(aa)) +
            (prefs.getBoolean("last_a11y_off",false) ? " · 화면 꺼짐" : " · 화면 켜짐") : "입력 없음");
        text.append("\\n미디어 버튼: ").append(mm > 0 ? stamp.format(new Date(mm)) +
            (prefs.getBoolean("last_media_off",false) ? " · 화면 꺼짐" : " · 화면 켜짐") : "입력 없음");
        text.append("\\n미디어 감지 준비: ")
            .append(prefs.getBoolean("media_session_ready",false)?"완료":"미실행/실패");
        long t = prefs.getLong("last_shortcut_trigger",0);
        if (t > 0) text.append("\\n녹음 명령: ").append(stamp.format(new Date(t)))
            .append(" · ").append(prefs.getString("last_shortcut_source",""));
        long saved = prefs.getLong("last_record_saved",0);
        if (saved > 0) text.append("\\n마지막 저장: ").append(stamp.format(new Date(saved)));
        String error = prefs.getString("last_shortcut_error", "");
        if (!error.isEmpty()) text.append("\\n오류: ").append(error);
        String mediaError = prefs.getString("last_media_error", "");
        if (!mediaError.isEmpty()) text.append("\\n미디어 세션 오류: ").append(mediaError);
'''
s = s.replace(anchor, diagnostics + anchor)
s = s.replace('if (VoiceRecorderService.isArmedInProcess()) text.append("✓ 녹음 대기 서비스 실행 중");',
'''if (VoiceRecorderService.isArmedInProcess()) text.append("✓ 녹음 대기 서비스 실행 중");
        else prefs.edit().putBoolean("media_session_ready",false).apply();''')
s = s.replace('TextView explanation = text("켜기 전에 마이크·알림·접근성 권한을 허용하세요. 앱이 켜져 있을 때 녹음 대기 서비스를 먼저 시작합니다.",',
'''TextView explanation = text("마이크와 알림 권한이 필요합니다. 접근성 방식과 미디어 세션 방식을 동시에 시도하며, 일부 휴대폰에서는 화면을 끄면 모두 차단될 수 있습니다. 미디어 세션이 선택되면 음악 재생 중 볼륨 버튼 동작에 영향을 줄 수 있습니다.",''')
s = s.replace('        gap(page, 20);\n        page.addView(text("작동에 필요한 권한"', '''        gap(page, 10);
        TextView refresh = chip("↻ 입력 진단 새로고침", PURPLE, PALE, 14);
        page.addView(refresh, params(-1, 46));
        refresh.setOnClickListener(v -> updateShortcutStatus());
        gap(page, 20);
        page.addView(text("작동에 필요한 권한"''')
activity.write_text(s)
print("HaruMemo 2.2 patch applied")
