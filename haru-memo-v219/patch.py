from pathlib import Path
import sys
root=Path(sys.argv[1])

def rep(path, old, new, count=-1):
    s=path.read_text(encoding='utf-8')
    if old not in s:
        raise RuntimeError(f'missing anchor {path}: {old[:180]!r}')
    path.write_text(s.replace(old,new,count),encoding='utf-8')

rep(root/'app/build.gradle', "applicationId 'app.harume.memo.v218'", "applicationId 'app.harume.memo.v219'")
rep(root/'app/build.gradle', 'versionCode 20', 'versionCode 21')
rep(root/'app/build.gradle', "versionName '2.18'", "versionName '2.19'")
rep(root/'app/src/main/AndroidManifest.xml', 'android:label="하루메모 2.18"', 'android:label="하루메모 2.19"')
rep(root/'app/src/main/res/xml/shortcuts.xml', 'app.harume.memo.v218', 'app.harume.memo.v219')

main=root/'app/src/main/java/app/harume/memo/MainActivity.java'
s=main.read_text(encoding='utf-8')
old='''        db = new MemoStore(this);
        db.syncExports();
        prefs = getSharedPreferences("haru_settings", MODE_PRIVATE);'''
new='''        db = new MemoStore(this);
        MemoImporter.autoRestorePublic(this, db);
        db.syncExports();
        prefs = getSharedPreferences("haru_settings", MODE_PRIVATE);'''
if old not in s: raise RuntimeError('onCreate db anchor missing')
s=s.replace(old,new)

