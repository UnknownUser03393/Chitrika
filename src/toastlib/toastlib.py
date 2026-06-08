"""
toastlib - library calling win10+ toast notification service.
<b>You must registerApplication first.</b>
"""

import ctypes
import os
import subprocess
import sys
import threading
import time
import uuid
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pythoncom
from winrt.windows.data.xml.dom import XmlDocument
from winrt.windows.foundation import IPropertyValue
from winrt.windows.ui.notifications import (
	ToastActivatedEventArgs,
	ToastDismissalReason,
	ToastDismissedEventArgs,
	ToastFailedEventArgs,
	ToastNotification,
	ToastNotificationManager,
)

DurationDefault = 'default'
DurationShort = 'short'
DurationLong = 'long'

ScenarioDefault = 'default'
ScenarioReminder = 'reminder'
ScenarioAlarm = 'alarm'
ScenarioIncomingCall = 'incomingCall'

ActivationForeground = 'foreground'
ActivationBackground = 'background'
ActivationProtocol = 'protocol'

DismissUser = ToastDismissalReason.USER_CANCELED
DismissTimeout = ToastDismissalReason.TIMED_OUT
DismissApp = ToastDismissalReason.APPLICATION_HIDDEN

_PKEY_FMTID = (ctypes.c_byte * 16)(*uuid.UUID('{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}').bytes_le)
_IID_PROPERTYSTORE = (ctypes.c_byte * 16)(*uuid.UUID('{886d8eeb-8cf2-4446-8d02-cdba1dbdcf99}').bytes_le)

_aumidCache: dict[str, str] = {}


class _PROPERTYKEY(ctypes.Structure):
	_fields_ = [('fmtid', ctypes.c_byte * 16), ('pid', wintypes.DWORD)]


class _PROPVARIANT(ctypes.Structure):
	_fields_ = [
		('vt', wintypes.WORD),
		('wReserved1', wintypes.BYTE),
		('wReserved2', wintypes.BYTE),
		('wReserved3', wintypes.DWORD),
		('data', ctypes.c_byte * 16),
	]


def registerApplication(appName: str) -> str:
	aumid = _aumidCache.get(appName)
	if aumid is not None:
		return aumid

	aumid = f'Chitrika.{appName}'
	programsDir = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
	shortcutDir = programsDir / 'Chitrika'
	shortcutPath = shortcutDir / f'{appName}.lnk'

	if not shortcutPath.exists():
		shortcutDir.mkdir(parents=True, exist_ok=True)

		psScript = (
			f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{shortcutPath}');"
			f"$s.TargetPath='{sys.executable}';"
			f"$s.Save()"
		)
		subprocess.run(
			['powershell', '-NoProfile', '-Command', psScript],
			capture_output=True,
		)

		pythoncom.CoInitialize()

		pkey = _PROPERTYKEY()
		pkey.fmtid = _PKEY_FMTID
		pkey.pid = 5

		pv = _PROPVARIANT()
		pv.vt = 31

		strPtr = ctypes.c_wchar_p(aumid)
		ctypes.memmove(ctypes.addressof(pv.data), ctypes.addressof(strPtr), ctypes.sizeof(ctypes.c_void_p))

		result = ctypes.c_void_p()
		ctypes.windll.shell32.SHGetPropertyStoreFromParsingName(
			str(shortcutPath), None, 2, ctypes.byref(_IID_PROPERTYSTORE), ctypes.byref(result),
		)

		if result.value:
			vtable = ctypes.cast(result, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

			fnSet = ctypes.cast(vtable[6], ctypes.WINFUNCTYPE(
				ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT),
			))
			fnSet(result, ctypes.byref(pkey), ctypes.byref(pv))

			fnCommit = ctypes.cast(vtable[7], ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p))
			fnCommit(result)

			fnRelease = ctypes.cast(vtable[2], ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p))
			fnRelease(result)

		pythoncom.CoUninitialize()

		subprocess.run(
			['attrib', '+h', str(shortcutPath)],
			capture_output=True,
		)
		subprocess.run(
			['attrib', '+h', str(shortcutDir)],
			capture_output=True,
		)

	_aumidCache[appName] = aumid
	return aumid


_XmlTemplate = '''<toast>
	<visual>
		<binding template="ToastGeneric"></binding>
	</visual>
</toast>'''


