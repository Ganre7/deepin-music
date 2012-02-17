#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 Deepin, Inc.
#               2011 Hou Shaohui
#
# Author:     Hou Shaohui <houshao55@gmail.com>
# Maintainer: Hou ShaoHui <houshao55@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import chardet
import sys
import os
import shutil
import gtk
import gobject
import locale
import time
import threading
import mimetypes
mimetypes.init()

from urllib import pathname2url, quote, unquote
from urlparse import urlparse
from urllib2 import urlopen

from logger import newLogger
from constant import DEFAULT_TIMEOUT
import socket
socket.setdefaulttimeout(DEFAULT_TIMEOUT)

from mutagen import File as MutagenFile
from mutagen.asf import ASF
from mutagen.apev2 import APEv2File
from mutagen.flac import FLAC
from mutagen.id3 import ID3FileType
from mutagen.oggflac import OggFLAC
from mutagen.oggspeex import OggSpeex
from mutagen.oggtheora import OggTheora
from mutagen.oggvorbis import OggVorbis
from mutagen.trueaudio import TrueAudio
from mutagen.wavpack import WavPack
try: from mutagen.mp4 import MP4 #@UnusedImport
except: from mutagen.m4a import M4A as MP4 #@Reimport
from mutagen.musepack import Musepack
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.optimfrog import OptimFROG
from easymp3 import EasyMP3

FORMATS = [EasyMP3, TrueAudio, OggTheora, OggSpeex, OggVorbis, OggFLAC,
            FLAC, APEv2File, MP4, ID3FileType, WavPack, Musepack,
            MonkeysAudio, OptimFROG, ASF]


logger = newLogger("utils")
fscoding = sys.getfilesystemencoding()

def file_is_supported(filename):
    ''' whther file is supported. '''
    try:
        fileobj = file(filename, "rb")
    except:
        return False
    try:
        header = fileobj.read(128)
        results = [Kind.score(filename, fileobj, header) for Kind in FORMATS]
    finally:
        fileobj.close()
    results = zip(results, FORMATS)
    results.sort()
    score, Kind = results[-1]
    if score > 0: return True
    else: return False


def get_scheme(uri):
    ''' get uri type, such as 'file://', return 'file'. '''
    if uri.rfind("://") == -1:
        return ""
    scheme = uri[:uri.index("://")]
    return scheme.lower()

def get_ext(uri, complete=True):
    ''' get uri extension, such as '123.mp3', return '.mp3|mp3'. '''
    if uri.rfind(".") == -1:
        return ""
    if get_scheme(uri) in ["http", "https"]:
        if uri.rfind("#") != -1:
            uri = uri[:uri.rindex("#")]
        if uri.rfind("?") != -1:
            uri = uri[:uri.rindex("?")]
    if complete:        
        return uri[uri.rindex("."):].lower()
    else:
        if uri[-1:] == ".": return ""
        return uri[uri.rindex(".")+1:].lower()
    
def get_path_from_uri(uri):    
    ''' get filepath from uri. '''
    if get_scheme(uri) == "file":
        uri = uri.replace("#", "%23")
    return unquote(urlparse(uri)[2])    

def get_uri_from_path(path):
    ''' get uri from filepath. '''
    if get_scheme(path): 
        return path
    return "file://" + quote(path)

def realuri(uri):
    '''Return the canonical path of the specified filename.'''
    if get_scheme(uri) == "file":
        return get_uri_from_path(os.path.realpath(get_path_from_uri(uri)))
    
def unescape_string_for_display(value):    
    ''' display of file name for users. '''
    return unquote(value)

def rebuild_uri(header_uri, base_uri):
    ''' return header_uri + base_uri '''
    header_uri = header_uri[:header_uri.rfind("/")]
    if base_uri.find("://") != -1:
        return base_uri
    elif base_uri[0] == "/":    
        return "file://" + quote(base_uri)
    else:
        return header_uri + "/" + quote(base_uri)
    

def unlink(uri):
    ''' Remove a file (same as remove(path)). '''
    if get_scheme != "file":
        return True
    path = get_path_from_uri(uri)
    if os.path.exists(path):
        return os.unlink(path)
    return False

def exists(uri):
    '''  Test whether a path exists.  Returns False for broken symbolic links. '''
    if get_scheme(uri) != "file":
        return True
    path = get_path_from_uri(uri)
    return os.path.exists(path)

def makedirs(uri, mode=0755):
    ''' Super-mkdir; create a leaf directory and all intermediate ones. '''
    path = urlparse(uri)[2]
    if not os.path.exists(path):
        os.makedirs(path, mode)
    
def get_name(uri):
    # return os.path.basename(get_path_from_uri(uri))
    return get_path_from_uri(uri).split("/")[-1]

def is_local_dir(uri):    
    return os.path.isdir(get_path_from_uri(uri))

