from pathlib import Path
import sys
root=Path(sys.argv[1]); j=root/'app/src/main/java/app/harume/memo'
man=root/'app/src/main/AndroidManifest.xml'; grad=root/'app/build.gradle'
def edit(path, a, b):
 s=path.read_text()
 assert a in s, (path,a[:50])
 path.write_text(s.replace(a,b))
edit(grad,"applicationId 'app.harume.memo.v21'","applicationId 'app.harume.memo.v23'")
edit(grad,"versionCode 3","versionCode 5")
edit(grad,"versionName '2.1'","versionName '2.3'")
edit(man,'android:label="하루메모 2.1"','android:label="하루메모 2.3"')
edit(man,'''                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>''','''                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
            <meta-data android:name="android.app.shortcuts" android:resource="@xml/shortcuts" />
        </activity>''')
edit(man,'''<activity android:name=".QuickRecordActivity" android:exported="false"
            android:theme="@style/QuickStartTheme" android:excludeFromRecents="true" />''','''<activity android:name=".QuickRecordActivity" android:exported="true"
            android:taskAffinity="" android:launchMode="singleTop"
            android:theme="@style/QuickStartTheme" android:excludeFromRecents="true" />
        <activity-alias android:name=".RoutineRecorderLauncher"
            android:label="하루메모 빠른 녹음" android:icon="@drawable/ic_mic"
            android:exported="true" android:targetActivity=".QuickRecordActivity">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity-alias>''')
s=man.read_text();a=s.index('        <service android:name=".RecordingAccessibilityService"');b=s.index('        <service android:name=".QuickRecordTileService"',a);man.write_text(s[:a]+s[b:])
strings=root/'app/src/main/res/values/strings.xml'
edit(strings,'</resources>','''    <string name="shortcut_record_short">녹음 시작·저장</string>
    <string name="shortcut_record_long">바로 녹음 시작·저장</string>
</resources>''')
(root/'app/src/main/res/xml/shortcuts.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">
  <shortcut android:shortcutId="haru_record_toggle" android:enabled="true"
    android:icon="@drawable/ic_mic"
    android:shortcutShortLabel="@string/shortcut_record_short"
    android:shortcutLongLabel="@string/shortcut_record_long">
    <intent android:action="android.intent.action.VIEW"
      android:targetPackage="app.harume.memo.v23"
      android:targetClass="app.harume.memo.QuickRecordActivity" />
  </shortcut>
</shortcuts>
''')
quick=j/'QuickRecordActivity.java'
edit(quick,'if (android.os.Build.VERSION.SDK_INT >= 27) setShowWhenLocked(true);','''if (android.os.Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            setTurnScreenOn(false);
        }
        if (VoiceRecorderService.isArmedInProcess()) {
            try { startService(new Intent(this, VoiceRecorderService.class)
                    .setAction(VoiceRecorderService.ACTION_TOGGLE)); }
            catch (RuntimeException ex) {
                Toast.makeText(this, "녹음 대기가 꺼졌습니다. 앱에서 다시 켜 주세요.", Toast.LENGTH_LONG).show();
            }
            finish(); return;
        }''')
service=j/'VoiceRecorderService.java'
edit(service,'setContentText("화면이 꺼졌을 때 볼륨 아래 길게 누르기 · 다시 누르면 저장")',
             'setContentText("삼성 루틴+ 버튼 동작과 하루메모 빠른 녹음을 연결하세요")')
edit(service,'setContentText("다시 길게 누르거나 여기를 눌러 종료·저장")',
             'setContentText("루틴+ 버튼이나 알림으로 종료·저장")')
main=j/'MainActivity.java';s=main.read_text()
a=s.index('        if (!accessibilityEnabled()) {',s.index('    private void prepareShortcut()'))
b=s.index('        try {',a)
s=s[:a]+s[b:]
s=s.replace('            accessibilityEnabled()) prepareShortcut();','            true) prepareShortcut();')
s=s.replace('"볼륨 아래 길게 누르기", 16, INK, true','"버튼 녹음 준비", 16, INK, true')
s=s.replace('"화면 꺼진 상태에서 볼륨 버튼으로 녹음", 13, MUTED, false',
            '"갤럭시 루틴+에서 볼륨 버튼에 녹음을 연결", 13, MUTED, false')
s=s.replace('"켜기 전에 마이크·알림·접근성 권한을 허용하세요. 앱이 켜져 있을 때 녹음 대기 서비스를 먼저 시작합니다."',
            '"마이크·알림 권한을 허용하고 대기를 켠 뒤 삼성 루틴+에서 볼륨 아래 버튼을 연결해 주세요."')
a=s.index('        TextView access = chip("② 접근성 서비스 켜기"')
b=s.index('        gap(page, 10);',a)
s=s[:a]+'''        TextView access = chip("② 삼성 루틴+ 설치 · 실행",PURPLE,PALE,14);
        page.addView(access,params(-1,49));
        access.setOnClickListener(v -> startActivity(new Intent(Intent.ACTION_VIEW,
            android.net.Uri.parse("https://galaxystore.samsung.com/detail/com.samsung.android.app.routineplus"))));
'''+s[b:]
a=s.index('        TextView info = text("사용: 앱에서 대기 중')
b=s.index('        info.setLineSpacing',a)
s=s[:a]+'''        TextView quickTest = chip("③ 녹음 시작·저장 바로가기 테스트",PURPLE,PALE,14);
        page.addView(quickTest,params(-1,49));
        quickTest.setOnClickListener(v -> startActivity(new Intent(this,QuickRecordActivity.class)));
        gap(page,20);
        TextView info = text("설치 후 삼성 굿락의 루틴+에서 '모드 및 루틴' > '루틴 추가' > '언제 실행할까요?' > 루틴+ '버튼 액션' > 볼륨 아래 길게 누르기를 지정하세요. '무엇을 할까요?' > '앱을 열거나 앱 동작 바로 실행'에서 하루메모 '녹음 시작·저장' 바로가기 또는 '하루메모 빠른 녹음' 앱을 연결하세요.\\n\\n먼저 화면이 켜진 상태에서 두 번 눌러 진동과 파일 저장을 테스트하세요. 꺼진 화면에서 루틴+가 동작하지 않는 기종에서는 두 번 누르기 또는 측면 버튼 동작을 사용해야 합니다. 재부팅 후에는 녹음 대기를 다시 켜 주세요.",13,MUTED,false);
'''+s[b:]
s=s.replace('            .append(" · 접근성: ").append(access?"연결":"필요")',
            '            .append(" · 버튼: 삼성 루틴+ 설정 필요")')
s=s.replace('        if (detected>0) text.append("\\n마지막 화면 꺼짐 버튼 감지: ")\\n            .append(stamp.format(new Date(detected)));',
            '        text.append("\\n버튼 입력은 삼성 루틴+가 감지합니다.");')
main.write_text(s)
print('HaruMemo 2.3 Samsung Routines+ shortcut ready')
