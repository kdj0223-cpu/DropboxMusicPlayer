from pathlib import Path
import sys
base=Path(sys.argv[1]); j=base/'app/src/main/java/app/harume/memo'
store=j/'MemoStore.java'
service=j/'VoiceRecorderService.java'
activity=j/'MainActivity.java'

(j/'MemoVault.java').write_text(r'''package app.harume.memo;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Log;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** SQLite is the authoritative store. Plain TXT and M4A are user-accessible copies. */
final class MemoVault {
    static final String NOTE_FOLDER = "Documents/HaruMemo/Notes/";
    static final String NOTE_FALLBACK = "Download/HaruMemo/Notes/";
    static final String AUDIO_FOLDER = "Music/HaruMemo/Recordings/";
    private static final String PREFS = "haru_vault";
    private MemoVault() { }

    private static SharedPreferences settings(Context ctx) {
        return ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static String notesLocation(Context ctx) {
        return settings(ctx).getString("note_folder", NOTE_FOLDER);
    }

    static String notesError(Context ctx) {
        return settings(ctx).getString("note_error", "");
    }

    static String audioError(Context ctx) {
        return settings(ctx).getString("audio_error", "");
    }

    static String filename(MemoStore.Memo m) {
        String date = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date(m.created));
        return "memo_" + date + "_" + m.id + ".txt";
    }

    private static String snapshot(MemoStore.Memo m) {
        SimpleDateFormat date = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.KOREA);
        String title = m.title == null || m.title.trim().isEmpty()
            ? new SimpleDateFormat("yyyy.MM.dd  a h:mm", Locale.KOREA).format(new Date(m.created))
            : m.title.trim();
        StringBuilder s=new StringBuilder();
        s.append("제목: ").append(title).append("\n")
         .append("작성: ").append(date.format(new Date(m.created))).append("\n")
         .append("수정: ").append(date.format(new Date(m.updated))).append("\n")
         .append("\n").append(m.body==null?"":m.body).append("\n");
        if(m.audio!=null) s.append("\n[연결 녹음]\n")
            .append(AUDIO_FOLDER).append(audioName(m.audio)).append("\n");
        return s.toString();
    }

    static void mirror(Context ctx, MemoStore.Memo m) {
        if (m==null) return;
        SharedPreferences p=settings(ctx);
        String key="txt_"+m.id;
        String content=snapshot(m);
        try {
            if(Build.VERSION.SDK_INT>=29) {
                ContentResolver resolver=ctx.getContentResolver();
                String current=p.getString(key,null);
                if(current!=null && current.startsWith("content:")) {
                    try (OutputStream out=resolver.openOutputStream(Uri.parse(current),"rwt")) {
                        if(out!=null) {
                            out.write(content.getBytes(StandardCharsets.UTF_8));
                            p.edit().remove("note_error").apply();
                            return;
                        }
                    } catch(Exception missing) {
                        Log.w("HaruMemo","Export file missing; recreate it",missing);
                    }
                }
                IOException problem=null;
                for(String directory : new String[]{NOTE_FOLDER,NOTE_FALLBACK}) {
                    Uri target=null;
                    try {
                        ContentValues cv=new ContentValues();
                        cv.put(MediaStore.MediaColumns.DISPLAY_NAME,filename(m));
                        cv.put(MediaStore.MediaColumns.MIME_TYPE,"text/plain");
                        cv.put(MediaStore.MediaColumns.RELATIVE_PATH,directory);
                        cv.put(MediaStore.MediaColumns.IS_PENDING,1);
                        target=resolver.insert(MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),cv);
                        if(target==null) throw new IOException("Document provider declined file");
                        try(OutputStream out=resolver.openOutputStream(target,"w")) {
                            if(out==null) throw new IOException("Cannot write TXT");
                            out.write(content.getBytes(StandardCharsets.UTF_8));
                        }
                        ContentValues done=new ContentValues();
                        done.put(MediaStore.MediaColumns.IS_PENDING,0);
                        resolver.update(target,done,null,null);
                        if(current!=null&&current.startsWith("content:")&&!current.equals(target.toString()))
                            try { resolver.delete(Uri.parse(current),null,null); } catch(Exception ignored){}
                        p.edit().putString(key,target.toString())
                            .putString("note_folder",directory).remove("note_error").apply();
                        return;
                    } catch(Exception ex) {
                        if(target!=null)try{resolver.delete(target,null,null);}catch(Exception ignored){}
                        problem=new IOException(directory+": "+ex.getMessage(),ex);
                    }
                }
                throw problem==null?new IOException("No public Documents location"):problem;
            }
            privateMirror(ctx,m,content);
        } catch(Exception ex) {
            Log.w("HaruMemo","Text export failed",ex);
            try { privateMirror(ctx,m,content); }
            catch(Exception privateEx) {
                p.edit().putString("note_error",privateEx.getClass().getSimpleName()+": "+privateEx.getMessage()).apply();
            }
        }
    }

    private static void privateMirror(Context ctx, MemoStore.Memo m, String text) throws IOException {
        File parent=new File(ctx.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS),"HaruMemo/Notes");
        if(!parent.exists()&&!parent.mkdirs()) throw new IOException("Private notes folder unavailable");
        try(FileOutputStream out=new FileOutputStream(new File(parent,filename(m)))) {
            out.write(text.getBytes(StandardCharsets.UTF_8));
        }
        settings(ctx).edit().putString("txt_"+m.id,new File(parent,filename(m)).getAbsolutePath())
            .putString("note_folder",parent.getAbsolutePath()+" (앱 삭제 시 함께 삭제됨)")
            .putString("note_error","공용 Documents에 저장하지 못해 앱 폴더에 저장했습니다.").apply();
    }

    static String publishAudio(Context ctx, File original) {
        if(original==null||!original.exists())return null;
        SharedPreferences p=settings(ctx);
        if(Build.VERSION.SDK_INT>=29) {
            ContentResolver resolver=ctx.getContentResolver();
            Uri created=null;
            try {
                ContentValues cv=new ContentValues();
                cv.put(MediaStore.MediaColumns.DISPLAY_NAME,original.getName());
                cv.put(MediaStore.MediaColumns.MIME_TYPE,"audio/mp4");
                cv.put(MediaStore.MediaColumns.RELATIVE_PATH,AUDIO_FOLDER);
                cv.put(MediaStore.MediaColumns.IS_PENDING,1);
                created=resolver.insert(MediaStore.Audio.Media.getContentUri(
                    MediaStore.VOLUME_EXTERNAL_PRIMARY),cv);
                if(created==null)throw new IOException("Cannot create audio in Music");
                try(FileInputStream src=new FileInputStream(original);
                    OutputStream out=resolver.openOutputStream(created,"w")) {
                    if(out==null) throw new IOException("Cannot open saved audio");
                    byte[] buf=new byte[32768];int n;
                    while((n=src.read(buf))!=-1)out.write(buf,0,n);
                }
                ContentValues done=new ContentValues();
                done.put(MediaStore.MediaColumns.IS_PENDING,0);
                resolver.update(created,done,null,null);
                p.edit().remove("audio_error").apply();
                original.delete();
                return created.toString();
            } catch(Exception ex) {
                Log.w("HaruMemo","Audio publication failed; preserve private file",ex);
                if(created!=null)try{resolver.delete(created,null,null);}catch(Exception ignored){}
                p.edit().putString("audio_error",ex.getClass().getSimpleName()+": "+ex.getMessage()).apply();
                return original.getAbsolutePath();
            }
        }
        try{
            File folder=new File(ctx.getExternalFilesDir(Environment.DIRECTORY_MUSIC),"HaruMemo/Recordings");
            if(!folder.exists()&&!folder.mkdirs())throw new IOException("Cannot create recordings directory");
            File to=new File(folder,original.getName());
            try(FileInputStream in=new FileInputStream(original);FileOutputStream out=new FileOutputStream(to)){
                byte[] buf=new byte[32768];int n;
                while((n=in.read(buf))!=-1)out.write(buf,0,n);
            }
            original.delete();
            p.edit().remove("audio_error").apply();
            return to.getAbsolutePath();
        } catch(Exception ex) {
            p.edit().putString("audio_error",ex.toString()).apply();
            return original.getAbsolutePath();
        }
    }

    static String audioName(Context ctx,String uri) {
        if(uri==null)return "";
        if(uri.startsWith("content:")){
            try(Cursor c=ctx.getContentResolver().query(Uri.parse(uri),
                new String[]{MediaStore.MediaColumns.DISPLAY_NAME},null,null,null)){
                if(c!=null&&c.moveToFirst())return c.getString(0);
            }catch(Exception ignored){}
        }
        return audioName(uri);
    }

    static String audioName(String path) {
        if(path==null)return "";
        int i=path.lastIndexOf('/');
        return i<0?path:path.substring(i+1);
    }

    static void deleteAudio(Context ctx,String path){
        if(path==null)return;
        try {
            if(path.startsWith("content:"))ctx.getContentResolver().delete(Uri.parse(path),null,null);
            else new File(path).delete();
        }catch(Exception ex){Log.w("HaruMemo","Could not delete recording",ex);}
    }

    static void deleteNote(Context ctx,long id){
        SharedPreferences p=settings(ctx);
        String key="txt_"+id;
        String uri=p.getString(key,null);
        if(uri!=null){
            try {
                if(uri.startsWith("content:"))ctx.getContentResolver().delete(Uri.parse(uri),null,null);
                else new File(uri).delete();
            }catch(Exception ignored){}
        }
        p.edit().remove(key).apply();
    }
}
''',encoding='utf-8')

