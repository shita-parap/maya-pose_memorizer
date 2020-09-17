# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PoseMemorizer GUI (Maya2018-)
# -----------------------------------------------------------------------------

import os
import traceback
import json
import functools

from maya import cmds
from maya import mel

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.OpenMayaUI import MQtUtil

from PySide2 import QtCore
from PySide2 import QtWidgets

import pose_memorizer as pomezer
import pose_memorizer.core as pomezer_core


# -----------------------------------------------------------------------------

WINDOWS_NAME = "PoseMemorizer"


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Callback
class Callback(object):
    """docstring for Callback."""

    def __init__(self, func, *args, **kwargs):
        super(Callback, self).__init__(*args, **kwargs)
        self._func = func
        self._args = args
        self._kwargs = kwargs
        return

    def __call__(self):
        cmds.undoInfo(openChunk=True)
        try:
            return self._func(*self._args, **self._kwargs)
        except:
            traceback.print_exc()
        finally:
            cmds.undoInfo(closeChunk=True)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class OptionFile(object):

    FILENAME = "option.json"

    def __init__(self):
        super(OptionFile, self).__init__()
        self.version = pomezer._version
        self.parameter = {}
        self._file_path = self._get_file_path()
        return

    def unify_sep(func):

        @functools.wraps(func)
        def _wrap(*args, **kwargs):

            def unify_path(path):
                sep = os.sep
                if sep == "\\":
                    return path.replace("/", sep)
                else:
                    return path.replace("\\", sep)

            path = func(*args, **kwargs)

            if hasattr(path, "__iter__") is True:
                return [unify_path(p) for p in path]
            else:
                return unify_path(path)
        return _wrap

    def _check_file_path(self):
        dir_path = os.path.dirname(self._file_path)
        if os.path.exists(dir_path) is False:
            os.makedirs(dir_path)
        return

    @unify_sep
    def _get_file_path(self):
        prefs_path = os.path.join(cmds.about(preferences=True), "prefs")
        ui_lang = cmds.about(uiLanguage=True)
        if ui_lang != "en_US":
            prefs_path = os.path.join(prefs_path, ui_lang, "prefs")

        return os.path.join(prefs_path, "scripts", pomezer._config_dir, self.FILENAME)

    def set_parameter(self, parameter):
        self.parameter = parameter
        return

    def load(self):
        data = {}
        with open(self._file_path, "r") as f:
            data = json.load(f)
        file_version = data.get("version", None)
        if file_version != self.version:
            return None

        return data

    def save(self):
        data = {"version": self.version}
        data.update(self.parameter)
        self._check_file_path()
        with open(self._file_path, "w") as f:
            json.dump(data, f, indent=4)
        return


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# ScrollWidget
class ScrollWidget(QtWidgets.QScrollArea):

    def __init__(self, parent=None):
        super(ScrollWidget, self).__init__(parent)
        self._parent = parent
        # scroll
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        return


# HorizontalLine
class HorizontalLine(QtWidgets.QFrame):

    def __init__(self, *args, **kwargs):
        super(HorizontalLine, self).__init__(*args, **kwargs)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        return


