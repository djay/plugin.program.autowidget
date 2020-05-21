import xbmc
import xbmcaddon
import xbmcgui

import json
import random
import time
import uuid

import six

from resources.lib import manage
from resources.lib import refresh
from resources.lib.common import directory
from resources.lib.common import utils

add = utils.get_art('add.png')
alert = utils.get_art('alert.png')
folder = utils.get_art('folder.png')
folder_shortcut = utils.get_art('folder-shortcut.png')
folder_sync = utils.get_art('folder-sync.png')
folder_next = utils.get_art('folder-next.png')
folder_merged = utils.get_art('folder-dots.png')
merge = utils.get_art('merge.png')
next = utils.get_art('next.png')
refresh_art = utils.get_art('refresh.png')
remove = utils.get_art('remove.png')
share = utils.get_art('share.png')
shuffle = utils.get_art('shuffle.png')
sync = utils.get_art('sync.png')
tools = utils.get_art('tools.png')
unpack = utils.get_art('unpack.png')

_addon = xbmcaddon.Addon()

label_warning_shown = utils.get_setting_bool('label.warning')


def _warn():
    dialog = xbmcgui.Dialog()
    dialog.ok('AutoWidget', utils.get_string(32073))
    
    utils.set_setting('label.warning', 'true')
    label_warning_shown = True


def root_menu():
    directory.add_menu_item(title=32007,
                            params={'mode': 'group'},
                            art=folder,
                            isFolder=True)
    directory.add_menu_item(title=32074,
                            params={'mode': 'widget'},
                            art=folder,
                            isFolder=True)
    directory.add_menu_item(title=32008,
                            params={'mode': 'tools'},
                            art=tools,
                            isFolder=True)
    return True, 'AutoWidget'
                            
                            
def my_groups_menu():
    groups = manage.find_defined_groups()
    if len(groups) > 0:
        for group in groups:
            _id = uuid.uuid4()
            group_name = group['label']
            group_id = group['id']
            group_type = group['type']
            
            cm = [(utils.get_string(32061),
                  ('RunPlugin('
                   'plugin://plugin.program.autowidget/'
                   '?mode=manage'
                   '&action=edit'
                   '&group={})').format(group_id))]
            
            directory.add_menu_item(title=group_name,
                                    params={'mode': 'group',
                                            'group': group_id,
                                            'target': group_type,
                                            'id': six.text_type(_id)},
                                    info=group.get('info'),
                                    art=group.get('art') or (folder_shortcut
                                                             if group_type == 'shortcut'
                                                             else folder_sync),
                                    cm=cm,
                                    isFolder=True)
    else:
        directory.add_menu_item(title=32068,
                                art=alert,
                                isFolder=False)
    return True, utils.get_string(32007)
    
    
def group_menu(group_id, target, _id):
    _window = utils.get_active_window()
    
    group = manage.get_group_by_id(group_id)
    if not group:
        utils.log('\"{}\" is missing, please repoint the widget to fix it.'
                  .format(group_id),
                  level=xbmc.LOGERROR)
        return False, 'AutoWidget'
    
    group_name = group['label']
    
    paths = manage.find_defined_paths(group_id)
    if len(paths) > 0:
        cm = []
        art = folder_shortcut if target == 'shortcut' else folder_sync
        
        for idx, path in enumerate(paths):
            if _window == 'media':
                cm = _create_context_items(group_id, path['id'], idx, len(paths))
            
            directory.add_menu_item(title=path['label'],
                                    params={'mode': 'path',
                                            'action': 'call',
                                            'group': group_id,
                                            'path': path['id']},
                                    info=path.get('info'),
                                    art=path.get('art') or art,
                                    cm=cm,
                                    isFolder=False)
                                    
        if target == 'widget' and _window != 'home':
            directory.add_separator(title=32010, char='/')
            
            directory.add_menu_item(title=utils.get_string(32028)
                                          .format(group_name),
                                    params={'mode': 'path',
                                            'action': 'random',
                                            'group': group_id,
                                            'id': six.text_type(_id),
                                            'path': '$INFO[Window(10000).Property(autowidget-{}-action)]'
                                                    .format(_id)},
                                    art=shuffle,
                                    isFolder=True)
            directory.add_menu_item(title=utils.get_string(32076)
                                          .format(group_name),
                                    params={'mode': 'path',
                                            'action': 'next',
                                            'group': group_id,
                                            'id': six.text_type(_id)},
                                    art=next,
                                    isFolder=True)
            directory.add_menu_item(title=utils.get_string(32089)
                                          .format(group_name),
                                    params={'mode': 'path',
                                            'action': 'merged',
                                            'group': group_id,
                                            'id': six.text_type(_id)},
                                    art=merge,
                                    isFolder=True)
    else:
        directory.add_menu_item(title=32032,
                                art=alert,
                                isFolder=False)
    
    return True, group_name
    
    
