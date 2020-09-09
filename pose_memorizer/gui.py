# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PoseMemorizer GUI (Maya2018-)
# -----------------------------------------------------------------------------

import os
import traceback
from math import degrees
from math import radians

from maya import cmds
from maya import mel
from maya.api import OpenMaya as om2

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.OpenMayaUI import MQtUtil

from PySide2 import QtCore
from PySide2 import QtWidgets

import pose_memorizer as pomezer

# -----------------------------------------------------------------------------

WINDOWS_NAME = "PoseMemorizer"
VERSION = pomezer._version
# WINDOWS_TITLE = "{title} Ver_{ver}".format(title=WINDOWS_NAME, ver=VERSION)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Callback
class Callback(object):
    """docstring for Callback."""

    def __init__(self, func, *args, **kwargs):
        # super(Callback, self).__init__(*args, **kwargs)
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
class PoseMemorizer(object):

    def __init__(self):
        super(PoseMemorizer, self).__init__()

        self.pose = {}
        self.mirror_matrix = self._make_mirror_matrix()
        return

    def _convert_quaternion(self, rotate, order):
        rot = om2.MEulerRotation([radians(r) for r in rotate], order)
        return rot.asQuaternion()

    def _make_mirror_matrix(self):
        x_trans = (-1, 1, 1)
        y_trans = (1, -1, 1)
        z_trans = (1, 1, -1)
        x_qua = (-1, 1, 1, -1)
        y_qua = (1, -1, 1, -1)
        z_qua = (1, 1, -1, -1)
        return {"x": (x_trans, x_qua), "y": (y_trans, y_qua), "z": (z_trans, z_qua)}

    def _make_pose_parameter(self, nodes):

        def get_transform(node):
            return cmds.getAttr("{}.translate".format(node))[0]

        def get_quaternion(node):
            conv_qua = self._convert_quaternion
            order = cmds.getAttr("{}.rotateOrder".format(node))
            rotate = conv_qua(cmds.getAttr("{}.rotate".format(node))[0], order)
            axis = conv_qua(cmds.getAttr("{}.rotateAxis".format(node))[0], order)
            orient = om2.MQuaternion()
            if cmds.attributeQuery("jointOrient", node=node, exists=True) is True:
                orient = conv_qua(cmds.getAttr("{}.jointOrient".format(node))[0], order)
            return axis * rotate * orient

        return {n: {"translate": get_transform(n), "rotate": get_quaternion(n)}
                for n in nodes}

    def _get_transform(self):
        return cmds.ls(selection=True, transforms=True)

    def _get_mirror_matrix(self, mirror_axis):
        return self.mirror_matrix.get(mirror_axis.lower())

    def _get_target_pose(self, mirror, mirror_name):
        pose = self.pose
        if mirror is True:
            split_name = mirror_name.split(" : ")
            left = split_name[0]
            right = split_name[1]
            change_pose = {}
            for n, m in self.pose.items():
                if left in n:
                    change_pose[n.replace(left, right)] = m
                elif right in n:
                    change_pose[n.replace(right, left)] = m
                else:
                    change_pose[n] = m
            pose = change_pose

        sel_trans = set(self._get_transform())
        target_pose = {n: m for n, m in pose.items() if n in sel_trans}

        return target_pose

    def _get_translate_rotate(self, pose, mirror, mirror_axis):

        def convert_matrix(node, parameter):
            conv_qua = self._convert_quaternion
            translate = parameter.get("translate")
            rot_qua = parameter.get("rotate")
            order = cmds.getAttr("{}.rotateOrder".format(node))
            inv_axis = conv_qua(cmds.getAttr("{}.rotateAxis".format(node))[0], order).inverse()
            inv_orient = om2.MQuaternion()
            if cmds.attributeQuery("jointOrient", node=node, exists=True) is True:
                inv_orient = conv_qua(cmds.getAttr("{}.jointOrient".format(node))[0], order).inverse()
            rotate = (inv_axis * rot_qua * inv_orient).asEulerRotation()
            return (tuple(translate), tuple(degrees(r) for r in rotate))

        def convert_mirror_matrix(node, parameter, mirror_trans, mirror_qua):
            conv_qua = self._convert_quaternion
            src_translate = parameter.get("translate")
            src_rotate = parameter.get("rotate")
            order = cmds.getAttr("{}.rotateOrder".format(node))
            inv_axis = conv_qua(cmds.getAttr("{}.rotateAxis".format(node))[0], order).inverse()
            inv_orient = om2.MQuaternion()
            if cmds.attributeQuery("jointOrient", node=node, exists=True) is True:
                inv_orient = conv_qua(cmds.getAttr("{}.jointOrient".format(node))[0], order).inverse()
            translate = [s * m for s, m in zip(src_translate, mirror_trans)]
            mirror_rot = om2.MQuaternion([s * m for s, m in zip(src_rotate, mirror_qua)])
            rotate = (inv_axis * mirror_rot * inv_orient).asEulerRotation()
            return (tuple(translate), tuple(degrees(r) for r in rotate))

        # main
        if mirror is True:
            mirror_trans, mirror_qua = self._get_mirror_matrix(mirror_axis)
            return {n: convert_mirror_matrix(n, m, mirror_trans, mirror_qua)
                    for n, m in pose.items()}
        else:
            return {n: convert_matrix(n, p) for n, p in pose.items()}

    def _get_command(self, trans_rot):
        tx_cmd = "setKeyframe -at tx -v {value} -dd true {node}"
        ty_cmd = "setKeyframe -at ty -v {value} -dd true {node}"
        tz_cmd = "setKeyframe -at tz -v {value} -dd true {node}"
        rx_cmd = "setKeyframe -at rx -v {value} -dd true {node}"
        ry_cmd = "setKeyframe -at ry -v {value} -dd true {node}"
        rz_cmd = "setKeyframe -at rz -v {value} -dd true {node}"

        reslut = []
        reslut_add = reslut.append

        for n, m in trans_rot.items():
            translate, rotate = m
            if cmds.getAttr("{}.translateX".format(n), lock=True) is False:
                reslut_add(tx_cmd.format(node=n, value=translate[0]))
            if cmds.getAttr("{}.translateY".format(n), lock=True) is False:
                reslut_add(ty_cmd.format(node=n, value=translate[1]))
            if cmds.getAttr("{}.translateZ".format(n), lock=True) is False:
                reslut_add(tz_cmd.format(node=n, value=translate[2]))
            if cmds.getAttr("{}.rotateX".format(n), lock=True) is False:
                reslut_add(rx_cmd.format(node=n, value=rotate[0]))
            if cmds.getAttr("{}.rotateY".format(n), lock=True) is False:
                reslut_add(ry_cmd.format(node=n, value=rotate[1]))
            if cmds.getAttr("{}.rotateZ".format(n), lock=True) is False:
                reslut_add(rz_cmd.format(node=n, value=rotate[2]))

        # DG Dirty
        nodes = " ".join(trans_rot.keys())
        reslut_add("dgdirty {}".format(nodes))
        return ";".join(reslut)

    def clear(self):
        self.pose = {}
        return

    def memorize(self):
        transform = self._get_transform()
        self.pose = self._make_pose_parameter(transform)
        return

    def apply(self, mirror, mirror_name, mirror_axis):
        # check memory pose
        if len(self.pose) == 0:
            return
        cmds.refresh(suspend=True)
        try:
            target_pose = self._get_target_pose(mirror, mirror_name)
            pose_tr = self._get_translate_rotate(target_pose, mirror, mirror_axis)
            cmd = self._get_command(pose_tr)
            mel.eval(cmd)
        finally:
            cmds.refresh(suspend=False)
            cmds.refresh(currentView=True)
        return


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# ScrollWidget
class ScrollWidget(QtWidgets.QScrollArea):
    """docstring for ScrollWidget."""

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
    """docstring for HorizontalLine"""

    def __init__(self, *args, **kwargs):
        super(HorizontalLine, self).__init__(*args, **kwargs)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        return


