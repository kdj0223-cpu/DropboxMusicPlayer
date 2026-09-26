from pathlib import Path
import sys
root=Path(sys.argv[1])

def rep(path,old,new,count=-1):
    s=path.read_text(encoding='utf-8')
    if old not in s:
        raise RuntimeError(f'missing anchor {path}: {old[:160]!r}')
    path.write_text(s.replace(old,new,count),encoding='utf-8')

gradle=root/'app/build.gradle'
rep(gradle,"applicationId 'app.harume.memo.v216'","applicationId 'app.harume.memo.v217'")
rep(gradle,'versionCode 18','versionCode 19')
rep(gradle,"versionName '2.16'","versionName '2.17'")
rep(root/'app/src/main/AndroidManifest.xml','android:label="하루메모 2.16"','android:label="하루메모 2.17"')
rep(root/'app/src/main/res/xml/shortcuts.xml','app.harume.memo.v216','app.harume.memo.v217')

fp=root/'app/src/main/java/app/harume/memo/FoldersPanel.java'
rep(fp,'    private LinearLayout rootHeader, folderBackRow;\n','    private LinearLayout rootHeader, folderBackRow, listHeader;\n')
old='''        root.addView(back,lp(-1,50));
        TextView help=label("아래 메모를 길게 눌러 위의 폴더에 넣으세요",12,MUTED,false);
        rootHelp=help;root.addView(help,lp(-1,29));

        // The folder strip never scrolls away while someone drags an older note.
        HorizontalScrollView horizontal=new HorizontalScrollView(host);
        folderStrip=horizontal;
        horizontal.setHorizontalScrollBarEnabled(false);
        horizontal.setFillViewport(true);
        folderTargets=row();folderTargets.setPadding(dp(1),dp(5),dp(1),dp(7));
        horizontal.addView(folderTargets);
        root.addView(horizontal,lp(-1,119));
        gap(root,8);

        LinearLayout tools=row();root.addView(tools,lp(-1,50));
        search=new EditText(host);search.setTextSize(14);search.setSingleLine(true);
        search.setHint("⌕  제목이나 내용 검색");search.setTextColor(INK);search.setHintTextColor(MUTED);
        search.setBackground(background(PAPER,LINE,13));search.setPadding(dp(12),0,dp(9),0);
        tools.addView(search,new LinearLayout.LayoutParams(0,dp(49),1));
        tools.addView(new View(host),lp(7,1));
        TextView importButton=button("TXT 가져오기",false);tools.addView(importButton,lp(108,47));
        importButton.setOnClickListener(v->MemoImporter.launch(host));
        gap(root,7);
        LinearLayout header=row();root.addView(header,lp(-1,43));
        heading=label("메모 리스트",18,INK,true);
'''
new='''        root.addView(back,lp(-1,50));

        LinearLayout tools=row();root.addView(tools,lp(-1,50));
        search=new EditText(host);search.setTextSize(14);search.setSingleLine(true);
        search.setHint("⌕  제목이나 내용 검색");search.setTextColor(INK);search.setHintTextColor(MUTED);
        search.setBackground(background(PAPER,LINE,13));search.setPadding(dp(12),0,dp(9),0);
        tools.addView(search,new LinearLayout.LayoutParams(0,dp(49),1));
        tools.addView(new View(host),lp(7,1));
        TextView importButton=button("TXT 가져오기",false);tools.addView(importButton,lp(108,47));
        importButton.setOnClickListener(v->MemoImporter.launch(host));
        gap(root,7);

        TextView help=label("아래 메모를 길게 눌러 위의 폴더에 넣으세요",12,MUTED,false);
        rootHelp=help;root.addView(help,lp(-1,29));

        HorizontalScrollView horizontal=new HorizontalScrollView(host);
        folderStrip=horizontal;
        horizontal.setHorizontalScrollBarEnabled(false);
        horizontal.setFillViewport(true);
        folderTargets=row();folderTargets.setPadding(dp(1),dp(5),dp(1),dp(7));
        horizontal.addView(folderTargets);
        root.addView(horizontal,lp(-1,119));
        gap(root,8);

        LinearLayout header=row();listHeader=header;root.addView(header,lp(-1,43));
        heading=label("메모 리스트",18,INK,true);
'''
rep(fp,old,new)
rep(fp,'''        if(folderStrip!=null)folderStrip.setVisibility(inside?View.GONE:View.VISIBLE);
        if(folderBackRow!=null)folderBackRow.setVisibility(inside?View.VISIBLE:View.GONE);
''','''        if(folderStrip!=null)folderStrip.setVisibility(inside?View.GONE:View.VISIBLE);
        if(folderBackRow!=null)folderBackRow.setVisibility(inside?View.VISIBLE:View.GONE);
        if(listHeader!=null)listHeader.setVisibility(inside?View.GONE:View.VISIBLE);
''')
rep(fp,'LinearLayout.LayoutParams p=lp(111,107);p.rightMargin=dp(9);','LinearLayout.LayoutParams p=lp(103,107);p.rightMargin=dp(9);')
rep(fp,'iconRow.addView(image,lp(59,51));','iconRow.addView(image,lp(51,51));')
rep(fp,'heading.setText(q.isEmpty()?(activeFolderId>0?"폴더 안의 메모":"메모 리스트"):"검색 결과");','heading.setText(q.isEmpty()?"메모 리스트":"검색 결과");')

