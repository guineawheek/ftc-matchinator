import PySimpleGUI as sg
from PIL import Image
from typing import List
import tkinter as tk
import json
import sys


# tool usable for creating region of interest maps

DEFAULT_LINE_COLOR = "#ff00ff"
SELECT_LINE_COLOR = "#00ff00"


class ROI:
    def __init__(self, name, x, y, w, h, rtype="Number", visible=True):
        self.name = name
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.rtype = rtype
        self.visible = visible
        # tkinter rectangle handle
        self.tk_handle = None
    
    def serialize(self):
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "visible": self.visible,
            "rtype": self.rtype,
        }
    
    def select(self, window: sg.Window):
        window['!ROIList'].set_value([self.name])

        window['!ROIName'].update(value=self.name)
        window['!ROIXcoord'].update(value=self.x)
        window['!ROIYcoord'].update(value=self.y)
        window['!ROIWidth'].update(value=self.w)
        window['!ROIHeight'].update(value=self.h)
        window['!ROIVisible'].update(value=self.visible)
        window['!ROIType'].update(value=self.rtype)
    
    def redraw(self, window: sg.Window, line_color):
        graph: sg.Graph = window['!ROIGraph']
        if self.tk_handle is not None: 
            graph.delete_figure(self.tk_handle)
        if self.visible:
            self.tk_handle = graph.draw_rectangle((self.x, self.y), (self.x + self.w, self.y + self.h), line_color=line_color, line_width=3)
        else:
            self.tk_handle = None
    
    def hide(self, window: sg.Window):
        graph: sg.Graph = window['!ROIGraph']
        if self.tk_handle is not None: 
            graph.delete_figure(self.tk_handle)
        self.tk_handle = None
    
    def refresh_axes(self, window: sg.Window, centerline):
        xline, yline = centerline

        cx, cy = self.x + self.w // 2, self.y + self.h // 2
        window['!ROIXoff'].update(value=cx - xline)
        window['!ROIYoff'].update(value=cy - yline)
    
    def xflip(self, window: sg.Window, centerline):
        xline, yline = centerline
        self.x = xline + xline - self.x - self.w
        window['!ROIXcoord'].update(value=self.x)
        self.refresh_axes(window, centerline)

    def yflip(self, window: sg.Window, centerline):
        xline, yline = centerline
        self.y = yline + yline - self.y - self.h
        window['!ROIYcoord'].update(value=self.y)
        self.refresh_axes(window, centerline)



    def set_on_validate_int(self, attr, value, min_val, max_val):
        # return None on success, value on fail
        try:
            v = int(value)
        except ValueError:
            return getattr(self, attr)
        
        if v < min_val:
            setattr(self, attr, min_val)
            return min_val
        if v > max_val:
            setattr(self, attr, max_val)
            return max_val
        
        setattr(self, attr, v)
        return None

    

