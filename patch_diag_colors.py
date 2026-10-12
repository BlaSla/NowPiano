import io, re
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

test_qss = '''""" 
            QPushButton {
                background: red !important;
                border: 5px solid lime !important;
                color: yellow !important;
                font-size: 24px;
                min-width: 54px;
                min-height: 42px;
            }
        """'''

# аменим содержимое _icon_qss
pat_icon = re.compile(r'(_icon_qss\s*=\s*)""".*?"""', re.DOTALL)
if pat_icon.search(src):
    src = pat_icon.sub(r'\1' + test_qss.replace('""" ', '"""').lstrip('"').rstrip('"'), src, count=1)
    print("[diag] _icon_qss -> тестовый")

# аменим содержимое _play_qss
pat_play = re.compile(r'(_play_qss\s*=\s*)""".*?"""', re.DOTALL)
if pat_play.search(src):
    src = pat_play.sub(r'\1' + test_qss.replace('""" ', '"""').lstrip('"').rstrip('"'), src, count=1)
    print("[diag] _play_qss -> тестовый")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
