from pathlib import Path
import sys
root=Path(sys.argv[1]); j=root/'app/src/main/java/app/harume/memo'
def rep(path,old,new):
    s=path.read_text(encoding='utf-8')
    if old not in s: raise RuntimeError(f'missing anchor {path}: {old[:120]!r}')
    path.write_text(s.replace(old,new),encoding='utf-8')

rep(root/'app/build.gradle',"applicationId 'app.harume.memo.v212'","applicationId 'app.harume.memo.v213'")
rep(root/'app/build.gradle',"versionCode 14","versionCode 15")
rep(root/'app/build.gradle',"versionName '2.12'","versionName '2.13'")
rep(root/'app/src/main/AndroidManifest.xml','android:label="하루메모 2.12"','android:label="하루메모 2.13"')
rep(root/'app/src/main/res/xml/shortcuts.xml','app.harume.memo.v212','app.harume.memo.v213')

styles=root/'app/src/main/res/values/styles.xml'
rep(styles,'<item name="android:windowIsTranslucent">false</item>','<item name="android:windowIsTranslucent">true</item>')
rep(styles,'<item name="android:windowBackground">@android:color/white</item>',
    '<item name="android:windowBackground">@android:color/transparent</item>')

quick=j/'QuickRecordActivity.java'
quick.write_text(r'''package app.harume.memo;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.widget.Toast;

public final class QuickRecordActivity extends Activity {
    private static final int ASK_MIC=800;
    private static final long START_TIMEOUT=7000, STOP_TIMEOUT=16000;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private SharedPreferences prefs;
    private boolean dispatched, ended, stopping;
    private long requestId, dispatchedAt;

    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        if(Build.VERSION.SDK_INT>=27){
            setShowWhenLocked(true);
            setTurnScreenOn(false);
        }
        prefs=getSharedPreferences("haru_settings",MODE_PRIVATE);
        prefs.edit().putLong("routine_last_received",System.currentTimeMillis())
            .remove("routine_last_error").commit();

        if(prefs.getBoolean(VoiceRecorderService.PREF_ACTIVE,false)
            && !VoiceRecorderService.isRecordingInProcess()){
            prefs.edit().putBoolean(VoiceRecorderService.PREF_ACTIVE,false)
                .remove(VoiceRecorderService.PREF_STARTED).commit();
        }
        stopping=VoiceRecorderService.isRecordingInProcess();
        if(stopping || checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED){
            dispatch();
        }else{
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},ASK_MIC);
        }
    }

    private void dispatch(){
        if(dispatched||ended)return;
        dispatched=true;
        requestId=System.currentTimeMillis();
        dispatchedAt=SystemClock.elapsedRealtime();
        prefs.edit().remove("routine_last_result").remove("routine_last_result_id")
            .putLong("routine_last_request",requestId).commit();
        Intent cmd=new Intent(this,VoiceRecorderService.class)
            .setAction(stopping?VoiceRecorderService.ACTION_STOP:VoiceRecorderService.ACTION_START)
            .putExtra(VoiceRecorderService.EXTRA_ROUTINE_REQUEST,requestId);
        try{
            if(stopping) startService(cmd); else startForegroundService(cmd);
            handler.postDelayed(this::awaitResult,90);
        }catch(RuntimeException ex){
            prefs.edit().putString("routine_last_error","서비스 실행 거부: "+ex.getClass().getSimpleName()).commit();
            finishFailed("녹음을 실행할 수 없어요.");
        }
    }

    private void awaitResult(){
        if(ended)return;
        long id=prefs.getLong("routine_last_result_id",-1);
        if(id==requestId){
            String result=prefs.getString("routine_last_result","");
            if("started".equals(result)) Toast.makeText(this,"녹음 시작됨",Toast.LENGTH_SHORT).show();
            else if("saved".equals(result)) Toast.makeText(this,"녹음 저장됨",Toast.LENGTH_SHORT).show();
            else if(!"duplicate".equals(result)){
                finishFailed(prefs.getString("routine_last_error","녹음 실행 실패")); return;
            }
            finishOk(); return;
        }
        long timeout=stopping?STOP_TIMEOUT:START_TIMEOUT;
        if(SystemClock.elapsedRealtime()-dispatchedAt>=timeout){
            prefs.edit().putString("routine_last_error","루틴 호출은 감지했지만 녹음 서비스 응답 시간 초과").commit();
            finishFailed("녹음 서비스 응답이 없어요."); return;
        }
        handler.postDelayed(this::awaitResult,120);
    }
    private void finishOk(){ended=true;handler.removeCallbacksAndMessages(null);finish();}
    private void finishFailed(String why){
        ended=true;handler.removeCallbacksAndMessages(null);
        Toast.makeText(this,why,Toast.LENGTH_LONG).show();finish();
    }
    @Override public void onRequestPermissionsResult(int request,String[] p,int[] results){
        super.onRequestPermissionsResult(request,p,results);
        if(request==ASK_MIC && results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED){
            dispatch();
        }else{
            prefs.edit().putString("routine_last_error","마이크 권한이 거부됨").commit();
            finishFailed("마이크 권한을 허용해 주세요.");
        }
    }
    @Override public void onDestroy(){handler.removeCallbacksAndMessages(null);super.onDestroy();}
}
''',encoding='utf-8')

