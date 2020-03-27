import xbmc
import xbmcaddon
import xbmcgui

import ast
import json
import os
import time

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl

from resources.lib.common import utils

_addon = xbmcaddon.Addon()
_addon_path = xbmc.translatePath(_addon.getAddonInfo('profile'))

folder_add = utils.get_art('folder-add.png')
folder_shortcut = utils.get_art('folder-shortcut.png')
folder_sync = utils.get_art('folder-sync.png')
share = utils.get_art('share.png')


def write_path(group_def, path_def=None, update=''):
    filename = os.path.join(_addon_path, '{}.group'.format(group_def['name'].lower()))

    if update and path_def:
        for path in group_def['paths']:
            if path['label'] == update:
                group_def['paths'][group_def['paths'].index(path)] = path_def
    elif path_def:
        group_def['paths'].append(path_def)

    with open(filename, 'w') as f:
        f.write(json.dumps(group_def, indent=4))
    
    
def add_path(group_def, labels):
    target = 'folder' if labels['is_folder'] else group_def['type']
    window = xbmc.getLocalizedString(labels['window'])
    
    art = {'icon': labels['icon']}
    art.update({i: '' for i in ['thumb', 'poster', 'fanart', 'landscape',
                                'banner', 'clearlogo', 'clearart']})
    
    path_def = {'type': labels['content'],
                'path': labels['path'],
                'label': labels['label'],
                'art': art,
                'target': target,
                'window': window}

    if group_def['type'] == 'shortcut':
        path_def['label'] = xbmcgui.Dialog().input(heading='Shortcut Label',
                                                 defaultt=labels['label'])
    elif group_def['type'] == 'widget':
        path_def['label'] = xbmcgui.Dialog().input(heading='Widget Label',
                                                   defaultt=labels['label'])

    write_path(group_def, path_def)


def remove_path(group, path):
    utils.ensure_addon_data()
    
    dialog = xbmcgui.Dialog()
    choice = dialog.yesno('AutoWidget', _addon.getLocalizedString(32035))
    
    if choice:
        group_def = get_group_by_name(group)
    
        filename = os.path.join(_addon_path, '{}.group'.format(group_def['name']))
        with open(filename, 'r') as f:
            group_json = json.loads(f.read())
    
        paths = group_json['paths']
        for path_json in paths:
            if path_json.get('name', '') == path or path_json.get('label', '') == path:
                group_json['paths'].remove(path_json)
                dialog.notification('AutoWidget', '{} removed.'.format(path))
                
        with open(filename, 'w') as f:
            f.write(json.dumps(group_json, indent=4))
            
        xbmc.executebuiltin('Container.Refresh()'.format(group))
    else:
        dialog.notification('AutoWidget', _addon.getLocalizedString(32036))
        
        
def shift_path(group, path, target):
    utils.ensure_addon_data()
    
    group_def = get_group_by_name(group)
    
    filename = os.path.join(_addon_path, '{}.group'.format(group_def['name']))
    with open(filename, 'r') as f:
        group_json = json.loads(f.read())

    paths = group_json['paths']
    for idx, path_json in enumerate(paths):
        if path_json['label'] == path:
            if target == 'up' and idx > 0:
                temp = paths[idx - 1]
                paths[idx - 1] = path_json
                paths[idx] = temp
            elif target == 'down' and idx < len(paths) - 1: 
                temp = paths[idx + 1]
                paths[idx + 1] = path_json
                paths[idx] = temp
            
            break
                
    group_json['paths'] = paths
            
    with open(filename, 'w') as f:
        f.write(json.dumps(group_json, indent=4))
        
    xbmc.executebuiltin('Container.Refresh()'.format(group))
    
    
def edit_dialog(group, path):
    utils.ensure_addon_data()
    
    dialog = xbmcgui.Dialog()
    group_def = get_group_by_name(group)
    path_def = get_path_by_name(group, path)
    
    options = []
    
    for key in path_def.keys():
        options.append('{}: {}'.format(key, path_def[key]))
        
    idx = dialog.select('Edit Path', options)
    if idx < 0:
        return
    
    key = options[idx].split(':')[0]
    edit_path(group, path, key)
        
        
