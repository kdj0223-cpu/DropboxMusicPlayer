from pathlib import Path
import sys,re
base=Path(sys.argv[1]); j=base/'app/src/main/java/app/harume/memo'
gradle=base/'app/build.gradle';manifest=base/'app/src/main/AndroidManifest.xml'
s=gradle.read_text(encoding='utf-8')
for old,new in [("applicationId 'app.harume.memo.v25'","applicationId 'app.harume.memo.v26'"),
("versionCode 7","versionCode 8"),("versionName '2.5'","versionName '2.6'")]:
    assert old in s,old
    s=s.replace(old,new)
gradle.write_text(s,encoding='utf-8')
shortcuts=base/'app/src/main/res/xml/shortcuts.xml'
s=shortcuts.read_text(encoding='utf-8')
assert 'app.harume.memo.v25' in s
shortcuts.write_text(s.replace('app.harume.memo.v25','app.harume.memo.v26'),encoding='utf-8')
s=manifest.read_text(encoding='utf-8')
s=s.replace('android:label="하루메모 2.3"','android:label="하루메모 2.6"')
assert 'RoutineRecorderLauncher' in s
s,count=re.subn(r'\s*<activity-alias android:name="\.RoutineRecorderLauncher"[\s\S]*?</activity-alias>','',s,count=1)
assert count==1
manifest.write_text(s,encoding='utf-8')

activity=j/'MainActivity.java'
s=activity.read_text(encoding='utf-8')
# Replace only the existing title widget: no modal, save edits after debounce.
old='titleStamp = text("", 16, INK, true);'
assert old in s
s=s.replace(old,'''titleEditor=new EditText(this);
        titleEditor.setTextColor(INK);
        titleEditor.setTextSize(16);
        titleEditor.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);
        titleEditor.setSingleLine(true);
        titleEditor.setSelectAllOnFocus(true);
        titleEditor.setBackgroundColor(android.graphics.Color.TRANSPARENT);
        titleEditor.setPadding(0,0,dp(4),0);
        titleEditor.setHint("제목 입력");
        titleEditor.setHintTextColor(MUTED);
        titleStamp=titleEditor;''')
s=s.replace('    private EditText bodyEditor, keywordInput;',
'''    private EditText bodyEditor, keywordInput, titleEditor;
    private boolean settingTitle;
    private Runnable delayedTitle;''')
s=s.replace('bodyEditor = null; saveStatus = null; titleStamp = null; pinAction = null;',
'''bodyEditor = null; saveStatus = null; titleStamp = null; titleEditor=null; pinAction = null;''')
anchor='if (dest == TAB_WRITE) drawWriter();'
assert anchor in s
s=s.replace(anchor,'if (dest == TAB_WRITE) { drawWriter(); setupInlineTitle(); }')
anchor='    private void scheduleSave() {'
assert anchor in s
methods='''    private void setupInlineTitle(){
        if(titleEditor==null)return;
        // Previous 2.1 had a modal title dialog bound to clicks; replace it.
        titleEditor.setOnClickListener(null);
        titleEditor.setFocusableInTouchMode(true);
        titleEditor.addTextChangedListener(new TextWatcher(){
            @Override public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            @Override public void onTextChanged(CharSequence s,int start,int before,int count){
                if(settingTitle)return;
                if(delayedTitle!=null)handler.removeCallbacks(delayedTitle);
                delayedTitle=()->persistInlineTitle();
                handler.postDelayed(delayedTitle,380);
            }
            @Override public void afterTextChanged(Editable e){}
        });
        titleEditor.setOnFocusChangeListener((v,focused)->{
            if(!focused)persistInlineTitle();
        });
    }
    private void persistInlineTitle(){
        if(delayedTitle!=null)handler.removeCallbacks(delayedTitle);
        delayedTitle=null;
        if(titleEditor==null||settingTitle)return;
        String title=titleEditor.getText().toString().trim();
        if(currentId<=0) {
            // Tapping a blank new memo must not create a note.
            String initial=stamp.format(new Date());
            if(title.isEmpty()||title.equals(initial))return;
            currentId=db.create(bodyEditor==null?"":bodyEditor.getText().toString(),null,0);
        }
        MemoStore.Memo m=db.find(currentId);
        if(m==null)return;
        String present=m.title==null?"":m.title.trim();
        if(title.equals(headline(m))||title.equals(present))return;
        // Clearing restores the automatic created-date title.
        db.setTitle(currentId,title);
        if(saveStatus!=null)saveStatus.setText("✓ 제목 저장됨");
    }
'''
s=s.replace(anchor,methods+anchor)
old='titleStamp.setText(m == null ? stamp.format(new Date()) : headline(m));'
assert old in s
s=s.replace(old,'''if(titleEditor==null||!titleEditor.hasFocus()){
            settingTitle=true;
            titleStamp.setText(m==null?stamp.format(new Date()):headline(m));
            settingTitle=false;
        }''')
