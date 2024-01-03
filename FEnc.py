import sys, os, subprocess, re, json, argparse
import datetime as dt
from typing import Self
from enum import Enum
from pathlib import Path, PurePath
import wx
import wx.propgrid as wxpg
import wx.adv as wxadv


class MediaType(Enum):
    VIDEO =    0, 'Video'
    IMAGE =    1, 'Image(s)'
    SEQUENCE = 2, 'Sequence'
    AUDIO =    3, 'Audio'
    DATA =     4, 'Data'

    def __init__(self, id: int, doc: str):
        self.id = id
        self.doc = doc

class Encoders():

    Collection = []
    ClassName = 'Encoder'

    def __init__(self, *args, **kwargs):
        self.index = Encoders.EncodersCount()
        self.name: str = kwargs.get('name')
        self.type: str = kwargs.get('type')
        self.system: bool = kwargs.get('system')
        self.general: list = kwargs.get('general')
        self.threading: list = kwargs.get('threading')
        self.formats: list = kwargs.get('formats')
        self.audio_codecs: list = kwargs.get('audio_codecs')
        self.colorcodings: dict = kwargs.get('colorcodings')
        self.options: dict = kwargs.get('options')

    @classmethod
    def Add(cls, *args, **kwargs):
        cls.Collection.append(cls(*args, **kwargs))

    @classmethod
    def GetEncoderByIndex(cls, index: int):
        return cls.Collection[index]

    @classmethod
    def GetEncoderByName(cls, name: str):
        for preset in cls.Collection:
            if preset.name == name:
                return preset
        return None

    @classmethod
    def EncodersCount(cls) -> int:
        return len(cls.Collection)
    
    @classmethod
    def GetEncoderNames(cls, type: MediaType) -> list:
        return [enc.name for enc in cls.Collection if enc.type == type and enc.system == False]

class VideoPresets():

    Collection = []
    ClassName = 'Video preset'

    def __init__(self, name: str, encoder: Encoders, encoder_format: str, system: bool = False, editable: bool = True):
        self.name = name
        self.index = VideoPresets.PresetCount()
        self.system = system
        self.editable = editable
        self.encoder = encoder
        self.encoder_options = encoder.options
        self.encoder_format = encoder_format

    @classmethod
    def Add(cls, name: str, encoder: Encoders, encoder_format: str, system: bool = False, editable: bool = True):
        cls.Collection.append(cls(name, encoder, encoder_format, system, editable))

    @classmethod
    def GetPresetByName(cls, name: str) -> Self:
        for preset in cls.Collection:
            if preset.name == name:
                return preset
        return None
            
    @classmethod
    def GetPresetByIndex(cls, index: int) -> Self:
        return cls.Collection[index]
    
    @classmethod
    def PresetCount(cls) -> int:
        return len(cls.Collection)
    
    @classmethod
    def PresetNameList(cls) -> list:
        return [preset.name for preset in cls.Collection]

    def SetVideoEncoder(self, encoder: Encoders) -> Self:
        self.encoder = encoder
        self.system = encoder.system
        self.editable = True
        self.encoder_options = encoder.options
        self.encoder_format = encoder.formats[0]
        return self

    def GetValueIndex(self, options_list: list, suboption_name: str) -> int:
        for i, suboption in enumerate(options_list):
            if suboption['name'] == suboption_name:
                return i

class AudioPresets():

    Collection = []
    ClassName = 'Audio preset'

    def __init__(self, name: str, encoder: Encoders, encoder_format: str, system: bool = False, editable: bool = True):
        self.name = name
        self.index = AudioPresets.Count()
        self.system = system
        self.editable = editable
        self.encoder = encoder
        self.encoder_options = encoder.options
        self.encoder_format = encoder_format

    @classmethod
    def Add(cls, name: str, encoder: Encoders, encoder_format: str, system: bool = False, editable: bool = True):
        cls.Collection.append(cls(name, encoder, encoder_format, system, editable))

    @classmethod
    def GetByName(cls, name: str):
        for preset in cls.Collection:
            if preset.name == name:
                return preset
            return None
            
    @classmethod
    def GetByIndex(cls, index: int):
        return cls.Collection[index]
    
    @classmethod
    def Count(cls) -> int:
        return len(cls.Collection)
    
    @classmethod
    def NameList(cls) -> list:
        return [preset.name for preset in cls.Collection]    

