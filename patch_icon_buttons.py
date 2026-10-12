import io
PATH = r"C:\NowPiano\src\piano_qt.py"
with io.open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# Ставим property icon_button="true" на кнопках управления
for name in ("btn_rewind", "btn_play", "btn_stop", "btn_loop"):
    marker = f"self.{name} = QPushButton"
    prop = f'self.{name}.setProperty("icon_button", "true")'
    if prop in src:
        print(f"[piano_qt] {name}: property уже стоит")
        continue
    # айти строку создания кнопки и добавить после неё setProperty
    idx = src.find(marker)
    if idx < 0:
        print(f"[piano_qt] {name}: не найден QPushButton")
        continue
    # айти конец строки
    end_of_line = src.find("\n", idx)
    if end_of_line < 0:
        print(f"[piano_qt] {name}: не найден конец строки")
        continue
    src = src[:end_of_line+1] + f'        {prop}\n' + src[end_of_line+1:]
    print(f"[piano_qt] {name}: property set")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(src)
print("DONE")
