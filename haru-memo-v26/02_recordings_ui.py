from pathlib import Path
import sys
p=Path(sys.argv[1]); j=p/'app/src/main/java/app/harume/memo'
(j/'RecordingsPanel.java').write_text(r'''package app.harume.memo;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.provider.DocumentsContract;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.function.LongConsumer;

final class RecordingsPanel {
    private static final int INK=0xFF222239, PURPLE=0xFF6556DB,
        MUTED=0xFF85859C, LINE=0xFFECECF3, PALE=0xFFF0EDFF;
    private final Activity host;
    private final MemoStore db;
    private final LongConsumer openNote;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final SimpleDateFormat day=new SimpleDateFormat("yyyy년 M월 d일 EEEE",Locale.KOREA);
    private final SimpleDateFormat stamp=new SimpleDateFormat("yyyy.MM.dd HH:mm",Locale.KOREA);
    private final SimpleDateFormat dkey=new SimpleDateFormat("yyyyMMdd",Locale.KOREA);
    private MediaPlayer mp;
    private String selected;
    private boolean repeat, userSeeking;
    private TextView activeName,clock,playButton,repeatButton,prevButton,nextButton,info;
    private SeekBar seek;
    private LinearLayout recordings;
    private List<MemoStore.Memo> recordingsCache;
    private int selectedIndex=-1;
    private boolean released;
    private final Runnable ticker=new Runnable(){
        @Override public void run(){
            if(released)return;
            updatePlayer();
            handler.postDelayed(this,350);
        }
    };
    RecordingsPanel(Activity host,MemoStore db,LongConsumer openNote){
        this.host=host;this.db=db;this.openNote=openNote;
        repeat=host.getSharedPreferences("haru_settings",Context.MODE_PRIVATE)
            .getBoolean("record_repeat",false);
    }
    private int dp(float n){return Math.round(n*host.getResources().getDisplayMetrics().density);}
    private LinearLayout vertical(){LinearLayout x=new LinearLayout(host);x.setOrientation(1);return x;}
    private LinearLayout horizontal(){LinearLayout x=new LinearLayout(host);x.setGravity(Gravity.CENTER_VERTICAL);return x;}
    private LinearLayout.LayoutParams lp(int w,int h){return new LinearLayout.LayoutParams(w<0?w:dp(w),h<0?h:dp(h));}
    private GradientDrawable bg(int color,int border,int radius){
        GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));
        if(border!=0)d.setStroke(dp(1),border);
        return d;
    }
    private TextView label(String s,int size,int color,boolean bold){
        TextView t=new TextView(host);t.setText(s);t.setTextColor(color);t.setTextSize(size);
        t.setGravity(Gravity.CENTER_VERTICAL);
        if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        return t;
    }
    private TextView button(String text,boolean accent){
        TextView t=label(text,14,accent?Color.WHITE:PURPLE,true);
        t.setGravity(Gravity.CENTER);t.setPadding(dp(10),0,dp(10),0);
        t.setBackground(bg(accent?PURPLE:PALE,0,12));
        return t;
    }
    private void pad(LinearLayout l,int y){l.addView(new View(host),lp(1,y));}
    private String clock(long ms){
        long total=Math.max(0,ms)/1000;
        return String.format(Locale.US,"%02d:%02d",total/60,total%60);
    }
    private String title(MemoStore.Memo m){
        return m.title==null||m.title.trim().isEmpty()?stamp.format(new Date(m.created)):m.title;
    }
    private void copy(String text){
        ((ClipboardManager)host.getSystemService(Context.CLIPBOARD_SERVICE))
            .setPrimaryClip(ClipData.newPlainText("하루메모 저장 경로",text));
        Toast.makeText(host,"경로를 복사했어요",Toast.LENGTH_SHORT).show();
    }
    private void openFolder(String folder){
        try{
            Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            String path="primary:"+folder.substring(0,folder.length()-1);
            intent.putExtra(DocumentsContract.EXTRA_INITIAL_URI,
                DocumentsContract.buildDocumentUri("com.android.externalstorage.documents",path));
            host.startActivity(intent);
        }catch(Exception e){
            Toast.makeText(host,"내 파일에서 해당 경로를 열어 주세요.",Toast.LENGTH_LONG).show();
        }
    }
    private void folderRow(LinearLayout parent,String description,String path){
        LinearLayout b=vertical();b.setPadding(dp(14),dp(10),dp(14),dp(12));
        b.setBackground(bg(Color.WHITE,LINE,14));parent.addView(b,lp(-1,-2));
        b.addView(label(description,12,MUTED,false),lp(-1,26));
        TextView p=label(path,13,INK,true);
        p.setMaxLines(2);b.addView(p,lp(-1,-2));pad(b,9);
        LinearLayout controls=horizontal();b.addView(controls,lp(-1,38));
        TextView copy=button("경로 복사",false);controls.addView(copy,lp(108,36));
        copy.setOnClickListener(v->copy(path));
        controls.addView(new View(host),lp(9,1));
        TextView open=button("폴더 보기",false);controls.addView(open,lp(108,36));
        open.setOnClickListener(v->openFolder(path.equals(MemoVault.AUDIO_FOLDER)
            ? MemoVault.AUDIO_FOLDER : MemoVault.NOTE_FOLDER));
    }
    View build(){
        released=false;
        LinearLayout root=vertical();root.setPadding(dp(16),dp(15),dp(16),0);
        root.setBackgroundColor(0xFFFAFAFE);
        root.addView(label("녹음 파일",25,INK,true),lp(-1,40));
        TextView subtitle=label("녹음 듣기 · 재생 위치 · 반복 재생",13,MUTED,false);
        root.addView(subtitle,lp(-1,26));pad(root,10);

        LinearLayout player=vertical();player.setPadding(dp(17),dp(13),dp(17),dp(14));
        player.setBackground(bg(Color.WHITE,LINE,19));root.addView(player,lp(-1,-2));
        activeName=label("재생할 녹음을 선택하세요",16,INK,true);
        activeName.setSingleLine(true);activeName.setEllipsize(android.text.TextUtils.TruncateAt.END);
        player.addView(activeName,lp(-1,35));
        seek=new SeekBar(host);seek.setMax(1000);seek.setEnabled(false);
        if(android.os.Build.VERSION.SDK_INT>=21)
            seek.setProgressTintList(android.content.res.ColorStateList.valueOf(PURPLE));
        player.addView(seek,lp(-1,40));
        seek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            @Override public void onStartTrackingTouch(SeekBar b){userSeeking=true;}
            @Override public void onStopTrackingTouch(SeekBar b){
                if(mp!=null){try{mp.seekTo(b.getProgress());}catch(Exception ignored){}}
                userSeeking=false;updatePlayer();
            }
            @Override public void onProgressChanged(SeekBar b,int progress,boolean fromUser){
                if(fromUser&&clock!=null&&mp!=null)
                    clock.setText(clock(progress)+" / "+clock(mp.getDuration()));
            }
        });
        clock=label("00:00 / 00:00",12,MUTED,false);clock.setGravity(Gravity.CENTER);
        player.addView(clock,lp(-1,22));
        pad(player,7);
        LinearLayout actions=horizontal();actions.setGravity(Gravity.CENTER);
        player.addView(actions,lp(-1,52));
        prevButton=button("−10초",false);actions.addView(prevButton,lp(74,43));
        actions.addView(new View(host),lp(8,1));
        playButton=button("▶ 재생",true);actions.addView(playButton,lp(96,49));
        actions.addView(new View(host),lp(8,1));
        nextButton=button("+10초",false);actions.addView(nextButton,lp(74,43));
        actions.addView(new View(host),lp(8,1));
        repeatButton=button(repeat?"↻ 반복 켜짐":"↻ 반복",repeat);
        actions.addView(repeatButton,lp(83,43));
        playButton.setOnClickListener(v->togglePlay());
        prevButton.setOnClickListener(v->jump(-10000));
        nextButton.setOnClickListener(v->jump(10000));
        repeatButton.setOnClickListener(v->{
            repeat=!repeat;
            host.getSharedPreferences("haru_settings",Context.MODE_PRIVATE).edit()
                .putBoolean("record_repeat",repeat).apply();
            repeatButton.setText(repeat?"↻ 반복 켜짐":"↻ 반복");
            repeatButton.setBackground(bg(repeat?PURPLE:PALE,0,12));
            repeatButton.setTextColor(repeat?Color.WHITE:PURPLE);
            if(mp!=null)mp.setLooping(repeat);
        });
        pad(root,12);
        ScrollView scroll=new ScrollView(host);scroll.setFillViewport(true);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout container=vertical();scroll.addView(container);
        folderRow(container,"녹음 파일 저장 위치",MemoVault.AUDIO_FOLDER);
        pad(container,10);
        folderRow(container,"메모 TXT 저장 위치",MemoVault.notesLocation(host));
        pad(container,8);
        info=label("",12,MUTED,false);info.setLineSpacing(dp(3),1f);
        container.addView(info,lp(-1,-2));
        pad(container,15);
        container.addView(label("녹음 목록",18,INK,true),lp(-1,34));
        recordings=vertical();container.addView(recordings,lp(-1,-2));
        pad(container,20);
        refresh();
        handler.post(ticker);
        return root;
    }
    void refresh(){
        if(released||recordings==null)return;
        recordings.removeAllViews();
        java.util.ArrayList<MemoStore.Memo> files=new java.util.ArrayList<>();
        for(MemoStore.Memo m:db.all(""))if(m.audio!=null&&!m.audio.isEmpty())files.add(m);
        recordingsCache=files;
        String last=null;
        if(files.isEmpty()){
            TextView none=label("아직 저장한 녹음이 없어요.",14,MUTED,false);
            none.setGravity(Gravity.CENTER);recordings.addView(none,lp(-1,96));
        }
        for(int i=0;i<files.size();i++){
            MemoStore.Memo m=files.get(i);
            String dayKey=dkey.format(new Date(m.created));
            if(!dayKey.equals(last)){
                last=dayKey;pad(recordings,12);
                recordings.addView(label(day.format(new Date(m.created)),14,INK,true),lp(-1,33));
            }
            LinearLayout card=vertical();card.setPadding(dp(14),dp(11),dp(14),dp(13));
            card.setBackground(bg(Color.WHITE,LINE,14));
            LinearLayout.LayoutParams c=lp(-1,-2);c.bottomMargin=dp(9);recordings.addView(card,c);
            card.addView(label(title(m),15,INK,true),lp(-1,28));
            String name=MemoVault.audioName(host,m.audio);
            TextView desc=label(stamp.format(new Date(m.created))+"  ·  "+clock(m.durationMs)
                +"\\n"+name,12,MUTED,false);
            desc.setMaxLines(2);card.addView(desc,lp(-1,-2));pad(card,9);
            LinearLayout actions=horizontal();card.addView(actions,lp(-1,34));
            TextView listen=button("▶ 재생",false);actions.addView(listen,lp(86,34));
            final int which=i;
            listen.setOnClickListener(v->select(which));
            actions.addView(new View(host),new LinearLayout.LayoutParams(0,1,1));
            TextView note=button("메모 열기",false);actions.addView(note,lp(93,34));
            note.setOnClickListener(v->{release();openNote.accept(m.id);});
            card.setOnClickListener(v->select(which));
        }
        String nErr=MemoVault.notesError(host),aErr=MemoVault.audioError(host);
        if(nErr.isEmpty()&&aErr.isEmpty())info.setText("휴대폰 '내 파일'에서 위 폴더를 열 수 있어요.");
        else info.setText((nErr.isEmpty()?"":"TXT: "+nErr+"\\n")+
            (aErr.isEmpty()?"":"녹음: "+aErr+"\\n"));
    }
    private void select(int i){
        if(recordingsCache==null||i<0||i>=recordingsCache.size())return;
        MemoStore.Memo m=recordingsCache.get(i);
        selectedIndex=i;
        if(selected!=null&&selected.equals(m.audio)&&mp!=null){
            togglePlay();return;
        }
        closePlayer();
        selected=m.audio;
        activeName.setText(title(m));
        try{
            mp=new MediaPlayer();
            if(selected.startsWith("content:"))mp.setDataSource(host,Uri.parse(selected));
            else mp.setDataSource(selected);
            mp.prepare();
            mp.setLooping(repeat);
            seek.setMax(Math.max(1,mp.getDuration()));seek.setEnabled(true);
            mp.setOnCompletionListener(p->{
                if(released)return;
                playButton.setText("▶ 재생");
                if(!repeat){try{mp.seekTo(0);}catch(Exception ignored){}}
                updatePlayer();
            });
            mp.start();
            playButton.setText("Ⅱ 일시정지");
            updatePlayer();
        }catch(Exception e){
            closePlayer();
            playButton.setText("▶ 재생");
            Toast.makeText(host,"녹음을 열 수 없어요. 파일이 이동·삭제됐을 수 있습니다.",
                Toast.LENGTH_LONG).show();
        }
    }
    private void togglePlay(){
        if(mp==null){
            if(selectedIndex>=0)select(selectedIndex);
            else Toast.makeText(host,"먼저 목록에서 녹음을 선택하세요.",Toast.LENGTH_SHORT).show();
            return;
        }
        if(mp.isPlaying()){mp.pause();playButton.setText("▶ 재생");}
        else{mp.start();playButton.setText("Ⅱ 일시정지");}
        updatePlayer();
    }
    private void jump(int ms){
        if(mp==null)return;
        try{mp.seekTo(Math.max(0,Math.min(mp.getDuration(),mp.getCurrentPosition()+ms)));}
        catch(Exception ignored){}
        updatePlayer();
    }
    private void updatePlayer(){
        if(mp==null||seek==null)return;
        try{
            int position=mp.getCurrentPosition(),duration=mp.getDuration();
            if(!userSeeking)seek.setProgress(position);
            if(!userSeeking)clock.setText(clock(position)+" / "+clock(duration));
        }catch(Exception ignored){}
    }
    private void closePlayer(){
        if(mp!=null){try{mp.stop();mp.release();}catch(Exception ignored){}mp=null;}
        if(seek!=null){seek.setProgress(0);seek.setEnabled(false);}
        if(clock!=null)clock.setText("00:00 / 00:00");
    }
    void release(){
        released=true;handler.removeCallbacks(ticker);closePlayer();
    }
}
''',encoding='utf-8')