def read_entire_file(uri):
    ''' Return entire_file content. '''
    data = ""
    if get_scheme(uri) == "file":
        f = file(get_path_from_uri(uri), "r")
        date = f.read()
        f.close()
    else:    
        try:
            f = urlopen(uri)
            data = f.read()
            f.close()
        except:    
            logger.logexception("failed read %s", uri)
            data = ""
    return data        
    
def auto_decode(s):    
    ''' auto detect the code and return unicode object. '''
    if isinstance(s, unicode):
        return s
    try:
        codedetect = chardet.detect(s)["encoding"]
        return s.decode(codedetect)
    except UnicodeError:
        return s.decode(charset, "replace") + " " + ("[Invalid Encoding]")    
    
def auto_encode(s, charset=fscoding): 
    ''' auto encode. '''
    if isinstance(s, unicode):
        return s.encode(charset, "replace")
    else:
        return auto_decode(s).encode(charset, "replace")

def get_mime_type(uri):
    ''' get mime type. '''
    if get_scheme(uri) in ["http", "https"]:
        if uri.rfind("#") != -1:
            uri = uri[:uri.rindex("#")]
        if uri.rfind("?") != -1:    
            uri = uri[:uri.rindex("?")]
    mimetype = mimetypes.guess_type(uri)[0]        
    if mimetype: return mimetype
    ext = get_ext(uri)
    if ext == ".pls": mimetype = "audio/x-scpls"
    elif ext == ".m3u": mimetype = "audio/x-mpegurl"
    elif ext == ".asx": mimetype = "video/x-ms-asf"
    else: mimetype = ""
    return mimetype

    
def duration_to_string(value, default="", i=1000):
    ''' convert duration to string. '''
    if not value: return default
    duration = "%02d:%02d" % ((value/(60*i)) % 60, (value/i) % 60)
    if value/(60*i) / 60 >= 1:
        duration = "%d:" % (value/(60*i) % 60) + duration
    return duration    

def parse_folder(dir):
    ''' return all uri in a folder excepted hidden one.'''
    dir  = get_path_from_uri(dir)
    uris = [ get_uri_from_path(os.path.join(dir, name)) for name in os.listdir(dir) if name[0] != "." and os.path.isfile(os.path.join(dir,name))]
    print "ParserFolder: %d founds" % len(uris)
    return uris

def get_uris_from_m3u(uri):
    ''' Return uri in a m3u playlist.'''
    uris = []
    content = read_entire_file(uri)
    lines = content.splitlines()
    for line in lines:
        if not line.startswith("#") and line.strip() != "":
            uris.append(line.strip())
    uris = [rebuild_uri(uri, u) for u in uris]        
    return uris

def get_uris_from_pls(uri):
    ''' return uri in a pls playlist. '''
    uris = []
    content = read_entire_file(uri)
    lines = content.splitlines()
    for line in lines:
        if line.lower().startswith("file") and line.find("=") != -1:
            uris.append(line[line.find("=") + 1:].strip())
    uris = [rebuild_uri(uri, u) for u in uris]        
    return uris



def parse_uris(uris, follow_folder=True, follow_playlist=True, callback=None, *args_cb, **kwargs_cb):
    ''' Receive a list of uris ,expand it and check if exist.
        if directory recursive add all uri in directory
        if playlist read all uri in playlist
        return all supported file found.
    '''
    if not uris:
        return []
    valid_uris = []
    for uri in uris:
        #check file exists only is file is local to speed parsing of shared/remote file
        uri = unquote(uri)
        if uri and uri.strip() != "" and exists(uri):
            ext = get_ext(uri)
            try:
                mime_type = get_mime_type(uri)
            except:    
                logger.logexception("falied to read file info from %s", uri)
                continue
            
            is_pls  = False
            is_m3u  = False
            # is_xsps = False
            try:
                is_pls = (mime_type == "audio/x-scpls")
                is_m3u = (mime_type == "audio/x-mpegurl" or mime_type == "audio/mpegurl" or mime_type == "audio/m3u")
                # is_xspf = (mime_type == "application/xspf+xml")
            except:    
                pass
            is_pls = is_pls or (ext == ".pls")
            is_m3u = is_m3u or (ext == ".m3u")
            # is_xspf = is_xspf or (ext == ".xspf")
            
            if is_local_dir(uri) and follow_folder:
                valid_uris.extend(parse_uris(parse_folder(uri), follow_folder, follow_playlist))
            elif follow_playlist and is_pls:    
                valid_uris.extend(parse_uris(get_uris_from_pls(uri), follow_folder, follow_playlist))
            elif follow_playlist and is_m3u:
                valid_uris.extend(parse_uris(get_uris_from_m3u(uri), follow_folder, follow_playlist))    
            elif get_scheme(uri) != "file" or file_is_supported(get_path_from_uri(uri)):
                valid_uris.append(uri)
                
    logger.loginfo("parse uris found %s uris", len(valid_uris))            
    if callback:
        def launch_callback(callback, uris, args, kwargs):
            callback(uris, *args, **kwargs)
        gobject.idle_add(launch_callback, callback, list(valid_uris), args_cb, kwargs_cb)    
    else:    
        return valid_uris
    