(root/'app/src/main/res/drawable/ic_folder_large.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="52dp"
    android:height="52dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#E7E2FF"
        android:strokeColor="#6556DB"
        android:strokeWidth="0.85"
        android:strokeLineJoin="round"
        android:pathData="M4,5.2 L9.5,5.2 L11.8,8.3 L19,8.3 Q20.5,8.3 20.5,9.8 L20.5,20.2 Q20.5,21.7 19,21.7 L4,21.7 Q2.5,21.7 2.5,20.2 L2.5,6.7 Q2.5,5.2 4,5.2 Z" />
    <path
        android:fillColor="#F4F1FF"
        android:pathData="M3.6,9.5 L19.4,9.5 L19.4,20 Q19.4,20.7 18.7,20.7 L4.3,20.7 Q3.6,20.7 3.6,20 Z" />
</vector>
''',encoding='utf-8')

main=root/'app/src/main/java/app/harume/memo/MainActivity.java'
rep(main,'        if (state == null) focusEditor();\n','        if (tab == TAB_WRITE) settleWriterForReading();\n')
focus='''    private void focusEditor() {
        if (tab != TAB_WRITE || bodyEditor == null) return;
        bodyEditor.requestFocus();
        bodyEditor.postDelayed(() -> {
            if (bodyEditor == null || !bodyEditor.hasFocus()) return;
            InputMethodManager m = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            if (m != null) m.showSoftInput(bodyEditor, InputMethodManager.SHOW_IMPLICIT);
            handler.postDelayed(this::syncEditorWithIme, 160);
            handler.postDelayed(this::syncEditorWithIme, 360);
        }, 190);
    }
'''
rep(main,focus,focus+'''    private void settleWriterForReading() {
        if (tab != TAB_WRITE || writerPanel == null) return;
        hideKeyboard();
        setCompactEditor(false);
        writerPanel.setFocusableInTouchMode(true);
        writerPanel.requestFocus();
        if (bodyEditor != null) bodyEditor.clearFocus();
        if (titleEditor != null) titleEditor.clearFocus();
    }
''')
rep(main,'        LinearLayout panel = vertical(); panel.setPadding(dp(17), dp(14), dp(17), dp(13));\n        writerPanel = panel;\n',
         '        LinearLayout panel = vertical(); panel.setPadding(dp(17), dp(14), dp(17), dp(13));\n        panel.setFocusableInTouchMode(true);\n        writerPanel = panel;\n')
rep(main,'''        refreshHistoryButtons();
        refreshWriterHeading();
        refreshRecordingButton();
    }
''','''        refreshHistoryButtons();
        refreshWriterHeading();
        refreshRecordingButton();
        settleWriterForReading();
    }
''',1)
rep(main,'        focusEditor();\n    }\n    private void flipPin()','        settleWriterForReading();\n    }\n    private void flipPin()')
rep(main,'        renderTab(TAB_WRITE);\n        focusEditor();\n    }\n    private void drawList()','        renderTab(TAB_WRITE);\n        settleWriterForReading();\n    }\n    private void drawList()')

print('HaruMemo 2.17 UI patch applied')