# -----------------------------------------------------------------------------
# PoseListWidget
class PoseListWidget(QtWidgets.QListWidget):

    itemRightClicked = QtCore.Signal(QtWidgets.QListWidgetItem)

    def __init__(self, *args, **kwargs):
        super(PoseListWidget, self).__init__(*args, **kwargs)
        self.__start_index = None
        self.__drag_button = None

        self.setObjectName(("pose_list"))
        self.setUniformItemSizes(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        return

    def mousePressEvent(self, event):
        self.clearSelection()
        self.__start_index = self.indexAt(event.pos())
        self.__drag_button = event.button()
        super(self.__class__, self).mousePressEvent(event)
        return

    def mouseMoveEvent(self, event):
        if self.__drag_button == QtCore.Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.row() >= 0:
                self.setSelection(self.rectForIndex(index),
                                  self.selectionCommand(index))
        super(self.__class__, self).mouseMoveEvent(event)
        return

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            items = self.selectedItems()
            if len(items) > 0 and self.__start_index == self.indexAt(event.pos()):
                self.itemRightClicked.emit(items.pop())
        self.__start_index = None
        self.__drag_button = None
        super(self.__class__, self).mouseReleaseEvent(event)
        return


# -----------------------------------------------------------------------------
# PoseMemorizerDockableWidget
class PoseMemorizerDockableWidget(MayaQWidgetDockableMixin, ScrollWidget):

    MIRRORNAME = ["Left : Right", "left : right", "_L : _R", "_l : _r"]
    MIRRORAXIS = ["X", "Y", "Z"]

    def __init__(self, parent=None):
        super(PoseMemorizerDockableWidget, self).__init__(parent=parent)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.pomezer = pomezer_core.PoseMemorizer()
        self.op_file = OptionFile()

        self.widget = QtWidgets.QWidget(self)
        widget = self.widget

        # layout
        self.layout = QtWidgets.QVBoxLayout(self)
        layout = self.layout
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        button_layout = QtWidgets.QHBoxLayout(self)
        button_layout.setSpacing(4)
        button_layout.setContentsMargins(0, 0, 0, 0)

        mirror_layout = QtWidgets.QHBoxLayout(self)
        mirror_layout.setSpacing(16)
        mirror_layout.setContentsMargins(0, 0, 0, 0)

        check_layout = QtWidgets.QHBoxLayout(self)
        check_layout.setSpacing(16)
        check_layout.setContentsMargins(0, 0, 0, 0)

        # Widget
        self.memorize_button = QtWidgets.QPushButton("Memorize", self)
        memorize_button = self.memorize_button
        memorize_button.clicked.connect(Callback(self._click_memorize))

        self.update_button = QtWidgets.QPushButton("Update", self)
        update_button = self.update_button
        update_button.clicked.connect(self._click_update)

        self.delete_button = QtWidgets.QPushButton("Delete", self)
        delete_button = self.delete_button
        delete_button.clicked.connect(self._click_delete)

        self.pose_list = PoseListWidget(self)
        pose_list = self.pose_list
        pose_list.itemDoubleClicked.connect(self._edit_item_name)
        pose_list.itemRightClicked.connect(self._right_click_item)

        self.mirror_name_combo = QtWidgets.QComboBox(self)
        mirror_name_combo = self.mirror_name_combo
        mirror_name_combo.addItems(self.MIRRORNAME)

        self.mirror_axis_combo = QtWidgets.QComboBox(self)
        mirror_axis_combo = self.mirror_axis_combo
        mirror_axis_combo.addItems(self.MIRRORAXIS)

        self.mirror_check = QtWidgets.QCheckBox("Mirror", self)
        mirror_check = self.mirror_check
        mirror_check.setChecked(True)

        self.setkey_check = QtWidgets.QCheckBox("Set Key", self)
        setkey_check = self.setkey_check
        setkey_check.setChecked(False)
        # setkey_check.setFixedHeight(28)

        self.namespace_check = QtWidgets.QCheckBox("Namespace Match", self)
        namespace_check = self.namespace_check
        namespace_check.setChecked(True)
        # namespace_check.setFixedHeight(28)

        self.apply_button = QtWidgets.QPushButton("Apply", self)
        apply_button = self.apply_button
        apply_button.clicked.connect(Callback(self._click_apply))
        apply_button.setFixedHeight(28)

        button_layout.addWidget(memorize_button, 3)
        button_layout.addWidget(update_button, 2)
        button_layout.addWidget(delete_button, 1)

        mirror_layout.addWidget(mirror_axis_combo)
        mirror_layout.addWidget(mirror_check)

        check_layout.addWidget(setkey_check)
        check_layout.addWidget(namespace_check)

        layout.addLayout(button_layout)
        layout.addWidget(pose_list)
        layout.addWidget(mirror_name_combo)
        layout.addLayout(mirror_layout)
        layout.addWidget(HorizontalLine())
        layout.addLayout(check_layout)
        layout.addWidget(HorizontalLine())
        layout.addWidget(apply_button)

        widget.setLayout(layout)
        self.setWidget(widget)

        self._option_load()
        QtWidgets.qApp.aboutToQuit.connect(self._option_save, QtCore.Qt.UniqueConnection)
        return

    def dockCloseEventTriggered(self):
        self._option_save()
        return

    def _add_pose(self, pose_data):
        name = pose_data.keys()[0]
        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, name)
        item.setData(QtCore.Qt.UserRole + 1, pose_data)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.pose_list.addItem(item)
        self.pose_list.clearSelection()
        return

    def _get_ui_parameter(self):
        reslut = {}
        reslut["mirror_name"] = self.mirror_name_combo.currentText()
        reslut["mirror_axis"] = self.mirror_axis_combo.currentText()
        reslut["mirror"] = self.mirror_check.isChecked()
        reslut["setkey"] = self.setkey_check.isChecked()
        reslut["namespace"] = self.namespace_check.isChecked()
        return reslut

    def _get_sel_item(self):
        items = self.pose_list.selectedItems()
        if len(items) == 0:
            return None
        return items[0]

    def _edit_item_name(self, item):
        self.pose_list.editItem(item)
        return

    def _right_click_item(self):
        item = self._get_sel_item()
        if item is None:
            return
        pose_data = item.data(QtCore.Qt.UserRole + 1)
        cmds.select(pose_data.keys(), replace=True)
        return

    def _click_memorize(self):
        pose_data = self.pomezer.get_pose()
        if len(pose_data) > 0:
            self._add_pose(pose_data)
        return

    def _click_update(self):
        item = self._get_sel_item()
        if item is None:
            return
        transform = item.data(QtCore.Qt.UserRole + 1).keys()
        pose_data = self.pomezer.get_pose(transform)
        item.setData(QtCore.Qt.UserRole + 1, pose_data)
        return

    def _click_delete(self):
        item = self._get_sel_item()
        if item is None:
            return
        self.pose_list.takeItem(self.pose_list.row(item))
        del(item)
        return

    def _click_apply(self):
        item = self._get_sel_item()
        if item is None:
            return
        pose_data = item.data(QtCore.Qt.UserRole + 1)
        ui_parameter = self._get_ui_parameter()
        mirror_name = ui_parameter["mirror_name"]
        mirror_axis = ui_parameter["mirror_axis"]
        mirror = ui_parameter["mirror"]
        setkey = ui_parameter["setkey"]
        namespace = ui_parameter["namespace"]
        self.pomezer.apply_pose(pose=pose_data,
                                mirror=mirror,
                                mirror_name=mirror_name,
                                mirror_axis=mirror_axis,
                                setkey=setkey,
                                namespace=namespace)
        return

    def _option_load(self):
        ui_parameter = self.op_file.load()
        if ui_parameter is None:
            return
        self.mirror_name_combo.setCurrentText(ui_parameter["mirror_name"])
        self.mirror_axis_combo.setCurrentText(ui_parameter["mirror_axis"])
        self.mirror_check.setChecked(ui_parameter["mirror"])
        self.setkey_check.setChecked(ui_parameter["setkey"])
        self.namespace_check.setChecked(ui_parameter["namespace"])
        return

    def _option_save(self):
        ui_parameter = self._get_ui_parameter()
        self.op_file.set_parameter(ui_parameter)
        self.op_file.save()
        return


