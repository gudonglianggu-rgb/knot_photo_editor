# -*- coding: utf-8 -*-
"""
结绳 · 图修 P图软件
功能：打开照片 -> 框选区域 -> 识别文字/字体 -> 原文字框 + 空白框修改
打包命令: buildozer android debug
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import pytesseract

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.core.text import LabelBase

# 注册中文字体
try:
    LabelBase.register(name='CJK', fn_regular='/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc')
except:
    pass

Builder.load_string('''
<PhotoEditor>:
    canvas.before:
        Color:
            rgba: 0.1, 0.1, 0.18, 1
        Rectangle:
            pos: self.pos
            size: self.size
    
    BoxLayout:
        orientation: 'vertical'
        spacing: '2dp'
        padding: '8dp'
        
        # 顶部标题栏
        BoxLayout:
            size_hint_y: 0.07
            spacing: '8dp'
            padding: ['4dp', '2dp']
            
            Button:
                text: '📁 打开'
                font_size: '14sp'
                background_normal: ''
                background_color: 0.06, 0.35, 0.65, 1
                color: 1, 1, 1, 1
                on_release: root.open_file()
            
            Label:
                text: '🪢 结绳 · 图修'
                font_size: '18sp'
                bold: True
                color: 0.91, 0.27, 0.38, 1
                size_hint_x: 0.6
            
            Button:
                text: '💾 保存'
                font_size: '14sp'
                background_normal: ''
                background_color: 0.91, 0.27, 0.38, 1
                color: 1, 1, 1, 1
                on_release: root.save_image()
        
        # 图片显示区 + 右面板
        BoxLayout:
            size_hint_y: 0.5
            spacing: '4dp'
            
            # 左侧图片区
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.7
                spacing: '2dp'
                
                RelativeLayout:
                    id: image_container
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.15, 0.25, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    Image:
                        id: main_image
                        keep_ratio: True
                        allow_stretch: True
                        size_hint: 1, 1
                        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
                    
                    Widget:
                        id: selection_overlay
                
                BoxLayout:
                    size_hint_y: 0.1
                    spacing: '4dp'
                    Button:
                        text: '🔍-'
                        font_size: '12sp'
                        size_hint_x: 0.15
                        background_normal: ''
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_release: root.zoom_out()
                    Slider:
                        id: zoom_slider
                        min: 0.5
                        max: 3.0
                        value: 1.0
                        step: 0.1
                        on_value: root.on_zoom(self.value)
                    Button:
                        text: '🔍+'
                        font_size: '12sp'
                        size_hint_x: 0.15
                        background_normal: ''
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_release: root.zoom_in()
            
            # 右侧操作面板
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.3
                spacing: '2dp'
                
                BoxLayout:
                    size_hint_y: 0.15
                    spacing: '2dp'
                    ToggleButton:
                        id: sel_toggle
                        text: '🔲 选区'
                        font_size: '11sp'
                        group: 'tools'
                        state: 'normal'
                        background_normal: ''
                        background_down: ''
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_release: root.toggle_selection(self.state)
                    Button:
                        text: '✂️ 裁剪'
                        font_size: '11sp'
                        background_normal: ''
                        background_color: 0.06, 0.35, 0.65, 1
                        color: 1, 1, 1, 1
                        on_release: root.crop_selection()
                
                BoxLayout:
                    size_hint_y: 0.15
                    spacing: '2dp'
                    Button:
                        text: '🔍 OCR'
                        font_size: '11sp'
                        background_normal: ''
                        background_color: 0.06, 0.35, 0.65, 1
                        color: 1, 1, 1, 1
                        on_release: root.run_ocr()
                    Button:
                        text: '🅰️ 字体'
                        font_size: '11sp'
                        background_normal: ''
                        background_color: 0.06, 0.35, 0.65, 1
                        color: 1, 1, 1, 1
                        on_release: root.identify_font()
        
        # 文字编辑区
        BoxLayout:
            size_hint_y: 0.15
            spacing: '4dp'
            padding: ['4dp', '2dp']
            
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.5
                spacing: '2dp'
                Label:
                    text: '📝 原文字框'
                    font_size: '11sp'
                    bold: True
                    color: 0.91, 0.27, 0.38, 1
                    size_hint_y: 0.2
                TextInput:
                    id: original_text
                    text: ''
                    font_size: '13sp'
                    readonly: True
                    background_color: 0.08, 0.08, 0.15, 1
                    foreground_color: 0.8, 0.8, 0.8, 1
                    size_hint_y: 0.8
                    multiline: True
            
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.5
                spacing: '2dp'
                Label:
                    text: '✏️ 修改文字框'
                    font_size: '11sp'
                    bold: True
                    color: 0.06, 0.35, 0.65, 1
                    size_hint_y: 0.2
                TextInput:
                    id: edit_text
                    text: ''
                    font_size: '13sp'
                    hint_text: '输入要替换的文字...'
                    background_color: 0.08, 0.08, 0.15, 1
                    foreground_color: 1, 1, 1, 1
                    cursor_color: 0.91, 0.27, 0.38, 1
                    size_hint_y: 0.8
                    multiline: True
        
        # 字体样式 + 操作
        BoxLayout:
            size_hint_y: 0.13
            spacing: '2dp'
            padding: ['4dp', '2dp']
            
            ScrollView:
                do_scroll_x: True
                do_scroll_y: False
                size_hint_x: 0.7
                GridLayout:
                    rows: 2
                    cols: 4
                    spacing: '2dp'
                    size_hint_x: None
                    width: self.minimum_width
                    Button:
                        text: '🅰️ 粗'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '60dp'
                        background_normal: ''
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_release: root.toggle_bold()
                    Button:
                        text: '🅸 斜'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '60dp'
                        background_normal: ''
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_release: root.toggle_italic()
                    Spinner:
                        id: font_spinner
                        text: '字体'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '80dp'
                        values: ['默认', '黑体', '宋体', '楷体', 'Arial', 'Times']
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_text: root.set_font(self.text)
                    Spinner:
                        id: size_spinner
                        text: '字号'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '60dp'
                        values: ['12','16','20','24','28','32','36','42','48']
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_text: root.set_font_size(self.text)
                    Button:
                        text: '⬛ 颜色'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '60dp'
                        background_normal: ''
                        background_color: 0.2, 0.2, 0.3, 1
                        color: 1, 1, 1, 1
                        on_release: root.show_color_picker()
                    Button:
                        text: '▶ 替换'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '80dp'
                        background_normal: ''
                        background_color: 0.91, 0.27, 0.38, 1
                        color: 1, 1, 1, 1
                        on_release: root.replace_text_on_image()
                    Button:
                        text: '🔄 重置'
                        font_size: '10sp'
                        size_hint_x: None
                        width: '60dp'
                        background_normal: ''
                        background_color: 0.3, 0.3, 0.4, 1
                        color: 1, 1, 1, 1
                        on_release: root.reset_image()
        
        Label:
            id: status_label
            text: '🪢 结绳 · 图修 v1.0 | 请打开一张图片'
            font_size: '10sp'
            color: 0.5, 0.6, 0.7, 1
            size_hint_y: 0.05
            halign: 'center'
''')

class PhotoEditor(BoxLayout):
    """结绳P图工具主逻辑类"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_path = None
        self.original_pil = None
        self.current_pil = None
        self.display_pil = None
        
        # 选区
        self.selection_active = False
        self.selection_start = None
        self.selection_rect = None
        
        # 字体样式
        self.font_bold = False
        self.font_italic = False
        self.font_name = '默认'
        self.font_size = 24
        self.font_color = (255, 255, 255, 255)
        
        # 缩放
        self.zoom_level = 1.0
        
        # 绑定触摸事件
        self.ids.selection_overlay.bind(
            on_touch_down=self.on_selection_down,
            on_touch_move=self.on_selection_move,
            on_touch_up=self.on_selection_up
        )
        
        Clock.schedule_once(lambda dt: self.update_status('🪢 结绳 · 图修 v1.0 | 请打开一张图片'), 0.1)
    
    def update_status(self, msg):
        self.ids.status_label.text = msg
    
    # ========= 文件操作 =========
    def open_file(self):
        content = BoxLayout(orientation='vertical', spacing=10)
        fc = FileChooserIconView(path='/sdcard', filters=['*.png','*.jpg','*.jpeg','*.bmp','*.webp'])
        content.add_widget(fc)
        bx = BoxLayout(size_hint_y=0.2, spacing=10)
        btn_cancel = Button(text='取消', background_normal='', background_color=(0.3,0.3,0.4,1))
        btn_open = Button(text='打开', background_normal='', background_color=(0.91,0.27,0.38,1))
        popup = Popup(title='📁 选择图片', content=content, size_hint=(0.9,0.8),
                      background='', background_color=(0.1,0.1,0.18,1))
        def on_open(btn):
            if fc.selection:
                self.load_image(fc.selection[0])
                popup.dismiss()
        def on_cancel(btn):
            popup.dismiss()
        btn_open.bind(on_press=on_open)
        btn_cancel.bind(on_press=on_cancel)
        bx.add_widget(btn_cancel)
        bx.add_widget(btn_open)
        content.add_widget(bx)
        popup.open()
    
    def load_image(self, path):
        try:
            self.image_path = path
            self.original_pil = Image.open(path).convert('RGB')
            self.current_pil = self.original_pil.copy()
            self.selection_rect = None
            self.zoom_level = 1.0
            self.ids.zoom_slider.value = 1.0
            self.display_image()
            self.update_status(f'✅ 已加载: {os.path.basename(path)} ({self.original_pil.size[0]}\\u00d7{self.original_pil.size[1]})')
        except Exception as e:
            self.update_status(f'❌ 加载失败: {str(e)}')
    
    def display_image(self):
        if self.current_pil is None:
            return
        img = self.current_pil.copy()
        if self.selection_rect:
            draw = ImageDraw.Draw(img)
            x1,y1,x2,y2 = self.selection_rect
            draw.rectangle([x1,y1,x2,y2], outline=(233,69,96), width=3)
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            od.rectangle([x1,y1,x2,y2], fill=(233,69,96,30))
            img = Image.alpha_composite(img.convert('RGBA'), overlay)
        self.display_pil = img
        img_rgba = img.convert('RGBA') if img.mode != 'RGBA' else img
        zw, zh = int(img_rgba.size[0]*self.zoom_level), int(img_rgba.size[1]*self.zoom_level)
        img_resized = img_rgba.resize((zw, zh), Image.LANCZOS)
        data = img_resized.tobytes()
        texture = Texture.create(size=(zw, zh), colorfmt='rgba')
        texture.blit_buffer(data, colorfmt='rgba', bufferfmt='ubyte')
        texture.flip_vertical()
        self.ids.main_image.texture = texture
    
    def save_image(self):
        if self.current_pil is None:
            self.update_status('❌ 没有图片可保存')
            return
        from datetime import datetime
        fn = f'结绳图修_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        paths = [
            os.path.join('/sdcard/DCIM', fn),
            os.path.join('/sdcard/Pictures', fn),
            os.path.join('/sdcard/Download', fn),
        ]
        saved = False
        for p in paths:
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                self.current_pil.save(p, 'PNG')
                saved = True
                self.update_status(f'💾 已保存: {p}')
                break
            except:
                continue
        if not saved:
            try:
                self.current_pil.save(fn, 'PNG')
                self.update_status(f'💾 已保存: {fn}')
            except:
                self.update_status('❌ 保存失败')
    
    # ========= 选区 =========
    def toggle_selection(self, state):
        self.selection_active = (state == 'down')
        if self.selection_active:
            self.update_status('🔲 选区模式: 在图片上拖拽框选')
        else:
            self.selection_rect = None
            self.display_image()
            self.update_status('已退出选区模式')
    
    def _img_coords(self, touch):
        """触摸坐标转图片坐标"""
        iw = self.ids.main_image
        if not iw.texture:
            return None
        x, y = touch.pos
        ix, iy = iw.x, iw.y
        iw2, ih2 = iw.width, iw.height
        if ix <= x <= ix+iw2 and iy <= y <= iy+ih2:
            rx = (x - ix) / iw2
            ry = 1 - (y - iy) / ih2
            pw, ph = self.current_pil.size
            return (int(rx * pw), int(ry * ph))
        return None
    
    def on_selection_down(self, widget, touch):
        if not self.selection_active or self.current_pil is None:
            return False
        c = self._img_coords(touch)
        if c:
            self.selection_start = c
            return True
        return False
    
    def on_selection_move(self, widget, touch):
        if not self.selection_active or not self.selection_start:
            return False
        c = self._img_coords(touch)
        if c:
            pw, ph = self.current_pil.size
            sx, sy = self.selection_start
            x1 = max(0, min(sx, c[0]))
            y1 = max(0, min(sy, c[1]))
            x2 = min(pw-1, max(sx, c[0]))
            y2 = min(ph-1, max(sy, c[1]))
            self.selection_rect = (x1,y1,x2,y2)
            self.display_image()
            return True
        return False
    
    def on_selection_up(self, widget, touch):
        if self.selection_active and self.selection_rect:
            x1,y1,x2,y2 = self.selection_rect
            if (x2-x1) > 5 and (y2-y1) > 5:
                self.update_status(f'✅ 选区: ({x1},{y1})-({x2},{y2})  {x2-x1}\\u00d7{y2-y1}')
            else:
                self.selection_rect = None
                self.display_image()
                self.update_status('选区太小已取消')
        self.selection_start = None
    
    def crop_selection(self):
        if self.current_pil is None:
            self.update_status('❌ 请先打开图片'); return
        if not self.selection_rect:
            self.update_status('❌ 请先框选区域'); return
        x1,y1,x2,y2 = self.selection_rect
        if (x2-x1) < 5 or (y2-y1) < 5:
            self.update_status('❌ 选区太小'); return
        cr = self.current_pil.crop((x1,y1,x2,y2))
        self.current_pil = cr
        self.selection_rect = None
        self.display_image()
        self.update_status(f'✂️ 已裁剪: {cr.size[0]}\\u00d7{cr.size[1]}')
    
    # ========= OCR =========
    def run_ocr(self):
        if self.current_pil is None:
            self.update_status('❌ 请先打开图片'); return
        if self.selection_rect:
            x1,y1,x2,y2 = self.selection_rect
            roi = self.current_pil.crop((x1,y1,x2,y2))
        else:
            roi = self.current_pil
        try:
            text = pytesseract.image_to_string(roi, lang='chi_sim+eng')
            text = text.strip()
            if text:
                self.ids.original_text.text = text
                self.ids.edit_text.text = text
                self.update_status(f'🔍 OCR完成 | {len(text)}字符')
            else:
                self.ids.original_text.text = '(未识别到文字)'
                self.update_status('⚠️ 未识别到文字')
        except Exception as e:
            self.update_status(f'❌ OCR失败: {str(e)}')
    
    # ========= 字体识别 =========
    def identify_font(self):
        if self.current_pil is None:
            self.update_status('❌ 请先打开图片'); return
        if self.selection_rect:
            x1,y1,x2,y2 = self.selection_rect
            roi = self.current_pil.crop((x1,y1,x2,y2))
        else:
            roi = self.current_pil
        try:
            img_cv = cv2.cvtColor(np.array(roi), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
            h,w = binary.shape
            if h==0 or w==0:
                self.update_status('⚠️ 选区内无内容'); return
            wp = cv2.countNonZero(binary)
            total = h*w
            density = wp/max(total,1)
            edges = cv2.Canny(gray, 50, 150)
            ed = cv2.countNonZero(edges)/max(total,1)
            guess = '默认'
            info = ''
            if density > 0.35:
                guess='粗体风格'; info='笔画较粗'
            elif density < 0.10:
                guess='细体风格'; info='笔画较细'
            else:
                guess='常规风格'; info='笔画适中'
            if ed > 0.15:
                info += '，带衬线'
                guess += '(衬线体)'
            else:
                info += '，无衬线'
                guess += '(无衬线体)'
            self.update_status(f'🅰️ 字体识别: {guess} | {info}')
            popup = Popup(title='🅰️ 字体识别', size_hint=(0.7,0.5),
                          background='', background_color=(0.1,0.1,0.18,1))
            lbl = Label(text=f'字体分析结果\\n\\n推断风格: {guess}\\n文字密度: {density:.1%}\\n边缘密度: {ed:.1%}',
                        font_size='14sp', color=(0.8,0.8,0.8,1), halign='center')
            bx2 = BoxLayout(orientation='vertical', spacing=10, padding=20)
            bx2.add_widget(lbl)
            btn_ok = Button(text='知道了', size_hint_y=0.3,
                           background_normal='', background_color=(0.91,0.27,0.38,1))
            btn_ok.bind(on_press=lambda x: popup.dismiss())
            bx2.add_widget(btn_ok)
            popup.content = bx2
            popup.open()
        except Exception as e:
            self.update_status(f'❌ 字体识别失败: {str(e)}')
    
    # ========= 文字替换 =========
    def replace_text_on_image(self):
        if self.current_pil is None:
            self.update_status('❌ 请先打开图片'); return
        if not self.selection_rect:
            self.update_status('❌ 请先框选要替换的区域'); return
        new_text = self.ids.edit_text.text.strip()
        if not new_text:
            self.update_status('❌ 修改文字框不能为空'); return
        x1,y1,x2,y2 = self.selection_rect
        if (x2-x1) < 10 or (y2-y1) < 10:
            self.update_status('❌ 选区太小'); return
        img = self.current_pil.copy().convert('RGBA')
        # 取背景色
        bg = self._get_bg_color(img, x1,y1,x2,y2)
        draw = ImageDraw.Draw(img)
        draw.rectangle([x1,y1,x2,y2], fill=bg)
        # 画新文字
        self._draw_text(img, new_text, x1,y1,x2,y2)
        self.current_pil = img.convert('RGB')
        self.display_image()
        ot = self.ids.original_text.text[:20]
        nt = new_text[:20]
        self.update_status(f'✅ 文字已替换: "{ot}..." \\u2192 "{nt}..."')
    
    def _get_bg_color(self, img, x1,y1,x2,y2):
        colors = []
        for cx,cy in [(x1+2,y1+2),(x2-2,y1+2),(x1+2,y2-2),(x2-2,y2-2)]:
            try:
                c = img.getpixel((cx,cy))
                if isinstance(c, tuple) and len(c)>=3:
                    colors.append(c[:3])
            except:
                continue
        if colors:
            return tuple(sum(c[i] for c in colors)//len(colors) for i in range(3))
        return (200,200,200)
    
    def _draw_text(self, img, text, x1,y1,x2,y2):
        draw = ImageDraw.Draw(img)
        fp = None
        fm = {
            '黑体': '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '宋体': '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
            '楷体': '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            'Arial': '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            'Times': '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        }
        if self.font_name in fm and os.path.exists(fm[self.font_name]):
            fp = fm[self.font_name]
        try:
            font = ImageFont.truetype(fp, self.font_size) if fp and os.path.exists(fp) else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=font)
        tw = bbox[2]-bbox[0]
        th = bbox[3]-bbox[1]
        cx = (x1+x2)//2
        cy = (y1+y2)//2
        tx = cx - tw//2
        ty = cy - th//2
        color = self.font_color[:3]
        draw.text((tx+1,ty+1), text, font=font, fill=(0,0,0,128))
        draw.text((tx,ty), text, font=font, fill=color)
    
    # ========= 缩放 =========
    def zoom_in(self):
        self.zoom_level = min(3.0, self.zoom_level+0.2)
        self.ids.zoom_slider.value = self.zoom_level
        self.display_image()
    def zoom_out(self):
        self.zoom_level = max(0.5, self.zoom_level-0.2)
        self.ids.zoom_slider.value = self.zoom_level
        self.display_image()
    def on_zoom(self, value):
        self.zoom_level = value
        self.display_image()
    
    # ========= 字体样式 =========
    def toggle_bold(self):
        self.font_bold = not self.font_bold
        self.update_status(f'粗体: {"ON" if self.font_bold else "OFF"}')
    def toggle_italic(self):
        self.font_italic = not self.font_italic
        self.update_status(f'斜体: {"ON" if self.font_italic else "OFF"}')
    def set_font(self, name):
        self.font_name = name
        self.update_status(f'字体: {name}')
    def set_font_size(self, size):
        try:
            self.font_size = int(size)
            self.update_status(f'字号: {size}')
        except:
            pass
    def show_color_picker(self):
        popup = Popup(title='⬛ 选择颜色', size_hint=(0.7,0.6),
                      background='', background_color=(0.1,0.1,0.18,1))
        from kivy.uix.colorpicker import ColorPicker
        cp = ColorPicker()
        btn_ok = Button(text='确定', size_hint_y=0.2,
                       background_normal='', background_color=(0.91,0.27,0.38,1))
        bx = BoxLayout(orientation='vertical')
        bx.add_widget(cp)
        bx.add_widget(btn_ok)
        def on_ok(btn):
            r = int(cp.color[0]*255)
            g = int(cp.color[1]*255)
            b = int(cp.color[2]*255)
            self.font_color = (r,g,b,255)
            self.update_status(f'颜色已设: RGB({r},{g},{b})')
            popup.dismiss()
        btn_ok.bind(on_press=on_ok)
        popup.content = bx
        popup.open()
    def reset_image(self):
        if self.original_pil:
            self.current_pil = self.original_pil.copy()
            self.selection_rect = None
            self.display_image()
            self.update_status('🔄 已重置为原始图片')


class KnotPhotoApp(App):
    def build(self):
        self.title = '🪢 结绳 · 图修'
        Window.size = (900, 700)
        return PhotoEditor()


if __name__ == '__main__':
    KnotPhotoApp().run()
