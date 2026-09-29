from pathlib import Path
import sys
p=Path(sys.argv[1])/'app/src/main/java/app/harume/memo/MainActivity.java'
s=p.read_text(encoding='utf-8')
old1='android.text.TextUtils.join("\\\\n",lines)'
new1='android.text.TextUtils.join("\\n",lines)'
old2='all.charAt(start-1)!=\'\\\\n\'?"\\\\n":""'
new2='all.charAt(start-1)!=\'\\n\'?"\\n":""'
if old1 not in s: raise RuntimeError("join newline anchor missing")
if old2 not in s: raise RuntimeError("checklist newline anchor missing")
s=s.replace(old1,new1).replace(old2,new2)
p.write_text(s,encoding='utf-8')
print("fixed checklist newline literals")