def edit_path(group, path, target):
    utils.ensure_addon_data()
    
    dialog = xbmcgui.Dialog()
    group_def = get_group_by_name(group)
    path_def = get_path_by_name(group, path)
    
    if target == 'art':
        names = []
        types = []
        for art in path_def['art'].keys():
            item = xbmcgui.ListItem('{}: {}'.format(art, path_def['art'][art]))
            item.setArt({'icon': path_def['art'][art]})
            names.append(art)
            types.append(item)
    
        idx = dialog.select('Select Art Type', types, useDetails=True)
        if idx < 0:
            return
            
        name = names[idx]
            
        value = dialog.browse(2, 'Select {}'.format(name.capitalize()),
                              'files', mask='.jpg|.png', useThumbs=True,
                              defaultt=path_def['art'][name])
        path_def['art'][name] = value
        
        write_path(group_def, path_def, update=path)
        xbmc.executebuiltin('Container.Refresh()')
    else:
        value = dialog.input(heading=target.capitalize(),
                             defaultt=path_def[target])
        path_def[target] = value
        write_path(group_def, path_def, update=path)
        xbmc.executebuiltin('Container.Refresh()')
    
    
def rename_group(group):
    dialog = xbmcgui.Dialog()
    group_def = get_group_by_name(group)
    
    old_name = group_def['name']
    new_name = dialog.input(heading='Rename {}'.format(old_name),
                            defaultt=old_name)
    
    if new_name:
        group_def['name'] = new_name
        write_path(group_def)
        remove_group(group, over=True)
        xbmc.executebuiltin('Container.Refresh()')
    

def get_group_by_name(group):
    for defined in find_defined_groups():
        if defined.get('name', '') == group:
            return defined


def get_path_by_name(group, path):
    for defined in find_defined_paths(group):
        if defined.get('label', '') == path:
            return defined
    
    
def find_defined_groups():
    groups = []
    
    for filename in [x for x in os.listdir(_addon_path) if x.endswith('.group')]:
        path = os.path.join(_addon_path, filename)
        
        with open(path, 'r') as f:
            group_json = json.loads(f.read())
        
        groups.append(group_json)

    return groups
    
    
def find_defined_paths(group=None):
    paths = []
    if group:
        filename = '{}.group'.format(group)
        path = os.path.join(_addon_path, filename)
        
        if os.path.exists(path):
            with open(path, 'r') as f:
                group_json = json.loads(f.read())
            
            return group_json['paths']
    else:
        for group in find_defined_groups():
            paths.append(find_defined_paths(group.get('name', '')))
    
    return paths
    

def add_group(target):
    dialog = xbmcgui.Dialog()
    group = dialog.input(heading=_addon.getLocalizedString(32037)) or ''
    
    if group:
        filename = os.path.join(_addon_path, '{}.group'.format(group.lower()))
        group_def = {'name': group, 'type': target, 'paths': []}
    
        with open(filename, 'w+') as f:
            f.write(json.dumps(group_def, indent=4))
            
        xbmc.executebuiltin('Container.Refresh()')
    else:
        dialog.notification('AutoWidget', _addon.getLocalizedString(32038))
    
    return group
        

def remove_group(group, over=False):
    utils.ensure_addon_data()
    
    dialog = xbmcgui.Dialog()
    if not over:
        choice = dialog.yesno('AutoWidget', _addon.getLocalizedString(32039))
    
    if over or choice:
        filename = '{}.group'.format(group).lower()
        filepath = os.path.join(_addon_path, filename)
        try:
            os.remove(filepath)
        except Exception as e:
            utils.log('{}'.format(e), level=xbmc.LOGERROR)
            
        dialog.notification('AutoWidget', '{} removed.'.format(group))
        
        xbmc.executebuiltin('Container.Update(plugin://plugin.program.autowidget/)')
    else:
        dialog.notification('AutoWidget', _addon.getLocalizedString(32040))