main=j/'MainActivity.java'
s=main.read_text(encoding='utf-8')

old='''    private boolean imeIsActuallyVisible() {
        if (root == null) return false;
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsets insets = root.getRootWindowInsets();
            if (insets != null)
                return insets.isVisible(WindowInsets.Type.ime());
        }
        Rect visible = new Rect();
        root.getWindowVisibleDisplayFrame(visible);
        int rootHeight = root.getRootView().getHeight();
        if (rootHeight <= 0) rootHeight = getResources().getDisplayMetrics().heightPixels;
        int hidden = Math.max(0, rootHeight - visible.bottom);
        return hidden > Math.max(dp(160), rootHeight / 5);
    }'''
new='''    private boolean imeIsActuallyVisible() {
        if (root == null) return false;
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsets insets = root.getRootWindowInsets();
            if (insets != null && insets.isVisible(WindowInsets.Type.ime())) return true;
            try {
                android.view.WindowMetrics metrics=getWindowManager().getCurrentWindowMetrics();
                WindowInsets current=metrics.getWindowInsets();
                if(current!=null && current.isVisible(WindowInsets.Type.ime())) return true;
            } catch(RuntimeException ignored) { }
        }
        int screenHeight=getResources().getDisplayMetrics().heightPixels;
        int rootHeight=root.getHeight();
        if(rootHeight>0 && screenHeight-rootHeight>Math.max(dp(180),screenHeight/5)) return true;
        Rect visible=new Rect();
        getWindow().getDecorView().getWindowVisibleDisplayFrame(visible);
        int obscured=Math.max(0,screenHeight-visible.bottom);
        return obscured>Math.max(dp(180),screenHeight/5);
    }'''
if old not in s: raise RuntimeError('IME method anchor missing')
s=s.replace(old,new)

old='''        writerPanel.requestLayout();
    }

    private boolean imeIsActuallyVisible()'''
new='''        writerPanel.requestLayout();
        refreshRecordingStrip();
    }

    private boolean imeIsActuallyVisible()'''
if old not in s: raise RuntimeError('compact end anchor missing')
s=s.replace(old,new)

old='''        recordButton.setText(active ? "■  녹음 종료" : awaitingStart ? "●  준비 중…"
            : hasAudio ? (m.audio.equals(playingAudio) ? "■ 재생 종료" : "▶ 녹음 재생")
            : "●  녹음");
        recordButton.setBackground(bg(active ? RED : PURPLE, 13));
        if (replaceRecordButton != null)
            replaceRecordButton.setVisibility(hasAudio && !active && !awaitingStart
                ? View.VISIBLE : View.GONE);'''
new='''        if(active){
            recordButton.setVisibility(View.GONE);
            if(replaceRecordButton!=null)replaceRecordButton.setVisibility(View.GONE);
            return;
        }
        recordButton.setVisibility(View.VISIBLE);
        recordButton.setText(awaitingStart ? "●  준비 중…"
            : hasAudio ? (m.audio.equals(playingAudio) ? "■ 재생 종료" : "▶ 녹음 재생")
            : "●  녹음");
        recordButton.setBackground(bg(PURPLE,13));
        if(replaceRecordButton!=null)
            replaceRecordButton.setVisibility(hasAudio&&!awaitingStart?View.VISIBLE:View.GONE);'''
if old not in s: raise RuntimeError('record button anchor missing')
s=s.replace(old,new)

old='''        boolean running = recording();
        bar.setVisibility(running ? View.VISIBLE : View.GONE);'''
new='''        boolean running = recording();
        boolean typing = tab==TAB_WRITE && bodyEditor!=null && bodyEditor.hasFocus() && imeIsActuallyVisible();
        bar.setVisibility(running && !compactWhileTyping && !typing ? View.VISIBLE : View.GONE);'''
if old not in s: raise RuntimeError('record strip anchor missing')
s=s.replace(old,new)

old='''        @Override public void run() {
            if (!isOpen) return;
            refreshRecordingStrip();
            handler.postDelayed(this, 700);
        }'''
new='''        @Override public void run() {
            if (!isOpen) return;
            syncEditorWithIme();
            refreshRecordingStrip();
            handler.postDelayed(this, 350);
        }'''
if old not in s: raise RuntimeError('recorder ticker anchor missing')
s=s.replace(old,new)

main.write_text(s,encoding='utf-8')
print('HaruMemo 2.13 final repair applied')
