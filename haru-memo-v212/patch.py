from pathlib import Path
import sys
root=Path(sys.argv[1])
j=root/'app/src/main/java/app/harume/memo'
def replace(path,old,new):
    content=path.read_text(encoding='utf-8')
    if old not in content: raise RuntimeError(f'Missing anchor {path}: {old[:100]!r}')
    path.write_text(content.replace(old,new),encoding='utf-8')

gradle=root/'app/build.gradle'
replace(gradle,"applicationId 'app.harume.memo.v211'","applicationId 'app.harume.memo.v212'")
replace(gradle,"versionCode 13","versionCode 14")
replace(gradle,"versionName '2.11'","versionName '2.12'")
manifest=root/'app/src/main/AndroidManifest.xml'
replace(manifest,'android:label="하루메모 2.11"','android:label="하루메모 2.12"')
shortcuts=root/'app/src/main/res/xml/shortcuts.xml'
replace(shortcuts,"app.harume.memo.v210","app.harume.memo.v212")
theme=root/'app/src/main/res/values/styles.xml'
replace(theme,'<item name="android:windowIsTranslucent">true</item>','<item name="android:windowIsTranslucent">false</item>')
replace(theme,'<item name="android:windowBackground">@android:color/transparent</item>',
'<item name="android:windowBackground">@android:color/white</item>')

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
import android.view.Gravity;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Called by Samsung Modes & Routines through the ONE shortcut in HaruMemo.
 * Do not finish immediately after launching a microphone FGS: on Android 14+
 * that removes the visible activity before the service has acquired the mic.
 */
public final class QuickRecordActivity extends Activity {
    private static final int ASK_MIC = 800;
    private static final long TIMEOUT_MS = 7000;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private SharedPreferences prefs;
    private TextView message;
    private boolean resumed, permissionReady, dispatched, ended;
    private long requestId, dispatchedAt;
    private boolean stopping;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            // Never force the display to light up for a routine invocation.
            setTurnScreenOn(false);
        }
        prefs = getSharedPreferences("haru_settings", MODE_PRIVATE);
        prefs.edit().putLong("routine_last_received", System.currentTimeMillis())
            .remove("routine_last_error").apply();
        message = new TextView(this);
        message.setTextSize(18);
        message.setTextColor(0xFF29283D);
        message.setGravity(Gravity.CENTER);
        int pad = (int) (25 * getResources().getDisplayMetrics().density);
        message.setPadding(pad,pad,pad,pad);
        message.setText("하루메모 · 녹음 확인 중…");
        setContentView(message);

        // The service and app share one process. A persisted "active" flag with
        // no running recorder is stale after the OS killed an earlier process.
        if (prefs.getBoolean(VoiceRecorderService.PREF_ACTIVE, false)
            && !VoiceRecorderService.isRecordingInProcess()) {
            prefs.edit().putBoolean(VoiceRecorderService.PREF_ACTIVE,false)
                .remove(VoiceRecorderService.PREF_STARTED)
                .putString("routine_last_error","이전 녹음이 비정상 종료되어 상태를 정리했습니다.")
                .commit();
        }
        stopping = VoiceRecorderService.isRecordingInProcess();
        if (stopping) {
            permissionReady = true; // stopping an existing recorder needs no new permission
        } else if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED) {
            permissionReady = true;
        } else {
            message.setText("마이크 권한이 필요합니다.");
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},ASK_MIC);
        }
    }

    @Override protected void onResume() {
        super.onResume();
        resumed = true;
        // Give the window a chance to become visible before starting microphone FGS.
        if (permissionReady && !dispatched)
            handler.postDelayed(this::dispatch,180);
    }

    @Override protected void onPause() {
        resumed = false;
        super.onPause();
    }

    private void dispatch() {
        if (ended || dispatched || !permissionReady || !resumed) return;
        dispatched = true;
        requestId = System.currentTimeMillis();
        dispatchedAt = SystemClock.elapsedRealtime();
        message.setText(stopping ? "녹음을 저장하고 있어요…" : "녹음을 시작하고 있어요…");
        // Clear the old result so an earlier recording cannot fake an ACK.
        prefs.edit().remove("routine_last_result")
            .remove("routine_last_result_id")
            .putLong("routine_last_request",requestId).commit();
        Intent service = new Intent(this,VoiceRecorderService.class)
            .setAction(stopping?VoiceRecorderService.ACTION_STOP:VoiceRecorderService.ACTION_START)
            .putExtra(VoiceRecorderService.EXTRA_ROUTINE_REQUEST,requestId);
        try {
            if (stopping) startService(service);
            else startForegroundService(service);
            handler.postDelayed(this::awaitResult,100);
        } catch (RuntimeException failure) {
            prefs.edit().putString("routine_last_error",
                "서비스 실행 거부: "+failure.getClass().getSimpleName()).commit();
            fail("안드로이드가 화면 꺼짐 상태의 마이크 실행을 차단했어요.");
        }
    }

    private void awaitResult() {
        if (ended) return;
        long id = prefs.getLong("routine_last_result_id",-1);
        if (id == requestId) {
            String result = prefs.getString("routine_last_result","");
            if ("started".equals(result)) {
                Toast.makeText(this,"녹음 시작됨",Toast.LENGTH_SHORT).show();
                finishSuccessfully();
            } else if ("saved".equals(result)) {
                Toast.makeText(this,"녹음 저장됨",Toast.LENGTH_SHORT).show();
                finishSuccessfully();
            } else if ("duplicate".equals(result)) {
                // Samsung can invoke the same shortcut more than once for a key action.
                finishSuccessfully();
            } else {
                fail(prefs.getString("routine_last_error","녹음 실패. 하루메모 설정을 확인하세요."));
            }
            return;
        }
        if (SystemClock.elapsedRealtime()-dispatchedAt >= (stopping ? 16000 : TIMEOUT_MS)) {
            prefs.edit().putString("routine_last_error",
                "루틴 실행은 감지했지만 제한 시간 내 녹음 서비스 응답이 없습니다. 잠금화면 제한 가능성.").commit();
            fail("녹음이 시작되지 않았어요. 화면 잠금 상태에서 실행이 제한될 수 있어요.");
            return;
        }
        handler.postDelayed(this::awaitResult,120);
    }

    private void finishSuccessfully() {
        ended=true;
        handler.removeCallbacksAndMessages(null);
        finish();
    }

    private void fail(String explanation) {
        ended=true;
        handler.removeCallbacksAndMessages(null);
        message.setText(explanation+"\n\n하루메모를 열어 녹음을 직접 시작할 수 있어요.");
        VoiceRecorderService.showShortcutFallback(this);
        Toast.makeText(this,explanation,Toast.LENGTH_LONG).show();
        handler.postDelayed(this::finish,2700);
    }

    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results) {
        super.onRequestPermissionsResult(request,permissions,results);
        if (request != ASK_MIC) return;
        if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
            permissionReady=true;
            if (resumed) handler.postDelayed(this::dispatch,180);
        } else {
            prefs.edit().putString("routine_last_error","마이크 권한이 거부됨").commit();
            fail("하루메모에 마이크 권한을 허용해 주세요.");
        }
    }

    @Override public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}
