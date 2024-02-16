import sys, os, subprocess, re, json, argparse
import datetime as dt
from typing import Self
from enum import Enum
from pathlib import Path, PurePath
import wx
import wx.richtext as rt
import wx.propgrid as pg
import wx.adv as adv

class MediaType(Enum):
    NONE  =    -1, 'Not media'
    VIDEO =    0,  'Video'
    IMAGE =    1,  'Image(s)'
    SEQUENCE = 2,  'Sequence'
    AUDIO =    3,  'Audio'
    DATA =     4,  'Data'

    def __init__(self, id: int, doc: str):
        self.id = id
        self.doc = doc

class Encoders():

    Collection = []
    ClassName = 'Encoder'
    video_filters = {
        'Scale filter': True,
        'Scale': {
            'ffoption': '-???', 
            'values':   ['-1', '320', '480', '720', '1080', '2160'],
            'current':  '-1',
            'doc':      'Scale video',
            'fixed':    False,
        },
        'Scale algo': {
            'ffoption': '-???', 
            'values':   ['bilinear', 'bicubic', 'bicublin', 'gauss', 'sinc', 'lanczos',],
            'current':  'bicubic',
            'doc':      'Scaling algorythm',
            'fixed':    False,
        },
    }
    audio_filters = {
        'Volume filter': True,
        'Volume': {
            'name':     'Volume',
            'ffoption': '-???', 
            'values':   ['25', '50', '75', '100', '125', '150'],
            'current':  '100',
            'doc':      'Change audio volume',
            'fixed':    False,
        }
    }

    def __init__(self, *args, **kwargs):
        self.index = Encoders.Count()
        self.name: str = kwargs.get('name')
        self.type: str = kwargs.get('type')
        self.system: bool = kwargs.get('system')
        self.general: list = kwargs.get('general')
        self.threading: list = kwargs.get('threading')
        self.formats: list = kwargs.get('formats')
        self.audio_codecs: list = kwargs.get('audio_codecs')
        self.colorcodings: dict = kwargs.get('colorcodings')
        self.options: dict = kwargs.get('options')
        if self.type == MediaType.VIDEO:
            self.options.update(self.video_filters)
        elif self.type == MediaType.AUDIO:
            self.options.update(self.audio_filters)

    @classmethod
    def Add(cls, *args, **kwargs):
        cls.Collection.append(cls(*args, **kwargs))

    @classmethod
    def ByIndex(cls, index: int):
        return cls.Collection[index]

    @classmethod
    def ByName(cls, name: str):
        for preset in cls.Collection:
            if preset.name == name:
                return preset
        return None

    @classmethod
    def Count(cls) -> int:
        return len(cls.Collection)
    
    @classmethod
    def Names(cls, type: MediaType) -> list:
        return [enc.name for enc in cls.Collection if enc.type == type and enc.system == False]

class VideoPresets():

    Collection = []
    ClassName = 'Video preset'
    wx_color_sys = wx.Colour(80,10,10)
    wx_color = wx.Colour(80,80,80)  

    def __init__(self, name: str, encoder: Encoders, default_format: str, system: bool = False):
        if encoder.type == MediaType.VIDEO:
            self.name = name
            self.index = VideoPresets.Count()
            self.system = system
            self.encoder = encoder
            self.encoder_options = encoder.options
            self.default_format = default_format
            self.options = self.encoder.options
            list_count = app.frame.list_vp.GetCount()
            app.frame.list_vp.InsertItems([self.name], list_count)
            if self.system: app.frame.list_vp.SetItemForegroundColour(list_count, self.wx_color_sys) 
        else:
            raise Exception('You are trying to assing a non-video Encoder to a video preset.')

    @classmethod
    def Add(cls, name: str, encoder: Encoders, default_format: str, system: bool = False):
        cls.Collection.append(cls(name, encoder, default_format, system))

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
    def Count(cls) -> int:
        return len(cls.Collection)
    
    @classmethod
    def NameList(cls) -> list:
        return [preset.name for preset in cls.Collection]

    def SetVideoEncoder(self, encoder: Encoders) -> Self:
        self.encoder = encoder
        self.system = encoder.system
        self.editable = True
        self.encoder_options = encoder.options
        self.default_format = encoder.formats[0]
        return self

    def GetValueIndex(self, options_list: list, suboption_name: str) -> int:
        for i, suboption in enumerate(options_list):
            if suboption['name'] == suboption_name:
                return i

class AudioPresets():

    Collection = []
    ClassName = 'Audio preset'
    wx_color_sys = wx.Colour(80,10,10)
    wx_color = wx.Colour(80,80,80)  

    def __init__(self, name: str, encoder: Encoders, default_format: str, system: bool = False, editable: bool = True):
        if encoder.type == MediaType.AUDIO:
            self.name = name
            self.index = AudioPresets.Count()
            self.system = system
            self.editable = editable
            self.encoder = encoder
            self.encoder_options = encoder.options
            self.default_format = default_format
            list_count = app.frame.list_ap.GetCount()
            app.frame.list_ap.InsertItems([self.name], list_count)
            if self.system: app.frame.list_ap.SetItemForegroundColour(list_count, self.wx_color_sys) 
        else:
            raise Exception('You are trying to assing a non-audio Encoder to a video preset.')

    @classmethod
    def Add(cls, name: str, encoder: Encoders, default_format: str, system: bool = False, editable: bool = True):
        cls.Collection.append(cls(name, encoder, default_format, system, editable))

    @classmethod
    def ByName(cls, name: str) -> Self:
        for preset in cls.Collection:
            if preset.name == name:
                return preset
            return None
            
    @classmethod
    def ByIndex(cls, index: int) -> Self:
        return cls.Collection[index]
    
    @classmethod
    def Count(cls) -> int:
        return len(cls.Collection)
    
    @classmethod
    def Names(cls) -> list:
        return [preset.name for preset in cls.Collection]
    
    def SetAudioEncoder(self, encoder: Encoders) -> Self:
        self.encoder = encoder
        self.system = encoder.system
        self.editable = True
        self.encoder_options = encoder.options
        self.default_format = encoder.formats[0]
        return self

