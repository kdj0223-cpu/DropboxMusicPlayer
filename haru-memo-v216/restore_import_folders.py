from pathlib import Path
import sys
folder=Path(sys.argv[1])/'app/src/main/java/app/harume/memo/FoldersPanel.java'
s=folder.read_text(encoding='utf-8')
old='long selectedFolder(){return activeFolderId;}'
new='long selectedFolder(){return activeFolderId>0?activeFolderId:MemoStore.ALL_FOLDERS;}'
assert old in s, 'Folder selection anchor missing'
folder.write_text(s.replace(old,new),encoding='utf-8')
print('TXT import from the outer list restores original folder metadata')