class Model:
    def __init__(self, window):
        self.roi: List[ROI] = []
        self.window = window
        self.roilist: sg.Listbox = window['!ROIList']
    
    def from_file(self, fname, img_size):
        self.clear_all()
        with open(fname, "r") as f:
            data = json.load(f)
        
        if (data['img_w'], data['img_h']) != img_size:
            sg.popup_ok(f"Warning: image size {img_size} != {(data['img_w'], data['img_h'])}")
        
        for sroi in data['roi']:
            roi = ROI(sroi['name'], sroi['x'], sroi['y'], sroi['w'], sroi['h'], rtype=sroi['rtype'], visible=sroi['visible'])
            self.add_roi(roi)
            roi.redraw(self.window, DEFAULT_LINE_COLOR)

    
    def to_file(self, fname, img_size):
        out = {
            "img_w": img_size[0],
            "img_h": img_size[1],
            "roi": [r.serialize() for r in self.roi]
        }
        with open(fname, "w") as f:
            json.dump(out, f)
    
    def clear_all(self):
        self.remove_selected(selected=[s.name for s in self.roi])
    
    def add_roi(self, r: ROI):
        # assumes that r will already have a proper handle
        self.roi.append(r)
        self.roilist.update(values=[roi.name for roi in self.roi])
    
    def remove_selected(self, selected=None):
        if selected is None:
            selected = self.roilist.get()
        new_roi = []
        last_r = None
        lr_cache = None
        for r in self.roi:
            if r.name in selected:
                r.hide(self.window)
                last_r = lr_cache
            else:
                new_roi.append(r)
                lr_cache = r
        self.roi = new_roi
        self.roilist.update(values=[roi.name for roi in self.roi])

        if last_r is None and self.roi: 
            last_r = self.roi[0]
        if self.roi:
            self.roilist.set_value([last_r.name])
        self.update_select_colors()

    def move_selected(self, d):
        s = self.roilist.get_indexes()
        if not s:
            return
        s = s[0]
        if s + d < 0 or s + d >= len(self.roi):
            # can't move it
            return
        self.roi[s], self.roi[s + d] = self.roi[s + d], self.roi[s]
        self.roilist.update(values=[roi.name for roi in self.roi], set_to_index=[s + d])

    def reload_names(self):
        self.roilist.update(values=[roi.name for roi in self.roi], set_to_index=self.roilist.get_indexes())

    
    def get_roi_by_handle(self, h: int) -> ROI:
        for r in self.roi:
            if r.tk_handle == h:
                return r
        return None
    
    def get_roi_by_name(self, n: str) -> ROI:
        for r in self.roi:
            if r.name == n:
                return r
        return None
    
    def get_untitled(self) -> str:
        n = 1
        name = f"Untitled-{n}"
        while name in [roi.name for roi in self.roi]:
            n += 1
            name = f"Untitled-{n}"
        return name
    
    def get_copy_name(self, name):
        names = {roi.name for roi in self.roi}
        n = 1
        rname = f"{name}-{n}"
        while rname in names:
            n += 1
            rname = f"{name}-{n}"
        
        return rname
    
    def get_selected_roi(self, values):
        if values is None:
            return None
        for r in self.roi:
            if r.name in values['!ROIList']:
                return r
    
    def update_select_colors(self):
        for i, r in enumerate(self.roi):
            if r.tk_handle is None:
                continue
            if i in self.roilist.get_indexes():
                r.redraw(self.window, SELECT_LINE_COLOR)
            else:
                r.redraw(self.window, DEFAULT_LINE_COLOR)
        
    def select_by_xy(self, x, y, centerline):
        for r in self.roi:
            if (r.x <= x <= r.x + r.w) and (r.y <= y <= r.y + r.h):
                r.select(self.window)
                r.refresh_axes(self.window, centerline)
                self.update_select_colors()
                return



