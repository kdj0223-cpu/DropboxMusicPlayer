from pathlib import Path
import sys
p=Path(sys.argv[1])/'app/src/main/java/app/harume/memo/MainActivity.java'
s=p.read_text(encoding='utf-8')

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
extra=anchor+'''
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
if anchor not in s: raise RuntimeError('begin editing anchor missing')
s=s.replace(anchor,extra)

old='''            TextView empty=text("내용이 없어요. 수정 버튼을 눌러 작성하세요.",15,MUTED,false);
            empty.setPadding(0,dp(12),0,dp(10));
            checklistReadContainer.addView(empty,params(-1,-2));'''
new='''            TextView empty=text("내용이 없어요. 여기를 눌러 작성하세요.",15,MUTED,false);
            empty.setPadding(0,dp(12),0,dp(10));
            empty.setClickable(true);
            empty.setOnClickListener(v->beginWriterEditing());
            checklistReadContainer.addView(empty,params(-1,-2));'''
if old not in s: raise RuntimeError('empty content anchor missing')
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
if old not in s: raise RuntimeError('normal content line anchor missing')
s=s.replace(old,new)

s=s.replace('titleStamp.setContentDescription("수정 버튼을 누른 뒤 제목을 변경할 수 있어요");',
            'titleStamp.setContentDescription("메모 내용을 눌러 수정 모드에 들어간 뒤 제목을 변경할 수 있어요");')

p.write_text(s,encoding='utf-8')
print('HaruMemo 2.19 tap-to-edit patch applied')
