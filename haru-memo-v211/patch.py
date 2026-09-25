from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'app/src/main/java/app/harume/memo/MainActivity.java'
gradle=root/'app/build.gradle'
manifest=root/'app/src/main/AndroidManifest.xml'

def replace(path, old, new):
    s=path.read_text(encoding='utf-8')
    if old not in s:
        raise RuntimeError("Missing anchor in "+str(path)+": "+old[:100])
    path.write_text(s.replace(old,new),encoding='utf-8')

replace(gradle,"applicationId 'app.harume.memo.v210'","applicationId 'app.harume.memo.v211'")
replace(gradle,"versionCode 12","versionCode 13")
replace(gradle,"versionName '2.10'","versionName '2.11'")
replace(manifest,'android:label="하루메모 2.10"','android:label="하루메모 2.11"')

s=main.read_text(encoding='utf-8')

old='''    private View writerHeader, writerTitleRow, writerFooter, writerTip;
    private boolean compactWhileTyping;'''
new='''    private View writerHeader, writerTitleRow, writerFooter, writerTip;
    private boolean compactWhileTyping;
    private final Runnable imeWatcher = new Runnable() {
        @Override public void run() {
            if (root == null) return;
            syncEditorWithIme();
            handler.postDelayed(this, 120);
        }
    };'''
if old not in s: raise RuntimeError("field anchor missing")
s=s.replace(old,new)

start=s.index('    private void installKeyboardLayoutObserver() {')
end=s.index('    private void drawWriter() {',start)
s=s[:start]+'''    private boolean imeIsActuallyVisible() {
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
    }

    /**
     * The enlarged writing layout follows the REAL keyboard state, never just focus.
     * This is important because HaruMemo deliberately focuses the editor on launch.
     * Samsung keeps that focus after the user hides the keyboard.
     */
    private void syncEditorWithIme() {
        boolean editingBody = tab == TAB_WRITE && bodyEditor != null && bodyEditor.hasFocus();
        boolean shouldExpand = editingBody && imeIsActuallyVisible();
        if (compactWhileTyping != shouldExpand) setCompactEditor(shouldExpand);
    }

    private void installKeyboardLayoutObserver() {
        if (Build.VERSION.SDK_INT >= 30) {
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                boolean shown = insets.isVisible(WindowInsets.Type.ime());
                boolean editingBody = tab == TAB_WRITE && bodyEditor != null && bodyEditor.hasFocus();
                final boolean expand = editingBody && shown;
                if (compactWhileTyping != expand)
                    handler.post(() -> setCompactEditor(expand));
                return insets;
            });
            root.requestApplyInsets();
        }
        // Keep this on every Android version as a Samsung/IME fallback.
        root.getViewTreeObserver().addOnGlobalLayoutListener(this::syncEditorWithIme);
    }

'''+s[end:]

old='''        // Do not rely on Samsung/Android IME visibility callbacks. The editor itself
        // is the authoritative signal that the user is typing. This immediately
        // removes surrounding chrome before/while the keyboard appears.
        bodyEditor.setOnFocusChangeListener((v, focused) -> {
            if (focused) {
                setCompactEditor(true);
                bodyEditor.post(() -> {
                    if (bodyEditor != null && bodyEditor.hasFocus()) {
                        bodyEditor.requestRectangleOnScreen(new Rect(0, 0,
                            Math.max(1, bodyEditor.getWidth()), Math.max(dp(240), bodyEditor.getHeight())), false);
                    }
                });
            } else {
                handler.postDelayed(() -> {
                    if (tab == TAB_WRITE && bodyEditor != null && !bodyEditor.hasFocus() &&
                        (titleEditor == null || !titleEditor.hasFocus())) setCompactEditor(false);
                }, 120);
            }
        });
        bodyEditor.setOnClickListener(v -> setCompactEditor(true));'''
new='''        // Focus alone must NEVER enlarge the page. The editor already owns focus at
        // app startup and Samsung keeps focus after the keyboard is dismissed.
        bodyEditor.setOnFocusChangeListener((v, focused) -> {
            if (!focused) {
                setCompactEditor(false);
            } else {
                // Allow the IME a moment to animate in, then read the real inset.
                handler.postDelayed(this::syncEditorWithIme, 80);
                handler.postDelayed(this::syncEditorWithIme, 220);
            }
        });
        bodyEditor.setOnClickListener(v -> {
            handler.postDelayed(this::syncEditorWithIme, 80);
            handler.postDelayed(this::syncEditorWithIme, 220);
        });'''
if old not in s: raise RuntimeError("focus listener anchor missing")
s=s.replace(old,new)

old='''                if (filling) return;
                if (bodyEditor != null && bodyEditor.hasFocus() && !compactWhileTyping) setCompactEditor(true);
                editAt = start;'''
new='''                if (filling) return;
                // Do not use text changes as a proxy for keyboard visibility.
                syncEditorWithIme();
                editAt = start;'''
if old not in s: raise RuntimeError("text watcher anchor missing")
s=s.replace(old,new)

old='''            if (m != null) m.showSoftInput(bodyEditor, InputMethodManager.SHOW_IMPLICIT);
        }, 190);'''
new='''            if (m != null) m.showSoftInput(bodyEditor, InputMethodManager.SHOW_IMPLICIT);
            handler.postDelayed(this::syncEditorWithIme, 160);
            handler.postDelayed(this::syncEditorWithIme, 360);
        }, 190);'''
if old not in s: raise RuntimeError("focusEditor anchor missing")
s=s.replace(old,new)

old='''        isOpen = true; handler.removeCallbacks(recorderTicker); handler.post(recorderTicker);'''
new='''        isOpen = true; handler.removeCallbacks(recorderTicker); handler.post(recorderTicker);
        handler.removeCallbacks(imeWatcher); handler.post(imeWatcher);'''
if old not in s: raise RuntimeError("onResume anchor missing")
s=s.replace(old,new)

old='''    @Override protected void onPause() { persistInlineTitle(); persistNow(); isOpen = false; handler.removeCallbacks(recorderTicker); super.onPause(); }'''
new='''    @Override protected void onPause() {
        persistInlineTitle(); persistNow(); isOpen = false;
        handler.removeCallbacks(recorderTicker);
        handler.removeCallbacks(imeWatcher);
        setCompactEditor(false);
        super.onPause();
    }'''
if old not in s: raise RuntimeError("onPause anchor missing")
s=s.replace(old,new)

old='''        handler.removeCallbacks(recorderTicker);
        if(recordingPanel!=null)recordingPanel.release();'''
new='''        handler.removeCallbacks(recorderTicker);
        handler.removeCallbacks(imeWatcher);
        if(recordingPanel!=null)recordingPanel.release();'''
if old not in s: raise RuntimeError("onDestroy anchor missing")
s=s.replace(old,new)

main.write_text(s,encoding='utf-8')
print("HaruMemo 2.11: editor expansion now follows actual IME visibility")