s=s.replace('        persistNow();\n        hideKeyboard();',
'''        persistInlineTitle();
        persistNow();
        hideKeyboard();''')
s=s.replace('    @Override protected void onPause() { persistNow();',
'''    @Override protected void onPause() { persistInlineTitle(); persistNow();''')
s=s.replace('        if (delayedSave != null) handler.removeCallbacks(delayedSave);',
'''        if(delayedTitle!=null)handler.removeCallbacks(delayedTitle);
        if (delayedSave != null) handler.removeCallbacks(delayedSave);''')
# Legacy menu "rename" now opens inline title field instead of a separate dialog.
a=s.index('    private void renameMemo(MemoStore.Memo m) {')
b=s.index('    private void confirmDelete(MemoStore.Memo m) {',a)
s=s[:a]+'''    private void renameMemo(MemoStore.Memo m) {
        editMemo(m.id);
        if(titleEditor!=null){
            titleEditor.requestFocus();
            titleEditor.selectAll();
            titleEditor.post(()->{
                android.view.inputmethod.InputMethodManager imm=
                    (android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
                if(imm!=null)imm.showSoftInput(titleEditor,
                    android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT);
            });
        }
    }
'''+s[b:]
# Replace settings with one phone-only setup screen; no standby toggle and no separate icon.
start=s.index('    private void drawSettings() {')
end=s.index('    private void prepareShortcut() {',start)
s=s[:start]+'''    private void drawSettings(){
        ScrollView sc=new ScrollView(this);pages.addView(sc,params(-1,-1));
        LinearLayout page=vertical();page.setPadding(dp(20),dp(19),dp(20),dp(32));sc.addView(page);
        page.addView(text("빠른 녹음",25,INK,true),params(-1,43));
        TextView about=text("하루메모 안에 녹음 바로가기가 들어 있어요. 별도 앱 아이콘이나 녹음 대기 스위치는 필요 없습니다.",14,MUTED,false);
        about.setLineSpacing(dp(5),1f);page.addView(about,params(-1,-2));
        gap(page,17);
        TextView a=chip("① 삼성 루틴+ 열기",PURPLE,PALE,14);
        page.addView(a,params(-1,49));
        a.setOnClickListener(v->{
            try{startActivity(new Intent(Intent.ACTION_VIEW,
                android.net.Uri.parse("https://galaxystore.samsung.com/detail/com.samsung.android.app.routineplus")));}
            catch(Exception ex){Toast.makeText(this,"Galaxy Store에서 루틴+를 검색해 주세요.",Toast.LENGTH_LONG).show();}
        });
        gap(page,9);
        TextView b=chip("② 삼성 모드 및 루틴",PURPLE,PALE,14);
        page.addView(b,params(-1,49));
        b.setOnClickListener(v->{
            Intent i=getPackageManager().getLaunchIntentForPackage("com.samsung.android.app.routines");
            try{startActivity(i!=null?i:new Intent(Settings.ACTION_SETTINGS));}
            catch(Exception ex){startActivity(new Intent(Settings.ACTION_SETTINGS));}
        });
        gap(page,11);
        TextView guide=text("루틴 추가 → 버튼 액션 → 볼륨 아래 두 번 누르기 → 앱 동작 바로 실행 → 하루메모의 '녹음 시작·저장'을 선택하세요. 시작은 짧은 진동, 종료 후 저장은 두 번 진동합니다.",14,INK,false);
        guide.setLineSpacing(dp(5),1f);page.addView(guide,params(-1,-2));
        gap(page,13);
        TextView test=chip("③ 녹음 동작 테스트",PURPLE,PALE,14);
        page.addView(test,params(-1,49));
        test.setOnClickListener(v->startActivity(new Intent(this,QuickRecordActivity.class)));
        gap(page,18);
        page.addView(text("파일 보관 위치",18,INK,true),params(-1,36));
        TextView paths=text("메모 TXT: "+MemoVault.notesLocation(this)+"\\n녹음 M4A: "+
            MemoVault.AUDIO_FOLDER+"\\n\\n'녹음 파일' 탭에서 재생하거나 경로를 복사할 수 있어요.",13,MUTED,false);
        paths.setLineSpacing(dp(4),1f);page.addView(paths,params(-1,-2));
        gap(page,14);
        settingsServiceStatus=text("",13,MUTED,false);
        settingsServiceStatus.setLineSpacing(dp(4),1f);page.addView(settingsServiceStatus,params(-1,-2));
        TextView refresh=chip("권한·파일 저장 상태 확인",PURPLE,PALE,13);
        page.addView(refresh,params(-1,44));
        refresh.setOnClickListener(v->updateShortcutStatus());
        gap(page,14);
        TextView note=text("삼성 루틴+의 화면 꺼짐 버튼 동작은 휴대폰 정책에 따라 제한될 수 있어요. 녹음 바로가기가 실행되지 않는 경우엔 루틴 설정을 확인해 주세요.",12,MUTED,false);
        note.setLineSpacing(dp(4),1f);page.addView(note,params(-1,-2));
        updateShortcutStatus();
    }
'''+s[end:]
start=s.index('    private void updateShortcutStatus() {')
end=s.index('    private boolean accessibilityEnabled() {',start)
s=s[:start]+'''    private void updateShortcutStatus(){
        if(settingsServiceStatus==null)return;
        boolean mic=checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED;
        boolean notify=Build.VERSION.SDK_INT<33||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED;
        StringBuilder b=new StringBuilder("마이크: ").append(mic?"허용":"필요")
            .append(" · 알림: ").append(notify?"허용":"필요");
        String n=MemoVault.notesError(this), a=MemoVault.audioError(this);
        if(!n.isEmpty())b.append("\\n메모 파일: ").append(n);
        if(!a.isEmpty())b.append("\\n녹음 파일: ").append(a);
        long received=prefs.getLong("routine_last_received",0);
        if(received>0)b.append("\\n마지막 버튼 동작: ").append(
            new SimpleDateFormat("HH:mm:ss",Locale.KOREA).format(new Date(received)));
        String e=prefs.getString("routine_last_error","");
        if(!e.isEmpty())b.append("\\n녹음 오류: ").append(e);
        settingsServiceStatus.setText(b.toString());
    }
'''+s[end:]
# Restore on-disk title in the writer if a different note is opened.
s=s.replace('        persistNow();\n        currentId = id;',
'''        persistInlineTitle();
        persistNow();
        currentId = id;''')
s=s.replace('        persistNow();\n        currentId = -1;',
'''        persistInlineTitle();
        persistNow();
        currentId = -1;''')
# Status currently refreshed from old Accessibility path onResume; the app no
# longer ships an Accessibility service, and the settings now shows meaningful file status.
s=re.sub(r'if \(settingsServiceStatus != null\) \{\s*settingsServiceStatus\.setText\(accessibilityEnabled\(\)[\s\S]*?\n        \}',
'''if(settingsServiceStatus!=null)updateShortcutStatus();''',s,count=1)
activity.write_text(s,encoding='utf-8')
print("v2.6 inline title, single launcher, simplified settings")
