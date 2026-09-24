from pathlib import Path
import sys
p=Path(sys.argv[1]); j=p/'app/src/main/java/app/harume/memo'
gradle=p/'app/build.gradle'; manifest=p/'app/src/main/AndroidManifest.xml'
def replace(path,a,b):
    s=path.read_text(encoding='utf-8')
    if a not in s: raise RuntimeError('Missing anchor: '+str(path)+' '+a[:65])
    path.write_text(s.replace(a,b),encoding='utf-8')
replace(gradle,"applicationId 'app.harume.memo.v23'","applicationId 'app.harume.memo.v25'")
replace(gradle,'versionCode 5','versionCode 7')
replace(gradle,"versionName '2.3'","versionName '2.5'")
replace(manifest,'android:label="하루메모 2.3"','android:label="하루메모 2.5"')
replace(manifest,'<application android:allowBackup=', '''<queries>
        <package android:name="com.samsung.android.app.routines" />
        <package android:name="com.samsung.android.app.routineplus" />
    </queries>
    <application android:allowBackup=''')
shortcuts=p/'app/src/main/res/xml/shortcuts.xml'
replace(shortcuts,'app.harume.memo.v23','app.harume.memo.v25')
service=j/'VoiceRecorderService.java'
replace(service,'private static volatile VoiceRecorderService instance;', '''private static volatile VoiceRecorderService instance;
    private long lastRoutineToggle;''')
replace(service,'''if (ACTION_TOGGLE.equals(action)) {
            if (!armed) return START_NOT_STICKY;
            if (recorder == null) beginRecording(-1);
            else finishRecording();''','''if (ACTION_TOGGLE.equals(action)) {
            if (!armed) {
                prefs().edit().putString("routine_last_error","녹음 대기가 중지됨").apply();
                return START_NOT_STICKY;
            }
            long now=android.os.SystemClock.elapsedRealtime();
            if (now-lastRoutineToggle<1100) return START_STICKY;
            lastRoutineToggle=now;
            prefs().edit().putLong("routine_last_toggle", System.currentTimeMillis())
                .remove("routine_last_error").apply();
            if (recorder == null) beginRecording(-1);
            else finishRecording();''')
replace(service,'''prefs().edit().putBoolean(PREF_ACTIVE, true).putLong(PREF_STARTED, started).commit();''',
'''prefs().edit().putBoolean(PREF_ACTIVE, true).putLong(PREF_STARTED, started)
                .putLong("routine_last_started",started).remove("routine_last_error").commit();''')
replace(service,'''db.attachAudio(memoId, recordingFile.getAbsolutePath(), lengthMs);''',
'''db.attachAudio(memoId, recordingFile.getAbsolutePath(), lengthMs);
            prefs().edit().putLong("routine_last_saved", System.currentTimeMillis()).commit();''')
replace(service,'''Log.e("HaruMemo", "Recorder start failed", ex);''',
'''Log.e("HaruMemo", "Recorder start failed", ex);
            prefs().edit().putString("routine_last_error","녹음 시작 실패: "+ex.getClass().getSimpleName()).apply();''')
replace(service,'"삼성 루틴+ 버튼 동작과 하루메모 빠른 녹음을 연결하세요"','"볼륨 아래 두 번 누르기 · 다시 두 번 누르면 저장"')
replace(service,'"루틴+ 버튼을 다시 누르거나 알림에서 종료·저장"','"다시 볼륨 아래 두 번 누르거나 알림에서 저장"')
quick=j/'QuickRecordActivity.java'
replace(quick,'''if (VoiceRecorderService.isArmedInProcess()) {
            try {''','''if (VoiceRecorderService.isArmedInProcess()) {
            getSharedPreferences("haru_settings",MODE_PRIVATE).edit()
                .putLong("routine_last_received",System.currentTimeMillis()).apply();
            try {''')
replace(quick,'''        if (getSharedPreferences("haru_settings", MODE_PRIVATE).getBoolean(VoiceRecorderService.PREF_ACTIVE, false)) {''',
'''        getSharedPreferences("haru_settings",MODE_PRIVATE).edit()
            .putString("routine_last_error","녹음 대기를 먼저 켜야 함").apply();
        if (getSharedPreferences("haru_settings", MODE_PRIVATE).getBoolean(VoiceRecorderService.PREF_ACTIVE, false)) {''')