s=store.read_text(encoding='utf-8')
s=s.replace('import android.content.Context;','import android.content.Context;')
s=s.replace('    MemoStore(Context c) { super(c, "harumemo.db", null, 2); }',
'''    private final Context app;
    MemoStore(Context c) { super(c,"harumemo.db",null,2);app=c.getApplicationContext(); }
    private void mirror(long id) { MemoVault.mirror(app,find(id)); }
    void syncExports() {
        for (Memo m : all("")) MemoVault.mirror(app,m);
    }''')
assert 'private final Context app;' in s
s=s.replace('        return getWritableDatabase().insertOrThrow("memo", null, v);',
'''        long id=getWritableDatabase().insertOrThrow("memo",null,v);
        mirror(id);
        return id;''')
s=s.replace('getWritableDatabase().update("memo", v, "id=?", new String[]{Long.toString(id)});',
'''getWritableDatabase().update("memo", v, "id=?", new String[]{Long.toString(id)});
        mirror(id);''')
s=s.replace('    void remove(long id) { getWritableDatabase().delete("memo", "id=?", new String[]{Long.toString(id)}); }',
'''    void remove(long id) {
        getWritableDatabase().delete("memo","id=?",new String[]{Long.toString(id)});
        MemoVault.deleteNote(app,id);
    }''')
store.write_text(s,encoding='utf-8')

s=service.read_text(encoding='utf-8')
old='db.attachAudio(memoId, recordingFile.getAbsolutePath(), lengthMs);'
assert old in s
s=s.replace(old,'''String saved=MemoVault.publishAudio(this,recordingFile);
            db.attachAudio(memoId,saved==null?recordingFile.getAbsolutePath():saved,lengthMs);''')
service.write_text(s,encoding='utf-8')

s=activity.read_text(encoding='utf-8')
assert 'new File(m.audio).delete()' in s
s=s.replace('new File(m.audio).delete()','MemoVault.deleteAudio(this,m.audio)')
# Files attached to notes can now be stored as content URIs as well as legacy paths.
s=s.replace('mp.setDataSource(path);',
'''if(path.startsWith("content:")) mp.setDataSource(this,android.net.Uri.parse(path));
            else mp.setDataSource(path);''')
# Reconcile existing database notes on first opening the new app.
s=s.replace('db = new MemoStore(this);','db = new MemoStore(this);\n        db.syncExports();')
activity.write_text(s,encoding='utf-8')
print("storage patch installed")