def active_widgets_menu():
    widgets = manage.find_defined_widgets()
    
    if len(widgets) > 0:
        for widget_def in widgets:
            _id = widget_def.get('id', '')
            action = widget_def.get('action', '')
            group = widget_def.get('group', '')
            path = widget_def.get('path', '')
            updated = widget_def.get('updated', '')
            
            path_def = manage.get_path_by_id(path, group)
            group_def = manage.get_group_by_id(group)
            
            title = ''
            if path_def and group_def:
                try:
                    path_def['label'] = path_def['label'].encode('utf-8')
                    group_def['label'] = group_def['label'].encode('utf-8')
                except:
                    pass
            
                title = '{} - {}'.format(path_def['label'], group_def['label'])
            elif group_def:
                title = group_def.get('label')

            art = {}
            params = {}
            if not action:
                art = folder_shortcut
                params = {'mode': 'group',
                          'group': group,
                          'target': 'shortcut',
                          'id': six.text_type(_id)}
                title = utils.get_string(32030).format(title)
            elif action in ['random', 'next', 'merged']:
                if action == 'random':
                    art = folder_sync
                elif action == 'next':
                    art = folder_next
                elif action == 'merged':
                    art = folder_merged
                
                params = {'mode': 'group',
                          'group': group,
                          'target': 'widget',
                          'id': six.text_type(_id)}
                
            cm = [(utils.get_string(32069), ('RunPlugin('
                                            'plugin://plugin.program.autowidget/'
                                            '?mode=refresh'
                                            '&target={})').format(_id)),
                  (utils.get_string(32070), ('RunPlugin('
                                            'plugin://plugin.program.autowidget/'
                                            '?mode=manage'
                                            '&action=edit_widget'
                                            '&target={})').format(_id))]
            
            if not group_def:
                title = '{} - [COLOR firebrick]{}[/COLOR]'.format(_id, utils.get_string(32071))
                
            directory.add_menu_item(title=title,
                                    art=art,
                                    params=params,
                                    cm=cm[1:] if not action else cm,
                                    isFolder=True)
    else:
        directory.add_menu_item(title=32072,
                                art=alert,
                                isFolder=False)

    return True, utils.get_string(32074)
    
    
def tools_menu():
    directory.add_menu_item(title=32006,
                            params={'mode': 'force'},
                            art=refresh_art,
                            info={'plot': utils.get_string(32020)},
                            isFolder=False)
    directory.add_menu_item(title=32064,
                            params={'mode': 'wipe'},
                            art=remove,
                            isFolder=False)
    return True, utils.get_string(32008)
    
    
def _initialize(group_def, action, _id):
    duration = utils.get_setting_float('service.refresh_duration')
    
    paths = group_def['paths']
    rand_idx = random.randrange(len(paths))
    init_path = paths[0]['id'] if action == 'next' else paths[rand_idx]['id']
    
    params = {'action': action,
              'id': _id,
              'group': group_def['id'],
              'refresh': duration,
              'path': init_path}
    details = manage.save_path_details(params)
    refresh.refresh(_id)
    
    return details
    
def show_path(group_id, path_id, titles=None):
    path_def = manage.get_path_by_id(path_id, group_id=group_id)
    if not path_def:
        return False, 'AutoWidget'
    
    params = {'jsonrpc': '2.0', 'method': 'Files.GetDirectory',
              'params': {'directory': path_def['path'],
                         'properties': utils.info_types},
              'id': 1}
    
    if not titles:
        titles = []
    
    files = json.loads(xbmc.executeJSONRPC(json.dumps(params)))
    if 'error' not in files:
        files = files['result']['files']
        
        for file in [x for x in files if x['label'] not in titles]:
            labels = {}
            for label in file:
                labels[label] = file[label]
            
            labels['title'] = file['label']
            hide_next = utils.get_setting_int('hide_next')
            next_item = labels['title'].lower() in ['next', 'next page']
            sort_to_end = next_item and hide_next == 1
            
            if not next_item or hide_next != 2:
                if next_item:
                    labels['title'] = '{} - {}'.format(labels['title'],
                                                       path_def['label'])
                    
                directory.add_menu_item(title=labels['title'],
                                        path=file['file'],
                                        art=file['art'],
                                        info=labels,
                                        isFolder=file['filetype'] == 'directory',
                                        props={'specialsort': 'bottom' if sort_to_end else '',
                                               'autoLabel': path_def['label']})
                titles.append(labels['title'])
    return titles, 'AutoWidget'
    
    
