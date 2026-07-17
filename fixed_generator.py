# -*- coding: utf-8 -*-
"""
修复版本的 GUI 生成器 — 基于原 Tkinter-Designer widget 映射逻辑。
支持单文件和多个 JSON 文件输入（多页面切换）。

原项目映射规则（基于 Figma 节点 name 小写匹配）：
  Button       → tk.Button
  Label        → tk.Label
  Entry        → tk.Entry
  Text         → tk.Text
  Checkbutton  → tk.Checkbutton + BooleanVar
  Radiobutton  → tk.Radiobutton + StringVar
  Listbox      → tk.Listbox
  Canvas       → tk.Canvas
  Frame        → tk.Frame
  rectangle/type=rectangle  → canvas.create_rectangle (图元)
  type=text (非 widget 名) → canvas.create_text (图元)

多文件模式：
  - 第一个 JSON 作为侧边栏（固定左侧）
  - 后续 JSON 作为内容页面，侧边栏 Button 自动绑定页面切换
  - 用法：python fixed_generator.py sidebar.json page1.json page2.json
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime


def rgb_to_hex(color_dict):
    """将 Figma 颜色字典转换为十六进制"""
    if not color_dict:
        return "#FFFFFF"
    r = int(color_dict.get("r", 1) * 255)
    g = int(color_dict.get("g", 1) * 255)
    b = int(color_dict.get("b", 1) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def parse_color(color_value):
    """解析颜色：可能是字典或字符串"""
    if isinstance(color_value, str):
        return color_value
    if isinstance(color_value, dict):
        return rgb_to_hex(color_value)
    return "#FFFFFF"


def get_fill_color(element):
    """从元素获取填充颜色"""
    fills = element.get("fills", [])
    for fill in fills:
        if fill.get("type") == "SOLID" and fill.get("visible", True):
            return parse_color(fill.get("color", {}))
    return "#FFFFFF"


def get_stroke_color(element):
    """获取描边颜色"""
    strokes = element.get("strokes", [])
    for stroke in strokes:
        color = stroke.get("color", None)
        if color:
            c = parse_color(color)
            if c != "#FFFFFF":
                return c
    return None


def get_child_text(element):
    """从 FRAME 子元素中提取第一个 TEXT 的内容"""
    children = element.get("children", [])
    for child in children:
        if child.get("type") == "TEXT":
            return child.get("characters", "")
    return ""


def get_font_info(element):
    """从 TEXT 元素提取字体信息"""
    font_name = element.get("fontName", {})
    family = font_name.get("family", "Inter")
    style = font_name.get("style", "Regular")
    weight = "bold" if "Bold" in style or "Semi" in style else "normal"
    size = element.get("fontSize", 14)
    return family, size, weight


# Widget 名称映射表（小写）
WIDGET_NAME_MAP = {
    "button":       "Button",
    "label":        "Label",
    "entry":        "Entry",
    "search":       "Entry",
    "textbox":      "Entry",
    "text":         "Text",
    "textarea":     "Text",
    "checkbutton":  "Checkbutton",
    "checkbox":     "Checkbutton",
    "radiobutton":  "Radiobutton",
    "radio":        "Radiobutton",
    "listbox":      "Listbox",
    "canvas":       "Canvas",
    "frame":        "Frame",
    "table":        "Treeview",
}

# 可交互 widget（需要生成 command 回调）
INTERACTIVE_WIDGETS = {"Button", "Checkbutton", "Radiobutton"}

# 文本输入 widget（预留 .get() 变量声明）
TEXT_INPUT_WIDGETS = {"Entry", "Text"}


def identify_widget_type(element):
    """基于节点名称识别 widget 类型。"""
    name = element.get("name", "").strip().lower()
    return WIDGET_NAME_MAP.get(name, None)


def process_json_data(data, offset_x=0, offset_y=0, widget_counter=None,
                      track_buttons=False):
    """处理单个 JSON 数据，返回 (widgets, primitives, widget_counter, button_list, button_borders)

    widgets: 真正的 Tkinter widget
    primitives: Canvas 图元
    widget_counter: 全局 widget 计数（传入引用，跨数据集共享）
    button_list: 如果 track_buttons=True，按处理顺序收集 Button widget 信息
    button_borders: 有圆角且需要边框的 Button 的边框层信息（用于生成边框圆角矩形）
    """
    if widget_counter is None:
        widget_counter = {}
    widgets = []
    primitives = []
    button_borders = []
    button_list = [] if track_buttons else None

    def process_element(elem, off_x=0, off_y=0):
        elem_type = elem.get("type", "UNKNOWN")
        elem_name = elem.get("name", "").strip()
        x = elem.get("x", 0) + off_x + offset_x
        y = elem.get("y", 0) + off_y + offset_y
        w = elem.get("width", 0)
        h = elem.get("height", 0)
        corner_radius = elem.get("cornerRadius", 0)

        widget_type = identify_widget_type(elem)


        # ── 情况 1b：识别到 widget → 生成真正的 Tkinter widget ──
        if widget_type and elem_type in ("FRAME", "SECTION"):
            widget_counter[widget_type] = widget_counter.get(widget_type, 0) + 1
            idx = widget_counter[widget_type]
            var_name = f"{widget_type.lower()}_{idx}"

            bg_color = get_fill_color(elem)
            text_content = get_child_text(elem)
            stroke_color = get_stroke_color(elem)

            widget_info = {
                "widget_type": widget_type,
                "var_name": var_name,
                "idx": idx,
                "x": x, "y": y, "w": w, "h": h,
                "bg_color": bg_color,
                "text": text_content,
                "stroke_color": stroke_color,
                "corner_radius": corner_radius,
                "var_holder": f"var_{var_name}" if widget_type in ("Checkbutton", "Radiobutton") else None,
            }
            widgets.append(widget_info)

            # 有圆角且有描边的 Button：收集边框层信息
            if widget_type == "Button" and corner_radius > 0 and stroke_color:
                button_borders.append({
                    "var_name": var_name,
                    "x": x - 1, "y": y - 1,
                    "w": w + 2, "h": h + 2,
                    "corner_radius": corner_radius,
                    "bg_color": bg_color,
                    "stroke_color": stroke_color,
                })

            if track_buttons and widget_type == "Button":
                button_list.append(widget_info)

            # ── Treeview 特殊处理 ──
            if widget_type == "Treeview":
                columns = []
                table_children = elem.get("children", [])

                # 递归提取所有 TEXT 节点（处理 FRAME > TEXT 嵌套）
                def extract_text_from_children(children_list):
                    texts = []
                    for child in children_list:
                        if child.get("type") == "TEXT":
                            t = child.get("characters", "").strip()
                            if t:
                                texts.append(t)
                        elif "children" in child:
                            texts.extend(extract_text_from_children(child["children"]))
                    return texts

                columns = extract_text_from_children(table_children)
                if not columns:
                    columns = ["Column 1", "Column 2"]
                widget_info["columns"] = columns

                # 提取列宽：从表头子节点的 x 坐标推算
                col_x_positions = sorted([
                    child.get("x", 0)
                    for child in table_children
                    if child.get("type") != "TEXT"
                ])
                table_total_w = elem.get("width", 317)
                if col_x_positions and col_x_positions[0] != 0:
                    col_x_positions.insert(0, 0)
                col_x_positions.append(table_total_w)
                col_widths = [
                    col_x_positions[i + 1] - col_x_positions[i]
                    for i in range(len(col_x_positions) - 1)
                ]
                # 确保宽度数与列数一致
                if len(col_widths) != len(columns):
                    col_widths = [table_total_w // len(columns)] * len(columns)
                widget_info["col_widths"] = col_widths
                for child in table_children:
                    if child.get("type") != "TEXT":
                        process_element(child, off_x + elem.get("x", 0),
                                        off_y + elem.get("y", 0))
                return

            # 提取子元素的字体信息
            children = elem.get("children", [])
            for child in children:
                if child.get("type") == "TEXT":
                    family, size, weight = get_font_info(child)
                    fg = get_fill_color(child)
                    widget_info["font_family"] = family
                    widget_info["font_size"] = size
                    widget_info["font_weight"] = weight
                    widget_info["fg_color"] = fg
                    break

            # Button 子元素中可能有图标等
            for child in children:
                ctype = child.get("type", "")
                if ctype == "TEXT":
                    continue
                process_element(child, off_x + elem.get("x", 0),
                                off_y + elem.get("y", 0))
            return

        # ── 情况 2：FRAME / SECTION 容器 ──
        if elem_type in ("FRAME", "SECTION"):
            bg_color = get_fill_color(elem)
            stroke_color = get_stroke_color(elem)

            has_bg = bg_color != "#FFFFFF" or corner_radius > 0 or stroke_color
            if has_bg:
                primitives.append({
                    "type": "rectangle",
                    "x": x, "y": y, "w": w, "h": h,
                    "bg_color": bg_color,
                    "radius": corner_radius,
                    "stroke_color": stroke_color,
                })

            for child in elem.get("children", []):
                process_element(child, off_x + elem.get("x", 0),
                                off_y + elem.get("y", 0))
            return

        # ── 情况 3：TEXT 图元（非 widget 名） ──
        if elem_type == "TEXT":
            content = elem.get("characters", "")
            if not content:
                return
            family, size, weight = get_font_info(elem)
            fg = get_fill_color(elem)
            primitives.append({
                "type": "text",
                "x": x, "y": y,
                "content": content,
                "font_family": family,
                "font_size": size,
                "font_weight": weight,
                "text_color": fg,
            })
            return

        # ── 情况 4：VECTOR 图元 ──
        if elem_type == "VECTOR":
            fills = elem.get("fills", [])
            has_image_fill = any(f.get("type") == "IMAGE" for f in fills)
            if has_image_fill:
                safe_name = re.sub(r'[^\w\-]', '_', elem_name)
                image_filename = f"{safe_name}.png"
                primitives.append({
                    "type": "image",
                    "x": x, "y": y, "w": w, "h": h,
                    "filename": image_filename,
                })
                return
            primitives.append({
                "type": "rectangle",
                "x": x, "y": y, "w": w, "h": h,
                "bg_color": "#888888",
                "radius": 0,
                "stroke_color": None,
            })
            return

        # ── 情况 5：RECTANGLE ──
        if elem_type == "RECTANGLE":
            fills = elem.get("fills", [])
            has_image_fill = any(f.get("type") == "IMAGE" for f in fills)
            if has_image_fill:
                safe_name = re.sub(r'[^\w\-]', '_', elem_name)
                image_filename = f"{safe_name}.png"
                primitives.append({
                    "type": "image",
                    "x": x, "y": y, "w": w, "h": h,
                    "filename": image_filename,
                })
                return
            primitives.append({
                "type": "rectangle",
                "x": x, "y": y, "w": w, "h": h,
                "bg_color": get_fill_color(elem),
                "radius": corner_radius,
                "stroke_color": get_stroke_color(elem),
            })
            return

    for elem in data:
        process_element(elem)

    # ── 后处理：调整被 Entry 遮挡的图片位置 ──
    for img in primitives:
        if img.get("type") != "image":
            continue
        ix, iy, iw, ih = img["x"], img["y"], img["w"], img["h"]
        for wi in widgets:
            if wi.get("widget_type") != "Entry":
                continue
            ex, ey, ew, eh = wi["x"], wi["y"], wi["w"], wi["h"]
            # 检测图片是否与 Entry 重叠
            if (ix + iw > ex and ix < ex + ew and
                    iy + ih > ey and iy < ey + eh):
                # 将图片移到 Entry 右侧
                img["x"] = ex + ew + 8
                break

    return widgets, primitives, widget_counter, button_list, button_borders


def compute_bounds(all_widgets, all_primitives, button_borders=None):
    """计算所有元素的边界框，返回 (min_x, min_y, max_x, max_y)"""
    all_elements = []
    for wi in all_widgets:
        all_elements.append((wi["x"], wi["y"], wi["w"], wi["h"]))
    for pi in all_primitives:
        pw = pi.get("w", 0)
        ph = pi.get("h", 0)
        all_elements.append((pi["x"], pi["y"], pw, ph))
    if button_borders:
        for bb in button_borders:
            all_elements.append((bb["x"], bb["y"], bb["w"], bb["h"]))

    min_x = min((e[0] for e in all_elements), default=0)
    min_y = min((e[1] for e in all_elements), default=0)
    max_x = max((e[0] + e[2] for e in all_elements), default=800)
    max_y = max((e[1] + e[3] for e in all_elements), default=600)
    return min_x, min_y, max_x, max_y


def adjust_coords(widgets, primitives, offset_x, offset_y, button_borders=None):
    """将所有元素的坐标减去偏移量"""
    for wi in widgets:
        wi["x"] -= offset_x
        wi["y"] -= offset_y
    for pi in primitives:
        pi["x"] -= offset_x
        pi["y"] -= offset_y
    if button_borders:
        for bb in button_borders:
            bb["x"] -= offset_x
            bb["y"] -= offset_y


def generate_canvas_primitives_code(primitives, lines, indent="    ",
                                     canvas_var="canvas"):
    """生成 Canvas 图元代码，返回 image_vars 列表"""
    image_primitives = [p for p in primitives if p["type"] == "image"]
    image_vars = []
    for idx, img in enumerate(image_primitives, 1):
        var_name = f"image_{idx}"
        image_vars.append(var_name)
        img["var_name"] = var_name

    if image_primitives:
        lines.append(f"{indent}if not HAS_PIL:\n")
        lines.append(f'{indent}    raise RuntimeError("Pillow (PIL) is required for image rendering. Install with: pip install Pillow")\n')
        lines.append("")
        for img in image_primitives:
            lines.append(f'{indent}{img["var_name"]} = ImageTk.PhotoImage(\n'
                         f'{indent}    Image.open(relative_to_assets("{img["filename"]}")).resize(({img["w"]}, {img["h"]}))\n'
                         f'{indent})\n')
        lines.append("")

    for pi in primitives:
        if pi["type"] == "rectangle":
            x1, y1 = pi["x"], pi["y"]
            x2, y2 = x1 + pi["w"], y1 + pi["h"]
            radius = pi.get("radius", 0)
            outline = f'"{pi["stroke_color"]}"' if pi.get("stroke_color") else '""'
            if radius > 0:
                lines.append(f'{indent}create_rounded_rectangle(\n'
                             f'{indent}    {canvas_var},\n'
                             f'{indent}    {x1}, {y1}, {x2}, {y2}, {radius},\n'
                             f'{indent}    fill="{pi["bg_color"]}", outline={outline})\n')
            else:
                lines.append(f'{indent}{canvas_var}.create_rectangle(\n'
                             f'{indent}    {x1}, {y1}, {x2}, {y2},\n'
                             f'{indent}    fill="{pi["bg_color"]}", outline={outline})\n')
        elif pi["type"] == "text":
            content = json.dumps(pi["content"], ensure_ascii=False)
            lines.append(f'{indent}{canvas_var}.create_text(\n'
                         f'{indent}    {pi["x"]},\n'
                         f'{indent}    {pi["y"]},\n'
                         f'{indent}    anchor="nw",\n'
                         f'{indent}    text={content},\n'
                         f'{indent}    fill="{pi["text_color"]}",\n'
                         f'{indent}    font=("{pi["font_family"]}", {pi["font_size"]} * -1, "{pi["font_weight"]}")\n'
                         f'{indent})\n')
        elif pi["type"] == "image":
            lines.append(f'{indent}{canvas_var}.create_image(\n'
                         f'{indent}    {pi["x"]} + {pi["w"]} / 2,\n'
                         f'{indent}    {pi["y"]} + {pi["h"]} / 2,\n'
                         f'{indent}    image={pi["var_name"]}\n'
                         f'{indent})\n'
                         f'{indent}{canvas_var}.{pi["var_name"]} = {pi["var_name"]}\n')

    return image_vars


def generate_button_borders_code(button_borders, lines, indent="    ",
                                canvas_var="canvas"):
    """为有圆角且有描边的 Button 生成边框层圆角矩形。

    边框矩形比 Button 大 2px（x-1, y-1, w+2, h+2），
    fill 与 Button 同色，outline 为描边色，形成边框视觉效果。
    Button widget 本身通过 place 叠在边框层上方。
    """
    if not button_borders:
        return

    lines.append(f"{indent}# ── Button 圆角边框层（位于 Button widget 下方）──\n")
    for bb in button_borders:
        vn = bb["var_name"]
        x1, y1 = bb["x"], bb["y"]
        x2, y2 = x1 + bb["w"], y1 + bb["h"]
        r = bb["corner_radius"]
        lines.append(f'{indent}# {vn} 边框层\n')
        lines.append(f'{indent}create_rounded_rectangle(\n'
                     f'{indent}    {canvas_var},\n'
                     f'{indent}    {x1}, {y1}, {x2}, {y2}, {r},\n'
                     f'{indent}    fill="{bb["bg_color"]}", outline="{bb["stroke_color"]}")\n')


def generate_widget_code(widgets, lines, parent_var="window", indent="    ",
                          skip_callbacks=False):
    """生成 Tkinter widget 代码。

    parent_var: widget 的父容器变量名
    skip_callbacks: 如果为 True，Button 等交互 widget 不生成 command 参数
    """
    for wi in widgets:
        wt = wi["widget_type"]
        vn = wi["var_name"]
        x, y = wi["x"], wi["y"]
        w, h = wi["w"], wi["h"]
        bg = wi["bg_color"]
        text = wi["text"]

        if wt == "Button":
            fg = wi.get("fg_color", "#FFFFFF")
            font_family = wi.get("font_family", "Inter")
            font_size = wi.get("font_size", 14)
            font_weight = wi.get("font_weight", "normal")
            cmd_part = ""
            if not skip_callbacks:
                cmd_part = f'\n{indent}    command={vn}_clicked,'
            lines.append(f'{indent}{vn} = Button(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    text={json.dumps(text, ensure_ascii=False)},\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    fg="{fg}",\n'
                         f'{indent}    font=("{font_family}", {font_size}, "{font_weight}"),\n'
                         f'{indent}    borderwidth=0,\n'
                         f'{indent}    highlightthickness=0,{cmd_part}\n'
                         f'{indent}    relief="flat",\n'
                         f'{indent}    activebackground="{bg}",\n'
                         f'{indent}    cursor="hand2"\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Label":
            fg = wi.get("fg_color", "#000000")
            font_family = wi.get("font_family", "Inter")
            font_size = wi.get("font_size", 14)
            font_weight = wi.get("font_weight", "normal")
            lines.append(f'{indent}{vn} = Label(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    text={json.dumps(text, ensure_ascii=False)},\n'
                         f'{indent}    fg="{fg}",\n'
                         f'{indent}    font=("{font_family}", {font_size}, "{font_weight}"),\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    borderwidth=0,\n'
                         f'{indent}    highlightthickness=0\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Entry":
            fg = wi.get("fg_color", "#000716")
            placeholder = text if text else ""
            lines.append(f'{indent}{vn} = Entry(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    bd=0,\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    fg="{fg}",\n'
                         f'{indent}    insertbackground="{fg}",\n'
                         f'{indent}    highlightthickness=0,\n'
                         f'{indent}    font=("Inter", 14)\n'
                         f'{indent})\n')
            if placeholder:
                lines.append(f'{indent}{vn}.insert(0, {json.dumps(placeholder, ensure_ascii=False)})\n')
                lines.append(f'{indent}{vn}.bind("<FocusIn>", lambda e: e.widget.delete(0, "end") if e.widget.get() == {json.dumps(placeholder, ensure_ascii=False)} else None)\n')
                lines.append(f'{indent}{vn}.bind("<FocusOut>", lambda e: e.widget.insert(0, {json.dumps(placeholder, ensure_ascii=False)}) if not e.widget.get() else None)\n')
            lines.append(f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Text":
            fg = wi.get("fg_color", "#000716")
            lines.append(f'{indent}{vn} = Text(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    bd=0,\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    fg="{fg}",\n'
                         f'{indent}    insertbackground="{fg}",\n'
                         f'{indent}    highlightthickness=0,\n'
                         f'{indent}    font=("Inter", 14)\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Checkbutton":
            var_holder = wi["var_holder"]
            lines.append(f'{indent}{var_holder} = BooleanVar(value=False)\n'
                         f'{indent}{vn} = Checkbutton(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    text={json.dumps(text, ensure_ascii=False)},\n'
                         f'{indent}    variable={var_holder},\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    activebackground="{bg}",\n'
                         f'{indent}    borderwidth=0,\n'
                         f'{indent}    highlightthickness=0,\n'
                         f'{indent}    command={vn}_clicked\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Radiobutton":
            var_holder = wi["var_holder"]
            lines.append(f'{indent}{var_holder} = StringVar(value="")\n'
                         f'{indent}{vn} = Radiobutton(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    text={json.dumps(text, ensure_ascii=False)},\n'
                         f'{indent}    variable={var_holder},\n'
                         f'{indent}    value="{vn}",\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    activebackground="{bg}",\n'
                         f'{indent}    borderwidth=0,\n'
                         f'{indent}    highlightthickness=0,\n'
                         f'{indent}    command={vn}_clicked\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Listbox":
            lines.append(f'{indent}{vn} = Listbox(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    borderwidth=0,\n'
                         f'{indent}    highlightthickness=0,\n'
                         f'{indent}    bg="{bg}"\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

        elif wt == "Canvas":
            lines.append(f'{indent}{vn} = Canvas(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    height={h},\n'
                         f'{indent}    width={w},\n'
                         f'{indent}    bd=0,\n'
                         f'{indent}    highlightthickness=0,\n'
                         f'{indent}    relief="ridge"\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y})\n')

        elif wt == "Treeview":
            columns = wi.get("columns", ["Column 1", "Column 2"])
            col_widths = wi.get("col_widths", [w // len(columns)] * len(columns))
            ROW_H = 30
            NUM_ROWS = 6
            SCROLL_W = 20

            # 生成列 ID（安全标识符）
            col_ids = []
            for col_name in columns:
                safe_name = re.sub(r'\W', '_', col_name.lower()).strip('_') or f"col_{len(col_ids)}"
                col_ids.append(safe_name)

            # ── ttk.Treeview 表格 ──
            vn_scroll = f"{vn}_scrollbar"
            lines.append(f'{indent}# ttk.Treeview 表格（{len(columns)} 列）\n')
            lines.append(f'{indent}style_{vn} = ttk.Style()\n')
            lines.append(f'{indent}style_{vn}.configure("Treeview", '
                         f'rowheight={ROW_H}, fieldbackground="#FFFFFF")\n')
            lines.append(f'{indent}{vn}_cols = {json.dumps(col_ids, ensure_ascii=False)}\n')
            lines.append(f'{indent}{vn} = ttk.Treeview(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    columns={vn}_cols,\n'
                         f'{indent}    show="headings",\n'
                         f'{indent}    height={max(1, h // ROW_H)}\n'
                         f'{indent})\n')

            # 配置列：居中 + 宽度
            for i, (col_name, col_id) in enumerate(zip(columns, col_ids)):
                lines.append(f'{indent}{vn}.heading("{col_id}", '
                             f'text={json.dumps(col_name, ensure_ascii=False)}, '
                             f'anchor="center")\n')
                lines.append(f'{indent}{vn}.column("{col_id}", '
                             f'width={col_widths[i]}, '
                             f'anchor="center")\n')

            # 斑马纹 tag
            lines.append(f'{indent}{vn}.tag_configure("oddrow", background="#FFFFFF")\n')
            lines.append(f'{indent}{vn}.tag_configure("evenrow", background="#F5F5F5")\n')

            # 6 行示例数据
            lines.append(f'{indent}# 插入示例数据（{NUM_ROWS} 行）\n')
            for row_idx in range(NUM_ROWS):
                row_values = []
                for col_name in columns:
                    if "选" in col_name:
                        val = ""
                    elif any(kw in col_name.lower() for kw in ("id", "uid", "编号")):
                        val = f"U{row_idx + 1001}"
                    elif any(kw in col_name for kw in ("昵称", "名称", "姓名")):
                        val = f"示例名称{row_idx + 1}"
                    else:
                        val = f"{col_name}{row_idx + 1}"
                    row_values.append(val)
                tag = "evenrow" if row_idx % 2 == 0 else "oddrow"
                lines.append(f'{indent}{vn}.insert("", "end", '
                             f'values={json.dumps(row_values, ensure_ascii=False)}, '
                             f'tags=("{tag}",))\n')

            # 垂直滚动条
            lines.append(f'{indent}{vn_scroll} = ttk.Scrollbar(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    orient="vertical",\n'
                         f'{indent}    command={vn}.yview\n'
                         f'{indent})\n')
            lines.append(f'{indent}{vn}.configure(yscrollcommand={vn_scroll}.set)\n')

            # 放置 Treeview + 滚动条
            lines.append(f'{indent}{vn}.place(x={x}, y={y}, width={w - SCROLL_W}, height={h})\n')
            lines.append(f'{indent}{vn_scroll}.place(x={x + w - SCROLL_W}, '
                         f'y={y}, width={SCROLL_W}, height={h})\n')

        elif wt == "Frame":
            lines.append(f'{indent}{vn} = Frame(\n'
                         f'{indent}    {parent_var},\n'
                         f'{indent}    bg="{bg}",\n'
                         f'{indent}    borderwidth=0,\n'
                         f'{indent}    highlightthickness=0\n'
                         f'{indent})\n'
                         f'{indent}{vn}.place(x={x}, y={y}, width={w}, height={h})\n')

    lines.append("")


def generate_single_page(data):
    """单文件模式：原有逻辑"""
    widgets, primitives, widget_counter, _, button_borders = process_json_data(data)

    # 计算边界
    min_x, min_y, max_x, max_y = compute_bounds(widgets, primitives, button_borders)
    window_width = int(max_x - min_x)
    window_height = int(max_y - min_y)

    adjust_coords(widgets, primitives, min_x, min_y, button_borders)

    # 代码生成
    lines = _build_header()

    # 回调函数
    has_callbacks = any(wi["widget_type"] in INTERACTIVE_WIDGETS for wi in widgets)
    if has_callbacks:
        lines.append("# ── Widget 回调函数 ──\n")
        for wi in widgets:
            if wi["widget_type"] in INTERACTIVE_WIDGETS:
                btn_text = wi.get("text", "")
                var_name = wi["var_name"]
                if btn_text and ("选择路径" in btn_text or "选择文件" in btn_text):
                    lines.append(f'def {var_name}_clicked():\n'
                                 f'    path = filedialog.askdirectory(title="选择保存路径")\n'
                                 f'    if path:\n'
                                 f'        print(f"Selected: {{path}}")\n')
                else:
                    lines.append(f'def {var_name}_clicked():\n'
                                 f'    print("{var_name} clicked")\n')

        lines.append("")

    # 文本获取函数
    has_text_inputs = any(wi["widget_type"] in TEXT_INPUT_WIDGETS for wi in widgets)
    if has_text_inputs:
        lines.append("# ── 文本获取方法 ──\n")
        for wi in widgets:
            if wi["widget_type"] in TEXT_INPUT_WIDGETS:
                var_name = wi["var_name"]
                lines.append(f'def get_{var_name}_text():\n'
                             f'    return {var_name}.get("1.0", "end-1c") if isinstance({var_name}, Text) else {var_name}.get()\n')
        lines.append("")

    # 主窗口
    # 自动生成 global 声明，避免模块级回调引用 widget 变量时报 NameError
    widget_var_names = [wi["var_name"] for wi in widgets]
    if "canvas" not in widget_var_names:
        widget_var_names.append("canvas")
    global_decl = f'    global {", ".join(widget_var_names)}\n' if widget_var_names else ''
    lines.append(f'\ndef create_main_window():\n'
                 f'{global_decl}'
                 f'    window = Tk()\n'
                 f'    window.title("JSON Generated GUI")\n'
                 f'    window.geometry("{window_width}x{window_height}")\n'
                 f'    window.configure(bg="#FFFFFF")\n'
                 f'    center_window(window, {window_width}, {window_height})\n'
                 f'\n'
                 f'    canvas = Canvas(\n'
                 f'        window,\n'
                 f'        bg="#FFFFFF",\n'
                 f'        height={window_height},\n'
                 f'        width={window_width},\n'
                 f'        bd=0,\n'
                 f'        highlightthickness=0,\n'
                 f'        relief="ridge"\n'
                 f'    )\n'
                 f'    canvas.place(x=0, y=0)\n\n')

    # Canvas 图元
    lines.append("    # ── Canvas 图元 ──\n")
    generate_canvas_primitives_code(primitives, lines)

    # Button 圆角边框层
    generate_button_borders_code(button_borders, lines)

    # Tkinter Widgets
    if widgets:
        lines.append("    # ── Tkinter Widget ──\n")
    generate_widget_code(widgets, lines)

    lines.append('    window.resizable(False, False)\n'
                 '    return window\n\n\n'
                 'window = create_main_window()\n\n'
                 'if __name__ == "__main__":\n'
                 '    window.mainloop()\n')

    code = "\n".join(lines)

    # 输出
    output_dir = Path(__file__).parent / "gui" / "build"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_path = output_dir / "assets" / "frame0"
    assets_path.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "gui.py"
    with open(str(output_file), 'w', encoding='utf-8') as f:
        f.write(code)

    image_primitives = [p for p in primitives if p["type"] == "image"]
    print(f"GUI generated at: {output_file}")
    print(f"Window: {window_width}x{window_height} | "
          f"Widgets: {len(widgets)} | "
          f"Button Borders: {len(button_borders)} | "
          f"Primitives: {len(primitives)} | "
          f"Images: {len(image_primitives)}")
    if widgets:
        for wi in widgets:
            print(f"  {wi['widget_type']}: {wi['var_name']} "
                  f"(text={wi['text'][:20]!r}, pos=({wi['x']}, {wi['y']}), "
                  f"size={wi['w']}x{wi['h']})")


def generate_multi_page(all_data):
    """多文件模式：第一个 JSON = 侧边栏，后续 = 内容页面"""
    sidebar_data = all_data[0]
    page_datas = all_data[1:]

    # ── 处理侧边栏 ──
    sb_widgets, sb_primitives, widget_counter, sb_buttons, sb_button_borders = \
        process_json_data(sidebar_data, track_buttons=True)

    # ── 处理页面 ──
    pages_widgets = []
    pages_primitives = []
    pages_button_borders = []
    pages_root_info = []

    for page_data in page_datas:
        root = page_data[0] if page_data else {}
        root_w = root.get("width", 0)
        root_h = root.get("height", 0)
        pages_root_info.append((root_w, root_h))

        pw, pp, widget_counter, _, page_bb = process_json_data(
            page_data, widget_counter=widget_counter)
        pages_widgets.append(pw)
        pages_primitives.append(pp)
        pages_button_borders.append(page_bb)

    # ── 计算侧边栏宽度 ──
    sb_min_x, sb_min_y, sb_max_x, sb_max_y = compute_bounds(sb_widgets, sb_primitives, sb_button_borders)
    sidebar_width = sb_max_x - sb_min_x

    # ── 调整侧边栏坐标（以 min_x, min_y 为原点） ──
    adjust_coords(sb_widgets, sb_primitives, sb_min_x, sb_min_y, sb_button_borders)

    # ── 调整页面坐标：减去页面根节点的 x/y，得到相对于 page_frame 内部的坐标 ──
    for i, (pw, pp, page_bb) in enumerate(zip(pages_widgets, pages_primitives, pages_button_borders)):
        page_data = page_datas[i]
        root = page_data[0] if page_data else {}
        root_x = root.get("x", 0)
        root_y = root.get("y", 0)
        adjust_coords(pw, pp, root_x, root_y, page_bb)

    # 侧边栏 primitives 渲染在主 Canvas；页面 primitives 在各 page_frame 内 Canvas 渲染
    all_primitives_combined = sb_primitives[:]

    # ── 计算窗口尺寸 ──
    all_widgets_combined = sb_widgets[:]
    all_button_borders_combined = sb_button_borders[:]
    for pw, pbb in zip(pages_widgets, pages_button_borders):
        all_widgets_combined.extend(pw)
        all_button_borders_combined.extend(pbb)

    _, _, max_x_global, _ = compute_bounds(all_widgets_combined, all_primitives_combined,
                                            all_button_borders_combined)
    # 侧边栏 + 最大页面宽度
    max_page_width = max((rw for rw, _ in pages_root_info), default=796)
    window_width = sidebar_width + max_page_width

    sb_actual_max = sb_max_y - sb_min_y
    window_height = max(sb_actual_max,
                        max((rh for _, rh in pages_root_info), default=600))

    # 处理侧边栏按钮与页面的映射
    num_pages = len(page_datas)
    page_button_map = {}
    for btn_idx, btn in enumerate(sb_buttons):
        if btn_idx < num_pages:
            page_button_map[btn["var_name"]] = btn_idx

    # ── 代码生成 ──
    lines = _build_header()

    # 页面切换函数 — 使用模块级 pages 列表避免作用域问题
    if num_pages > 1:
        lines.append("# ── 页面切换 ──\n")
        lines.append("# pages 列表在 create_main_window() 中填充\n")
        lines.append("pages = []\n")
        lines.append("\n")
        lines.append("def show_page(index):\n")
        lines.append('    """切换显示的内容页面"""\n')
        lines.append("    for i, page in enumerate(pages):\n")
        lines.append("        if i == index:\n")
        lines.append(f"            page.place(x={sidebar_width}, y=0, "
                     f"width={max_page_width}, height={window_height})\n")
        lines.append("        else:\n")
        lines.append("            page.place_forget()\n")
        lines.append("")

    # 非侧边栏按钮的回调函数
    all_page_widgets_flat = []
    for pw in pages_widgets:
        all_page_widgets_flat.extend(pw)
    all_page_button_borders_flat = []
    for pbb in pages_button_borders:
        all_page_button_borders_flat.extend(pbb)

    has_other_callbacks = any(
        wi["widget_type"] in INTERACTIVE_WIDGETS
        for wi in all_page_widgets_flat
        if wi["var_name"] not in page_button_map
    )
    if has_other_callbacks:
        lines.append("# ── Widget 回调函数 ──\n")
        for wi in all_page_widgets_flat:
            if wi["widget_type"] in INTERACTIVE_WIDGETS and wi["var_name"] not in page_button_map:
                btn_text = wi.get("text", "")
                var_name = wi["var_name"]
                if btn_text and ("选择路径" in btn_text or "选择文件" in btn_text):
                    lines.append(f'def {var_name}_clicked():\n'
                                 f'    path = filedialog.askdirectory(title="选择保存路径")\n'
                                 f'    if path:\n'
                                 f'        print(f"Selected: {{path}}")\n')
                else:
                    lines.append(f'def {var_name}_clicked():\n'
                                 f'    print("{var_name} clicked")\n')

        lines.append("")

    # 文本获取函数
    has_text_inputs = any(
        wi["widget_type"] in TEXT_INPUT_WIDGETS for wi in all_page_widgets_flat)
    if has_text_inputs:
        lines.append("# ── 文本获取方法 ──\n")
        for wi in all_page_widgets_flat:
            if wi["widget_type"] in TEXT_INPUT_WIDGETS:
                var_name = wi["var_name"]
                lines.append(f'def get_{var_name}_text():\n'
                             f'    return {var_name}.get("1.0", "end-1c") '
                             f'if isinstance({var_name}, Text) else {var_name}.get()\n')
        lines.append("")

    # 窗口标题（从侧边栏提取）
    title_text = "JSON Generated GUI"
    for wi in sb_widgets:
        if wi["widget_type"] == "Label" and wi["text"]:
            title_text = f"{wi['text']} - JSON Generated GUI"
            break

    # 主窗口创建
    # 自动生成 global 声明，避免模块级回调引用 widget 变量时报 NameError
    all_widget_var_names = []
    for wl in [sb_widgets] + pages_widgets:
        for w in wl:
            all_widget_var_names.append(w["var_name"])
    if "canvas" not in all_widget_var_names:
        all_widget_var_names.append("canvas")
    global_decl = f'    global {", ".join(all_widget_var_names)}\n' if all_widget_var_names else ''
    lines.append(f'\ndef create_main_window():\n'
                 f'{global_decl}'
                 f'    window = Tk()\n'
                 f'    window.title({json.dumps(title_text, ensure_ascii=False)})\n'
                 f'    window.geometry("{window_width}x{window_height}")\n'
                 f'    window.configure(bg="#FFFFFF")\n'
                 f'    center_window(window, {window_width}, {window_height})\n'
                 f'\n'
                 f'    canvas = Canvas(\n'
                 f'        window,\n'
                 f'        bg="#FFFFFF",\n'
                 f'        height={window_height},\n'
                 f'        width={window_width},\n'
                 f'        bd=0,\n'
                 f'        highlightthickness=0,\n'
                 f'        relief="ridge"\n'
                 f'    )\n'
                 f'    canvas.place(x=0, y=0)\n\n')

    # ── Canvas 图元（所有 JSON 的图元合并到主 Canvas） ──
    lines.append("    # ── Canvas 图元 ──\n")
    generate_canvas_primitives_code(all_primitives_combined, lines)

    # ── 侧边栏 Widget ──
    if sb_widgets:
        lines.append("    # ── 侧边栏 Widget ──\n")
    for wi in sb_widgets:
        vn = wi["var_name"]
        wt = wi["widget_type"]

        # 侧边栏按钮：如果是页面切换按钮，使用 show_page 回调
        if vn in page_button_map:
            page_idx = page_button_map[vn]
            # 单独生成带 lambda 的 Button
            x, y, w, h = wi["x"], wi["y"], wi["w"], wi["h"]
            bg = wi["bg_color"]
            text = wi["text"]
            fg = wi.get("fg_color", "#FFFFFF")
            font_family = wi.get("font_family", "Inter")
            font_size = wi.get("font_size", 14)
            font_weight = wi.get("font_weight", "normal")
            lines.append(f'    {vn} = Button(\n'
                         f'        window,\n'
                         f'        text={json.dumps(text, ensure_ascii=False)},\n'
                         f'        bg="{bg}",\n'
                         f'        fg="{fg}",\n'
                         f'        font=("{font_family}", {font_size}, "{font_weight}"),\n'
                         f'        borderwidth=0,\n'
                         f'        highlightthickness=0,\n'
                         f'        command=lambda: show_page({page_idx}),\n'
                         f'        relief="flat",\n'
                         f'        activebackground="{bg}",\n'
                         f'        cursor="hand2"\n'
                         f'    )\n'
                         f'    {vn}.place(x={x}, y={y}, width={w}, height={h})\n')
        else:
            # 正常生成
            generate_widget_code([wi], lines, parent_var="window",
                                 skip_callbacks=False)
    # ── 侧边栏 Button 圆角边框层 ──
    generate_button_borders_code(sb_button_borders, lines)


    # ── 页面 Frame + Canvas + Widget ──
    for page_idx, (pw, pp, page_bb, (root_w, root_h)) in enumerate(
            zip(pages_widgets, pages_primitives, pages_button_borders, pages_root_info)):
        pf_name = f"page_frame_{page_idx + 1}"
        pc_name = f"canvas_page_{page_idx + 1}"
        lines.append(f"    # ── 页面 {page_idx + 1} ──\n")
        lines.append(f'    {pf_name} = Frame(\n'
                     f'        window,\n'
                     f'        bg="#FFFFFF",\n'
                     f'        borderwidth=0,\n'
                     f'        highlightthickness=0\n'
                     f'    )\n')
        if page_idx == 0:
            lines.append(f'    {pf_name}.place(x={sidebar_width}, y=0, '
                         f'width={max_page_width}, height={window_height})\n')
        else:
            lines.append(f'    # {pf_name} 默认隐藏，通过 show_page({page_idx}) 显示\n')
        lines.append(f'    pages.append({pf_name})\n')

        # Per-page Canvas（承载该页面的所有图元）
        lines.append(f'    {pc_name} = Canvas(\n'
                     f'        {pf_name},\n'
                     f'        bg="#FFFFFF",\n'
                     f'        height={window_height},\n'
                     f'        width={max_page_width},\n'
                     f'        bd=0,\n'
                     f'        highlightthickness=0,\n'
                     f'        relief="ridge"\n'
                     f'    )\n'
                     f'    {pc_name}.place(x=0, y=0)\n')

        if pp:
            generate_canvas_primitives_code(pp, lines, canvas_var=pc_name)

        if page_bb:
            generate_button_borders_code(page_bb, lines, canvas_var=pc_name)

        if pw:
            generate_widget_code(pw, lines, parent_var=pf_name,
                                 skip_callbacks=False)

    lines.append('    window.resizable(False, False)\n'
                 '    return window\n\n\n'
                 'window = create_main_window()\n\n'
                 'if __name__ == "__main__":\n'
                 '    window.mainloop()\n')

    code = "\n".join(lines)

    # ── 输出 ──
    output_dir = Path(__file__).parent / "gui" / "build"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_path = output_dir / "assets" / "frame0"
    assets_path.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "gui.py"
    with open(str(output_file), 'w', encoding='utf-8') as f:
        f.write(code)

    total_image_primitives = sum(
        1 for p in all_primitives_combined if p["type"] == "image")

    print(f"GUI generated at: {output_file}")
    print(f"Window: {window_width}x{window_height}")
    print(f"Sidebar: {sidebar_width}px | Pages: {num_pages} | Button Borders: {len(all_button_borders_combined)}")
    print(f"Widgets: {len(sb_widgets) + sum(len(pw) for pw in pages_widgets)} "
          f"| Primitives: {len(all_primitives_combined)} "
          f"| Images: {total_image_primitives}")
    print(f"\nSidebar buttons → page mapping:")
    for btn_var, page_idx in page_button_map.items():
        print(f"  {btn_var} → show_page({page_idx})")

    print(f"\nSidebar widgets:")
    for wi in sb_widgets:
        marker = " [PAGE_SWITCH]" if wi["var_name"] in page_button_map else ""
        print(f"  {wi['widget_type']}: {wi['var_name']} "
              f"(text={wi['text'][:30]!r}, pos=({wi['x']}, {wi['y']})){marker}")
    for i, pw in enumerate(pages_widgets):
        print(f"\nPage {i + 1} widgets:")
        for wi in pw:
            print(f"  {wi['widget_type']}: {wi['var_name']} "
                  f"(text={wi['text'][:30]!r}, pos=({wi['x']}, {wi['y']}))")


def _build_header():
    """构建生成文件头部（导入、工具函数）"""
    return [
        f'# -*- coding: utf-8 -*-\n'
        f'# Generated by Fixed Generator on {datetime.now().isoformat()}\n'
        f'# 基于 Tkinter-Designer widget 映射逻辑\n'
        f'\n'
        f'import sys\n'
        f'from pathlib import Path\n'
        f'from tkinter import (\n'
        f'    BooleanVar,\n'
        f'    Button,\n'
        f'    Canvas,\n'
        f'    Checkbutton,\n'
        f'    Entry,\n'
        f'    filedialog,\n'
        f'    Frame,\n'
        f'    Label,\n'
        f'    Listbox,\n'
        f'    PhotoImage,\n'
        f'    Radiobutton,\n'
        f'    StringVar,\n'
        f'    Text,\n'
        f'    Tk,\n'
        f'    ttk,\n'
        f')\n'
        f'\n'
        f'try:\n'
        f'    from PIL import Image, ImageTk\n'
        f'    HAS_PIL = True\n'
        f'except ImportError:\n'
        f'    HAS_PIL = False\n'
        f'\n'
        f'if getattr(sys, \'frozen\', False):\n'
        f'    OUTPUT_PATH = Path(sys._MEIPASS)\n'
        f'    ASSETS_PATH = OUTPUT_PATH / "gui" / "build" / "assets" / "frame0"\n'
        f'else:\n'
        f'    OUTPUT_PATH = Path(__file__).parent\n'
        f'    ASSETS_PATH = OUTPUT_PATH / "assets" / "frame0"\n'
        f'\n'
        f'\n'
        f'def relative_to_assets(path: str) -> Path:\n'
        f'    return ASSETS_PATH / Path(path)\n'
        f'\n'
        f'\n'
        f'def center_window(window, width, height):\n'
        f'    window.update_idletasks()\n'
        f'    x = int((window.winfo_screenwidth() - width) / 2)\n'
        f'    y = int((window.winfo_screenheight() - height) / 2)\n'
        f'    window.geometry(f"{{width}}x{{height}}+{{x}}+{{y}}")\n'
        f'\n'
        f'\n'
        f'def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):\n'
        f'    radius = max(0, min(radius, abs(x2 - x1) / 2, abs(y2 - y1) / 2))\n'
        f'    if radius == 0:\n'
        f'        return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)\n'
        f'    points = [\n'
        f'        x1 + radius, y1,\n'
        f'        x2 - radius, y1,\n'
        f'        x2, y1,\n'
        f'        x2, y1 + radius,\n'
        f'        x2, y2 - radius,\n'
        f'        x2, y2,\n'
        f'        x2 - radius, y2,\n'
        f'        x1 + radius, y2,\n'
        f'        x1, y2,\n'
        f'        x1, y2 - radius,\n'
        f'        x1, y1 + radius,\n'
        f'        x1, y1,\n'
        f'    ]\n'
        f'    return canvas.create_polygon(points, smooth=True, **kwargs)\n'
        f'\n'
        f'\n',
    ]


def main():
    # ── 解析命令行参数 ──
    base_dir = Path(__file__).parent / "gui" / "layouts"

    if len(sys.argv) > 1:
        json_files = []
        for f in sys.argv[1:]:
            p = Path(f)
            if p.is_absolute():
                json_files.append(str(p))
            else:
                json_files.append(str(base_dir / f))
    else:
        # 默认单文件
        json_files = [str(base_dir / "new.json")]

    # ── 加载 JSON ──
    all_data = []
    for jf in json_files:
        if not Path(jf).exists():
            print(f"ERROR: File not found: {jf}")
            sys.exit(1)
        with open(jf, 'r', encoding='utf-8') as f:
            all_data.append(json.load(f))

    print(f"Loaded {len(all_data)} JSON file(s):")
    for i, (jf, data) in enumerate(zip(json_files, all_data)):
        root = data[0] if data else {}
        print(f"  [{i}] {Path(jf).name} → "
              f"root: '{root.get('name', '?')}' "
              f"({root.get('type', '?')}, "
              f"{root.get('width', 0)}x{root.get('height', 0)})")

    # ── 调度 ──
    if len(all_data) == 1:
        print("\n▶ Single-page mode")
        generate_single_page(all_data[0])
    else:
        print(f"\n▶ Multi-page mode: 1 sidebar + {len(all_data) - 1} page(s)")
        generate_multi_page(all_data)


if __name__ == "__main__":
    main()
