import xbmc
import xbmcaddon
import xbmcgui

import ast
import json
import os
import random
import re
import time
import uuid

from xml.etree import ElementTree

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl

from resources.lib import manage
from resources.lib.common import utils

_addon = xbmcaddon.Addon()
_addon_path = xbmc.translatePath(_addon.getAddonInfo('profile'))
if xbmc.getCondVisibility('System.HasAddon(script.skinshortcuts)'):
    _shortcuts = xbmcaddon.Addon('script.skinshortcuts')
    _shortcuts_path = xbmc.translatePath(_shortcuts.getAddonInfo('profile'))
else:
    _shortcuts_path = ''
_skin_root = xbmc.translatePath('special://skin/')
_skin_id = os.path.basename(os.path.normpath(_skin_root))
_skin = xbmcaddon.Addon(_skin_id)
_skin_path = xbmc.translatePath(_skin.getAddonInfo('profile'))

activate_window_pattern = '(\w+)*\((\w+\)*),*(.*?\)*),*(return)*\)'
skin_string_pattern = 'autowidget-{}-{}'
skin_string_info_pattern = '$INFO[Skin.String({})]'.format(skin_string_pattern)
path_replace_pattern = '{}({})'
widget_param_pattern = '^(?:\w+)(\W\w+)?$'


def _get_random_paths(group_id, force=False, change_sec=3600):
    wait_time = 5 if force else change_sec
    now = time.time()
    seed = now - (now % wait_time)
    rand = random.Random(seed)
    paths = manage.find_defined_paths(group_id)
    rand.shuffle(paths)

    return paths


def _save_path_details(path, converted, setting=''):
    params = dict(parse_qsl(path.split('?')[1].replace('\"', '')))

    _id = params['id']
    if _id in converted:
        return
    
    path_to_saved = os.path.join(_addon_path, '{}.widget'.format(_id))

    if setting:
        params.update({'setting': setting})

    with open(path_to_saved, 'w') as f:
        f.write(json.dumps(params, indent=4))

    return params


def _update_strings(_id, path_def, setting=None):
    action = path_def['path']
    
    if setting:
        current = utils.get_skin_string(setting)
        if _id not in current:
            return
            
        if '?' in action:
            action = '{}&id={}'.format(action, _id)
        elif action.endswith('/'):
            action = '{}?id={}'.format(action, _id)
        else:
            action = '{}/?id={}'.format(action, _id)
        
        utils.log('Setting {} to {}'.format(setting, action))
        utils.set_skin_string(setting, action)
    elif not setting:
        label = path_def['label']
        target = path_def['window']
        label_string = skin_string_pattern.format(_id, 'label')
        action_string = skin_string_pattern.format(_id, 'action')
        target_string = skin_string_pattern.format(_id, 'target')

        utils.log('Setting {} to {}'.format(label_string, label))
        utils.log('Setting {} to {}'.format(action_string, action))
        utils.log('Setting {} to {}'.format(target_string, target))
        utils.set_skin_string(label_string, label)
        utils.set_skin_string(action_string, action)
        utils.set_skin_string(target_string, target)
    
    
def _convert_widgets(notify=False):
    dialog = xbmcgui.Dialog()
    
    converted = []
    
    converted.extend(_convert_skin_strings(converted))
    
    if _shortcuts_path:    
        dialog.notification('AutoWidget', 'Converting new widgets...')
        converted.extend(_convert_shortcuts(converted))
        converted.extend(_convert_properties(converted))
    
    utils.log('{}'.format(converted), xbmc.LOGNOTICE)
    return converted
    
    
def _convert_skin_strings(converted):
    xml_path = os.path.join(_skin_path, 'settings.xml')
    if not os.path.exists(xml_path):
        return converted
    
    try:
        settings = ElementTree.parse(xml_path).getroot()
    except ParseError:
        utils.log('Unable to parse: {}/settings.xml'.format(_skin_id))
    ids = []
        
    for setting in settings.findall('setting'):
        if not setting.text or not all(i in setting.text
                                       for i in ['plugin.program.autowidget',
                                                 'mode=path',
                                                 'action=random']):
            continue
        
        details = _save_path_details(setting.text, converted, setting=setting.get('id'))
        _id = details['id']
        
        converted.append(_id)
    
    return converted