def _setAttr(doc: XmlDocument, el: Any, name: str, value: str) -> None:
	attr = doc.create_attribute(name)
	attr.value = value
	el.attributes.set_named_item(attr)


def _buildXml(
	title: str,
	content: str,
	*,
	icon: Path | None = None,
	heroImage: Path | None = None,
	scenario: str | None = None,
	activationType: str | None = None,
	launch: str | None = None,
	actions: list[dict[str, str]] | None = None,
	inputs: list[dict[str, str]] | None = None,
	audioSrc: str | None = None,
	audioSilent: bool = False,
	audioLoop: bool = False,
) -> XmlDocument:
	doc = XmlDocument()
	doc.load_xml(_XmlTemplate)

	toast = doc.select_single_node('/toast')
	if scenario is not None:
		_setAttr(doc, toast, 'scenario', scenario)
	if activationType is not None:
		_setAttr(doc, toast, 'activationType', activationType)
	if launch is not None:
		_setAttr(doc, toast, 'launch', launch)

	binding = doc.select_single_node('//binding')

	if heroImage:
		img = doc.create_element('image')
		img.set_attribute('placement', 'hero')
		img.set_attribute('src', heroImage.absolute().as_uri())
		binding.append_child(img)

	for text in (title, content):
		el = doc.create_element('text')
		el.inner_text = text
		binding.append_child(el)

	if icon:
		img = doc.create_element('image')
		img.set_attribute('placement', 'appLogoOverride')
		img.set_attribute('hint-crop', 'circle')
		img.set_attribute('src', icon.absolute().as_uri())
		binding.append_child(img)

	hasActions = bool(actions) or bool(inputs)
	if hasActions:
		actionsEl = doc.create_element('actions')

		if inputs:
			for inp in inputs:
				inputEl = doc.create_element('input')
				inputEl.set_attribute('id', inp['id'])
				inputEl.set_attribute('type', inp.get('type', 'text'))
				if 'title' in inp:
					inputEl.set_attribute('title', inp['title'])
				if 'placeholder' in inp:
					inputEl.set_attribute('placeHolderContent', inp['placeholder'])
				if 'default' in inp:
					inputEl.set_attribute('defaultInput', inp['default'])
				actionsEl.append_child(inputEl)

		if actions:
			for act in actions:
				actionEl = doc.create_element('action')
				actionEl.set_attribute('content', act['content'])
				actionEl.set_attribute('arguments', act.get('arguments', ''))
				actionEl.set_attribute(
					'activationType',
					act.get('activationType', ActivationForeground),
				)
				if 'imageUri' in act:
					actionEl.set_attribute('imageUri', act['imageUri'])
				if 'hintInputId' in act:
					actionEl.set_attribute('hint-inputId', act['hintInputId'])
				actionsEl.append_child(actionEl)

		toast.append_child(actionsEl)

	if audioSrc or audioSilent or audioLoop:
		audio = doc.create_element('audio')
		if audioSrc:
			audio.set_attribute('src', audioSrc)
		if audioSilent:
			audio.set_attribute('silent', 'true')
		if audioLoop:
			audio.set_attribute('loop', 'true')
		visual = doc.select_single_node('/toast/visual')
		toast.insert_before(audio, visual)

	return doc