def async_parse_uris(*args, **kwargs):    
    ''' asynchronous parse uris. '''
    t = threading.Thread(target=parse_uris, args=args, kwargs=kwargs)
    t.setDaemon(True)
    t.start()
    
def move_to_trash(uri):    
    ''' move uri to trash. '''
    path = get_path_from_uri(uri)
    path = os.path.realpath(os.path.expanduser(path))
    if not os.path.exists(path):
        logger.logdebug("File %s doesn't exists.", path)
        return False
    # find the trash folder
    home_dir = os.path.realpath(os.path.expandusr("~"))
    dirs_name = path.split("/")
    dirs_name = filter(lambda name: name != "", dirs_name)
    trash_dir = None
    r = range(0, len(dirs_name))
    r.reverse()
    for i in r:
        tmp_path = os.path.realpath("/" + "/".join(dirs_name[:i]))
        if tmp_path == home_dir:
            trash_dir = home_dir + "/.local/share/Trash"
            trash_dir = os.environ.get("XDG_DATA_HOME", trash_dir)
            break
        elif os.path.ismount(tmp_path):
            trash_dir = tmp_path + "/.Trash-%d" % os.getuid()
            break
        else:
            continue
    if not trash_dir:    
        logger.logerror("trash dir not found.")
        return False
    for subdir in ["files", "info"]:
        if not os.path.exists(trash_dir + "/" + subdir):
            try:
                os.makedirs(trash_dir + "/" + subdir, 0700)
            except:    
                logger.logwarn("Failed to create trash dir %s", trash_dir + "/" + subdir)
                return False
    if path.rfind("/") != -1:        
        filename = path[path.rindex("/") + 1:]
    delete_date = time.strftime("%Y-%M-%dT%H:%M:%S")    
    destpath = trash_dir + "/files/" + filename
    infopath = trash_dir + "/info/" + filename + ".trashinfo"
    try:
        shutil.move(path, destpath)
        f = open(infopath, "w")
        f.write("[Trash Info]\nPath=%s\nDeletionDate=%s\n" % (quote(path), delete_date))
        f.close()
    except:    
        logger.logexception("Failed to move to trash %s", path)
        return False
    else:
        return True
    
def download_iterator(remote_uri, local_uri, buffer_len=4096, timeout=DEFAULT_TIMEOUT):
    
    try:
        logger.loginfo("download %s starting...", remote_uri)
        handle_read = urlopen(remote_uri, timeout=timeout)
        handle_write = file(get_path_from_uri(local_uri), "w")
        info = handle_read.info()
        try:
            total_size = int(info.getheader("content-length"))
        except:    
            total_size = 20000000
        current_size = 0    
        date = handle_read.read(buffer_len)
        handle_write.write(data)
        current_size += len(data)
        
        while data:
            data = handle_read.read(buffer_len)
            current_size += len(data)
            handle_write.write(data)
            percent = current_size * 100 / total_size
            yield (total_size, current_size, percent)
            
        handle_read.close()    
        handle_write.close()
        logger.loginfo("download %s finish" % remote_uri)
    except GeneratorExit:    
        try:
            unlink(local_uri)
        except:    
            pass
    except:    
        logger.logexception("Error while downloading %s", remote_uri)
        try:
            unlink(local_uri)
        except:
            pass
        raise IOError
    
def download(remote_uri, local_uri, buffer_len=4096, timeout=DEFAULT_TIMEOUT):
    try:
        logger.loginfo("download %s starting...", remote_uri)
        handle_read = urlopen(remote_uri, timeout=timeout)
        handle_write = file(get_path_from_uri(local_uri), "w")
        
        data = handle_read.read(buffer_len)
        handle_write.write(data)
        
        while data:
            data = handle_read.read(buffer_len)
            handle_write.write(data)
            
        handle_read.close()    
        handle_write.close()
        logger.loginfo("download %s finish." % remote_uri)
    except:    
        logger.logexception("Error while downloading %s", remote_uri)
        try:
            unlink(local_uri)
        except:    
            pass
        return False
    if not exists(local_uri):
        return False
    return True
    
def threaded(func):
    ''' the func threaded. '''
    def wrapper(*args):
        t = threading.Thread(target=func, args=args)
        t.setDaemon(True)
        t.start()
    return wrapper    

def print_timeing(func):
    def wrapper(*arg):
        start_time = time.time()
        res = func(*arg)
        end_time   = time.time()
        if hasattr(func, "im_class"):
            class_name = func.im_class__name__ + ":"
        print "%s took %0.3fms" % (class_name + func.func_name, (start_time - end_time) * 1000.0)    
        return res
    return wrapper

def dbus_service_available(bus, interface, try_start_service=False):
    ''' detect the dbus service is available. and try to start it.'''
    try:
        import dbus
    except:    
        return False
    if try_start_service:
        bus.start_service_by_name(interface)
    obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")    
    dbus_interface = dbus.Interface(obj, "org.freedesktop.DBus")
    avail = dbus_interface.ListNames()
    return interface in avail