def main(fname):
    # todo:

    img = Image.open(fname)
    img_size = img.size
    centerline = (img_size[0] // 2, img_size[1] // 2)
    img.close()

    sg.theme('Dark Blue 3')

    mouse_tool = [[sg.T('ROI click mode', enable_events=True)],
           [sg.R('Draw (F1)', 1, key='!DrawROI', enable_events=True)],
           [sg.R('Resize (F2)', 1, key='!ResizeROI', enable_events=True)],
           [sg.R('Move (F3)', 1, key='!MoveROI', enable_events=True)],
           [sg.R('Select (F4)', 1, key='!SelectROI', enable_events=True, default=True)],
           [sg.T("Load/save")],
           [sg.InputText(visible=False, enable_events=True, key="!SaveLayoutPath"), sg.FileSaveAs('Save Layout', key='!SaveLayout', file_types=(("JSON file", ".json"),))],
           [sg.B('Load Layout', key='!LoadLayout', enable_events=True)],
           [sg.B('Load image', key='!LoadImage', enable_events=True)],
           ]
    
    rect_select = [[sg.T("Regions of interest:")],
        [sg.Listbox([], key="!ROIList", size=(24, 15), expand_y=True, enable_events=True)]]
    
    params = [
        [sg.T("Region name (return to commit)")],
        [sg.Input(key="!ROIName", size=(20, None))],
        [sg.T("Region type")],
        [sg.OptionMenu(["Number", "Text", "Image"], key="!ROIType", default_value="Number", size=(10, None))],
        [sg.B("Move up in list", key="!ROIMoveUp")],
        [sg.B("Move down in list", key="!ROIMoveDown")],
        [sg.B("Duplicate region", key="!ROIDup")],
        [sg.B("Delete region", key="!ROIDelete")],
    ]
    
    gen_tool = [
        [sg.Checkbox("Show ROI", key="!ROIVisible", size=(15, None), enable_events=True, default=True)],
        [sg.T("X "),    sg.Input(size=(8, None), key="!ROIXcoord", enable_events=True, justification="right")],
        [sg.T("Y "),    sg.Input(size=(8, None), key="!ROIYcoord", enable_events=True, justification="right")],
        [sg.T("Width"),  sg.Input(size=(8, None), key="!ROIWidth",  enable_events=True, justification="right")],
        [sg.T("Height"), sg.Input(size=(8, None), key="!ROIHeight", enable_events=True, justification="right")],
        [sg.T("X-center offset"), sg.Input(size=(8, None), key="!ROIYoff", enable_events=True, disabled=True, justification="right")],
        [sg.T("Y-center offset"), sg.Input(size=(8, None), key="!ROIXoff", enable_events=True, disabled=True, justification="right")],
        [sg.B("Flip horiz", key="!ROIXflip", enable_events=True), sg.B("Flip vert", key="!ROIYflip", enable_events=True)]
    ]

    layout = [[
               sg.Graph(
                canvas_size=img_size,
                graph_bottom_left=(0, img_size[1]-1),
                graph_top_right=(img_size[0], 0),
                key="!ROIGraph",
                enable_events=True,
                background_color='lightblue',
                drag_submits=True,
                ),  ],
            [sg.Col(mouse_tool, key='!MouseToolCol'),
            sg.Col(rect_select, key="!ROISelectCol"),
            sg.Col(params, key="!ROIParamsCol", element_justification="right"),
            sg.Col(gen_tool, key="!GenToolCol", element_justification="right"),
            #sg.Col(display, key="!DisplayCol", element_justification="right", vertical_alignment="top") 
             ],
            [sg.Text(key='!ROIInfo', size=(60, 1))]
            ]

    window = sg.Window("ROInator", layout, return_keyboard_events=True, finalize=True)
    for h in ["!ROIXcoord", "!ROIYcoord", "!ROIWidth", "!ROIHeight", "!ROIName"]:
        window[h].bind("<Return>", "_Enter")


    model = Model(window)

    # get the graph element for ease of use later
    graph: sg.Graph = window["!ROIGraph"]  # type: sg.Graph
    BASE_IMG_ID = graph.draw_image(filename=fname, location=(0,0))
    graph.update()

    dragging = False
    roi: ROI = None
    start_point = end_point = prior_rect = None

    return_code = 0

    while True:
        event, values = window.read()
        roi = model.get_selected_roi(values)
        #print(event, values)
        if event == sg.WIN_CLOSED or event == "Escape:9":
            return_code = 0
            break  # exit

        if event in ('!MoveROI', "F3:69"):
            graph.set_cursor(cursor='fleur')
        elif event in ("!ResizeROI", "F2:68"):
            graph.set_cursor(cursor='sizing')
        elif event in ("!DrawROI", "F1:67"):
            graph.set_cursor(cursor='cross')

        elif not event.startswith('!ROIGraph'):
            graph.set_cursor(cursor='left_ptr')

        if event == "F3:69":
            window['!MoveROI'].update(value=True)
        elif event == "F2:68":
            window['!ResizeROI'].update(value=True)
        elif event == "F1:67":
            window['!DrawROI'].update(value=True)
        elif event == "F4:70":
            window['!SelectROI'].update(value=True)

        if event == "!ROIGraph":
            x, y = values["!ROIGraph"]
            if not dragging:
                if values['!MoveROI']:
                    model.select_by_xy(x, y, centerline)
                start_point = (x, y)
                dragging = True
                lastxy = x, y
            else:
                end_point = (x, y)
            if prior_rect:
                graph.delete_figure(prior_rect)
            delta_x, delta_y = x - lastxy[0], y - lastxy[1]
            lastxy = x,y
            if None not in (start_point, end_point):
                if values['!MoveROI']:
                    if roi and ((0 <= roi.x + delta_x) and (0 <= roi.y + delta_y) and (roi.x + roi.w + delta_x < img_size[0]) and (roi.y + roi.h + delta_y < img_size[1])):
                        # update boxes
                        roi.x += delta_x
                        roi.y += delta_y
                        window['!ROIXcoord'].update(value=roi.x)
                        window['!ROIYcoord'].update(value=roi.y)
                        roi.refresh_axes(window, centerline)

                        if roi.tk_handle:
                            graph.move_figure(roi.tk_handle, delta_x, delta_y)
                            graph.update()
                elif values['!ResizeROI']:
                    if roi and (roi.w + delta_x > 0) and (roi.h + delta_y > 0) and (roi.x + roi.w + delta_x < img_size[0]) and (roi.y + roi.h + delta_y < img_size[1]):
                        # update w/h
                        roi.w += delta_x
                        roi.h += delta_y
                        window['!ROIWidth'].update(value=roi.w)
                        window['!ROIHeight'].update(value=roi.h)
                        roi.refresh_axes(window, centerline)
                        roi.redraw(window, SELECT_LINE_COLOR)


                elif values['!DrawROI']:
                    end_point = (max(0, min(end_point[0], img_size[0]-1)), max(0, min(end_point[1], img_size[1]-1)))
                    prior_rect = graph.draw_rectangle(start_point, end_point, line_color=SELECT_LINE_COLOR, line_width=3)
                
            if values['!SelectROI']:
                model.select_by_xy(x, y, centerline)



            window["!ROIInfo"].update(value=f"mouse {values['!ROIGraph']}")
        elif event == "!ROIList":
            if roi:
                roi.select(window)
                model.update_select_colors()
        elif event.endswith('+UP'):
            if values['!DrawROI'] and start_point is not None:
                # rectify the start/end points
                start_point, end_point = (min(start_point[0], end_point[0]), min(start_point[1], end_point[1])), (max(start_point[0], end_point[0]), max(start_point[1], end_point[1])), 
                graph.delete_figure(prior_rect)
                prior_rect = graph.draw_rectangle(start_point, end_point, line_color=SELECT_LINE_COLOR, line_width=3)
                graph.update()
                
                # create new ROI entry
                new_roi = ROI(model.get_untitled(), start_point[0], start_point[1], end_point[0] - start_point[0], end_point[1] - start_point[1])
                new_roi.tk_handle = prior_rect
                model.add_roi(new_roi)
                new_roi.select(window)
                model.update_select_colors()
                new_roi.refresh_axes(window, centerline)

            window["!ROIInfo"].update(value=f"grabbed rectangle from {start_point} to {end_point}")

            start_point, end_point = None, None 
            dragging = False
            prior_rect = None
        elif event in ("!ROIDelete"):
            model.remove_selected()
        
        elif event == "!ROIMoveUp":
            model.move_selected(-1)
        elif event == "!ROIMoveDown":
            model.move_selected(1)
        
        elif event == "!ROIVisible" and roi is not None:
            roi.visible = values['!ROIVisible']
            roi.redraw(window, SELECT_LINE_COLOR)
        
        elif event == "!ROIXflip":
            roi.xflip(window, centerline)
            roi.redraw(window, SELECT_LINE_COLOR)
            pass
        elif event == "!ROIYflip":
            roi.yflip(window, centerline)
            roi.redraw(window, SELECT_LINE_COLOR)
            pass

        
        elif event == "!ROIXcoord_Enter" and roi is not None:
            new_val = roi.set_on_validate_int("x", values['!ROIXcoord'], 0, img_size[0] - roi.w - 1)
            if new_val is not None:
                window['!ROIXcoord'].update(value=new_val)
            roi.redraw(window, SELECT_LINE_COLOR)
            roi.refresh_axes(window, centerline)

        elif event == "!ROIYcoord_Enter" and roi is not None:
            new_val = roi.set_on_validate_int("y", values['!ROIYcoord'], 0, img_size[1] - roi.h - 1)
            if new_val is not None:
                window['!ROIYcoord'].update(value=new_val)
            roi.redraw(window, SELECT_LINE_COLOR)
            roi.refresh_axes(window, centerline)

        elif event == "!ROIWidth_Enter" and roi is not None:
            new_val = roi.set_on_validate_int("w", values['!ROIWidth'], 0, img_size[0] - roi.x - 1)
            if new_val is not None:
                window['!ROIWidth'].update(value=new_val)
            roi.redraw(window, SELECT_LINE_COLOR)
            roi.refresh_axes(window, centerline)

        elif event == "!ROIHeight_Enter" and roi is not None:
            new_val = roi.set_on_validate_int("h", values['!ROIHeight'], 0, img_size[1] - roi.y - 1)
            if new_val is not None:
                window['!ROIHeight'].update(value=new_val)
            roi.redraw(window, SELECT_LINE_COLOR)
            roi.refresh_axes(window, centerline)


        elif event == "!ROIDup" and roi is not None:
            new_roi = ROI(model.get_copy_name(roi.name), roi.x, roi.y, roi.w, roi.h)
            # shouldn't be necessary to render a new one
            model.add_roi(new_roi)
            new_roi.select(window)
            new_roi.redraw(window, SELECT_LINE_COLOR)
            model.update_select_colors()
        
        elif event == "!ROIName_Enter" and roi is not None:
            cur_name = roi.name
            new_name = values['!ROIName']
            if new_name in [r.name for r in model.roi]:
                window['!ROIName'].update(value=cur_name)
            else:
                roi.name = new_name
                model.reload_names()
            
        elif event == "!LoadImage":
            return_code = 1
            break
        elif event == "!LoadLayout":
            layout_fname = sg.popup_get_file("Open layout file", file_types=(("JSON layout files", ".json"),))
            if layout_fname is None:
                continue
            model.from_file(layout_fname, img_size)
        elif event == "!SaveLayoutPath":
            model.to_file(values['!SaveLayout'], img_size)

        
    window.close()
    return return_code

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = sg.popup_get_file("Open image file")
    while fname is not None:
        ret = main(fname)
        if ret != 1:
            break
        fname = sg.popup_get_file("Open image file")