activity=j/'MainActivity.java'
s=activity.read_text(encoding='utf-8')
start=s.index('    private void drawSettings() {')
end=s.index('    private void prepareShortcut() {',start)
s=s[:start]+'''    private void drawSettings() {
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);
        pages.addView(scroll,params(-1,-1));
        LinearLayout page=vertical();page.setPadding(dp(20),dp(24),dp(20),dp(35));
        scroll.addView(page);
        page.addView(text("화면 꺼짐 녹음",25,INK,true),params(-1,42));
        page.addView(text("볼륨 아래를 두 번 누르면 녹음, 다시 두 번 누르면 저장",14,MUTED,false));
        gap(page,17);
        LinearLayout box=vertical();box.setPadding(dp(17),dp(18),dp(17),dp(20));
        box.setBackground(stroke(PAPER,LINE,20));page.addView(box,params(-1,-2));
        LinearLayout row=horizontal();box.addView(row,params(-1,50));
        row.addView(text("녹음 대기",17,INK,true),new LinearLayout.LayoutParams(0,-1,1));
        shortcutSwitch=new Switch(this);shortcutSwitch.setChecked(prefs.getBoolean("volume_shortcut",false));
        shortcutSwitch.setThumbTintList(new ColorStateList(new int[][]{
            new int[]{android.R.attr.state_checked},new int[]{}},new int[]{PURPLE,0xFFCBCBDD}));
        row.addView(shortcutSwitch,params(-2,-2));
        box.addView(text("먼저 이 스위치를 켜세요. 화면을 꺼도 녹음을 시작할 수 있도록 서비스를 유지해요.",13,MUTED,false));
        gap(box,10);
        settingsServiceStatus=text("",14,PURPLE,true);
        settingsServiceStatus.setLineSpacing(dp(5),1f);
        box.addView(settingsServiceStatus,params(-1,-2));
        shortcutSwitch.setOnCheckedChangeListener((button,enabled)->{
            prefs.edit().putBoolean("volume_shortcut",enabled).commit();
            if(enabled)prepareShortcut();
            else {
                try{startService(new Intent(this,VoiceRecorderService.class)
                    .setAction(VoiceRecorderService.ACTION_DISARM));}
                catch(RuntimeException ex){android.util.Log.w("HaruMemo","Stop standby",ex);}
            }
            handler.postDelayed(this::updateShortcutStatus,450);
        });
        gap(page,18);
        page.addView(text("휴대폰에서 한 번만 연결",17,INK,true),params(-1,38));
        TextView install=chip("① 삼성 루틴+ 설치 · 열기",PURPLE,PALE,14);
        page.addView(install,params(-1,49));
        install.setOnClickListener(v->{
            try{startActivity(new Intent(Intent.ACTION_VIEW,
                android.net.Uri.parse("https://galaxystore.samsung.com/detail/com.samsung.android.app.routineplus")));}
            catch(Exception e){Toast.makeText(this,"Galaxy Store에서 루틴+를 검색해 주세요.",Toast.LENGTH_LONG).show();}
        });
        gap(page,9);
        TextView routines=chip("② 모드 및 루틴 열기",PURPLE,PALE,14);
        page.addView(routines,params(-1,49));
        routines.setOnClickListener(v->{
            Intent i=getPackageManager().getLaunchIntentForPackage("com.samsung.android.app.routines");
            try{startActivity(i!=null?i:new Intent(Settings.ACTION_SETTINGS));}
            catch(Exception e){startActivity(new Intent(Settings.ACTION_SETTINGS));}
        });
        gap(page,12);
        TextView how=text("루틴 추가 → 언제 실행할까요? → 루틴+의 버튼 액션 → 볼륨 아래 / 두 번 누르기 → 무엇을 할까요? → 앱 동작 바로 실행 → 하루메모 '녹음 시작·저장'. 안 보이면 '하루메모 빠른 녹음'을 선택하세요.",14,INK,false);
        how.setLineSpacing(dp(5),1f);page.addView(how,params(-1,-2));
        gap(page,16);
        TextView test=chip("③ 녹음 시작·저장 테스트",PURPLE,PALE,14);
        page.addView(test,params(-1,49));
        test.setOnClickListener(v->startActivity(new Intent(this,QuickRecordActivity.class)));
        gap(page,10);
        TextView refresh=chip("진단 새로고침",PURPLE,PALE,14);
        page.addView(refresh,params(-1,45));
        refresh.setOnClickListener(v->updateShortcutStatus());
        gap(page,16);
        TextView caution=text("PC·ADB·접근성 설정은 필요 없어요. 삼성 루틴+는 별도로 설치해야 하며, 기종과 잠금화면 정책에 따라 화면이 꺼진 상태의 버튼 동작이 제한될 수 있습니다. 녹음 대기가 꺼지면 하루메모에서 다시 켜 주세요.",12,MUTED,false);
        caution.setLineSpacing(dp(4),1f);page.addView(caution,params(-1,-2));
        updateShortcutStatus();
    }
''' + s[end:]
start=s.index('    private void updateShortcutStatus() {')
end=s.index('    private boolean accessibilityEnabled() {',start)
s=s[:start]+'''    private void updateShortcutStatus() {
        if(settingsServiceStatus==null)return;
        boolean mic=checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED;
        boolean notify=Build.VERSION.SDK_INT<33||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED;
        boolean armed=VoiceRecorderService.isArmedInProcess();
        java.text.SimpleDateFormat f=new java.text.SimpleDateFormat("HH:mm:ss",java.util.Locale.KOREA);
        StringBuilder t=new StringBuilder();
        t.append("마이크: ").append(mic?"허용":"권한 필요")
            .append(" · 알림: ").append(notify?"허용":"권한 필요")
            .append("\\n녹음 대기: ").append(armed?"실행 중":"중지됨");
        if(prefs.getBoolean("volume_shortcut",false)&&!armed)
            t.append("\\n앱을 연 상태에서 스위치를 껐다가 다시 켜 주세요.");
        long received=prefs.getLong("routine_last_received",0);
        if(received>0)t.append("\\n버튼 바로가기 호출: ").append(f.format(new Date(received)));
        long started=prefs.getLong("routine_last_started",0);
        if(started>0)t.append("\\n마지막 녹음 시작: ").append(f.format(new Date(started)));
        long saved=prefs.getLong("routine_last_saved",0);
        if(saved>0)t.append("\\n마지막 저장: ").append(f.format(new Date(saved)));
        String err=prefs.getString("routine_last_error","");
        if(!err.isEmpty())t.append("\\n오류: ").append(err);
        settingsServiceStatus.setText(t.toString());
    }
''' + s[end:]
activity.write_text(s,encoding='utf-8')
print("HaruMemo 2.5: phone-only Samsung Routines+ double-press route")