def _show(
	doc: XmlDocument,
	appName: str,
	*,
	duration: str = DurationDefault,
	ttl: int | None = None,
	tag: str | None = None,
	group: str | None = None,
	suppressPopup: bool = False,
	onClick: Callable[[dict[str, Any]], None] = lambda _: None,
	onDismiss: Callable[[ToastDismissalReason], None] = lambda _: None,
	onFailure: Callable[[int], None] = lambda _: None,
) -> None:
	if duration == DurationDefault and ttl is not None:
		duration = DurationShort if ttl <= 7 else DurationLong
	toastEl = doc.select_single_node('/toast')
	_setAttr(doc, toastEl, 'duration', duration)

	notification = ToastNotification(doc)

	if ttl is not None:
		notification.expiration_time = datetime.now(timezone.utc) + timedelta(seconds=ttl)

	if tag is not None:
		notification.tag = tag
	if group is not None:
		notification.group = group

	if suppressPopup:
		notification.suppress_popup = True

	notifier = ToastNotificationManager.create_toast_notifier_with_id(registerApplication(appName))

	event = threading.Event()
	resultHolder: dict[str, Any] = {}

	def _onActivated(*a: Any) -> None:
		e = ToastActivatedEventArgs._from(a[1])  # type: ignore[attr-defined]
		userInput: dict[str, str] = {}
		for name in e.user_input:
			userInput[name] = IPropertyValue._from(e.user_input[name]).get_string()  # type: ignore[attr-defined]
		resultHolder['click'] = {'arguments': e.arguments, 'userInput': userInput}
		event.set()

	def _onDismissed(*a: Any) -> None:
		e = ToastDismissedEventArgs._from(a[1])  # type: ignore[attr-defined]
		resultHolder['dismiss'] = e.reason
		event.set()

	def _onFailed(*a: Any) -> None:
		e = ToastFailedEventArgs._from(a[1])  # type: ignore[attr-defined]
		resultHolder['fail'] = e.error_code
		event.set()

	ta = notification.add_activated(_onActivated)
	td = notification.add_dismissed(_onDismissed)
	tf = notification.add_failed(_onFailed)

	try:
		notifier.show(notification)
		deadline = time.time() + (ttl or 30) + 5
		while not event.is_set() and time.time() < deadline:
			pythoncom.PumpWaitingMessages()

		if 'click' in resultHolder:
			onClick(resultHolder['click'])
		elif 'dismiss' in resultHolder:
			reason = resultHolder['dismiss']
			if reason == ToastDismissalReason.APPLICATION_HIDDEN:
				onFailure(reason.value)
			else:
				onDismiss(reason)
		elif 'fail' in resultHolder:
			onFailure(resultHolder['fail'])
		else:
			onDismiss(ToastDismissalReason.TIMED_OUT)
	finally:
		notification.remove_activated(ta)
		notification.remove_dismissed(td)
		notification.remove_failed(tf)


def showNotify(
	appName: str,
	title: str,
	content: str,
	*,
	icon: Path | None = None,
	heroImage: Path | None = None,
	duration: str = DurationDefault,
	ttl: int | None = None,
	scenario: str | None = None,
	tag: str | None = None,
	group: str | None = None,
	silent: bool = False,
	launch: str | None = None,
	activationType: str | None = None,
	actions: list[dict[str, str]] | None = None,
	inputs: list[dict[str, str]] | None = None,
	audioSrc: str | None = None,
	audioSilent: bool = False,
	audioLoop: bool = False,
	onClick: Callable[[dict[str, Any]], None] = lambda _: None,
	onDismiss: Callable[[ToastDismissalReason], None] = lambda _: None,
	onFailure: Callable[[int], None] = lambda _: None,
) -> None:
	doc = _buildXml(
		title,
		content,
		icon=icon,
		heroImage=heroImage,
		scenario=scenario,
		activationType=activationType,
		launch=launch,
		actions=actions,
		inputs=inputs,
		audioSrc=audioSrc,
		audioSilent=audioSilent,
		audioLoop=audioLoop,
	)
	_show(
		doc,
		appName,
		duration=duration,
		ttl=ttl,
		tag=tag,
		group=group,
		suppressPopup=silent,
		onClick=onClick,
		onDismiss=onDismiss,
		onFailure=onFailure,
	)


def sendInput(
	appName: str,
	sender: str,
	messageContent: str,
	callback: Callable[[str], None],
	*,
	placeholder: str = 'message...',
	ttl: int = 25,
) -> str | ToastDismissalReason:
	result: dict[str, str | ToastDismissalReason] = {}

	def handleClick(data: dict[str, Any]):
		text = data['userInput'].get('message', '')
		result['value'] = text
		callback(text)

	def handleDismiss(reason: ToastDismissalReason):
		result['reason'] = reason

	showNotify(
		appName,
		sender,
		messageContent,
		ttl=ttl,
		activationType=ActivationBackground,
		inputs=[{'id': 'message', 'type': 'text', 'placeholder': placeholder}],
		actions=[{'content': 'Send', 'arguments': 'send', 'activationType': ActivationBackground, 'hintInputId': 'message'}],
		onClick=handleClick,
		onDismiss=handleDismiss,
	)
	return result.get('value', result.get('reason'))