# -----------------------------------------------------------------------------
# PoseMemorizerMainWindow
class PoseMemorizerMainWindow(object):

    HEIGHT = 360
    WIDTH = 280

    _windows_name = WINDOWS_NAME
    _windows_title = WINDOWS_NAME

    def __init__(self, restore=False):
        super(PoseMemorizerMainWindow, self).__init__()
        self.name = self._windows_name.replace(" ", "_").lower()
        self.workspace_name = "{}WorkspaceControl".format(self.name)

        self.widget = None

        # Restore
        if restore is True:
            self._make_widget()
            # Restore parent
            mixinPtr = MQtUtil.findControl(self.name)
            wks = MQtUtil.findControl(self.workspace_name)
            MQtUtil.addWidgetToMayaLayout(long(mixinPtr), long(wks))

        # Create New Workspace
        else:
            self._check_workspase()
            self._make_widget()

        self._set_stylesheet()
        return

    def _check_workspase(self):
        wks = MQtUtil.findControl(self.workspace_name)
        if wks is not None:
            self.close()
        return

    def _set_stylesheet(self):
        try:
            styleFile = os.path.join(os.path.dirname(__file__), "style.css")
            with open(styleFile, "r") as f:
                style = f.read()
        except IOError:
            style = ""

        self.widget.setStyleSheet(style)
        return

    def _resize(self, height, width):
        workspace_name = self.workspace_name
        cmds.workspaceControl(workspace_name, edit=True, resizeHeight=height)
        cmds.workspaceControl(workspace_name, edit=True, resizeWidth=width)
        return

    def _make_uiscript(self):
        reslut = ("from pose_memorizer import gui;"
                  "pomezer_ui=gui.{classname}(restore=True)")

        class_name = self.__class__.__name__
        return reslut.format(classname=class_name)

    def _make_close_command(self):
        return "deleteUI {};".format(self.workspace_name)

    def _make_widget(self):
        self.widget = PoseMemorizerDockableWidget()
        self.widget.setObjectName(self.name)
        return

    def close(self):
        # Mel Command
        cmd = self._make_close_command()
        mel.eval(cmd)
        return

    def show(self):
        widget = self.widget
        uiscript = self._make_uiscript()

        # Show Workspace & Set uiscript
        widget.show(dockable=True, uiScript=uiscript, retain=False)
        # Resize Workspace
        self._resize(self.HEIGHT, self.WIDTH)
        # Set Windows Title
        widget.setWindowTitle(self._windows_title)
        return


# -----------------------------------------------------------------------------
def main():
    # show gui
    pomezer_window = PoseMemorizerMainWindow()
    pomezer_window.show()
    return


if __name__ == '__main__':
    main()


# -----------------------------------------------------------------------------
# EOF
# -----------------------------------------------------------------------------