class MediaFiles():

    Collection = []

    def __init__(self, filepath: str):
        self.id = MediaFiles.Count()+1 # starting at 1 to correspond to the list
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
        app.frame.list_files.Append([self.id, self.filepath, self.type.doc, 'Not set', 'Not set']) 
        self.log_panel = app.frame.log_add(self.filename, self)
        app.frame.flog(text=f'File "{self.filename}" added.')
        app.frame.flog(self.log_panel, f'File "{self.filename}" added.')
        print('Init: Media added:', filepath)


    def __new__(cls, filepath: str):
        if cls.GetByFilepath(filepath) is None:
            print('instance added')
            return super(MediaFiles, cls).__new__(cls)
        else:
            print('instance not added')
            app.frame.flog(text=f'File {filepath} was already added to the sources. Skipped.')
            return None

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
            app.frame.flog(text=f'Re-probing file "{self.filename}" as sequence.')
            probe_param[9:9] = sequence_param
        else:
            app.frame.flog(text=f'Probing file "{self.filename}".')
        try:
            probe = subprocess.check_output(probe_param, encoding='utf-8')
        except:
            app.frame.flog(text=f'Unable to add file "{self.filename}". Check if it\'s a media file. Skipped.')
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
            self.type = MediaType.IMAGE
            # detect frame counter
            rs = re.compile(r'\d{3,6}$')
            counter_match = rs.search(self.basename)
            if counter_match is not None:
                self.type = MediaType.SEQUENCE
                self.counter_length: str = len(counter_match.group())
                self.filepath = self.filepath.replace(self.filename, '') # cut off filename
                self.basename = self.basename.replace(counter_match.group(), f'%0{self.counter_length}d')
                self.filename = self.basename + self.extension
                self.filepath += self.filename # add the updated filename back
                # re-probe as sequence now
                self.probe(['-pattern_type', 'sequence', '-framerate', str(self.format.get('r_frame_rate', self.out_framerate)), '-start_number', '0'])
        elif has_tags(fn, ffmpeg.formats_audio):
            self.type = MediaType.AUDIO
        elif has_tags(fn, ffmpeg.formats_video):
            self.type = MediaType.VIDEO
        else:
            self.type = MediaType.DATA
   
    @classmethod
    def Add(cls, filepath: str):
        cls.Collection.append(cls(filepath))
    
    @classmethod
    def GetIndex(cls, media) -> int:
        return cls.Collection.index(media)
    
    @classmethod
    def GetIdByFilepath(cls, filepath: str) -> int:
        return cls.GetByFilepath(filepath).id

    @classmethod
    def GetByIndex(cls, index: int):
        return cls.Collection[index]

    @classmethod
    def GetByFilepath(cls, filepath: str):
        for media in cls.Collection:
            if media.filepath == filepath:
                return media
        return None
    
    @classmethod
    def GetIndexByFilepath(cls, filepath: str) -> int:
        return cls.GetIndex(cls.GetByFilepath(filepath))

    @classmethod
    def Count(cls) -> int:
        return len(cls.Collection)

    @classmethod
    def SetVideo(cls, file_name: str, preset: VideoPresets):
        index = cls.GetIndex(cls.GetByFilepath(file_name))
        cls.Collection[index].video_preset = preset

    @classmethod
    def SetAudio(cls, file_name: str, preset: AudioPresets):
        index = cls.GetIndex(cls.GetByFilepath(file_name))
        cls.Collection[index].audio_preset = preset

    @classmethod
    def Delete(cls, filepath):
        app.frame.tree_file_info.DeleteAllItems()
        media = cls.GetByFilepath(filepath)
        file_index = cls.GetIndexByFilepath(filepath)
        file_id = media.id
        file_item = app.frame.item_by_fileid(str(file_id))
        app.frame.list_files.DeleteItem(file_item)
        app.frame.log_pop(media.log_panel)
        cls.Collection.pop(file_index)
        app.frame.flog(text=f'File "{filepath}" deleted.')

class FileDropTarget(wx.FileDropTarget): 
    # !TODO! can also respond to Ctr/Shif/Alt, it's useful for more features
    def __init__(self, listbox):
        wx.FileDropTarget.__init__(self)
        self.listbox = listbox

    def OnDropFiles(self, x, y, filepaths):
        app.frame.flog(text=f'Adding {len(filepaths)} files...')
        app.frame.list_files.Select(-1)
        for filepath in filepaths:
            MediaFiles.Add(filepath)
        return True

class MyMainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MyFrame.__init__
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.SetSize((900, 900))
        self.SetTitle(MyApp.ver)
        self.video_preset = None
        self.audio_preset = None
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
        sizer_main.Add(sizer_presets, 3, wx.BOTTOM | wx.EXPAND | wx.TOP, 0)

        # Video presets panel
        self.nb_video = wx.Notebook(self.panel_main, wx.ID_ANY, style=wx.NB_BOTTOM | wx.NB_FIXEDWIDTH)
        sizer_presets.Add(self.nb_video, 1, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        self.nb_video_select = wx.Panel(self.nb_video, wx.ID_ANY)
        self.nb_video_select.SetToolTip("List of video presets")
        self.nb_video.AddPage(self.nb_video_select, "Video preset")

        sizer_nb_video_select = wx.BoxSizer(wx.VERTICAL)

        # Video preset list
        self.list_video_preset = wx.ListBox(self.nb_video_select, wx.ID_ANY, choices=VideoPresets.PresetNameList(), style=wx.LB_NEEDED_SB | wx.LB_SINGLE | wx.LB_OWNERDRAW)
        sizer_nb_video_select.Add(self.list_video_preset, 1, wx.ALL | wx.EXPAND, 3)
        self.list_video_preset.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.list_video_preset.SetItemForegroundColour(0, wx.Colour(80,10,10)) 
        self.list_video_preset.SetItemForegroundColour(1, wx.Colour(80,10,10))
        self.list_video_preset.SetItemForegroundColour(2, wx.Colour(80,80,80))
        self.list_video_preset.SetItemForegroundColour(3, wx.Colour(80,80,80))
        #self.list_video_preset.SetSelection(0)
        #self.prop_video_show()

        self.nb_video_edit = wx.Panel(self.nb_video, wx.ID_ANY)
        self.nb_video_edit.SetToolTip("Video preset editor")
        self.nb_video.AddPage(self.nb_video_edit, "Edit")

        sizer_nb_video_edit = wx.BoxSizer(wx.VERTICAL)

        self.prop_video_preset = wxpg.PropertyGridManager(self.nb_video_edit, wx.ID_ANY, style=wxpg.PG_NO_INTERNAL_BORDER | wxpg.PG_BOLD_MODIFIED)
        sizer_nb_video_edit.Add(self.prop_video_preset, 9, wx.ALL | wx.EXPAND, 3)

        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_nb_video_edit.Add(sizer_2, 0, wx.EXPAND, 0)

        # Video preset buttons
        self.button_save_video_preset = wx.Button(self.nb_video_edit, wx.ID_ANY, "Save")
        self.button_save_video_preset.SetToolTip("Save preset")
        sizer_2.Add(self.button_save_video_preset, 1, wx.ALL | wx.EXPAND, 5)

        self.button_dup_video_preset = wx.Button(self.nb_video_edit, wx.ID_ANY, "Duplicate")
        self.button_dup_video_preset.SetToolTip("Make a copy")
        sizer_2.Add(self.button_dup_video_preset, 0, wx.ALL | wx.EXPAND, 5)

        self.button_del_video_preset = wx.Button(self.nb_video_edit, wx.ID_ANY, "Delete")
        self.button_del_video_preset.SetToolTip("Delete preset")
        sizer_2.Add(self.button_del_video_preset, 0, wx.ALL | wx.EXPAND, 5)

        # Audio presets panel
        self.nb_audio = wx.Notebook(self.panel_main, wx.ID_ANY, style=wx.NB_BOTTOM | wx.NB_FIXEDWIDTH)
        sizer_presets.Add(self.nb_audio, 1, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        self.nb_audio_select = wx.Panel(self.nb_audio, wx.ID_ANY)
        self.nb_audio.AddPage(self.nb_audio_select, "Audio preset")

        sizer_nb_audio_select = wx.BoxSizer(wx.VERTICAL)

        # Audio preset list
        self.list_audio_preset = wx.ListBox(self.nb_audio_select, wx.ID_ANY, choices=AudioPresets.NameList(), style=wx.LB_NEEDED_SB | wx.LB_SINGLE | wx.LB_OWNERDRAW)
        self.list_audio_preset.SetBackgroundColour(wx.Colour(240, 240, 240))
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

        # Audio preset buttons
        self.button_save_audio_preset = wx.Button(self.nb_audio_edit, wx.ID_ANY, "Save audio preset")
        self.button_save_audio_preset.SetToolTip("Save preset")
        sizer_3.Add(self.button_save_audio_preset, 1, wx.ALL | wx.EXPAND, 5)

        self.button_dup_audio_preset = wx.Button(self.nb_audio_edit, wx.ID_ANY, "Duplicate")
        self.button_dup_audio_preset.SetToolTip("Make a copy")
        sizer_3.Add(self.button_dup_audio_preset, 0, wx.ALL | wx.EXPAND, 5)

        self.button_del_audio_preset = wx.Button(self.nb_audio_edit, wx.ID_ANY, "Delete")
        self.button_del_audio_preset.SetToolTip("Delete preset")
        sizer_3.Add(self.button_del_audio_preset, 0, wx.ALL | wx.EXPAND, 5)

        # File sources
        sizer_files = wx.FlexGridSizer(2, 2, 0, 0)
        sizer_main.Add(sizer_files, 2, wx.BOTTOM | wx.EXPAND | wx.TOP, 5)

        label_file_list = wx.StaticText(self.panel_main, wx.ID_ANY, "Sources")
        sizer_files.Add(label_file_list, 3, wx.LEFT | wx.TOP, 5)

        label_file_info = wx.StaticText(self.panel_main, wx.ID_ANY, "Source info")
        sizer_files.Add(label_file_info, 1, wx.LEFT | wx.TOP, 5)

        self.list_files = wx.ListCtrl(self.panel_main, wx.ID_ANY, style=wx.BORDER_NONE | wx.LC_HRULES | wx.LC_REPORT) # | wx.LC_SINGLE_SEL
        self.list_files.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=25)
        self.list_files.AppendColumn("File", format=wx.LIST_FORMAT_LEFT, width=320)
        self.list_files.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_files.AppendColumn("Video preset", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_files.AppendColumn("Audio preset", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_files.ShowSortIndicator(0)
        sizer_files.Add(self.list_files, 3, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        # File sources info
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
        self.nb_log = wx.Notebook(self.panel_main, wx.ID_ANY)
        sizer_main.Add(self.nb_log, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.flog_tab = self.log_add('FFEnc log', None) # [{'panel':,'sizer':,'text':}]

        # Encoded
        label_queue = wx.StaticText(self.panel_main, wx.ID_ANY, "Results", style=wx.ALIGN_LEFT)
        sizer_main.Add(label_queue, 0, wx.LEFT | wx.TOP, 5)

        self.list_queue = wx.ListCtrl(self.panel_main, wx.ID_ANY, style=wx.BORDER_NONE | wx.LC_HRULES | wx.LC_LIST | wx.LC_SINGLE_SEL)
        sizer_main.Add(self.list_queue, 1, wx.ALL | wx.EXPAND, 5)

        # Layout
        sizer_files.AddGrowableRow(1)
        sizer_files.AddGrowableCol(0)
        sizer_files.AddGrowableCol(1)

        self.flog_tab['panel'].SetSizer(self.flog_tab['sizer'])
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
        self.prop_video_preset.Bind(wxpg.EVT_PG_CHANGED, self.pg_changed)

        # Bind dnd
        dt = FileDropTarget(self.list_files)
        self.list_files.SetDropTarget(dt)
    
    def encode(self, event):  
        notify("Encoding is not implemetnted yet")

    def file_selected(self, event):
        item_file = self.list_files.GetFirstSelected()
        item_filepath = self.list_files.GetItemText(item_file, 1)
        self.tree_file_info.DeleteAllItems()
        media = MediaFiles.GetByFilepath(item_filepath)
        if media is not None:
            print('selected list item:', item_file, 'file id:', media.id, 'path:', item_filepath)
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
        file_item = self.list_files.GetFirstSelected()
        if file_item != wx.NOT_FOUND:
            filepath = self.list_files.GetItemText(file_item, 1)
            MediaFiles.Delete(filepath)

    def GetSelectedVideoPreset(self) -> VideoPresets:
        preset_item = self.list_video_preset.GetSelection()
        if preset_item != wx.NOT_FOUND:
            return VideoPresets.GetPresetByIndex(preset_item)
        else:
            return None

    def video_preset_selected(self, event):
        self.video_preset = self.GetSelectedVideoPreset()
        if self.video_preset.system is False: 
            self.prop_video_show()

    def video_preset_activated(self, event):
        file_item = self.list_files.GetFirstSelected()
        if self.video_preset is not None:
            if file_item != wx.NOT_FOUND:
                while file_item != wx.NOT_FOUND:
                    file_name = self.list_files.GetItemText(file_item, 1)
                    MediaFiles.SetVideo(file_name, self.video_preset)
                    self.list_files.SetItem(file_item, 3, self.video_preset.name)
                    file_item = self.list_files.GetNextSelected(file_item)
            else:
                if self.video_preset.system is False: 
                    self.prop_video_show()
                    self.nb_video.ChangeSelection(1)
        else:
            raise Exception('Video preset selection was lost. This is a bug, report!')

    def audio_preset_selected(self, event):
        #preset_item = self.list_audio_preset.GetSelection()
        #self.prop_audio_show(AudioPresets.GetByIndex(preset_item))
        pass

    def audio_preset_activated(self, event):
        file_item = self.list_files.GetFirstSelected()
        preset_item = self.list_audio_preset.GetSelection()
        if preset_item != wx.NOT_FOUND:
            preset = AudioPresets.GetByIndex(preset_item)
            if file_item != wx.NOT_FOUND:
                while file_item != wx.NOT_FOUND:
                    file_name = self.list_files.GetItemText(file_item, 1)
                    MediaFiles.SetAudio(file_name, preset)
                    self.list_files.SetItem(file_item, 4, preset.name)
                    file_item = self.list_files.GetNextSelected(file_item)
            else:
                if preset.system is False:
                    self.prop_audio_show(preset)
                    self.nb_audio.ChangeSelection(1)

    def prop_video_show(self):
        print('selected preset index=', self.video_preset.index, 'name=', self.video_preset.name, 'encoder=', self.video_preset.encoder.name)
        self.prop_video_preset.Clear()
        self.vp_page = self.prop_video_preset.AddPage("Video Settings")
        self.vp_page.Append(wxpg.PropertyCategory("Video Preset"))
        self.vp_page.Append(wxpg.StringProperty("Name", wxpg.PG_LABEL, self.video_preset.name))
        self.vp_page.Append(wxpg.PropertyCategory("Codec"))
        list_encoders = Encoders.GetEncoderNames(MediaType.VIDEO)
        self.vp_page.Append(wxpg.EditEnumProperty("Encoder", wxpg.PG_LABEL, list_encoders, range(len(list_encoders)), value=self.video_preset.encoder.name))
        self.vp_page.Append(wxpg.PropertyCategory("Container"))
        self.vp_page.Append(wxpg.EditEnumProperty("Format", wxpg.PG_LABEL, self.video_preset.encoder.formats, range(len(self.video_preset.encoder.formats)), value=self.video_preset.encoder_format))
        self.vp_page.Append(wxpg.PropertyCategory("Encoder options"))
    
        for optionkey, optionval in self.video_preset.encoder_options.items():
            #print('adding op:', optionkey)
            if optionval['fixed']:
                enum_prop = wxpg.EnumProperty
                # Enum prop restricted case, and wxpg requires int default value
                if type(optionval['values'][0]) != dict:
                    current = optionval['values'].index(optionval['current'])
                else:
                    for i, x in enumerate(optionval['values']):
                        if x['name'] == optionval['current']:
                            current = i
                            break
            else:
                # Enum prop editable case, and wxpg requires str default value
                enum_prop = wxpg.EditEnumProperty
                current = optionval['current']

            if type(optionval['values'][0]) == dict: # if elements are dicts get the list of name keys
                opt_values = [x['name'] for x in optionval['values']]
                self.vp_page.Append(enum_prop(optionkey, wxpg.PG_LABEL, opt_values, range(len(opt_values)), value=current))
                if optionval['values'][current].get('suboptions', None) is not None: 
                    print('theres subs in', optionval['values'][current]['name'])
                    for suboption in optionval['values'][current]['suboptions']:
                        self.vp_page.Append(wxpg.EditEnumProperty(suboption['name'], wxpg.PG_LABEL, suboption['values'], range(len(suboption['values'])), value=suboption['current']))
            else: # list type
                self.vp_page.Append(enum_prop(optionkey, wxpg.PG_LABEL, optionval['values'], range(len(optionval['values'])), value=current))

            # next to add !TODO! color data and transform filters

    def pg_changed(self, event: wxpg.PropertyGridEvent):
        print('video prop changed item:', event.PropertyName, 'to value:', event.Value)
        val_int = type(event.Value) == int
        match event.PropertyName:
            case 'Encoder':
                list_encoders = Encoders.GetEncoderNames(MediaType.VIDEO)
                val = list_encoders[event.Value] if val_int else event.Value
                self.video_preset = self.video_preset.SetVideoEncoder(Encoders.GetEncoderByName(val))
            case 'Format':
                val = self.video_preset.encoder.formats[event.Value] if val_int else event.Value
                self.video_preset.encoder_format = val
            case 'Color coding':
                val = self.video_preset.encoder.options['Color coding']['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Color coding'].update({'current': val})
            case 'Rate control':
                opt_values = [x['name'] for x in self.video_preset.encoder.options['Rate control']['values']]
                val = opt_values[event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Rate control'].update({'current': val})
            case 'Preset':
                val = self.video_preset.encoder_options['Preset']['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Preset'].update({'current': val})
            case 'Tune':
                val = self.video_preset.encoder_options['Tune']['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Tune'].update({'current': val})
            case 'Profile':
                val = self.video_preset.encoder_options['Profile']['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Profile'].update({'current': val})
            case 'Lookahead':
                val = self.video_preset.encoder_options['Lookahead']['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Lookahead'].update({'current': val})
            case 'Quality':
                branch = self.video_preset.encoder_options['Rate control']
                index = self.video_preset.GetValueIndex(branch['values'], branch['current'])
                branch = self.video_preset.encoder_options['Rate control']['values'][index]['suboptions']
                subindex = self.video_preset.GetValueIndex(branch, 'Quality')
                val = branch[subindex]['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Rate control']['values'][index]['suboptions'][subindex].update({'current': val})
            case 'Max quality':
                branch = self.video_preset.encoder_options['Rate control']
                index = self.video_preset.GetValueIndex(branch['values'], branch['current'])
                branch = self.video_preset.encoder_options['Rate control']['values'][index]['suboptions']
                subindex = self.video_preset.GetValueIndex(branch, 'Max quality')
                val = branch[subindex]['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Rate control']['values'][index]['suboptions'][subindex].update({'current': val})
            case 'Bitrate':
                branch = self.video_preset.encoder_options['Rate control']
                index = self.video_preset.GetValueIndex(branch['values'], branch['current'])
                branch = self.video_preset.encoder_options['Rate control']['values'][index]['suboptions']
                subindex = self.video_preset.GetValueIndex(branch, 'Bitrate')
                val = branch[subindex]['values'][event.Value] if val_int else event.Value
                self.video_preset.encoder_options['Rate control']['values'][index]['suboptions'][subindex].update({'current': val})
        #print('\nafter update preset_encoder_options=', preset.encoder_options)
        self.prop_video_show()


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

    def log_add(self, title: str, media: MediaFiles) -> dict:
        tab = {}
        tab['panel'] = wx.Panel(self.nb_log, wx.ID_ANY)
        self.nb_log.AddPage(tab['panel'], select=True, text=title)

        tab['sizer'] = wx.BoxSizer(wx.HORIZONTAL)

        tab['text'] = wx.TextCtrl(tab['panel'], wx.ID_ANY, '', style=wx.BORDER_NONE | wx.HSCROLL | wx.TE_AUTO_URL | wx.TE_BESTWRAP | wx.TE_MULTILINE | wx.TE_NOHIDESEL | wx.TE_READONLY | wx.TE_RICH2)
        tab['text'].SetBackgroundColour(wx.Colour(208, 208, 208))
        tab['sizer'].Add(tab['text'], 1, wx.ALL | wx.EXPAND, 3)

        tab['panel'].SetSizer(tab['sizer'])
        tab['panel'].Layout()
        page = self.nb_log.FindPage(tab['panel'])
        self.nb_log.SetSelection(page)
        return tab

    def log_pop(self, tab: dict):
        self.nb_log.SetSelection(0)
        tab['sizer'].Remove(0)
        pn = self.nb_log.FindPage(tab['panel'])
        self.nb_log.DeletePage(pn) 

    def nb_switched(self, event):
        selected = self.nb_log.GetSelection()
        if selected != wx.NOT_FOUND:
            if selected == 0:
                for item in range(self.list_files.GetItemCount()):
                    self.list_files.Select(item, 1)
            else:
                for item in range(self.list_files.GetItemCount()):
                    self.list_files.Select(item, 1 if item == selected-1 else 0)

    def item_by_fileid(self, fileid: str):
        item_index = self.list_files.FindItem(start=-1,str=fileid)
        if item_index == wx.NOT_FOUND:
            raise Exception('Internal file list error. This is a bug, report!')
        else:
            return item_index

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

    def flog(self, tab: dict=None, text: str=''):
        if tab is None: tab = self.flog_tab
        timestamp = dt.datetime.strftime(dt.datetime.now(), '%H:%M:%S')
        if tab['text'].GetValue() != '':
            tab['text'].AppendText(f'\n{timestamp}: {text}')
        else:
            tab['text'].SetValue(f'{timestamp}: {text}')

class MyApp(wx.App):
    ver = 'FFEnc v0.09a'
    def OnInit(self):
        self.frame = MyMainFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

class FFmpeg():
    formats_video = ['mp4','mov','webm','dnxhd','mxf','avi','mpeg','mpegts','dv','flv','matroska','apng','exr','gif','jpg','png','tif','dds']
    #codecs_video =  ['prores','libx264','libx265', 'h264_nvenc','hevc_nvenc','h264_qsv','hevc_qsv','libvpx-vp9','vp9_qsv','mpeg2video','mpeg2_qsv','libx265dnxhd','mpegts','dvvideo','flv1','gif','apng','png','mjpeg','tiff','dds','HDR','WebP']
    color_spaces =  ['bt709', 'bt2020nc', 'bt2020c', 'rgb', 'bt470bg', 'smpte170m', 'smpte240m', 'smpte2085', 'ycocg']
    color_ranges =  ['tv', 'pc', 'mpeg', 'jpeg']
    formats_audio = ['Video container','ac3','wav','mp3','ogg','flac','aiff','alac']
    codecs_audio =  ['aac','ac3','flac','alac','dvaudio','pcm_s16le','pcm_s24le','pcm_s32le','pcm_f32le']
    sequence_tags = ['image2','pipe']

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
            app.frame.flog(text=f'FFmpeg executable found at {self.ffmpegexe}')
        else:
            app.frame.flog(text=f'FFmpeg executable not found at {self.ffmpegexe}')
        my_file = Path(self.ffprobeexe)
        if my_file.is_file():
            app.frame.flog(text=f'FFprobe executable found at {self.ffprobeexe}')
        else:
            app.frame.flog(text=f'FFprobe executable not found at {self.ffprobeexe}')

class Filter():
    pass

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

    # Add system codecs
    # No video
    Encoders.Add(
        name=         'No video',
        type=         MediaType.VIDEO,
        system=       True,
        options=      {'ffoption': None}
    )
    # No audio
    Encoders.Add(
        name=         'No audio',
        type=         MediaType.AUDIO,
        system=       True,
        options=      {'ffoption': None}
    )
    # Video stream copy
    Encoders.Add(
        name=         'Video stream copy',
        type=         MediaType.VIDEO,
        system=       True,
        options=      {'ffoption': '-c:v copy'}
    )
    # Audio stream copy
    Encoders.Add(
        name=         'Audio stream copy',
        type=         MediaType.AUDIO,
        system=       True,
        options=      {'ffoption': '-c:a copy'}
    )     
    # Nearly default libx264 mp4
    Encoders.Add(
        name=         'libx264',
        type=         MediaType.VIDEO,
        system=       False,
        general=      ['dr1', 'delay', 'threads'],
        threading=    ['other'],
        formats=      ['mp4', 'mov'],
        audio_codecs= ['aac', 'ac3', 'mp3', 'dts', 'mp2', 'alac', 'dvaudio'],
        options=      {
            'Color coding': {
                'ffoption': '-pix_fmt',
                'values': ['yuv420p', 'yuvj420p', 'yuv422p', 'yuvj422p', 'yuv444p', 'yuvj444p', 'yuv420p10le', 'yuv422p10le', 'yuv444p10le', 'gray', 'gray10le'],
                'current': 'yuv420p',
                'fixed': True
            },
            'Preset': {
                'ffoption': '-preset',
                'values': ['medium', 'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'slow', 'veryslow', 'placebo'],
                'current': 'slow',
                'fixed': False,
            },
            'Rate control': {
                'values': [
                    {
                        'name': 'Constant quality',
                        'ffoption': '-crf',
                        'suboptions': [
                            {
                            'name': 'Quality',
                            'values': ['-1', '0', '5', '10', '20', '25', '30', '40', '50'],
                            'current': '-1',
                            'fixed': False,
                            },
                            {
                            'name': 'Max quality',
                            'values': ['-1', '0', '5', '10', '20', '25', '30', '40', '50'],
                            'current': '-1',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name':'Constant quantization',
                        'ffoption': '-qp',
                        'suboptions': [ 
                            {
                            'name': 'Rate',
                            'values': ['-1', '5', '10', '20', '25', '30', '40', '51'],
                            'current': '25',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name':'AQ mode',
                        'ffoption': '-aq-mode',
                        'suboptions': [
                            {
                            'name': 'AQ method',
                            'values': ['-1', '0', '1', '2', '3'],
                            'current': '-1',
                            'fixed': True,
                            },
                            {
                            'name': 'AQ strength',
                            'values': ['-1', '0', '10', '20', '50', '100', '500'],
                            'current': '-1',
                            'fixed': False,
                            },
                        ],
                    },
                ],
                'current': 'Constant quality',
                'fixed': True,
            },
            'Tune': {
                'ffoption': '-tune',
                'values': ['film', 'grain', 'animation', 'zerolatency', 'fastdecode', 'stillimage'],
                'current': 'film', 
                'fixed': True,
            },
            'Lookahead': {
                'ffoption': '-rc-lookahead',
                'values': ['-1', '5', '10', '25', '30', '50', '100'],
                'current': '25',
                'fixed': False,
            },
        }
    )
    # Nearly default nv_enc264 mp4
    Encoders.Add(
        name=         'h264_nvenc',
        type=         MediaType.VIDEO,
        system=       False,
        general=      ['dr1', 'delay', 'hardware'],
        threading=    ['none'],
        formats=      ['mp4', 'mov'],
        audio_codecs= ['aac', 'ac3', 'mp3', 'dts', 'mp2', 'alac', 'dvaudio'],
        devices=      ['cuda', 'd3d11va'],
        options=
        {
            'Color coding': {
                'ffoption': '-pix_fmt',
                'values': ['yuv420p', 'yuv444p', 'yuv444p16le', 'p010le', 'p016le', 'bgr0', 'bgra', 'rgb0', 'rgba'],
                'current': 'yuv420p',
                'curindex': 0, 
                'fixed': False,
            },
            'Preset': {
                'ffoption': '-preset',
                'values': ['p1', 'p2', 'p3 ', 'p4', 'p5', 'p6', 'p7'],
                'current': 'p6',
                'fixed': False,
            },
            'Rate control': {
                'values': [
                    {
                        'name': 'Auto by preset',
                        'ffoption': '-rc -1',
                    },
                    {
                        'name': 'Constant QP mode',
                        'ffoption': '-rc constqp',
                        'suboptions': [
                            {
                            'name': 'Quality',
                            'ffoption': '-qp',
                            'values': ['-1', '0', '5', '10', '20', '25', '30', '40', '51'],
                            'current': '0',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name': 'Variable bitrate',
                        'ffoption': '-rc vbr',
                        'suboptions': [
                            {
                            'name':'Quality',
                            'ffoption': '-cq',
                            'values': ['0', '5', '10', '20', '25', '30', '40', '51'],
                            'current': '0',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name': 'Constant bitrate',
                        'ffoption': '-rc cbr',
                        'suboptions': [
                            {
                            'name': 'Bitrate', 
                            'ffoption': '-v:b',
                            'values': ['256k', '512k', '1M', '2M', '4M', '8M', '12M', '20M', '30M', '40M'],
                            'current': '8M',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name': 'Constant bitrate low delay high quality',
                        'ffoption': '-rc cbr_ld_hq',
                        'suboptions': [
                            {
                            'name': 'Bitrate', 
                            'ffoption': '-v:b',
                            'values': ['256k', '512k', '1M', '2M', '4M', '8M', '12M', '20M', '30M', '40M'],
                            'current': '8M',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name': 'Constant bitrate high quality mode',
                        'ffoption': '-rc cbr_hq',
                        'suboptions': [
                            {
                            'name': 'Bitrate', 
                            'ffoption': '-v:b',
                            'values': ['256k', '512k', '1M', '2M', '4M', '8M', '12M', '20M', '30M', '40M'],
                            'current': '8M',
                            'fixed': False,
                            },
                        ],
                    },
                    {
                        'name': 'Variable bitrate high quality',
                        'ffoption': '-rc vbr_hq',
                        'suboptions': [
                            {
                            'name':'Quality',
                            'ffoption': '-cq',
                            'values': ['0', '5', '10', '20', '25', '30', '40', '51'],
                            'current': '0',
                            'fixed': False,
                            },
                        ],
                    },
                ],
                'current': 'Auto by preset',
                'fixed': True,
            },
            'Tune': {
                'ffoption': '-tune',
                'values': ['hq', 'll', 'ull', 'lossless'],
                'current': 'hq',
                'fixed': True,
            },
            'Profile': {
                'ffoption': '-profile',
                'values': ['baseline', 'main', 'high', 'high444p'],
                'current': 'main',
                'fixed': True,
            },
            'Lookahead': {
                'ffoption': '-rc-lookahead',
                'values': ['-1', '5', '10', '25', '30', '50', '100'],
                'current': '25',
                'fixed': False,
            },
        }
    )
    
    # Add system codecs and presets
    VideoPresets.Add('No video', Encoders.GetEncoderByIndex(0), '', system=True, editable=False)
    VideoPresets.Add('Stream copy', Encoders.GetEncoderByIndex(1), '', system=True, editable=False)
    AudioPresets.Add('No audio', Encoders.GetEncoderByIndex(2), '', system=True, editable=False)
    AudioPresets.Add('Stream copy', Encoders.GetEncoderByIndex(3), '', system=True, editable=False)
    VideoPresets.Add('libx h264 420p cbr 8M slow', Encoders.GetEncoderByIndex(4), 'mp4', system=False, editable=True)
    VideoPresets.Add('nv h264 420p Preset p6-Better', Encoders.GetEncoderByIndex(5), 'mp4', system=False, editable=True)
    
    app = MyApp(0)
    app.frame.flog(text=f'{app.ver} started.')
    ffmpeg = FFmpeg('C:\\Program Files\\ffmpeg\\bin\\')
    app.MainLoop()
