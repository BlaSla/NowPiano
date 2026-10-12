import io, re
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# айти и заменить повреждённый блок: от "_icon_qss =" до "self.btn_play.setStyleSheet(_play_qss)"
# щем начало
start_marker = "_icon_qss ="
end_marker = "self.btn_play.setStyleSheet(_play_qss)"
i_start = src.find(start_marker)
i_end = src.find(end_marker)

if i_start < 0 or i_end < 0:
    print("[fix] WARNING: не нашёл маркеры. роверь вручную.")
else:
    # пределяем отступ по строке, в которой встречается _icon_qss
    line_start = src.rfind("\n", 0, i_start) + 1
    indent = src[line_start:i_start]  # ведущие пробелы

    new_block = f'''{indent}_icon_qss = """
{indent}    QPushButton {{
{indent}        background: transparent;
{indent}        border: none;
{indent}        outline: none;
{indent}        color: #2f6dbb;
{indent}        font-size: 30px;
{indent}        min-width: 54px;
{indent}        min-height: 42px;
{indent}        padding: 2px 8px;
{indent}    }}
{indent}    QPushButton:hover {{
{indent}        color: #4a90e2;
{indent}        background: rgba(74, 144, 226, 50);
{indent}        border-radius: 8px;
{indent}    }}
{indent}    QPushButton:pressed {{
{indent}        color: #1f4a80;
{indent}        background: rgba(74, 144, 226, 100);
{indent}        border-radius: 8px;
{indent}    }}
{indent}"""
{indent}_play_qss = """
{indent}    QPushButton {{
{indent}        background: transparent;
{indent}        border: none;
{indent}        color: #2f6dbb;
{indent}        font-size: 30px;
{indent}        min-width: 54px;
{indent}        min-height: 42px;
{indent}        padding: 2px 8px;
{indent}    }}
{indent}    QPushButton:hover {{
{indent}        color: #4a90e2;
{indent}        background: rgba(74, 144, 226, 50);
{indent}        border-radius: 8px;
{indent}    }}
{indent}    QPushButton:pressed {{
{indent}        color: #1f4a80;
{indent}        background: rgba(74, 144, 226, 100);
{indent}        border-radius: 8px;
{indent}    }}
{indent}"""
{indent}'''
    src = src[:i_start] + new_block + src[i_end:]
    print("[fix] _icon_qss и _play_qss восстановлены")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