class MediaFiles():

    Collection: list[Self] = []

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
        app.frame.list_sources.Append([self.id, self.filepath, self.type.doc, 'Not set', 'Not set']) 
        self.log_panel = app.frame.log_add(self.filename, self)
        app.frame.flog(text='File', file=self.filename, end='added.')
        app.frame.flog(tab=self.log_panel, text='File', file=self.filename, end='added.')
        print('Init: Media added:', filepath)


    def __new__(cls, filepath: str):
        result = None
        if cls.GetByFilepath(filepath) is None:
            if cls.probe_type(filepath):
                result = super(MediaFiles, cls).__new__(cls)
        else:
            app.frame.flog(text='File', file=filepath, end='is already in the sources. Skipped.')
        return result
   
    @classmethod
    def Add(cls, filepath: str):
        item = cls(filepath)
        if item is not None:
            cls.Collection.append(item)

    @classmethod
    def probe_type(cls, filename: str) -> bool:
        print('type probe')
        probe_param = [
            ffmpeg.ffprobeexe,
            '-v', 'error',
            '-hide_banner',
            filename]
        try:
            probe = subprocess.check_output(probe_param, encoding='utf-8')
        except:
            app.frame.flog(text=f'FFmpeg did not recognize', file=os.path.basename(filename), end='as media file')
            return False
        else:
            return True

    def probe(self, sequence_param: list = None):
        probe_param = [
                ffmpeg.ffprobeexe,
                '-v', 'error',
                '-hide_banner',
                '-show_streams',
                '-show_format',
                '-sexagesimal',
                '-of', 'json',
                self.filepath]
        if sequence_param is not None: 
            app.frame.flog(text='Re-probing file', file=self.filename, end='as sequence.')
            probe_param[9:9] = sequence_param
        else:
            app.frame.flog(text='Probing file', file=self.filename)
        try:
            probe = subprocess.check_output(probe_param, encoding='utf-8')
        except:
            app.frame.flog(text=f'Unable to add file', file=self.filename)
            self.format = None
            return None
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
    def GetIndex(cls, media) -> int:
        return cls.Collection.index(media)
    
    @classmethod
    def GetIdByFilepath(cls, filepath: str) -> int:
        return cls.GetByFilepath(filepath).id

    @classmethod
    def GetByIndex(cls, index: int) -> Self:
        return cls.Collection[index]

    @classmethod
    def GetByFilepath(cls, filepath: str) -> Self:
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
        app.frame.tree_info.DeleteAllItems()
        media = cls.GetByFilepath(filepath)
        file_index = cls.GetIndexByFilepath(filepath)
        file_id = media.id
        file_item = app.frame.item_by_fileid(str(file_id))
        app.frame.list_sources.DeleteItem(file_item)
        app.frame.log_pop(media.log_panel)
        cls.Collection.pop(file_index)
        app.frame.flog(text=f'File "{filepath}" deleted.')

class FileDropTarget(wx.FileDropTarget): 
    # !TODO! can also respond to Ctr/Shif/Alt, it's useful for more features
    def __init__(self, listbox):
        wx.FileDropTarget.__init__(self)
        self.listbox = listbox

    def OnDropFiles(self, x, y, filepaths):
        app.frame.flog(text='Adding', file=len(filepaths), end='files...')
        app.frame.list_sources.Select(-1)
        for filepath in filepaths:
            MediaFiles.Add(filepath)
        return True

class FFColor(Enum):
    TEXT = 1, (10, 10, 10)
    FILE = 2, (25, 50, 220)
    ERR  = 3, (250, 50, 50)

    def __init__(self, id: int, value: tuple[int,int,int]):
        self.id = id
        self._value_ = value

    @property
    def wx(self) -> tuple[int,int,int]:
        return self.value

class MyMainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        # begin wxGlade: MyFrame.__init__
        kwargs["style"] = kwargs.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwargs)

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

        self.panel_vp_select = wx.Panel(self.nb_video, wx.ID_ANY)
        self.panel_vp_select.SetToolTip("List of video presets")
        self.nb_video.AddPage(self.panel_vp_select, "Video preset")

        sizer_vp_select = wx.BoxSizer(wx.VERTICAL)

        # Video preset list
        self.list_vp = wx.ListBox(self.panel_vp_select, wx.ID_ANY, choices=[], style=wx.LB_NEEDED_SB | wx.LB_SINGLE | wx.LB_OWNERDRAW)
        sizer_vp_select.Add(self.list_vp, 1, wx.ALL | wx.EXPAND, 3)
        self.list_vp.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.list_vp.SetSelection(-1)

        # Video preset properties
        self.panel_vp_edit = wx.Panel(self.nb_video, wx.ID_ANY)
        self.panel_vp_edit.SetToolTip("Video preset editor")
        self.nb_video.AddPage(self.panel_vp_edit, "Edit")

        sizer_vp_edit = wx.BoxSizer(wx.VERTICAL)

        self.pg_vp = pg.PropertyGridManager(self.panel_vp_edit, wx.ID_ANY, style=pg.PG_BOLD_MODIFIED | pg.PG_EX_HELP_AS_TOOLTIPS | pg.PG_TOOLTIPS)
        sizer_vp_edit.Add(self.pg_vp, 9, wx.ALL | wx.EXPAND, 3)
        #self.prop_video_show()

        # Video preset buttons
        sizer_vp_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_vp_edit.Add(sizer_vp_buttons, 0, wx.EXPAND, 0)
        
        self.button_vp_save = wx.Button(self.panel_vp_edit, wx.ID_ANY, "Save")
        self.button_vp_save.SetToolTip("Save preset")
        sizer_vp_buttons.Add(self.button_vp_save, 1, wx.ALL | wx.EXPAND, 5)

        self.button_vp_dup = wx.Button(self.panel_vp_edit, wx.ID_ANY, "Duplicate")
        self.button_vp_dup.SetToolTip("Make a copy")
        sizer_vp_buttons.Add(self.button_vp_dup, 0, wx.ALL | wx.EXPAND, 5)

        self.button_vp_del = wx.Button(self.panel_vp_edit, wx.ID_ANY, "Delete")
        self.button_vp_del.SetToolTip("Delete preset")
        sizer_vp_buttons.Add(self.button_vp_del, 0, wx.ALL | wx.EXPAND, 5)

        # Audio presets panel
        self.nb_audio = wx.Notebook(self.panel_main, wx.ID_ANY, style=wx.NB_BOTTOM | wx.NB_FIXEDWIDTH)
        sizer_presets.Add(self.nb_audio, 1, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        self.nb_ap_select = wx.Panel(self.nb_audio, wx.ID_ANY)
        self.nb_audio.AddPage(self.nb_ap_select, "Audio preset")

        sizer_ap_select = wx.BoxSizer(wx.VERTICAL)

        # Audio preset list
        self.list_ap = wx.ListBox(self.nb_ap_select, wx.ID_ANY, choices=AudioPresets.Names(), style=wx.LB_NEEDED_SB | wx.LB_SINGLE | wx.LB_OWNERDRAW)
        self.list_ap.SetBackgroundColour(wx.Colour(240, 240, 240))
        sizer_ap_select.Add(self.list_ap, 1, wx.ALL | wx.EXPAND, 3)
        self.list_ap.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.list_ap.SetSelection(-1)

        # Audio preset properties
        self.nb_ap_edit = wx.Panel(self.nb_audio, wx.ID_ANY)
        self.nb_audio.AddPage(self.nb_ap_edit, "Edit")

        sizer_nb_ap_edit = wx.BoxSizer(wx.VERTICAL)

        self.pg_ap = pg.PropertyGridManager(self.nb_ap_edit, wx.ID_ANY, style=pg.PG_BOLD_MODIFIED | pg.PG_EX_HELP_AS_TOOLTIPS | pg.PG_TOOLTIPS)
        sizer_nb_ap_edit.Add(self.pg_ap, 9, wx.ALL | wx.EXPAND, 3)
        #self.prop_audio_show()

        # Audio preset buttons
        ap_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer_nb_ap_edit.Add(ap_buttons_sizer, 0, wx.EXPAND, 0)

        self.button_ap_save = wx.Button(self.nb_ap_edit, wx.ID_ANY, "Save audio preset")
        self.button_ap_save.SetToolTip("Save preset")
        ap_buttons_sizer.Add(self.button_ap_save, 1, wx.ALL | wx.EXPAND, 5)

        self.button_ap_dup = wx.Button(self.nb_ap_edit, wx.ID_ANY, "Duplicate")
        self.button_ap_dup.SetToolTip("Make a copy")
        ap_buttons_sizer.Add(self.button_ap_dup, 0, wx.ALL | wx.EXPAND, 5)

        self.button_ap_del = wx.Button(self.nb_ap_edit, wx.ID_ANY, "Delete")
        self.button_ap_del.SetToolTip("Delete preset")
        ap_buttons_sizer.Add(self.button_ap_del, 0, wx.ALL | wx.EXPAND, 5)

        # File sources
        sizer_sources = wx.FlexGridSizer(2, 2, 0, 0)
        sizer_main.Add(sizer_sources, 2, wx.BOTTOM | wx.EXPAND | wx.TOP, 5)

        label_file_list = wx.StaticText(self.panel_main, wx.ID_ANY, "Sources")
        sizer_sources.Add(label_file_list, 3, wx.LEFT | wx.TOP, 5)

        label_file_info = wx.StaticText(self.panel_main, wx.ID_ANY, "Source info")
        sizer_sources.Add(label_file_info, 1, wx.LEFT | wx.TOP, 5)

        self.list_sources = wx.ListCtrl(self.panel_main, wx.ID_ANY, style=wx.BORDER_NONE | wx.LC_HRULES | wx.LC_REPORT) # | wx.LC_SINGLE_SEL
        self.list_sources.AppendColumn("#", format=wx.LIST_FORMAT_LEFT, width=25)
        self.list_sources.AppendColumn("File", format=wx.LIST_FORMAT_LEFT, width=320)
        self.list_sources.AppendColumn("Type", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_sources.AppendColumn("Video preset", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_sources.AppendColumn("Audio preset", format=wx.LIST_FORMAT_LEFT, width=80)
        self.list_sources.ShowSortIndicator(0)
        sizer_sources.Add(self.list_sources, 3, wx.EXPAND | wx.LEFT | wx.TOP, 5)

        # File sources info
        self.tree_info = wx.TreeCtrl(self.panel_main, wx.ID_ANY, style=wx.TR_SINGLE | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT)
        self.tree_info.SetToolTip("Media file info")
        self.tree_info.SetBackgroundColour(wx.Colour(208, 208, 208))
        sizer_sources.Add(self.tree_info, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

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
        self.flog_tab = self.log_add('FFEnc', None) # {'panel':,'sizer':,'text':}

        # Encoded
        label_queue = wx.StaticText(self.panel_main, wx.ID_ANY, "Results", style=wx.ALIGN_LEFT)
        sizer_main.Add(label_queue, 0, wx.LEFT | wx.TOP, 5)

        self.list_queue = wx.ListCtrl(self.panel_main, wx.ID_ANY, style=wx.BORDER_NONE | wx.LC_HRULES | wx.LC_LIST | wx.LC_SINGLE_SEL)
        sizer_main.Add(self.list_queue, 1, wx.ALL | wx.EXPAND, 5)

        # Layout
        sizer_sources.AddGrowableRow(1)
        sizer_sources.AddGrowableCol(0)
        sizer_sources.AddGrowableCol(1)

        self.panel_main.SetSizer(sizer_main)
        self.panel_vp_select.SetSizer(sizer_vp_select)
        self.panel_vp_edit.SetSizer(sizer_vp_edit)
        self.nb_ap_select.SetSizer(sizer_ap_select)
        self.nb_ap_edit.SetSizer(sizer_nb_ap_edit)
        self.flog_tab['panel'].SetSizer(self.flog_tab['sizer'])

        self.Layout()
        self.Centre()

        # Bind events
        self.list_vp.Bind(wx.EVT_LISTBOX, self.vp_selected)
        self.list_vp.Bind(wx.EVT_LISTBOX_DCLICK, self.vp_activated) # assign video preset
        self.list_ap.Bind(wx.EVT_LISTBOX, self.ap_selected)
        self.list_ap.Bind(wx.EVT_LISTBOX_DCLICK, self.ap_activated) # assign audio preset
        self.pg_vp.Bind(pg.EVT_PG_CHANGED, self.pg_vp_changed)
        self.pg_ap.Bind(pg.EVT_PG_CHANGED, self.pg_ap_changed)
        self.button_vp_save.Bind(wx.EVT_BUTTON, self.vp_save)
        self.button_vp_dup.Bind(wx.EVT_BUTTON, self.vp_dup)
        self.button_vp_del.Bind(wx.EVT_BUTTON, self.vp_del)
        self.button_ap_save.Bind(wx.EVT_BUTTON, self.ap_save)
        self.button_ap_dup.Bind(wx.EVT_BUTTON, self.ap_dup)
        self.button_ap_del.Bind(wx.EVT_BUTTON, self.ap_del)
        self.list_sources.Bind(wx.EVT_LIST_ITEM_SELECTED, self.file_selected)
        self.list_sources.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.file_activated) # delete
        self.button_encode.Bind(wx.EVT_BUTTON, self.encode)
        self.nb_log.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.log_switched)

        # Bind dnd
        dt = FileDropTarget(self.list_sources)
        self.list_sources.SetDropTarget(dt)
    
    def encode(self, event): 
        if self.list_sources.GetItemCount() > 0:
            encode_list = []
            # list selected
            source_item = self.list_sources.GetFirstSelected()
            if source_item != wx.NOT_FOUND:
                while source_item != wx.NOT_FOUND:
                    encode_list.append([self.list_sources.GetItemText(source_item, 0), self.list_sources.GetItemText(source_item, 1)])
                    source_item = self.list_sources.GetNextSelected(source_item)
                
                self.flog(text=f'Encoding {len(encode_list)} selected sources...')
            else:
                # no selection gets all items
                for list_item in range(self.list_sources.GetItemCount()):
                    encode_list.append([self.list_sources.GetItemText(source_item, 0), self.list_sources.GetItemText(source_item, 1)])
                
                self.flog(text=f'No sources selected. Encoding all {len(encode_list)} sources...')
            
            for id, item in encode_list:
                self.flog(id, text=f'Encoding...')
                #page = self.nb_log.FindPage(tab['panel'])
                #self.nb_log.SetSelection(page)

        else:
            self.flog(error=f'No sources added.', color=wx.RED)
        


        notify("Encoding finished")

    def file_selected(self, event):
        item_file = self.list_sources.GetFirstSelected()
        item_filepath = self.list_sources.GetItemText(item_file, 1)
        self.tree_info.DeleteAllItems()
        media = MediaFiles.GetByFilepath(item_filepath)
        if media is not None:
            print('selected list item:', item_file, 'file id:', media.id, 'path:', item_filepath)
            info_root_id = self.tree_info.AddRoot(media.filename)
            for stream in media.streams:
                info_stream_id = self.tree_info.AppendItem(info_root_id, f'Stream #{stream['index']}: {stream.get('codec_type', 'unidentified')}')
                for category, props in ffmpeg.stream_properies.items():
                    info_category = self.tree_info.AppendItem(info_stream_id, category)
                    cnt = 0
                    for propkey, propname in props.items():
                        val = stream.get(propkey, None)
                        if val is not None:
                            cnt += 1
                            self.tree_info.AppendItem(info_category, f'{propname}: {self.value_formatter(propkey, val)}')
                    if cnt == 0: self.tree_info.Delete(info_category)
            
            info_container_id = self.tree_info.AppendItem(info_root_id, 'Container')
            for propkey, propname in ffmpeg.format_properties['Format'].items():
                val = media.format.get(propkey, None)
                if val is not None:
                    self.tree_info.AppendItem(info_container_id, f'{propname}: {self.value_formatter(propkey, val)}')

            self.tree_info.Expand(info_root_id)

    def file_activated(self, event): # delete file by dclick
        file_item = self.list_sources.GetFirstSelected()
        if file_item != wx.NOT_FOUND:
            filepath = self.list_sources.GetItemText(file_item, 1)
            MediaFiles.Delete(filepath)

    def vp_selected(self, event):
        preset_item = self.list_vp.GetSelection()
        if preset_item != wx.NOT_FOUND:
            self.video_preset = VideoPresets.GetPresetByIndex(preset_item)
            print('selected vpreset index=', self.video_preset.index, 'name=', self.video_preset.name, 'encoder=', self.video_preset.encoder.name)
            self.video_prop_show()
        else:
            self.video_preset = None

    def ap_selected(self, event):
        preset_item = self.list_ap.GetSelection()
        if preset_item != wx.NOT_FOUND:
            self.audio_preset = AudioPresets.ByIndex(preset_item)
            print('selected apreset index=', self.audio_preset.index, 'name=', self.audio_preset.name, 'encoder=', self.audio_preset.encoder.name)
            self.audio_prop_show()
        else:
            self.audio_preset = None
        pass

    def vp_activated(self, event):
        source_item = self.list_sources.GetFirstSelected()
        if self.video_preset is not None:
            if source_item != wx.NOT_FOUND:
                while source_item != wx.NOT_FOUND:
                    file_name = self.list_sources.GetItemText(source_item, 1)
                    MediaFiles.SetVideo(file_name, self.video_preset)
                    self.list_sources.SetItem(source_item, 3, self.video_preset.name)
                    source_item = self.list_sources.GetNextSelected(source_item)
            else:
                self.video_prop_show(True)
        else:
            raise Exception('Video preset selection was lost. This is a bug, report!')

    def ap_activated(self, event):
        file_item = self.list_sources.GetFirstSelected()
        if self.audio_preset is not None:
            if file_item != wx.NOT_FOUND:
                while file_item != wx.NOT_FOUND:
                    file_name = self.list_sources.GetItemText(file_item, 1)
                    MediaFiles.SetAudio(file_name, self.audio_preset)
                    self.list_sources.SetItem(file_item, 4, self.audio_preset.name)
                    file_item = self.list_sources.GetNextSelected(file_item)
            else:
                self.audio_prop_show(True)

    def video_prop_show(self, switch: bool=False):
        print('showing video preset', self.video_preset.name)
        self.pg_vp.Clear()
        if self.video_preset.system is False:
            # Main part
            self.vp_page: pg.PropertyGridPage = self.pg_vp.AddPage("Video Settings")
            self.vp_page.Append(pg.PropertyCategory("Video Preset"))
            p: pg.PGProperty = self.vp_page.Append(pg.StringProperty("Name", pg.PG_LABEL, self.video_preset.name))
            p.SetHelpString('Video preset name')
            self.vp_page.Append(pg.PropertyCategory("Codec"))
            list_encoders = Encoders.Names(MediaType.VIDEO)
            p = self.vp_page.Append(pg.EditEnumProperty("Encoder", pg.PG_LABEL, list_encoders, range(len(list_encoders)), value=self.video_preset.encoder.name))
            p.SetHelpString('Video encoder name')
            self.vp_page.Append(pg.PropertyCategory("Container"))
            p = self.vp_page.Append(pg.EditEnumProperty("Format", pg.PG_LABEL, self.video_preset.encoder.formats, range(len(self.video_preset.encoder.formats)), value=self.video_preset.default_format))
            p.SetHelpString('File format')
            self.prop_encoder_options_build(self.video_preset)
            if switch: self.nb_video.ChangeSelection(1)

    def audio_prop_show(self, switch: bool=False):
        print('showing audio preset', self.audio_preset.name)
        self.pg_ap.Clear()
        if self.audio_preset.system is False:
            # Main part
            self.ap_page: pg.PropertyGridPage = self.pg_ap.AddPage("Audio Settings")
            self.ap_page.Append(pg.PropertyCategory("Audio Preset"))
            p: pg.PGProperty = self.ap_page.Append(pg.StringProperty("Name", pg.PG_LABEL, self.audio_preset.name))
            p.SetHelpString('Audio preset name')
            self.ap_page.Append(pg.PropertyCategory("Codec"))
            list_encoders = Encoders.Names(MediaType.AUDIO)
            p = self.ap_page.Append(pg.EditEnumProperty("Encoder", pg.PG_LABEL, list_encoders, range(len(list_encoders)), value=self.audio_preset.encoder.name))
            p.SetHelpString('Audio encoder name')
            self.ap_page.Append(pg.PropertyCategory("Container"))
            p = self.ap_page.Append(pg.EditEnumProperty("Format", pg.PG_LABEL, self.audio_preset.encoder.formats, range(len(self.audio_preset.encoder.formats)), value=self.audio_preset.default_format))
            p.SetHelpString('Audio only file format')
            self.prop_encoder_options_build(self.audio_preset)
            if switch: self.nb_audio.ChangeSelection(1)      

    def prop_encoder_options_build(self, preset: VideoPresets | AudioPresets):
        if preset.encoder.type == MediaType.AUDIO:
            this_page = self.ap_page
        elif preset.encoder.type == MediaType.VIDEO:
            this_page = self.vp_page

        for optionkey, optionval in preset.encoder_options.items():
            print('adding op:', optionkey)
            if type(optionval) == bool:
                if optionval: this_page.Append(pg.PropertyCategory(optionkey))
                enum_prop = None
            elif optionval['fixed']:
                enum_prop = pg.EnumProperty
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
                enum_prop = pg.EditEnumProperty
                current = optionval['current']
            
            if enum_prop is not None:
                if type(optionval['values'][0]) == dict: # if elements are dicts get the list of name keys
                    opt_values = [x['name'] for x in optionval['values']]
                    p = this_page.Append(enum_prop(optionkey, pg.PG_LABEL, opt_values, range(len(opt_values)), value=current))
                    p.SetHelpString(optionval['doc'])
                    print(optionkey, 'added')
                    if optionval['values'][current].get('suboptions', None) is not None: 
                        print(optionkey, 'has subops')
                        print('theres subs in', optionval['values'][current]['name'])
                        for suboption in optionval['values'][current]['suboptions']:
                            p: pg.PGProperty = this_page.Append(pg.EditEnumProperty(suboption['name'], pg.PG_LABEL, suboption['values'], range(len(suboption['values'])), value=suboption['current']))
                            p.SetHelpString(suboption['doc'])
                else: # list type
                    p: pg.PGProperty = this_page.Append(enum_prop(optionkey, pg.PG_LABEL, optionval['values'], range(len(optionval['values'])), value=current))
                    p.SetHelpString(optionval['doc'])
                    print(optionkey, 'added')

    def pg_vp_changed(self, event: pg.PropertyGridEvent):
        print('video prop changed item:', event.PropertyName, 'to value:', event.Value)
        val_int = type(event.Value) == int
        if event.PropertyName == 'Name':
            if event.Value != '':
                self.video_preset.name = event.Value
        elif event.PropertyName == 'Encoder':
            # encoder option
            list_encoders = Encoders.Names(MediaType.VIDEO)
            val = list_encoders[event.Value] if val_int else event.Value
            self.video_preset = self.video_preset.SetVideoEncoder(Encoders.ByName(val))
        elif event.PropertyName == 'Format':
            # format option
            val = self.video_preset.encoder.formats[event.Value] if val_int else event.Value
            self.video_preset.default_format = val
        elif event.PropertyName in ['Color coding', 'Preset', 'Tune', 'Profile', 'Lookahead', 'Scale', 'Scale algo']:
            # top level options
            val = self.video_preset.encoder_options[event.PropertyName]['values'][event.Value] if val_int else event.Value
            self.video_preset.encoder_options[event.PropertyName].update({'current': val})
        elif event.PropertyName == 'Rate control':
            # options with suboptions
            opt_values = [x['name'] for x in self.video_preset.encoder_options[event.PropertyName]['values']]
            val = opt_values[event.Value] if val_int else event.Value
            self.video_preset.encoder_options[event.PropertyName].update({'current': val})
        elif event.PropertyName in ['Quality', 'Max quality', 'Bitrate']:
            # suboptions of Rate Control
            branch = self.video_preset.encoder_options['Rate control']
            index = self.video_preset.GetValueIndex(branch['values'], branch['current'])
            branch = self.video_preset.encoder_options['Rate control']['values'][index]['suboptions']
            subindex = self.video_preset.GetValueIndex(branch, event.PropertyName)
            val = branch[subindex]['values'][event.Value] if val_int else event.Value
            self.video_preset.encoder_options['Rate control']['values'][index]['suboptions'][subindex].update({'current': val})
        self.video_prop_show()

    def pg_ap_changed(self, event: pg.PropertyGridEvent):
        print('audio prop changed item:', event.PropertyName, 'to value:', event.Value)
        val_int = type(event.Value) == int
        if event.PropertyName == 'Name':
            if event.Value != '':
                self.audio_preset.name = event.Value
        elif event.PropertyName == 'Encoder':
            # encoder option
            list_encoders = Encoders.Names(MediaType.AUDIO)
            val = list_encoders[event.Value] if val_int else event.Value
            self.audio_preset = self.audio_preset.SetAudioEncoder(Encoders.ByName(val))
        elif event.PropertyName == 'Format':
            # format option
            val = self.audio_preset.encoder.formats[event.Value] if val_int else event.Value
            self.audio_preset.default_format = val
        elif event.PropertyName in ['Color coding', 'Preset', 'Tune', 'Profile', 'Lookahead', 'Volume']:
            # top level options
            val = self.audio_preset.encoder_options[event.PropertyName]['values'][event.Value] if val_int else event.Value
            self.audio_preset.encoder_options[event.PropertyName].update({'current': val})
        elif event.PropertyName in ['Rate control']:
            # options with suboptions
            opt_values = [x['name'] for x in self.audio_preset.encoder_options[event.PropertyName]['values']]
            val = opt_values[event.Value] if val_int else event.Value
            self.audio_preset.encoder_options[event.PropertyName].update({'current': val})
        elif event.PropertyName in ['Quality', 'Max quality', 'Bitrate']:
            # suboptions of Rate Control
            branch = self.audio_preset.encoder_options['Rate control']
            index = self.audio_preset.GetValueIndex(branch['values'], branch['current'])
            branch = self.audio_preset.encoder_options['Rate control']['values'][index]['suboptions']
            subindex = self.audio_preset.GetValueIndex(branch, event.PropertyName)
            val = branch[subindex]['values'][event.Value] if val_int else event.Value
            self.audio_preset.encoder_options['Rate control']['values'][index]['suboptions'][subindex].update({'current': val})
        self.audio_prop_show()

    def vp_save(self, event):
        self.flog(0, 'Pretending to save video preset')

    def vp_dup(self, event):
        self.flog(0, 'Pretending to duplicate video preset')

    def vp_del(self, event):
        self.flog(0, 'Pretending to delete video preset')

    def ap_save(self, event):
        self.flog(0, 'Pretending to save audio preset')

    def ap_dup(self, event):
        self.flog(0, 'Pretending to duplicate audio preset')

    def ap_del(self, event):
        self.flog(0, 'Pretending to delete audio preset')

    def log_add(self, title: str, media: MediaFiles) -> dict:
        tab: dict[str, wx.Panel|wx.BoxSizer|rt.RichTextCtrl] = {} # {'panel':,'sizer':,'text':}
        tab['panel'] = wx.Panel(self.nb_log, wx.ID_ANY)
        self.nb_log.AddPage(tab['panel'], select=True, text=title)
        tab['sizer'] = wx.BoxSizer(wx.HORIZONTAL)
        tab['text'] = rt.RichTextCtrl(
            parent=tab['panel'],
            id=wx.ID_ANY,
            #value=f'{title} log',
            style=wx.BORDER_NONE | wx.HSCROLL | wx.TE_AUTO_URL | rt.RE_MULTILINE | rt.RE_READONLY) #| wx.TE_RICH2
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

    def log_switched(self, event):
        selected = self.nb_log.GetSelection()
        if selected != wx.NOT_FOUND:
            if selected == 0:
                for item in range(self.list_sources.GetItemCount()):
                    self.list_sources.Select(item, 1)
            else:
                for item in range(self.list_sources.GetItemCount()):
                    self.list_sources.Select(item, 1 if item == selected-1 else 0)

    def item_by_fileid(self, fileid: str):
        item_index = self.list_sources.FindItem(start=-1,str=fileid)
        if item_index == wx.NOT_FOUND:
            raise Exception('Internal file list error. This is a bug, report!')
        else:
            return item_index

    def check_files(self):
        if self.list_sources.ItemCount < 1:
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

    def flog(self, tab: dict=None, **kwargs): # kw = {'text', 'file', 'error', 'end'}
        if tab is None: tab = self.flog_tab
        timestamp = dt.datetime.strftime(dt.datetime.now(), '%H:%M:%S ')
        logtxt: rt.RichTextCtrl = tab['text']
        logtxt.MoveEnd()
        logtxt.WriteText(timestamp)
        if kwargs.get('text') is not None:
            logtxt.BeginTextColour(FFColor.TEXT.wx)
            logtxt.WriteText(f'{kwargs['text']} ')
            logtxt.EndTextColour()
        if kwargs.get('file') is not None:
            logtxt.BeginTextColour(FFColor.FILE.wx)
            logtxt.WriteText(f'{kwargs['file']} ')
            logtxt.EndTextColour()
        if kwargs.get('error') is not None:
            logtxt.BeginTextColour(FFColor.ERR.wx)
            logtxt.WriteText(f'{kwargs['error']} ')
            logtxt.EndTextColour()
        if kwargs.get('end') is not None:
            logtxt.BeginTextColour(FFColor.TEXT.wx)
            logtxt.WriteText(kwargs['end'])
            logtxt.EndTextColour()
        logtxt.MoveEnd()
        logtxt.ScrollIntoView(logtxt.GetCaretPosition(), wx.WXK_DOWN)
        logtxt.Newline()
        #self.nb_log.SetSelection(tab)

class MyApp(wx.App):
    ver = 'FFEnc v0.096a'
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
    notif = adv.NotificationMessage(MyApp.ver, message=text, parent=None)
    adv.NotificationMessage.SetTitle(notif, MyApp.ver)
    adv.NotificationMessage.SetIcon(notif, feicon)
    adv.NotificationMessage.Show(notif, timeout=8)    

def has_tags(text: str, tag_list: list) -> bool:
    return any(item in text for item in tag_list)


if __name__ == "__main__":
    args = sys.argv
    print(f'argumens: {args}')

    app = MyApp(0)
    app.frame.flog(text=f'{app.ver} started.')
    ffmpeg = FFmpeg('C:\\Program Files\\ffmpeg\\bin\\')

    # Add codecs
    set_encoders = [
        {   #0
            'name':            'No video',
            'type':            MediaType.VIDEO,
            'system':          True,
            'options':         {
                'ffoption': None
            }
        },
        {   #1
            'name':            'Video stream copy',
            'type':            MediaType.VIDEO,
            'system':          True,
            'options':         {
                'ffoption': '-c:v copy'
            }
        },
        {   #2
            'name':            'No audio',
            'type':            MediaType.AUDIO,
            'system':          True,
            'options':         {
                'ffoption': None
            }
        },
        {   #3
            'name':            'Audio stream copy',
            'type':            MediaType.AUDIO,
            'system':          True,
            'options':         {
                'ffoption': '-c:a copy'
            }
        },
        {   #4
            'name':            'libx264',
            'type':            MediaType.VIDEO, 'system': False,
            'general':         ['dr1', 'delay', 'threads'],
            'threading':       ['other'],
            'formats':         ['mp4', 'mov'],
            'audio_codecs':    ['aac', 'ac3', 'mp3', 'dts', 'mp2', 'alac', 'dvaudio'],
            'options':         {
                'Encoder options': True,
                'Color coding': {
                    'ffoption': '-pix_fmt',
                    'values': ['yuv420p', 'yuvj420p', 'yuv422p', 'yuvj422p', 'yuv444p', 'yuvj444p', 'yuv420p10le', 'yuv422p10le', 'yuv444p10le', 'gray', 'gray10le'],
                    'current': 'yuv420p',
                    'doc': 'Pixel format/chroma subsampling mode. 10 or 16 in the names states the bitdepth.',
                    'fixed': True
                },
                'Preset': {
                    'ffoption': '-preset',
                    'values': ['medium', 'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'slow', 'veryslow', 'placebo'],
                    'current': 'slow',
                    'doc': 'Sets the encoding preset.',
                    'fixed': False,
                },
                'Profile': {
                    'ffoption': '-profile',
                    'values': ['baseline', 'main', 'high', 'high10', 'high422', 'high444'],
                    'current': 'high',
                    'doc': 'Encoding profile. High10, high422 and high444 modes support 10-bit color.',
                    'fixed': True,
                },
                'Encoder rate control': True,
                'Rate control': {
                    'values': [
                        {
                            'name': 'Constant quality',
                            'ffoption': '-crf',
                            'doc': 'Constant quality mode.',
                            'suboptions': [
                                {
                                'name': 'Quality',
                                'values': ['-1', '0', '5', '10', '20', '25', '30', '40', '50'],
                                'current': '-1',
                                'doc': 'Selects the quality for constant quality mode.',
                                'fixed': False,
                                },
                                {
                                'name': 'Max quality',
                                'values': ['-1', '0', '5', '10', '20', '25', '30', '40', '50'],
                                'current': '-1',
                                'doc': 'Prevents VBV from lowering quality beyond this point.',
                                'fixed': False,
                                },
                            ],
                        },
                        {
                            'name':'Constant quantization',
                            'ffoption': '-qp',
                            'doc': 'Constant quantization mode.',
                            'suboptions': [ 
                                {
                                'name': 'Quality',
                                'values': ['-1', '5', '10', '20', '25', '30', '40', '51'],
                                'current': '25',
                                'doc': 'Constant quantization parameter',
                                'fixed': False,
                                },
                            ],
                        },
                        {
                            'name': 'AQ mode',
                            'ffoption': '-aq-mode',
                            'doc': 'AQ mode',
                            'suboptions': [
                                {
                                'name': 'AQ method',
                                'values': ['-1', '0', '1', '2', '3'],
                                'current': '-1',
                                'doc': 'AQ method number',
                                'fixed': True,
                                },
                                {
                                'name': 'AQ strength',
                                'values': ['-1', '0', '10', '20', '50', '100', '500'],
                                'current': '-1',
                                'doc': 'Reduces blocking and blurring in flat and textured areas.',
                                'fixed': False,
                                },
                            ],
                        },
                    ],
                    'current': 'Constant quality',
                    'doc': 'Rate control mode',
                    'fixed': True,
                },
                'Encoder tune': True,
                'Tune': {
                    'ffoption': '-tune',
                    'values': ['film', 'grain', 'animation', 'zerolatency', 'fastdecode', 'stillimage'],
                    'current': 'film', 
                    'doc': 'Tune the encoding params.',
                    'fixed': True,
                },
                'Lookahead': {
                    'ffoption': '-rc-lookahead',
                    'values': ['-1', '5', '10', '25', '30', '50', '100'],
                    'current': '25',
                    'doc': 'Number of frames to look ahead for frametype and ratecontrol.',
                    'fixed': False,
                },
            }
        },
        {   #5
            'name':            'h264_nvenc',
            'type':            MediaType.VIDEO,
            'system':          False,
            'general':         ['dr1', 'delay', 'hardware'],
            'threading':       ['none'],
            'formats':         ['mp4', 'mov'],
            'audio_codecs':    ['aac', 'ac3', 'mp3', 'dts', 'mp2', 'alac', 'dvaudio'],
            'devices':         ['cuda', 'd3d11va'],
            'options':         {
                'Encoder options': True,
                'Color coding': {
                    'ffoption': '-pix_fmt',
                    'values': ['yuv420p', 'yuv444p', 'yuv444p16le', 'p010le', 'p016le', 'bgr0', 'bgra', 'rgb0', 'rgba'],
                    'current': 'yuv420p',
                    'doc': 'Pixel format/chroma subsampling mode. 10 or 16 in the names states the bitdepth.',
                    'fixed': False,
                },
                'Preset': {
                    'ffoption': '-preset',
                    'values': ['p1', 'p2', 'p3 ', 'p4', 'p5', 'p6', 'p7'],
                    'current': 'p6',
                    'doc': 'Encoding preset',
                    'fixed': False,
                },
                'Profile': {
                    'ffoption': '-profile',
                    'values': ['baseline', 'main', 'high', 'high444p'],
                    'current': 'high',
                    'doc': 'Encoding profile',
                    'fixed': True,
                },
                'Encoder rate control': True,
                'Rate control': {
                    'values': [
                        {
                            'name': 'Auto by preset',
                            'ffoption': '-rc -1',
                            'doc': 'Rate/quality controlled by the Preset',
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
                                'doc': 'Constant QP mode',
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
                                'doc': 'Variable bitrate mode',
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
                                'doc': 'Constant bitrate mode',
                                'fixed': False,
                                },
                            ],
                        },
                        {
                            'name': 'Constant bitrate low delay HQ',
                            'ffoption': '-rc cbr_ld_hq',
                            'suboptions': [
                                {
                                'name': 'Bitrate', 
                                'ffoption': '-v:b',
                                'values': ['256k', '512k', '1M', '2M', '4M', '8M', '12M', '20M', '30M', '40M'],
                                'current': '8M',
                                'doc': 'Constant bitrate low delay high quality',
                                'fixed': False,
                                },
                            ],
                        },
                        {
                            'name': 'Constant bitrate HQ',
                            'ffoption': '-rc cbr_hq',
                            'suboptions': [
                                {
                                'name': 'Bitrate', 
                                'ffoption': '-v:b',
                                'values': ['256k', '512k', '1M', '2M', '4M', '8M', '12M', '20M', '30M', '40M'],
                                'current': '8M',
                                'doc': 'Constant bitrate high quality mode',
                                'fixed': False,
                                },
                            ],
                        },
                        {
                            'name': 'Variable bitrate HQ',
                            'ffoption': '-rc vbr_hq',
                            'suboptions': [
                                {
                                'name':'Quality',
                                'ffoption': '-cq',
                                'values': ['0', '5', '10', '20', '25', '30', '40', '51'],
                                'current': '0',
                                'doc': 'Variable bitrate high quality',
                                'fixed': False,
                                },
                            ],
                        },
                    ],
                    'current': 'Auto by preset',
                    'doc': 'Overrides the preset rate-control',
                    'fixed': True,
                },
                'Encoder tune': True,
                'Tune': {
                    'ffoption': '-tune',
                    'values': ['hq', 'll', 'ull', 'lossless'],
                    'current': 'hq',
                    'doc': 'Sets the encoding tuning info',
                    'fixed': True,
                },
                'Lookahead': {
                    'ffoption': '-rc-lookahead',
                    'values': ['-1', '5', '10', '25', '30', '50', '100'],
                    'current': '25',
                    'doc': 'Number of frames to look ahead for rate-control',
                    'fixed': False,
                },
            }
        },
        {   #6
            'name':            'aac',
            'type':            MediaType.AUDIO,
            'system':          False,
            'general':         ['dr1', 'delay', 'small'],
            'threading':       ['none'],
            'formats':         ['aac', 'mp4'],
            'sample_rates':    [96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350],
            'channel_layouts': [],
            'sample_formats':  ['fltp'],
            'options':         {
                'Encoder options': True,
                'Coder': {
                    'ffoption': '-aac_coder', 
                    'values': ['anmr', 'twoloop', 'fast'],
                    'current': 'twoloop',
                    'doc': 'Coding algorithm: ANMR, Two loop searching, Default fast search.',
                    'fixed': True,
                },
                'Force M/S stereo coding': {
                    'ffoption': '-aac_ms', 
                    'values': ['auto', 'true', 'false'],
                    'current': 'auto',
                    'doc': 'Force M/S stereo coding',
                    'fixed': True,                
                },
                'Intensity stereo coding': {
                    'ffoption': '-aac_is', 
                    'values': ['true', 'false'],
                    'current': 'true',
                    'doc': 'Intensity stereo coding',
                    'fixed': True,                
                },
                'Perceptual noise substitution': {
                    'ffoption': '-aac_pns', 
                    'values': ['true', 'false'],
                    'current': 'true',
                    'doc': 'Perceptual noise substitution',
                    'fixed': True,                
                },
                'Temporal noise shaping': {
                    'ffoption': '-aac_tns', 
                    'values': ['true', 'false'],
                    'current': 'true',
                    'doc': 'Temporal noise shaping',
                    'fixed': True,                
                },
                'Long term prediction': {
                    'ffoption': '-aac_ltp', 
                    'values': ['true', 'false'],
                    'current': 'false',
                    'doc': 'Long term prediction',
                    'fixed': True,                
                },
                'AAC-Main prediction': {
                    'ffoption': '-aac_pred', 
                    'values': ['true', 'false'],
                    'current': 'false',
                    'doc': 'AAC-Main prediction',
                    'fixed': True,                
                },
                'Use PCEs': {
                    'ffoption': '-aac_pce', 
                    'values': ['true', 'false'],
                    'current': 'false',
                    'doc': 'Forces the use of PCEs',
                    'fixed': True,                
                },
            }
        },
        {   #7
            'name':            'ac3',
            'type':            MediaType.AUDIO,
            'system':          False,
            'general':         ['dr1'],
            'threading':       ['none'],
            'formats':         ['aac', 'mp4'],
            'sample_rates':    [48000, 44100, 32000],
            'channel_layouts': ['mono', 'stereo', '3.0(back)', '3.0 quad(side)', 'quad 4.0', '5.0(side)', '5.0 2channels (FC+LFE)', ' 2.1 4 channels (FL+FR+LFE+BC)', '3.1', '4.1', '5.1(side)', '5.1'],
            'sample_formats':  ['fltp'],
            'options':         {
                'Encoder options': True,
                'Center Mix Level': {
                    'ffoption': '-center_mixlev', 
                    'values': ['0', '0.594604', '1'],
                    'current': '0.594604',
                    'doc': 'Center Mix Level',
                    'fixed': False,
                },
                'Surround Mix Level': {
                    'ffoption': '-surround_mixlev', 
                    'values': ['0', '0.5', '1'],
                    'current': '0.5',
                    'doc': 'Surround Mix Level',
                    'fixed': False,
                },
                'Mixing Level': {
                    'ffoption': '-mixing_level', 
                    'values': ['-1', '10', '20', '30', '50', '80', '111'],
                    'current': '-1',
                    'doc': 'Mixing Level',
                    'fixed': False,
                },
                'Copyright Bit': {
                    'ffoption': '-copyright', 
                    'values': ['-1', '0', '1'],
                    'current': '-1',
                    'doc': 'Copyright Bit',
                    'fixed': True,
                },
            }   
        },
        {   #8
            'name':            'pcm_s16le',
            'type':            MediaType.AUDIO,
            'system':          False,
            'general':         ['dr1', 'variable'],
            'threading':       ['none'],
            'formats':         ['wav', 'mov'],
            'sample_rates':    [],
            'channel_layouts': [],
            'sample_formats':  ['s16'],
            'options':         {
                'Encoder options': False,
            }
        },
    ]

    for encoder in set_encoders:
        Encoders.Add(**encoder)

    set_audio_presets = [
        {
            'name':            'No audio',
            'encoder':         Encoders.ByName('No audio'), 
            'default_format':  '',
            'system':          True,
        },
        {
            'name':            'Stream copy',
            'encoder':         Encoders.ByName('Audio stream copy'), 
            'default_format':  '',
            'system':          True,
        },
        {
            'name':            'aac',
            'encoder':         Encoders.ByName('aac'),
            'default_format':  'aac',
            'system':          False,
        },
        {
            'name':            'ac3',
            'encoder':         Encoders.ByName('ac3'),
            'default_format':  'ac3',
            'system':          False,
        },
        {
            'name':            'pcm 16 bit',
            'encoder':         Encoders.ByName('pcm_s16le'),
            'default_format':  'wav',
            'system':          False,
        },
    ]

    for ap in set_audio_presets:
        AudioPresets.Add(**ap)

    set_video_presets = [
        {
            'name': 'No video',
            'encoder': Encoders.ByName('No video'),
            'default_format': '',
            'system': True,
        },
        {
            'name': 'Stream copy',
            'encoder': Encoders.ByName('Video stream copy'),
            'default_format': '',
            'system': True,
        },
        {
            'name': 'libx h264 420p cbr 8M slow',
            'encoder': Encoders.ByName('libx264'),
            'default_format': 'mp4',
            'system': False,
        },
        {
            'name': 'nv h264 420p Preset p6-Better',
            'encoder': Encoders.ByName('h264_nvenc'),
            'default_format': 'mp4',
            'system': False,
        },
    ]

    for vp in set_video_presets:
        VideoPresets.Add(**vp)

    app.MainLoop()

    # encoder options contain entire set (default settings)
    # but preset options contain the subset of changed options