def _convert_shortcuts(converted):    
    for xml in [x for x in os.listdir(_shortcuts_path)
                if x.endswith('.DATA.xml') and 'powermenu' not in x]:
        xml_path = os.path.join(_shortcuts_path, xml)
        
        try:
            shortcuts = ElementTree.parse(xml_path).getroot()
        except ParseError:
            utils.log('Unable to parse: {}'.format(xml))

        for shortcut in shortcuts.findall('shortcut'):
            label_node = shortcut.find('label')
            action_node = shortcut.find('action')

            if not action_node.text:
                continue

            match = re.search(activate_window_pattern, action_node.text)
            if not match:
                continue

            groups = list(match.groups())

            if not groups[2] or not all(i in groups[2] for i in [
                'plugin.program.autowidget', 'mode=path', 'action=random']):
                continue

            details = _save_path_details(groups[2], converted)
            _id = details['id']
            label_node.text = skin_string_info_pattern.format(_id, 'label')

            # groups[0] = skin_string_pattern.format(_id, 'command')
            groups[1] = skin_string_info_pattern.format(_id, 'target')
            groups[2] = skin_string_info_pattern.format(_id, 'action')

            action_node.text = path_replace_pattern.format(groups[0],
                                                           ','.join(groups[1:]))

            converted.append(_id)

        utils.prettify(shortcuts)
        tree = ElementTree.ElementTree(shortcuts)
        tree.write(xml_path)

    return converted

        
def _convert_properties(converted):
    props_path = os.path.join(_shortcuts_path,
                              '{}.properties'.format(_skin_id))
    if not os.path.exists(props_path):
        return converted
        
    with open(props_path, 'r') as f:
        content = ast.literal_eval(f.read())
    
    props = [x for x in content if all(i in x[3]
                                       for i in ['plugin.program.autowidget',
                                                 'mode=path', 'action=random'])]
    for prop in props:
        prop_index = content.index(prop)
        suffix = re.search(widget_param_pattern, prop[2])
        if not suffix:
            continue
        
        if 'ActivateWindow' in prop[3]:
            match = re.search(activate_window_pattern, prop[3])
            if not match:
                continue
                
            groups = list(match.groups())
            if not groups[2] or not all(i in groups[2] for i in ['plugin.program.autowidget', 'mode=path', 'action=random']):
                continue
        
            details = _save_path_details(groups[2], converted)
        else:
            details = _save_path_details(prop[3], converted)
            
        if not details:
            continue
        
        _id = details['id']
        prop[3] = skin_string_info_pattern.format(_id, 'action')
        content[prop_index] = prop
        
        params = [x for x in content if x[:2] == prop[:2]
                  and re.search(widget_param_pattern,
                                x[2]) and re.search(widget_param_pattern,
                                                    x[2]).groups() == suffix.groups()]
        for param in params:
            param_index = content.index(param)
            norm = param[2].lower()
            if 'name' in norm and not 'sort' in norm:
                param[3] = skin_string_info_pattern.format(_id, 'label')
            elif 'target' in norm:
                param[3] = skin_string_info_pattern.format(_id, 'target')
            
            content[param_index] = param
        
        converted.append(_id)
        
    with open(props_path, 'w') as f:
        f.write('{}'.format(content))
        
    return converted


def refresh_paths(notify=False, force=False):
    converted = 0
    utils.ensure_addon_data()

    if force:
        converted = _convert_widgets(notify)

    if notify:
        dialog = xbmcgui.Dialog()
        dialog.notification('AutoWidget', _addon.getLocalizedString(32033))
    
    for group_def in manage.find_defined_groups():
        paths = []

        for widget in [x for x in os.listdir(_addon_path) if x.endswith('.widget')]:
            saved_path = os.path.join(_addon_path, widget)
            with open(saved_path, 'r') as f:
                widget_json = json.loads(f.read())

            if group_def['id'] == widget_json['group']:
                _id = widget_json['id']
                group_id = widget_json['group']
                action = widget_json['action'].lower()
                setting = widget_json.get('setting')

                if action == 'random' and len(paths) == 0:
                    paths = _get_random_paths(group_id, force)

                if paths:
                    path_def = paths.pop()
                    _update_strings(_id, path_def, setting)

    if len(converted) > 0:
        xbmc.executebuiltin('ReloadSkin()')
