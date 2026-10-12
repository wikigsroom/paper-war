extends RefCounted
# A paper sheet is a native keyboard focus scope within its viewport. Keep
# original focus modes so closing it never enables battle hotkeys as buttons.
var locked: bool=false
var modes: Array=[]
var previous: WeakRef

func capture(root: Control):
	if locked:return
	locked=true
	var focused=root.get_viewport().gui_get_focus_owner()
	if is_instance_valid(focused) and (focused==root or root.is_ancestor_of(focused)):previous=weakref(focused)
	for control in root.find_children("*","Control",true,false):
		if control.focus_mode==Control.FOCUS_NONE:continue
		modes.append({"control":weakref(control),"mode":control.focus_mode})
		control.focus_mode=Control.FOCUS_NONE

func enter(sheet: Control):
	if not is_instance_valid(sheet) or sheet.is_queued_for_deletion() or not sheet.is_visible_in_tree():return
	var focused=sheet.get_viewport().gui_get_focus_owner()
	if is_instance_valid(focused) and sheet.is_ancestor_of(focused):return
	for control in sheet.find_children("*","Control",true,false):
		if control.focus_mode==Control.FOCUS_NONE or not control.is_visible_in_tree():continue
		if control is BaseButton and control.disabled:continue
		control.grab_focus();return

func release(restore: bool=true):
	for entry in modes:
		var control=entry.control.get_ref()
		if is_instance_valid(control) and not control.is_queued_for_deletion():control.focus_mode=entry.mode
	modes.clear();locked=false
	var focused=previous.get_ref() if previous else null
	previous=null
	if not restore or not is_instance_valid(focused) or not focused.is_visible_in_tree() or focused.is_queued_for_deletion():return
	if focused.focus_mode==Control.FOCUS_NONE or (focused is BaseButton and focused.disabled):return
	focused.grab_focus()