main=j/'MainActivity.java'
s=main.read_text(encoding='utf-8')
old='private static final int TAB_WRITE = 0, TAB_LIST = 1, TAB_SETTINGS = 2;'
assert old in s
s=s.replace(old,'private static final int TAB_WRITE = 0, TAB_LIST = 1, TAB_RECORDINGS = 2, TAB_SETTINGS = 3;')
old='    private MediaPlayer player;'
assert old in s
s=s.replace(old,'    private RecordingsPanel recordingPanel;\n    private MediaPlayer player;')
s=s.replace('        tabSettings = makeTab("⚙", "설정", TAB_SETTINGS);',
'''        makeTab("♫", "녹음 파일", TAB_RECORDINGS);
        tabSettings = makeTab("⚙", "설정", TAB_SETTINGS);''')
# The v2-v2.5 navigation uses array ordering to set active tab colors.
s=s.replace('TextView[] tabs = {tabWrite, tabList, tabSettings};',
'''TextView[] tabs = {tabWrite, tabList, tabRecordings, tabSettings};''')
s=s.replace('    private TextView tabWrite, tabList, tabSettings, noteCount',
'''    private TextView tabWrite, tabList, tabRecordings, tabSettings, noteCount''')
s=s.replace('        makeTab("♫", "녹음 파일", TAB_RECORDINGS);',
'''        tabRecordings = makeTab("♫", "녹음 파일", TAB_RECORDINGS);''')
s=s.replace('        pages.removeAllViews();',
'''        if(recordingPanel!=null){recordingPanel.release();recordingPanel=null;}
        pages.removeAllViews();''')
s=s.replace('        else if (dest == TAB_LIST) drawList();\n        else drawSettings();',
'''        else if (dest == TAB_LIST) drawList();
        else if (dest == TAB_RECORDINGS) drawRecordings();
        else drawSettings();''')
marker='    private void drawSettings() {'
assert marker in s
s=s.replace(marker,'''    private void drawRecordings(){
        recordingPanel=new RecordingsPanel(this,db,id->editMemo(id));
        pages.addView(recordingPanel.build(),new LinearLayout.LayoutParams(-1,-1));
    }

'''+marker)
s=s.replace('        if (noteCards != null) fillList();',
'''        if (noteCards != null) fillList();
        if (recordingPanel != null) recordingPanel.refresh();''')
s=s.replace('        stopPlayback(); db.close(); super.onDestroy();',
'''        if(recordingPanel!=null)recordingPanel.release();
        stopPlayback(); db.close(); super.onDestroy();''')
main.write_text(s,encoding='utf-8')
print("recordings player tab installed")