start=s.index('        writerEditToolbar = horizontal();')
end=s.index('        gap(page, 4);
        FrameLayout contentHost', start)
newblock='''        writerEditToolbar = horizontal();
        writerEditToolbar.setGravity(Gravity.RIGHT | Gravity.CENTER_VERTICAL);
        page.addView(writerEditToolbar, params(-1, 40));
        editAction = chip("✎  수정", PURPLE, PALE, 12);
        writerEditToolbar.addView(editAction, params(82, 34));

        checklistAction = chip("☐ 체크", PURPLE, PALE, 10);
        doneAction = chip("✓ 완료", Color.WHITE, PURPLE, 10);
        undoButton = chip("↶ 되돌리기", PURPLE, PALE, 10);
        redoButton = chip("↷ 다시 실행", PURPLE, PALE, 10);
        TextView[] editTools = new TextView[]{checklistAction, doneAction, undoButton, redoButton};
        for (int i=0;i<editTools.length;i++) {
            TextView tool=editTools[i];
            tool.setFocusable(false);
            LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(34),1f);
            if(i>0)p.leftMargin=dp(4);
            writerEditToolbar.addView(tool,p);
        }
        writerHistoryRow = writerEditToolbar;
        undoButton.setContentDescription("메모 내용 되돌리기");
        redoButton.setContentDescription("메모 내용 다시 실행");
        editAction.setOnClickListener(v -> beginWriterEditing());
        doneAction.setOnClickListener(v -> finishWriterEditing(true));
        checklistAction.setOnClickListener(v -> insertChecklistItem());
        undoButton.setOnClickListener(v -> applyEditorUndo());
        redoButton.setOnClickListener(v -> applyEditorRedo());
'''
s=s[:start]+newblock+s[end:]

old='''        checklistReadContainer = vertical();
        checklistReadContainer.setPadding(0, dp(4), 0, dp(7));
        writerReadScroll.addView(checklistReadContainer, new ScrollView.LayoutParams(-1, -2));'''
new='''        checklistReadContainer = vertical();
        checklistReadContainer.setPadding(0, dp(4), 0, dp(7));
        checklistReadContainer.setClickable(true);
        checklistReadContainer.setOnClickListener(v -> beginWriterEditing());
        writerReadScroll.setClickable(true);
        writerReadScroll.setOnClickListener(v -> beginWriterEditing());
        writerReadScroll.addView(checklistReadContainer, new ScrollView.LayoutParams(-1, -2));'''
if old not in s: raise RuntimeError('read container anchor missing')
s=s.replace(old,new)

old='''        if (editAction != null) editAction.setVisibility(editing ? View.GONE : View.VISIBLE);
        if (doneAction != null) doneAction.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (checklistAction != null) checklistAction.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (writerHistoryRow != null) writerHistoryRow.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (!editing) setCompactEditor(false);'''
new='''        if (writerEditToolbar != null) writerEditToolbar.setVisibility(View.VISIBLE);
        if (editAction != null) editAction.setVisibility(editing ? View.GONE : View.VISIBLE);
        if (doneAction != null) doneAction.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (checklistAction != null) checklistAction.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (undoButton != null) undoButton.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (redoButton != null) redoButton.setVisibility(editing ? View.VISIBLE : View.GONE);
        if (!editing) setCompactEditor(false);'''
if old not in s: raise RuntimeError('writer mode anchor missing')
s=s.replace(old,new)

anchor='''    private void beginWriterEditing() {
        if (tab != TAB_WRITE || bodyEditor == null || writerEditing) return;
        applyWriterMode(true);
        bodyEditor.requestFocus();
        int end = bodyEditor.length();
        bodyEditor.setSelection(end);
        handler.postDelayed(() -> {
            if (!writerEditing || bodyEditor == null || !bodyEditor.hasFocus()) return;
            InputMethodManager m=(InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
            if(m!=null)m.showSoftInput(bodyEditor,InputMethodManager.SHOW_IMPLICIT);
        },120);
    }
'''
insert=anchor+'''
    private void beginWriterEditingAtLine(int lineIndex) {
        if (tab != TAB_WRITE || bodyEditor == null) return;
        if (!writerEditing) beginWriterEditing();
        String body=bodyEditor.getText().toString();
        String[] lines=body.split("\\n",-1);
        int pos=0;
        for(int i=0;i<lines.length;i++) {
            int end=pos+lines[i].length();
            if(i==lineIndex) {
                bodyEditor.setSelection(Math.min(end,bodyEditor.length()));
                return;
            }
            pos=end+1;
        }
        bodyEditor.setSelection(bodyEditor.length());
    }
'''
if anchor not in s: raise RuntimeError('begin edit anchor missing')
s=s.replace(anchor,insert)

old='''            TextView empty=text("내용이 없어요. 수정 버튼을 눌러 작성하세요.",15,MUTED,false);
            empty.setPadding(0,dp(12),0,dp(10));
            checklistReadContainer.addView(empty,params(-1,-2));'''
new='''            TextView empty=text("내용이 없어요. 여기를 눌러 작성하세요.",15,MUTED,false);
            empty.setPadding(0,dp(12),0,dp(10));
            empty.setClickable(true);
            empty.setOnClickListener(v->beginWriterEditing());
            checklistReadContainer.addView(empty,params(-1,-2));'''
if old not in s: raise RuntimeError('empty readable anchor missing')
s=s.replace(old,new)

old='''                TextView lineView=text(line.isEmpty()?" ":line,17,INK,false);
                lineView.setLineSpacing(dp(4),1.12f);
                lineView.setPadding(0,dp(2),0,dp(3));
                checklistReadContainer.addView(lineView,params(-1,-2));'''
new='''                TextView lineView=text(line.isEmpty()?" ":line,17,INK,false);
                lineView.setLineSpacing(dp(4),1.12f);
                lineView.setPadding(0,dp(2),0,dp(3));
                lineView.setClickable(true);
                lineView.setOnClickListener(v->beginWriterEditingAtLine(lineIndex));
                checklistReadContainer.addView(lineView,params(-1,-2));'''
if old not in s: raise RuntimeError('normal line anchor missing')
s=s.replace(old,new)
s=s.replace('titleStamp.setContentDescription("수정 버튼을 누른 뒤 제목을 변경할 수 있어요");',
            'titleStamp.setContentDescription("메모 내용을 눌러 수정 모드에 들어간 뒤 제목을 변경할 수 있어요");')
main.write_text(s,encoding='utf-8')

vault=root/'app/src/main/java/app/harume/memo/MemoVault.java'
s=vault.read_text(encoding='utf-8')
s=s.replace('''    static final String AUDIO_FOLDER = "Music/HaruMemo/Recordings/";
    private static final String PREFS = "haru_vault";''',
'''    static final String AUDIO_FOLDER = "Music/HaruMemo/Recordings/";
    static final String FOLDER_FILE = "harumemo_folders.txt";
    private static final String PREFS = "haru_vault";''')
insert_after='''    static String audioError(Context ctx) {
        return settings(ctx).getString("audio_error", "");
    }
'''
extra='''
    static void adoptTextUri(Context ctx,long memoId,String uri) {
        if(uri==null||uri.isEmpty())return;
        settings(ctx).edit().putString("txt_"+memoId,uri).apply();
    }

    static void adoptFoldersUri(Context ctx,String uri) {
        if(uri==null||uri.isEmpty())return;
        settings(ctx).edit().putString("folders_uri",uri).apply();
    }

    static void mirrorFolders(Context ctx, java.util.List<MemoStore.Folder> folders) {
        StringBuilder text=new StringBuilder("HaruMemo-Folders-v1\n");
        for(MemoStore.Folder f:folders) text.append(f.name).append('\n');
        SharedPreferences p=settings(ctx);
        try {
            if(Build.VERSION.SDK_INT>=29) {
                ContentResolver resolver=ctx.getContentResolver();
                String current=p.getString("folders_uri",null);
                if(current!=null&&current.startsWith("content:")) {
                    try(OutputStream out=resolver.openOutputStream(Uri.parse(current),"rwt")) {
                        if(out!=null){out.write(text.toString().getBytes(StandardCharsets.UTF_8));return;}
                    } catch(Exception ignored) { }
                }
                for(String directory:new String[]{NOTE_FOLDER,NOTE_FALLBACK}) {
                    Uri target=null;
                    try {
                        ContentValues cv=new ContentValues();
                        cv.put(MediaStore.MediaColumns.DISPLAY_NAME,FOLDER_FILE);
                        cv.put(MediaStore.MediaColumns.MIME_TYPE,"text/plain");
                        cv.put(MediaStore.MediaColumns.RELATIVE_PATH,directory);
                        cv.put(MediaStore.MediaColumns.IS_PENDING,1);
                        target=resolver.insert(MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),cv);
                        if(target==null)continue;
                        try(OutputStream out=resolver.openOutputStream(target,"w")) {
                            if(out==null)throw new IOException("Cannot write folder catalog");
                            out.write(text.toString().getBytes(StandardCharsets.UTF_8));
                        }
                        ContentValues done=new ContentValues();done.put(MediaStore.MediaColumns.IS_PENDING,0);
                        resolver.update(target,done,null,null);
                        p.edit().putString("folders_uri",target.toString()).apply();
                        return;
                    } catch(Exception ex) {
                        if(target!=null)try{resolver.delete(target,null,null);}catch(Exception ignored){}
                    }
                }
                return;
            }
            File parent=new File(ctx.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS),"HaruMemo/Notes");
            if(!parent.exists())parent.mkdirs();
            try(FileOutputStream out=new FileOutputStream(new File(parent,FOLDER_FILE))) {
                out.write(text.toString().getBytes(StandardCharsets.UTF_8));
            }
        } catch(Exception ex) {
            Log.w("HaruMemo","Folder catalog export failed",ex);
        }
    }
'''
if insert_after not in s: raise RuntimeError('vault insert anchor missing')
s=s.replace(insert_after,insert_after+extra)
vault.write_text(s,encoding='utf-8')

store=root/'app/src/main/java/app/harume/memo/MemoStore.java'
s=store.read_text(encoding='utf-8')
s=s.replace('''    void syncExports() { for (Memo m : all("")) MemoVault.mirror(app, m); }''',
'''    void syncExports() {
        for (Memo m : all("")) MemoVault.mirror(app, m);
        MemoVault.mirrorFolders(app, folders());
    }''')
old='''        return getWritableDatabase().insertOrThrow("folders", null, v);'''
new='''        long id=getWritableDatabase().insertOrThrow("folders", null, v);
        MemoVault.mirrorFolders(app,folders());
        return id;'''
if old not in s: raise RuntimeError('createFolder anchor missing')
s=s.replace(old,new)
old='''        for (Memo m : all("")) if (m.folderId == id) mirror(m.id);
    }
    boolean moveMemo'''
new='''        for (Memo m : all("")) if (m.folderId == id) mirror(m.id);
        MemoVault.mirrorFolders(app,folders());
    }
    boolean moveMemo'''
if old not in s: raise RuntimeError('renameFolder anchor missing')
s=s.replace(old,new)
old='''        for (Memo m : all("")) if (m.folderId == UNFILED) mirror(m.id);
    }
    private Memo from'''
new='''        for (Memo m : all("")) if (m.folderId == UNFILED) mirror(m.id);
        MemoVault.mirrorFolders(app,folders());
    }
    private Memo from'''
if old not in s: raise RuntimeError('deleteFolder anchor missing')
s=s.replace(old,new)
store.write_text(s,encoding='utf-8')

imp=root/'app/src/main/java/app/harume/memo/MemoImporter.java'
s=imp.read_text(encoding='utf-8')
s=s.replace('import android.content.Context;\n', 'import android.content.Context;\nimport android.content.ContentUris;\nimport android.database.Cursor;\nimport android.os.Build;\nimport android.provider.MediaStore;\n')
s=s.replace('import java.util.Set;\n', 'import java.util.Set;\nimport java.util.List;\n')
anchor='''    static void launch(Activity activity) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);'''
auto='''    static int autoRestorePublic(Context context, MemoStore db) {
        if (db.count() > 0 || !db.folders().isEmpty() || Build.VERSION.SDK_INT < 29) return 0;
        ArrayList<Uri> memoUris=new ArrayList<>();
        Uri folderCatalog=null;
        try {
            Uri files=MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
            String[] projection={MediaStore.MediaColumns._ID,MediaStore.MediaColumns.DISPLAY_NAME,MediaStore.MediaColumns.RELATIVE_PATH};
            String selection="(relative_path=? OR relative_path=?) AND (display_name LIKE ? OR display_name=?)";
            String[] args={MemoVault.NOTE_FOLDER,MemoVault.NOTE_FALLBACK,"memo_%.txt",MemoVault.FOLDER_FILE};
            try(Cursor c=context.getContentResolver().query(files,projection,selection,args,MediaStore.MediaColumns.DATE_MODIFIED+" ASC")) {
                if(c!=null)while(c.moveToNext()) {
                    long id=c.getLong(0);String name=c.getString(1);
                    Uri uri=ContentUris.withAppendedId(files,id);
                    if(MemoVault.FOLDER_FILE.equals(name)) folderCatalog=uri;
                    else if(name!=null&&name.startsWith("memo_")&&name.endsWith(".txt")) memoUris.add(uri);
                }
            }
        } catch(Exception blocked) {
            return 0;
        }
        if(folderCatalog!=null) {
            try(InputStream in=context.getContentResolver().openInputStream(folderCatalog)) {
                if(in!=null) {
                    String raw=new String(readLimited(in),StandardCharsets.UTF_8);
                    if(raw.startsWith("HaruMemo-Folders-v1\n")) {
                        for(String name:raw.substring("HaruMemo-Folders-v1\n".length()).split("\n")) {
                            String clean=name.trim();if(clean.isEmpty())continue;
                            boolean found=false;for(MemoStore.Folder f:db.folders())if(f.name.equalsIgnoreCase(clean)){found=true;break;}
                            if(!found)try{db.createFolder(clean);}catch(Exception ignored){}
                        }
                        MemoVault.adoptFoldersUri(context,folderCatalog.toString());
                    }
                }
            } catch(Exception ignored) { }
        }
        int imported=0;
        SharedPreferences fingerprints=context.getSharedPreferences("harumemo_imported",Context.MODE_PRIVATE);
        for(Uri uri:memoUris) {
            try(InputStream in=context.getContentResolver().openInputStream(uri)) {
                if(in==null)continue;
                byte[] bytes=readLimited(in);String hash=sha(bytes);
                if(fingerprints.getBoolean(hash,false))continue;
                Parsed memo=parse(new String(bytes,StandardCharsets.UTF_8));if(memo==null)continue;
                long folder=MemoStore.UNFILED;
                if(memo.folderName!=null&&!memo.folderName.isEmpty()&&!"미분류".equals(memo.folderName)) {
                    for(MemoStore.Folder f:db.folders())if(f.name.equalsIgnoreCase(memo.folderName)){folder=f.id;break;}
                    if(folder==MemoStore.UNFILED)try{folder=db.createFolder(memo.folderName);}catch(Exception ignored){}
                }
                long id=db.createImported(memo.body,memo.title,memo.created,null,0,folder);
                MemoVault.deleteNote(context,id);
                MemoVault.adoptTextUri(context,id,uri.toString());
                fingerprints.edit().putBoolean(hash,true).apply();
                imported++;
            } catch(Exception ignored) { }
        }
        return imported;
    }

'''
if anchor not in s: raise RuntimeError('importer launch anchor missing')
s=s.replace(anchor,auto+anchor)
imp.write_text(s,encoding='utf-8')

print('HaruMemo 2.19 patch applied')
