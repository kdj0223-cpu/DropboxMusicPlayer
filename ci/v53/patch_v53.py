from pathlib import Path

root = Path("DropboxMusicPlayer")

# Fresh package id so the APK installs independently from every earlier broken build.
p = root / "app/build.gradle"
s = p.read_text()
s = s.replace("applicationId 'com.dongjin.dropboxmusic'", "applicationId 'com.dongjin.nudeongmusic'")
s = s.replace("versionCode 13", "versionCode 100")
s = s.replace("versionName '5.2.4-nudeong'", "versionName '5.3.0-nudeong'")
p.write_text(s)

# Use actual Nudeong illustrations/scenes instead of Instagram screenshot rectangles.
art_block = """private static final int[] NUDEONG_ART = {
            R.drawable.nudeong_phone,
            R.drawable.nudeong_desk,
            R.drawable.nudeong_couch,
            R.drawable.nudeong_evolution,
            R.drawable.nudeong_counter,
            R.drawable.nudeong_snow
    }"""
for java_name in ["TrackAdapter.java", "YoutubeTrackAdapter.java"]:
    p = root / "app/src/main/java/com/dongjin/dropboxmusic" / java_name
    s = p.read_text()
    a = s.find("private static final int[] NUDEONG_ART = {")
    if a >= 0:
        b = s.find("};", a)
        if b < 0:
            raise SystemExit(f"NUDEONG_ART end missing: {java_name}")
        s = s[:a] + art_block + s[b + 1:]
    p.write_text(s)

# Dropbox home: segmented Dropbox/YouTube switch matching the reference UI.
p = root / "app/src/main/java/com/dongjin/dropboxmusic/MainActivity.java"
s = p.read_text()
needle = "        findViewById(R.id.btnRefresh).setOnClickListener(v -> loadLibrary());\n"
addition = """        findViewById(R.id.btnModeYoutube).setOnClickListener(v ->
                startActivity(new Intent(this, YoutubeLibraryActivity.class)));
        findViewById(R.id.btnModeDropbox).setOnClickListener(v -> { });
"""
if needle in s and "btnModeYoutube" not in s:
    s = s.replace(needle, needle + addition)
p.write_text(s)

# YouTube library: same tabs; Dropbox returns to the Dropbox library.
p = root / "app/src/main/java/com/dongjin/dropboxmusic/YoutubeLibraryActivity.java"
s = p.read_text()
old = "        findViewById(R.id.btnMode).setOnClickListener(v -> finish());\n"
new = """        findViewById(R.id.btnMode).setOnClickListener(v -> {
            Intent i = new Intent(this, MainActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(i);
            finish();
        });
        findViewById(R.id.btnModeDropbox).setOnClickListener(v -> {
            Intent i = new Intent(this, MainActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(i);
            finish();
        });
        findViewById(R.id.btnModeYoutube).setOnClickListener(v -> { });
"""
if old in s:
    s = s.replace(old, new)
p.write_text(s)

# MainActivity is launcher. Component names are fully-qualified because applicationId is new
# while Java source remains in com.dongjin.dropboxmusic.
p = root / "app/src/main/AndroidManifest.xml"
s = p.read_text()
for name in [
    "SettingsActivity",
    "PlayerActivity",
    "YoutubePlayerActivity",
    "YoutubeLibraryActivity",
    "MainActivity",
    "ModeSelectActivity",
    "PlaybackService",
]:
    s = s.replace(f'android:name=".{name}"', f'android:name="com.dongjin.dropboxmusic.{name}"')

old_main = """        <activity
            android:name="com.dongjin.dropboxmusic.MainActivity"
            android:exported="false" />"""
new_main = """        <activity
            android:name="com.dongjin.dropboxmusic.MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>"""
if old_main in s:
    s = s.replace(old_main, new_main)

old_mode = """        <activity
            android:name="com.dongjin.dropboxmusic.ModeSelectActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>"""
new_mode = """        <activity
            android:name="com.dongjin.dropboxmusic.ModeSelectActivity"
            android:exported="false" />"""
if old_mode in s:
    s = s.replace(old_mode, new_mode)

p.write_text(s)
