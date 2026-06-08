try:
    from .toastlib.toastlib import (
        registerApplication,
        sendInput,
        showNotify,
        DurationDefault,
        DurationShort,
        DurationLong,
        ScenarioDefault,
        ScenarioReminder,
        ScenarioAlarm,
        ScenarioIncomingCall,
        ActivationForeground,
        ActivationBackground,
        ActivationProtocol,
        DismissUser,
        DismissTimeout,
        DismissApp,
    )
except ImportError:
    # toastlib requires pywin32 + winrt; winrt has no Python 3.14 wheel yet.
    # Fall back to stubs so the server can still start.
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

    DismissUser = 0
    DismissTimeout = 1
    DismissApp = 2

    def registerApplication(appName: str) -> str:  # noqa: ARG001
        return f'Chitrika.{appName}'

    def sendInput(appName: str, sender: str, messageContent: str, callback, **kw):  # noqa: ARG001
        return None

    def showNotify(appName: str, title: str, content: str, **kw):  # noqa: ARG001
        pass
