import sys, os, subprocess, re, json
import datetime as dt
from enum import Enum
from pathlib import Path, PurePath
import wx
import wx.propgrid as wxpg
import wx.adv as wxadv


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, listbox):
        wx.FileDropTarget.__init__(self)
        self.listbox = listbox

    def OnDropFiles(self, x, y, filepaths):
        app.frame.flog(0, f'Adding {len(filepaths)} files...')
        for filepath in filepaths:
            Media_File(filepath)
        return True

class MyMainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.SetSize((800, 900))
        self.SetTitle(MyApp.ver)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(wx.Bitmap("ffenc.png", wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        self.frame_statusbar = self.CreateStatusBar(1)
        self.frame_statusbar.SetStatusWidths([-1])
        # statusbar fields
        frame_statusbar_fields = ["Ready"]
        for i in range(len(frame_statusbar_fields)):
            self.frame_statusbar.SetStatusText(frame_statusbar_fields[i], i)

        self.panel_main = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE)

        sizer_main = wx.BoxSizer(wx.VERTICAL)

        # PRESETS
        sizer_presets = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_presets, 2, wx.BOTTOM | wx.EXPAND | wx.TOP, 0)

        self.nb_video = wx.Notebook(self.panel_main, wx.ID_ANY, style=wx.NB_BOTTOM | wx.NB_FIXEDWIDTH)
        sizer_presets.Add(self.nb_video, 1, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        self.nb_video_select = wx.Panel(self.nb_video, wx.ID_ANY)
        self.nb_video_select.SetToolTip("List of video presets")
        self.nb_video.AddPage(self.nb_video_select, "Video preset")

        sizer_nb_video_select = wx.BoxSizer(wx.VERTICAL)

        # Video preset list
        self.list_video_preset = wx.ListBox(self.nb_video_select, wx.ID_ANY, choices=['Preset 1', 'Preset 2', 'Preset 3', 'Preset 4', 'Copy stream', 'No video'], style=wx.LB_NEEDED_SB | wx.LB_SINGLE)
        self.list_video_preset.SetSelection(0)
        sizer_nb_video_select.Add(self.list_video_preset, 1, wx.ALL | wx.EXPAND, 3)

        self.nb_video_edit = wx.Panel(self.nb_video, wx.ID_ANY)
        self.nb_video_edit.SetToolTip("Video preset editor")
        self.nb_video.AddPage(self.nb_video_edit, "Edit")

        sizer_nb_video_edit = wx.BoxSizer(wx.VERTICAL)

        self.prop_video_preset = wxpg.PropertyGridManager(self.nb_video_edit, wx.ID_ANY, style=wxpg.PG_NO_INTERNAL_BORDER | wxpg.PG_BOLD_MODIFIED)
        sizer_nb_video_edit.Add(self.prop_video_preset, 9, wx.ALL | wx.EXPAND, 3)
        self.prop_video_show()

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_nb_video_edit.Add(sizer_2, 0, wx.EXPAND, 0)

        self.button_save_video_preset = wx.Button(self.nb_video_edit, wx.ID_ANY, "Save")
        self.button_save_video_preset.SetToolTip("Save preset")
        sizer_2.Add(self.button_save_video_preset, 1, wx.ALL | wx.EXPAND, 5)

        self.button_dup_video_preset = wx.Button(self.nb_video_edit, wx.ID_ANY, "Duplicate")
        self.button_dup_video_preset.SetToolTip("Make a copy")
        sizer_2.Add(self.button_dup_video_preset, 0, wx.ALL | wx.EXPAND, 5)

        self.button_del_video_preset = wx.Button(self.nb_video_edit, wx.ID_ANY, "Delete")
        self.button_del_video_preset.SetToolTip("Delete preset")
        sizer_2.Add(self.button_del_video_preset, 0, wx.ALL | wx.EXPAND, 5)

        self.nb_audio = wx.Notebook(self.panel_main, wx.ID_ANY, style=wx.NB_BOTTOM | wx.NB_FIXEDWIDTH)
        sizer_presets.Add(self.nb_audio, 1, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        self.nb_audio_select = wx.Panel(self.nb_audio, wx.ID_ANY)
        self.nb_audio.AddPage(self.nb_audio_select, "Audio preset")

        sizer_nb_audio_select = wx.BoxSizer(wx.VERTICAL)

        # Audio preset list
        self.list_audio_preset = wx.ListBox(self.nb_audio_select, wx.ID_ANY, choices=['Preset 1', 'Copy stream', 'No audio'], style=wx.LB_NEEDED_SB | wx.LB_SINGLE)
        self.list_audio_preset.SetSelection(0)
        sizer_nb_audio_select.Add(self.list_audio_preset, 1, wx.ALL | wx.EXPAND, 3)

        self.nb_audio_edit = wx.Panel(self.nb_audio, wx.ID_ANY)
        self.nb_audio.AddPage(self.nb_audio_edit, "Edit")

        sizer_nb_audio_edit = wx.BoxSizer(wx.VERTICAL)

        self.prop_audio_preset = wxpg.PropertyGridManager(self.nb_audio_edit, wx.ID_ANY, style=wxpg.PG_NO_INTERNAL_BORDER | wxpg.PG_BOLD_MODIFIED)
        sizer_nb_audio_edit.Add(self.prop_audio_preset, 9, wx.ALL | wx.EXPAND, 3)
        self.prop_audio_show()

        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_nb_audio_edit.Add(sizer_3, 0, wx.EXPAND, 0)

        self.button_save_audio_preset = wx.Button(self.nb_audio_edit, wx.ID_ANY, "Save audio preset")
        self.button_save_audio_preset.SetToolTip("Save preset")
        sizer_3.Add(self.button_save_audio_preset, 1, wx.ALL | wx.EXPAND, 5)

        self.button_dup_audio_preset = wx.Button(self.nb_audio_edit, wx.ID_ANY, "Duplicate")
        self.button_dup_audio_preset.SetToolTip("Make a copy")
        sizer_3.Add(self.button_dup_audio_preset, 0, wx.ALL | wx.EXPAND, 5)

        self.button_del_audio_preset = wx.Button(self.nb_audio_edit, wx.ID_ANY, "Delete")
        self.button_del_audio_preset.SetToolTip("Delete preset")
        sizer_3.Add(self.button_del_audio_preset, 0, wx.ALL | wx.EXPAND, 5)

        # Files
        sizer_files = wx.FlexGridSizer(2, 2, 0, 0)
        sizer_main.Add(sizer_files, 2, wx.BOTTOM | wx.EXPAND | wx.TOP, 5)

        label_file_list = wx.StaticText(self.panel_main, wx.ID_ANY, "File list")
        sizer_files.Add(label_file_list, 3, wx.LEFT | wx.TOP, 5)

        label_file_info = wx.StaticText(self.panel_main, wx.ID_ANY, "File info")
        sizer_files.Add(label_file_info, 1, wx.LEFT | wx.TOP, 5)

        self.list_files = wx.ListCtrl(self.panel_main, wx.ID_ANY, style=wx.BORDER_NONE | wx.LC_HRULES | wx.LC_REPORT) # | wx.LC_SINGLE_SEL
        self.list_files.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=25)
        self.list_files.AppendColumn("File", format=wx.LIST_FORMAT_LEFT, width=320)
        self.list_files.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_files.AppendColumn("Video preset", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_files.AppendColumn("Audio preset", format=wx.LIST_FORMAT_LEFT, width=80)
        sizer_files.Add(self.list_files, 3, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        self.tree_file_info = wx.TreeCtrl(self.panel_main, wx.ID_ANY, style=wx.TR_SINGLE | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        self.tree_file_info.SetToolTip("Media file info")
        self.tree_file_info.SetBackgroundColour(wx.Colour(208, 208, 208))
        sizer_files.Add(self.tree_file_info, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # Main buttons
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(sizer_buttons, 0, wx.BOTTOM | wx.EXPAND | wx.TOP, 5)

        self.button_encode = wx.Button(self.panel_main, wx.ID_ANY, "Encode")
        self.button_encode.SetToolTip("Start encoding")
        sizer_buttons.Add(self.button_encode, 1, wx.ALL | wx.EXPAND, 5)

        self.button_stop = wx.Button(self.panel_main, wx.ID_ANY, "Stop")
        self.button_stop.SetToolTip("Stop encoding")
        self.button_stop.Enable(False)
        sizer_buttons.Add(self.button_stop, 1, wx.ALL | wx.EXPAND, 5)

        self.button_settings = wx.Button(self.panel_main, wx.ID_ANY, "Settings")
        self.button_settings.SetToolTip("Application settings")
        sizer_buttons.Add(self.button_settings, 1, wx.ALL | wx.EXPAND, 5)

        # Progress gauges
        sizer_progress = wx.BoxSizer(wx.HORIZONTAL)
        #sizer_progress.Remove()
        sizer_main.Add(sizer_progress, 0, wx.BOTTOM | wx.EXPAND | wx.TOP, 5)

        label_current = wx.StaticText(self.panel_main, wx.ID_ANY, "Current")
        sizer_progress.Add(label_current, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.gauge_current = wx.Gauge(self.panel_main, wx.ID_ANY, 1)
        self.gauge_current.SetBackgroundColour(wx.Colour(192, 192, 192))
        self.gauge_current.SetToolTip("Current file progress")
        sizer_progress.Add(self.gauge_current, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        label_total = wx.StaticText(self.panel_main, wx.ID_ANY, "Total")
        sizer_progress.Add(label_total, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.gauge_all = wx.Gauge(self.panel_main, wx.ID_ANY, 1)
        self.gauge_all.SetBackgroundColour(wx.Colour(192, 192, 192))
        self.gauge_all.SetToolTip("Total progress")
        sizer_progress.Add(self.gauge_all, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        # Activity logs
        self.log_tabs = [] # [{'panel':,'sizer':,'text':}]
        self.nb_log = wx.Notebook(self.panel_main, wx.ID_ANY)
        sizer_main.Add(self.nb_log, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        self.log_add('FFEnc log')

        # Encoded
        label_queue = wx.StaticText(self.panel_main, wx.ID_ANY, "Results", style=wx.ALIGN_LEFT)
        sizer_main.Add(label_queue, 0, wx.LEFT | wx.TOP, 5)

        self.list_queue = wx.ListCtrl(self.panel_main, wx.ID_ANY, style=wx.BORDER_NONE | wx.LC_HRULES | wx.LC_LIST | wx.LC_SINGLE_SEL)
        sizer_main.Add(self.list_queue, 1, wx.ALL | wx.EXPAND, 5)

        # Layout
        sizer_files.AddGrowableRow(1)
        sizer_files.AddGrowableCol(0)
        sizer_files.AddGrowableCol(1)

        self.log_tabs[0]['panel'].SetSizer(self.log_tabs[0]['sizer'])
        self.nb_audio_edit.SetSizer(sizer_nb_audio_edit)
        self.nb_audio_select.SetSizer(sizer_nb_audio_select)
        self.nb_video_edit.SetSizer(sizer_nb_video_edit)
        self.nb_video_select.SetSizer(sizer_nb_video_select)
        self.panel_main.SetSizer(sizer_main)

        self.Layout()
        self.Centre()

        # Bind events
        self.list_files.Bind(wx.EVT_LIST_ITEM_SELECTED, self.file_selected)
        self.list_files.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.file_activated) # delete
        self.list_video_preset.Bind(wx.EVT_LISTBOX, self.video_preset_selected)
        self.list_video_preset.Bind(wx.EVT_LISTBOX_DCLICK, self.video_preset_activated) # assign video preset
        self.list_audio_preset.Bind(wx.EVT_LISTBOX, self.audio_preset_selected)
        self.list_audio_preset.Bind(wx.EVT_LISTBOX_DCLICK, self.audio_preset_activated) # assign audio preset
        self.button_save_video_preset.Bind(wx.EVT_BUTTON, self.save_video_preset)
        self.button_dup_video_preset.Bind(wx.EVT_BUTTON, self.dup_video_preset)
        self.button_del_video_preset.Bind(wx.EVT_BUTTON, self.del_video_preset)
        self.button_save_audio_preset.Bind(wx.EVT_BUTTON, self.save_audio_preset)
        self.button_dup_audio_preset.Bind(wx.EVT_BUTTON, self.dup_audio_preset)
        self.button_del_audio_preset.Bind(wx.EVT_BUTTON, self.del_video_preset)
        self.button_encode.Bind(wx.EVT_BUTTON, self.encode)
        self.nb_log.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.nb_switched)

        # Bind dnd
        dt = FileDropTarget(self.list_files)
        self.list_files.SetDropTarget(dt)

    def encode(self, event):  
        notify("Encoding is not implemetnted yet")

    def file_selected(self, event):
        item = self.list_files.GetFirstSelected()
        itemname = self.list_files.GetItemText(item, 1)
        self.tree_file_info.DeleteAllItems()
        media: Media_File = source_files[itemname]
        info_root_id = self.tree_file_info.AddRoot(media.filename)
        for stream in media.streams:
            info_stream_id = self.tree_file_info.AppendItem(info_root_id, f'Stream #{stream['index']}: {stream.get('codec_type', 'unidentified')}')
            for category, props in ffmpeg.stream_properies.items():
                info_category = self.tree_file_info.AppendItem(info_stream_id, category)
                cnt = 0
                for propkey, propname in props.items():
                    val = stream.get(propkey, None)
                    if val is not None:
                        cnt += 1
                        self.tree_file_info.AppendItem(info_category, f'{propname}: {self.value_formatter(propkey, val)}')
                if cnt == 0: self.tree_file_info.Delete(info_category)
        
        info_container_id = self.tree_file_info.AppendItem(info_root_id, 'Container')
        for propkey, propname in ffmpeg.format_properties['Format'].items():
            val = media.format.get(propkey, None)
            if val is not None:
                self.tree_file_info.AppendItem(info_container_id, f'{propname}: {self.value_formatter(propkey, val)}')

        self.tree_file_info.Expand(info_root_id)

    def file_activated(self, event): # delete file by dclick
        item = self.list_files.GetFirstSelected()
        itemname = self.list_files.GetItemText(item, 1)
        media: Media_File = source_files[itemname]
        source_files[itemname].delete()

    def video_preset_selected(self, event):
        item = self.list_video_preset.GetSelection()
        itemname = self.list_video_preset.GetString(item)
        self.prop_video_show()

    def video_preset_activated(self, event):
        count = self.list_files.GetSelectedItemCount()
        if count != 0:
            preset_item = self.list_video_preset.GetSelection()
            preset_name = self.list_video_preset.GetString(preset_item)
            file_item = self.list_files.GetFirstSelected()
            for i in range(count):
                self.list_files.SetItem(file_item, 3, preset_name)
                source_files[self.list_files.GetItemText(file_item, 1)].video_preset = preset_name
                file_item = self.list_files.GetNextSelected(file_item)
        else:
            self.flog(0, 'Select a file to apply preset')

    def audio_preset_selected(self, event):
        item = self.list_audio_preset.GetSelection()
        itemname = self.list_audio_preset.GetString(item)
        self.prop_audio_show()

    def audio_preset_activated(self, event):
        count = self.list_files.GetSelectedItemCount()
        if count != 0:
            preset_item = self.list_audio_preset.GetSelection()
            preset_name = self.list_audio_preset.GetString(preset_item)
            file_item = self.list_files.GetFirstSelected()
            for i in range(count):
                self.list_files.SetItem(file_item, 4, preset_name)
                source_files[self.list_files.GetItemText(file_item, 1)].audio_preset = preset_name
                file_item = self.list_files.GetNextSelected(file_item)
        else:
            self.flog(0, 'Select a file to apply preset')

    def prop_video_show(self, preset_name: str = None):
        self.prop_video_preset.Clear()
        page = self.prop_video_preset.AddPage("Video Settings")
        page.Append(wxpg.PropertyCategory("Video Preset"))
        page.Append(wxpg.StringProperty("Name",  wxpg.PG_LABEL, 'Preset 1'))
        page.Append(wxpg.PropertyCategory("Container"))
        page.Append(wxpg.EditEnumProperty("Format", wxpg.PG_LABEL, FFmpeg.formats_video, range(len(FFmpeg.formats_video)), value=FFmpeg.formats_video[0]))
        page.Append(wxpg.PropertyCategory("Encoder"))
        page.Append(wxpg.EditEnumProperty("Codec", wxpg.PG_LABEL, FFmpeg.codecs_video, range(len(FFmpeg.codecs_video)), value=FFmpeg.codecs_video[0]))
        page.Append(wxpg.EnumProperty("Rate control", wxpg.PG_LABEL, ['crf','vbr'], [0,1]))
        page.Append(wxpg.EditEnumProperty("Bitrate", wxpg.PG_LABEL, ['256k', '512k', '1M', '2M', '4M', '8M', '10M', '15M', '20M', '30M', '40M'], [0,1,2,3,4,5,6,7,8,9,10], value='10M'))
        page.Append(wxpg.EditEnumProperty("Preset", wxpg.PG_LABEL, ['veryslow','slow','fast'], [0,1,2], value='veryslow'))
        page.Append(wxpg.PropertyCategory('Transofrm'))
        scale_prop = wxpg.IntProperty("Scale", wxpg.PG_LABEL, 100)
        scale_prop.SetEditor(wxpg.PGEditor_SpinCtrl)
        page.Append(scale_prop)
        page.Append(wxpg.PropertyCategory('Color settings'))
        page.Append(wxpg.EditEnumProperty("Range", wxpg.PG_LABEL, FFmpeg.color_ranges, range(len(FFmpeg.color_ranges)), value=FFmpeg.color_ranges[0]))
        page.Append(wxpg.EditEnumProperty("Color space", wxpg.PG_LABEL, FFmpeg.color_spaces, range(len(FFmpeg.color_spaces)), value=FFmpeg.color_spaces[0]))

    def prop_audio_show(self, preset_name: str = None):
        self.prop_audio_preset.Clear()
        page = self.prop_audio_preset.AddPage("Audio Settings")
        page.Append(wxpg.PropertyCategory("Audio Preset"))
        page.Append(wxpg.StringProperty("Name",  wxpg.PG_LABEL, 'Preset 1'))
        page.Append(wxpg.PropertyCategory("Container"))
        page.Append(wxpg.EditEnumProperty("Format", wxpg.PG_LABEL, FFmpeg.formats_audio, range(len(FFmpeg.formats_audio)), value=FFmpeg.formats_audio[0]))
        page.Append(wxpg.PropertyCategory("Encoder"))
        page.Append(wxpg.EditEnumProperty("Codec", wxpg.PG_LABEL, FFmpeg.codecs_audio, range(len(FFmpeg.codecs_audio)), value=FFmpeg.codecs_audio[0]))
        page.Append(wxpg.EnumProperty("Rate control", wxpg.PG_LABEL, ['crf','vbr'], [0,1]))
        page.Append(wxpg.EditEnumProperty("Bitrate", wxpg.PG_LABEL, ['32k','64k','128k','256k','512k','1M','2M','4M'], [0,1,2,3,4,5,6,7], value='10M'))
        page.Append(wxpg.EditEnumProperty("Preset", wxpg.PG_LABEL, ['veryslow','slow','fast'], [0,1,2], value='veryslow'))
        page.Append(wxpg.PropertyCategory('Transofrm'))
        volume_prop = wxpg.IntProperty("Volume", wxpg.PG_LABEL, 100)
        volume_prop.SetEditor(wxpg.PGEditor_SpinCtrl)
        page.Append(volume_prop)

    def save_video_preset(self, event):
        self.flog(0, 'Pretending to save video preset')

    def dup_video_preset(self, event):
        self.flog(0, 'Pretending to duplicate video preset')

    def del_video_preset(self, event):
        self.flog(0, 'Pretending to delete video preset')

    def save_audio_preset(self, event):
        self.flog(0, 'Pretending to save audio preset')

    def dup_audio_preset(self, event):
        self.flog(0, 'Pretending to duplicate audio preset')

    def del_audio_preset(self, event):
        self.flog(0, 'Pretending to delete audio preset')

    def log_add(self, title: str) -> int:
        self.log_tabs.append({'panel': wx.Panel(self.nb_log, wx.ID_ANY)})
        id = len(self.log_tabs)-1
        self.nb_log.AddPage(self.log_tabs[id]['panel'], select=True, text=title)

        self.log_tabs[id]['sizer'] = wx.BoxSizer(wx.HORIZONTAL)

        self.log_tabs[id]['text'] = wx.TextCtrl(self.log_tabs[id]['panel'], wx.ID_ANY, '', style=wx.BORDER_NONE | wx.HSCROLL | wx.TE_AUTO_URL | wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_NOHIDESEL | wx.TE_READONLY | wx.TE_RICH2)
        self.log_tabs[id]['text'].SetBackgroundColour(wx.Colour(208, 208, 208))
        self.log_tabs[id]['sizer'].Add(self.log_tabs[id]['text'], 1, wx.ALL | wx.EXPAND, 3)

        self.log_tabs[id]['panel'].SetSizer(self.log_tabs[id]['sizer'])
        self.log_tabs[id]['panel'].Layout()

        for index in range(self.nb_log.GetPageCount()):
            if self.nb_log.GetPageText(index) == title:
                self.log_tabs[id]['page'] = index
                break
            
        self.nb_log.SetSelection(self.log_tabs[id]['page'])
        return id

    def log_pop(self, id: int):
        self.nb_log.SetSelection(self.log_tabs[0]['page'])
        self.log_tabs[id]['sizer'].Remove(0)
        self.nb_log.DeletePage(self.log_tabs[id]['page'])
        self.log_tabs.pop(id)

    def nb_switched(self, event):
        selected = self.nb_log.GetSelection()
        if selected != wx.NOT_FOUND:
            if selected == 0:
                for item in range(self.list_files.GetItemCount()):
                    self.list_files.Select(item, 1)
            else:
                for item in range(self.list_files.GetItemCount()):
                    self.list_files.Select(item, 1 if item == selected-1 else 0)

    def check_files(self):
        if self.list_files.ItemCount < 1:
            self.button_encode.Disable()
        else:
            self.button_encode.Enable()

    def value_formatter(self, property_key: str, property_value: any):
        if ('CREATED_TIME' in property_key.upper()) or ('CREATION_TIME' in property_key.upper()):
            return dt.datetime.strftime(dt.datetime.fromisoformat(property_value), '%Y-%m-%d %H:%M')
        elif 'SIZE' == property_key.upper():
            property_value = int(property_value)
            if property_value > 1000000000:
                return f'{round(property_value/1000000, 2)} GB'
            elif property_value > 1000000:
                return f'{round(property_value/1000000, 2)} MB'
            elif property_value > 1000:
                return f'{round(property_value/1000, 2)} KB'
            else:
                return f'{round(property_value, 2)} B'
        elif 'BIT_RATE' in property_key.upper():
            property_value = int(property_value)
            if property_value > 1000000:
                return f'{round(property_value/1000000, 2)} MB/s'
            elif property_value > 1000:
                return f'{round(property_value/1000, 2)} KB/s'
            else:
                return f'{round(property_value, 2)} B/s'
        else:
            return property_value

    def flog(self, id: int, text: str):
        timestamp = dt.datetime.strftime(dt.datetime.now(), '%H:%M:%S')
        if self.log_tabs[id]['text'].GetValue() != '':
            self.log_tabs[id]['text'].AppendText(f'\n{timestamp}: {text}')
        else:
            self.log_tabs[id]['text'].SetValue(f'{timestamp}: {text}')

class MyApp(wx.App):
    ver = 'FFEnc v0.01a'
    def OnInit(self):
        self.frame = MyMainFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

class FFmpeg():
    formats_video = ['mp4','mov','webm','dnxhd','mxf','avi','mpeg','dv','flv','apng','exr','gif','jpg','png','tif','dds']
    codecs_video =  ['prores','libx264','libx265', 'h264_nvenc','hevc_nvenc','h264_qsv','hevc_qsv','libvpx-vp9','vp9_qsv','mpeg2video','mpeg2_qsv','libx265dnxhd','mpegts','dvvideo','flv1','gif','apng','png','mjpeg','tiff','dds','HDR','WebP']
    color_spaces =  ['bt709', 'bt2020nc', 'bt2020c', 'rgb', 'bt470bg', 'smpte170m', 'smpte240m', 'smpte2085', 'ycocg']
    color_ranges =  ['tv', 'pc', 'mpeg', 'jpeg']
    formats_audio = ['Video container','ac3','wav','mp3','ogg','flac','aiff','alac']
    codecs_audio =  ['aac','ac3','flac','alac','dvaudio','pcm_s16le','pcm_s24le','pcm_s32le','pcm_f32le']
    sequence_tags = ['image2', 'pipe']

    # media properties interpreter, only these get displayed in info box
    stream_properies = {
        'Codec': { 
            'codec_name': 'Name',
            'codec_tag_string': 'Tag',
            'profile': 'Profile',
            'pix_fmt': 'Color coding',
            'bits_per_raw_sample': 'Bit depth',
            'bit_rate': 'Bit rate',
            'max_bit_rate': 'Max bitrate'
        },
        'Dimensions': {
            'width': 'Width',
            'height': 'Height',
            'sample_aspect_ratio': 'Pixel ratio',
            'display_aspect_ratio': 'Frame ratio',
        },
        'Sampling': {
            'sample_rate': 'Sampling rate',
            'channel_layout': 'Channels'
        },
        'Time': {
            'r_frame_rate': 'Frame rate',
            'avg_frame_rate': 'Average frame rate',
            'time_base': 'Time base',
            'start_time': 'Start',
            'duration': 'Duration',
            'nb_frames': 'Frames'
        },
        'Color': {
            'color_range': 'Range',
            'color_space': 'Colorspace',
            'color_primaries': 'Primaries',
            'color_transfer': 'Transfer function'
        },
        'Tags': {
            'TAG:LANGUAGE': 'Language',
            'TAG:TITLE': 'Title',
            'TAG"DURATION': 'Duration',
            'TAG:CREATION_TIME': 'Created',
            'TAG:ENCODER': 'Encoder',
            'TAG:HANDLER_NAME': 'Handler',
            'TAG:VENDOR_ID': 'Vendor'
        }
    }

    format_properties = {
        'Format': {
            'format_name': 'Format name',
            'format_long_name': 'Format long name',
            'nb_streams': 'Nubmer of streams',
            'start_time': 'Start',
            'duration': 'Duration',
            'size': 'Size',
            'bit_rate': 'Bit rate',
            'TAG:CREATION_TIME': 'Created',
            'TAG:ENCODER': 'Encoder',
            'TAG:MAJOR_BRAND': 'Brand'
        }

    }
  
    def __init__(self, path: str):
        self.path = path
        self.ffmpegexe = self.path + 'ffmpeg.exe'
        self.ffprobeexe = self.path + 'ffprobe.exe'
        my_file = Path(self.ffmpegexe)
        if my_file.is_file():
            app.frame.flog(0, f'FFmpeg executable found at {self.ffmpegexe}')
        else:
            app.frame.flog(0, f'FFmpeg executable not found at {self.ffmpegexe}')
        my_file = Path(self.ffprobeexe)
        if my_file.is_file():
            app.frame.flog(0, f'FFprobe executable found at {self.ffprobeexe}')
        else:
            app.frame.flog(0, f'FFprobe executable not found at {self.ffprobeexe}')

class Encoder():
    
    class Option():
        def __init__(self, *args, **kwargs):
            self.name = kwargs.keys()[0]
            self.preset = kwargs.get('option')
            self.preset.values = kwargs.get('values')
            

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('Name')
        self.general = kwargs.get('General')
        self.threading = kwargs.get('Threading')
        self.colorcoding = kwargs.get('Color coding')
        options = kwargs.get('Options', None)

class Filter():
    pass

class Video_Preset():
    def __init__(self):
        self.editable = True

class Audio_Preset():
    def __init__(self):
        self.editable = True

class Media_Type(Enum):
    video =    0, 'Video'
    image =    1, 'Image(s)'
    sequence = 2, 'Sequence'
    audio =    3, 'Audio'
    data =     4, 'Data'

    def __init__(self, id: int, doc: str):
        self.id = id
        self.doc = doc

class Media_File():
    def __init__(self, filepath: str):
        self.index = len(source_files)
        self.origpath = filepath
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.extension = PurePath(self.filepath).suffix
        self.basename = PurePath(self.filepath).stem
        self.out_basename = self.basename
        self.out_framerate = 30
        self.video_preset = None
        self.audio_preset = None
        
        self.probe()
        self.detect_type()

        if self.filepath in source_files:
            app.frame.flog(0, f'File {self.filepath} was already added to the sources. Skipped.')
        else:
            source_files[self.filepath] = self
            app.frame.list_files.Append([self.index+1, self.filepath, self.type.doc, 'Not set', 'Not set']) 
            app.frame.log_add(self.filename)
            app.frame.flog(0, f'File "{self.filename}" added.')
            app.frame.flog(self.index+1, f'File "{self.filename}" added.')

    def probe(self, sequence_param: list = None):
        probe_param = [
                ffmpeg.ffprobeexe,
                '-v', 'error',
                '-hide_banner',
                '-show_streams', '-show_format',
                '-sexagesimal',
                '-of', 'json',
                self.filepath]
        if sequence_param is not None: 
            app.frame.flog(0, f'Re-probing file "{self.filename}" as sequence.')
            probe_param[9:9] = sequence_param
        else:
            app.frame.flog(0, f'Probing file "{self.filename}".')
        try:
            probe = subprocess.check_output(probe_param, encoding='utf-8')
        except:
            app.frame.flog(0, f'Unable to add file "{self.filename}". Check if it\'s a media file. Skipped.')
            self.streams = None
            self.format = None
        else:
            p = json.loads(probe)
            self.streams: list = p.get('streams')
            # move/rename tags to the main level for easiers search
            for i, stream in enumerate(self.streams):
                if stream.get('tags', None) is not None:
                    for itemkey, itemval in stream['tags'].items():
                        self.streams[i]['TAG:'+itemkey.upper()] = itemval
                    del stream['tags']
            self.format: dict = p.get('format')
            if self.format.get('tags', None) is not None:
                for itemkey, itemval in self.format['tags'].items():
                    self.format['TAG:'+itemkey.upper()] = itemval
                del self.format['tags']

    def detect_type(self):
        # type detection from the probe
        fn = self.format.get('format_name')
        if has_tags(fn, ffmpeg.sequence_tags):
            self.type = Media_Type.image
            # detect frame counter
            rs = re.compile(r'\d{3,6}$')
            counter_match = rs.search(self.basename)
            if counter_match is not None:
                self.type = Media_Type.sequence
                self.counter_length: str = len(counter_match.group())
                self.filepath = self.filepath.replace(self.filename, '') # cut off filename
                self.basename = self.basename.replace(counter_match.group(), f'%0{self.counter_length}d')
                self.filename = self.basename + self.extension
                self.filepath += self.filename # add the updated filename back
                # re-probe as sequence now
                self.probe(['-pattern_type', 'sequence', '-framerate', str(self.format.get('r_frame_rate', self.out_framerate)), '-start_number', '0'])
        elif has_tags(fn, ffmpeg.formats_audio):
            self.type = Media_Type.audio
        elif has_tags(fn, ffmpeg.formats_video):
            self.type = Media_Type.video
        else:
            self.type = Media_Type.data

    def delete(self):
        app.frame.tree_file_info.DeleteAllItems()
        app.frame.list_files.DeleteItem(source_files[self.filepath].index)
        app.frame.log_pop(source_files[self.filepath].index+1)
        del source_files[self.filepath]
        app.frame.flog(0, f'File "{self.filename}" deleted.')        


def notify(text: str):
    feicon = wx.NullIcon
    feicon.CopyFromBitmap(wx.Bitmap("ffenc.png", wx.BITMAP_TYPE_ANY))
    notif = wxadv.NotificationMessage(MyApp.ver, message=text, parent=None)
    wxadv.NotificationMessage.SetTitle(notif, MyApp.ver)
    wxadv.NotificationMessage.SetIcon(notif, feicon)
    wxadv.NotificationMessage.Show(notif, timeout=8)    

def has_tags(text: str, tag_list: list) -> bool:
    return any(item in text for item in tag_list)


if __name__ == "__main__":
    args = sys.argv
    print(f'argumens: {args}')
    app = MyApp(0)
    app.frame.flog(0, f'{app.ver} started.')
    ffmpeg = FFmpeg('C:\\Program Files\\ffmpeg\\bin\\')
    encoders = {}
    enc_libx264 = Encoder(
        {
        'Name':         'libx264',
        'Type':         'video',
        'General':      ['dr1', 'delay', 'threads'],
        'Threading':    ['other'],
        'Color coding':                  {'option': '-pix_fmt',
                                          'values': ['yuv420p', 'yuvj420p', 'yuv422p', 'yuvj422p', 'yuv444p', 'yuvj444p', 'yuv420p10le', 'yuv422p10le', 'yuv444p10le', 'gray', 'gray10le'],
                                          'current': 'yuv420p',
                                          'fixed': True},
        'Options':
            {
            'Preset':                    {'option': '-preset',
                                          'values': ['medium', 'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'slow', 'veryslow', 'placebo'],
                                          'current': 'slow',
                                          'fixed': True},
            'Tune':                      {'option': '-tune',
                                          'values': ['film', 'grain', 'animation', 'zerolatency', 'fastdecode', 'stillimage'],
                                          'current': 'film',
                                          'fixed': True},
            'Rate control':
                {
                'Constant quantization': {'option': '-crf' ,
                                          'values': ['256k', '512k', '1M', '2M', '4M', '8M', '10M', '20M', '40M'],
                                          'current': '10M',
                                          'fixed': False},
                'Constant quality':      {'option': '-qp',
                                          'values': ['1M', '2M', '4M', '8M', '10M', '20M', '40M'],
                                          'current': '10M',
                                          'fixed': False}
                },
            'Lookahead':                 {'option': 'rc-lookahead',
                                          'values': [-1, 5, 10, 25, 30, 50, 100],
                                          'current': 25,
                                          'fixed': False}
            }
        })
    encoders['libx264'] = enc_libx264
    source_files = {} 
    app.MainLoop()