# -----------------------------------------------------------------------------
# PoseMemorizerDockableWidget
class PoseMemorizerDockableWidget(MayaQWidgetDockableMixin, ScrollWidget):

    MIRRORNAME = ["Left : Right", "left : right", "_L : _R", "_l : _r"]
    MIRRORAXIS = ["X", "Y", "Z"]

    def __init__(self, parent=None):
        super(PoseMemorizerDockableWidget, self).__init__(parent=parent)

        self.pomezer = PoseMemorizer()

        self.widget = QtWidgets.QWidget(self)
        widget = self.widget

        # layout
        self.layout = QtWidgets.QVBoxLayout(self)
        layout = self.layout
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        mirror_layout =  QtWidgets.QHBoxLayout(self)
        mirror_layout.setSpacing(16)
        mirror_layout.setContentsMargins(0, 0, 0, 0)

        self.memorize_button = QtWidgets.QPushButton("Memorize", self)
        memorize_button = self.memorize_button
        memorize_button.clicked.connect(Callback(self._click_memorize))

        self.mirror_name_combo = QtWidgets.QComboBox(self)
        mirror_name_combo = self.mirror_name_combo
        mirror_name_combo.addItems(self.MIRRORNAME)

        self.mirror_axis_combo = QtWidgets.QComboBox(self)
        mirror_axis_combo = self.mirror_axis_combo
        mirror_axis_combo.addItems(self.MIRRORAXIS)

        self.mirror_check = QtWidgets.QCheckBox("Mirror", self)
        mirror_check = self.mirror_check
        mirror_check.setChecked(True)
        # mirror_check.setFixedHeight(28)

        self.apply_button = QtWidgets.QPushButton("Apply", self)
        apply_button = self.apply_button
        apply_button.setEnabled(False)
        apply_button.clicked.connect(Callback(self._click_apply))
        apply_button.setFixedHeight(28)

        mirror_layout.addWidget(mirror_axis_combo)
        mirror_layout.addWidget(mirror_check)

        layout.addWidget(memorize_button)
        layout.addWidget(HorizontalLine())
        layout.addWidget(QtWidgets.QLabel("-Mirror Type-", self))
        layout.addWidget(mirror_name_combo)
        layout.addLayout(mirror_layout)
        layout.addSpacing(2)
        layout.addWidget(apply_button)
        layout.addStretch(0)

        widget.setLayout(layout)
        self.setWidget(widget)
        return

    def _check_pose(self):
        self.apply_button.setEnabled(len(self.pomezer.pose) > 0)
        return

    def _click_memorize(self):
        self.pomezer.memorize()
        self._check_pose()
        return

    def _click_apply(self):
        mirror = self.mirror_check.isChecked()
        mirror_name = self.mirror_name_combo.currentText()
        mirror_axis = self.mirror_axis_combo.currentText()
        self.pomezer.apply(mirror, mirror_name, mirror_axis)
        return


# -----------------------------------------------------------------------------
# PoseMemorizerMainWindow
class PoseMemorizerMainWindow(object):

    HEIGHT = 160
    WIDTH = 240

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
            # Current Directory
            os.chdir(os.path.dirname(__file__))
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
    # Current Directory
    os.chdir(os.path.dirname(__file__))

    # show gui
    pomezer_window = PoseMemorizerMainWindow()
    pomezer_window.show()

    return


if __name__ == '__main__':
    main()


# -----------------------------------------------------------------------------
# EOF
# -----------------------------------------------------------------------------