''',encoding='utf-8')

service=j/'VoiceRecorderService.java'
replace(service,'    private long lastRoutineToggle;',
'''    private long lastRoutineToggle, lastShortcutCommandElapsed;
    static final String EXTRA_ROUTINE_REQUEST = "routine_request_id";
    static boolean isRecordingInProcess() {
        VoiceRecorderService current=instance;
        return current != null && current.recorder != null;
    }
    private void acknowledge(long id,String result) {
        if(id <= 0) return;
        android.content.SharedPreferences.Editor e=prefs().edit()
            .putLong("routine_last_result_id",id).putString("routine_last_result",result);
        if ("failed".equals(result) && prefs().getString("routine_last_error","").isEmpty())
            e.putString("routine_last_error","녹음 시작 또는 저장에 실패했습니다.");
        e.commit();
    }''')

begin=service.read_text(encoding='utf-8')
start=begin.index('    @Override public int onStartCommand(Intent i, int flags, int id) {')
end=begin.index('    private void arm() {',start)
new_command='''    @Override public int onStartCommand(Intent i, int flags, int id) {
        if (i==null) return armed || recorder!=null ? START_STICKY:START_NOT_STICKY;
        String action=i.getAction();
        long request=i.getLongExtra(EXTRA_ROUTINE_REQUEST,0);
        if(ACTION_ARM.equals(action)){arm();return START_STICKY;}
        if(ACTION_DISARM.equals(action)){
            armed=false;
            prefs().edit().putBoolean(PREF_ARMED,false).apply();
            if(recorder!=null)finishRecording();
            else{stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
            return START_NOT_STICKY;
        }
        if(request>0 && (ACTION_START.equals(action)||ACTION_STOP.equals(action))){
            long now=android.os.SystemClock.elapsedRealtime();
            if(now-lastShortcutCommandElapsed<1100){
                acknowledge(request,"duplicate");
                return recorder!=null||armed?START_STICKY:START_NOT_STICKY;
            }
            lastShortcutCommandElapsed=now;
        }
        if(ACTION_TOGGLE.equals(action)){
            if(!armed){
                prefs().edit().putString("routine_last_error","녹음 대기 서비스가 실행되지 않았습니다.").apply();
                acknowledge(request,"failed");
                return START_NOT_STICKY;
            }
            long now=android.os.SystemClock.elapsedRealtime();
            if(now-lastRoutineToggle<1100)return START_STICKY;
            lastRoutineToggle=now;
            prefs().edit().putLong("routine_last_toggle",System.currentTimeMillis())
                .remove("routine_last_error").apply();
            if(recorder==null)beginRecording(-1);
            else finishRecording();
        } else if(ACTION_START.equals(action)){
            if(recorder==null)beginRecording(i.getLongExtra(EXTRA_MEMO_ID,-1));
            acknowledge(request,recorder!=null?"started":"failed");
        } else if(ACTION_STOP.equals(action)){
            long before=prefs().getLong("routine_last_saved",0);
            if(recorder!=null)finishRecording();
            else prefs().edit().putString("routine_last_error","저장할 녹음이 실행 중이지 않습니다.").commit();
            acknowledge(request,prefs().getLong("routine_last_saved",0)>before?"saved":"failed");
        }
        return armed||recorder!=null?START_STICKY:START_NOT_STICKY;
    }

'''
service.write_text(begin[:start]+new_command+begin[end:],encoding='utf-8')
print("HaruMemo 2.12: routine shortcut waits for foreground microphone acknowledgment")