def call_path(group_id, path_id):
    path_def = manage.get_path_by_id(path_id, group_id=group_id)
    if not path_def:
        return
    
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    xbmc.sleep(500)
    final_path = ''
    
    if path_def['target'] == 'shortcut' and path_def['is_folder'] == 0 \
                                        and path_def['content'] != 'addons':
        if path_def['path'] == 'addons://install/':
            final_path = 'InstallFromZip'
        elif 'plugin.video.youtube' in path_def['path']:
            final_path = 'RunPlugin({})'.format(path_def['path'])
        elif path_def['path'].startswith('androidapp://sources/apps/'):
            final_path = 'StartAndroidActivity({})'.format(path_def['path']
                                                           .replace('androidapp://sources/apps/', ''))
        elif all(i in path_def['path'] for i in ['(', ')']) and '://' not in path_def['path']:
            final_path = path_def['path']
        else:
            final_path = 'PlayMedia({})'.format(path_def['path'])
    elif path_def['target'] == 'widget' or path_def['is_folder'] == 1 \
                                        or path_def['content'] == 'addons':
        final_path = 'ActivateWindow({},{},return)'.format(path_def.get('window', 'Videos'),
                                                           path_def['path'])
    elif path_def['target'] == 'settings':
        final_path = 'Addon.OpenSettings({})'.format(path_def['path']
                                                     .replace('plugin://', ''))
        
    if final_path:
        xbmc.executebuiltin(final_path)


def path_menu(group_id, action, _id):
    _window = utils.get_active_window()
    if _window not in ['home', 'media'] and not label_warning_shown:
        _warn()
    
    group_def = manage.get_group_by_id(group_id)
    if not group_def:
        utils.log('\"{}\" is missing, please repoint the widget to fix it.'
                  .format(group_id),
                  level=xbmc.LOGERROR)
        return False, 'AutoWidget'
    
    group_name = group_def.get('label', '')
    paths = group_def.get('paths', [])
    
    widget_def = manage.get_widget_by_id(_id, group_id)
    
    if not widget_def and _window == 'home':
        widget_def = _initialize(group_def, action, _id)
    
    if not widget_def:
        return True, group_name
    
    if len(paths) > 0 and widget_def:
        if _window == 'media':
            rand = random.randrange(len(paths))
            call_path(group_id, paths[rand]['id'])
            return False, group_name
        else:
            show_path(group_id, widget_def.get('path', ''))
            return True, group_name
    else:
        directory.add_menu_item(title=32032,
                                art=alert,
                                isFolder=False)
        return True, group_name
    return True, group_name
        
        
def merged_path(group_id):
    _window = utils.get_active_window()
    
    group_def = manage.get_group_by_id(group_id)
    if not group_def:
        utils.log('\"{}\" is missing, please repoint the widget to fix it.'
                  .format(group_id),
                  level=xbmc.LOGERROR)
        return False, 'AutoWidget'
    
    group_name = group_def.get('label', '')
    paths = manage.find_defined_paths(group_id)
    
    if len(paths) > 0:
        titles = []

        for path_def in paths:
            titles, cat = show_path(group_id, path_def['id'])
                    
        return True, group_name
    else:
        directory.add_menu_item(title=32032,
                                art=alert,
                                isFolder=False)
        return False, group_name
        
        
def merged_path(group_id):
    _window = utils.get_active_window()
    
    group_def = manage.get_group_by_id(group_id)
    if not group_def:
        utils.log('\"{}\" is missing, please repoint the widget to fix it.'
                  .format(group_id),
                  level=xbmc.LOGERROR)
        return False, 'AutoWidget'
    
    group_name = group_def.get('label', '')
    paths = manage.find_defined_paths(group_id)
    
    if len(paths) > 0:
        titles = []

        for path_def in paths:
            titles, cat = show_path(group_id, path_def['id'])
                    
        return True, group_name
    else:
        directory.add_menu_item(title=32032,
                                art=alert,
                                isFolder=False)
        return False, group_name


def _create_context_items(group_id, path_id, idx, length):
    cm = [(utils.get_string(32048),
          ('RunPlugin('
           'plugin://plugin.program.autowidget/'
           '?mode=manage'
           '&action=edit'
           '&group={}'
           '&path={})').format(group_id, path_id))]
    if idx > 0:
        cm.append((utils.get_string(32026),
                  ('RunPlugin('
                   'plugin://plugin.program.autowidget/'
                   '?mode=manage'
                   '&action=shift_path'
                   '&target=up'
                   '&group={}'
                   '&path={})').format(group_id, path_id)))
    if idx < length - 1:
        cm.append((utils.get_string(32027),
                  ('RunPlugin('
                   'plugin://plugin.program.autowidget/'
                   '?mode=manage'
                   '&action=shift_path'
                   '&target=down'
                   '&group={}'
                   '&path={})').format(group_id, path_id)))
                                                      
    return cm
